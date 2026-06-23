from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from time import perf_counter
from typing import Any, Protocol
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.agent.orchestration import CoordinatorAgent, SafetyDecision
from app.ai.schemas import ChatTurn
from app.ai.search_worker.grounding import sanitize_source_uri
from app.authorization.policy import PolicyResult, evaluate_required_scopes
from app.authorization.principal import AuthenticatedPrincipal
from app.core.config import Settings
from app.db.repositories.agent_settings import AgentRuntimeSettingsRepository
from app.db.repositories.conversations import ConversationsRepository
from app.models.domain import (
    Message,
    SEARCH_METADATA_ALLOWED_CITATION_KEYS,
    SEARCH_METADATA_ALLOWED_ROOT_KEYS,
    SEARCH_METADATA_ALLOWED_SOURCE_KEYS,
    SEARCH_METADATA_ALLOWED_SUGGESTION_KEYS,
    ToolExecution,
)
from app.schemas.chat import MessageResponse, SubmitTurnRequest, SubmitTurnResponse, ToolExecutionResponse
from app.schemas.search import (
    SEARCH_DENIED_COPY,
    SEARCH_PROVIDER_FAILED_COPY,
    SEARCH_TIMEOUT_COPY,
    SEARCH_UNAVAILABLE_COPY,
    SearchTurnResult,
    SearchWorkerResult,
)
from app.security.search_capability import mint_search_capability


DIRECT_CHAT_PLACEHOLDER = "Lượt trò chuyện bình thường chưa được triển khai trong nhánh hiện tại."

TOOL_STATUS_BY_STATE = {
    "grounded": "succeeded",
    "missing_grounding": "succeeded",
    "denied": "denied",
    "search_unavailable": "failed",
    "provider_failed": "failed",
    "timeout": "timed_out",
}
RETRYABLE_SEARCH_STATES = {"search_unavailable", "provider_failed", "timeout"}
SEARCH_READY_STATES = {"ready"}


class SearchWorker(Protocol):
    async def run(
        self,
        *,
        user_id: str,
        conversation_id: str,
        prompt: str,
        correlation_id: str | None,
        capability_token: str | None = None,
    ) -> SearchWorkerResult: ...


class ConversationTurnForbidden(ValueError):
    pass


class ConversationTurnNotFound(ValueError):
    pass


@dataclass(slots=True)
class SearchTurnOutcome:
    assistant_content: str
    search: SearchTurnResult
    persisted_search_metadata: dict[str, Any]
    tool_status: str
    output_summary: str | None
    duration_ms: int


@dataclass(slots=True)
class RetryTarget:
    user_message: Message
    assistant_message: Message


def allowlist_search_metadata(payload: dict[str, Any]) -> dict[str, Any]:
    filtered: dict[str, Any] = {}
    for key, value in payload.items():
        if key not in SEARCH_METADATA_ALLOWED_ROOT_KEYS:
            continue
        if key == "sources" and isinstance(value, list):
            filtered[key] = [
                {
                    source_key: source[source_key]
                    for source_key in SEARCH_METADATA_ALLOWED_SOURCE_KEYS
                    if source_key in source
                }
                for source in value
                if isinstance(source, dict)
            ]
            for source in filtered[key]:
                if "uri" not in source:
                    continue
                sanitized_uri = sanitize_source_uri(source.get("uri"))
                if sanitized_uri:
                    source["uri"] = sanitized_uri
                else:
                    source.pop("uri", None)
            continue
        if key == "citations" and isinstance(value, list):
            filtered[key] = [
                {
                    citation_key: citation[citation_key]
                    for citation_key in SEARCH_METADATA_ALLOWED_CITATION_KEYS
                    if citation_key in citation
                }
                for citation in value
                if isinstance(citation, dict)
            ]
            continue
        if key == "suggestions" and isinstance(value, dict):
            filtered[key] = {
                suggestion_key: value[suggestion_key]
                for suggestion_key in SEARCH_METADATA_ALLOWED_SUGGESTION_KEYS
                if suggestion_key in value
            }
            continue
        filtered[key] = value
    return filtered


class ChatTurnsService:
    def __init__(
        self,
        session: AsyncSession,
        *,
        settings: Settings,
        now: datetime,
        correlation_id: str | None,
        search_provider: str,
        search_status: str,
        search_worker: SearchWorker | None,
    ) -> None:
        self.session = session
        self.settings = settings
        self.now = now
        self.correlation_id = correlation_id
        self.search_provider = search_provider if search_provider in {"gemini", "firecrawl"} else "gemini"
        self.search_status = search_status
        self.search_worker = search_worker
        self.conversations = ConversationsRepository(session)
        self.agent_settings = AgentRuntimeSettingsRepository(session)

    async def submit_turn(
        self,
        *,
        principal: AuthenticatedPrincipal,
        conversation_id: UUID,
        payload: SubmitTurnRequest,
    ) -> SubmitTurnResponse:
        chat_policy = evaluate_required_scopes(
            principal_scopes=set(principal.scopes),
            required={"chat:write"},
        )
        if chat_policy is not PolicyResult.allow:
            raise ConversationTurnForbidden("chat_write_required")
        try:
            conversation = await self._get_or_create_owned_conversation(
                principal=principal,
                conversation_id=conversation_id,
                prompt=payload.prompt,
                is_retry=payload.retry_of_message_id is not None,
            )
            retry_target = await self._load_retry_target(
                conversation_id=conversation.id,
                retry_of_message_id=payload.retry_of_message_id,
                mode=payload.mode,
            )

            if retry_target is None:
                user_message = await self._append_user_message(
                    conversation_id=conversation.id,
                    prompt=payload.prompt,
                )
            else:
                user_message = retry_target.user_message

            guardrail_decision = await self._guardrail_decision(prompt=payload.prompt)
            if not guardrail_decision.allowed:
                assistant_message = await self._handle_guardrail_turn(
                    conversation_id=conversation.id,
                    decision=guardrail_decision,
                    retry_target=retry_target,
                )
                tool_execution = await self.conversations.add_tool_execution(
                    user_id=principal.user_id,
                    conversation_id=conversation.id,
                    tool_name="guardrail",
                    input_summary=payload.prompt[: self.settings.search_max_prompt_chars],
                    output_summary=guardrail_decision.reason or "guardrail_policy_denied",
                    status="denied",
                    duration_ms=0,
                    correlation_id=self.correlation_id,
                )
                response = SubmitTurnResponse(
                    conversation_id=conversation.id,
                    mode=payload.mode,
                    user_message=self._message_response(user_message),
                    assistant_message=self._message_response(assistant_message),
                    tool_execution=self._tool_execution_response(tool_execution),
                )
                await self.session.commit()
                return response

            if payload.mode == "direct_chat":
                if retry_target is not None:
                    raise ConversationTurnNotFound("retry_not_supported_for_direct_chat")

                assistant_message = await self._append_direct_chat_placeholder(
                    conversation_id=conversation.id,
                )
                response = SubmitTurnResponse(
                    conversation_id=conversation.id,
                    mode=payload.mode,
                    user_message=self._message_response(user_message),
                    assistant_message=self._message_response(assistant_message),
                    tool_execution=None,
                )
                await self.session.commit()
                return response

            search_outcome = await self._handle_search_turn(
                principal=principal,
                conversation_id=conversation.id,
                prompt=payload.prompt,
                retry_target=retry_target,
            )

            if retry_target is None:
                assistant_message = await self._append_search_message(
                    conversation_id=conversation.id,
                    content=search_outcome.assistant_content,
                    persisted_search_metadata=search_outcome.persisted_search_metadata,
                )
            else:
                assistant_message = await self._update_search_message(
                    message=retry_target.assistant_message,
                    content=search_outcome.assistant_content,
                    persisted_search_metadata=search_outcome.persisted_search_metadata,
                )

            tool_execution = await self.conversations.add_tool_execution(
                user_id=principal.user_id,
                conversation_id=conversation.id,
                tool_name="google_search",
                input_summary=payload.prompt[: self.settings.search_max_prompt_chars],
                output_summary=search_outcome.output_summary,
                status=search_outcome.tool_status,
                duration_ms=search_outcome.duration_ms,
                correlation_id=self.correlation_id,
            )
            response = SubmitTurnResponse(
                conversation_id=conversation.id,
                mode=payload.mode,
                user_message=self._message_response(user_message),
                assistant_message=self._message_response(assistant_message, search_outcome.search),
                tool_execution=self._tool_execution_response(tool_execution),
            )
            await self.session.commit()
            return response
        except Exception:
            if self.session.in_transaction():
                await self.session.rollback()
            raise

    async def _get_or_create_owned_conversation(
        self,
        *,
        principal: AuthenticatedPrincipal,
        conversation_id: UUID,
        prompt: str,
        is_retry: bool,
    ):
        conversation = await self.conversations.get_conversation_for_update(
            conversation_id=conversation_id,
        )
        if conversation is None:
            if is_retry:
                raise ConversationTurnNotFound("conversation_not_found")
            return await self.conversations.create_conversation(
                conversation_id=conversation_id,
                user_id=principal.user_id,
                title=self._derive_conversation_title(prompt),
            )

        if conversation.deleted_at is not None or conversation.user_id != principal.user_id:
            raise ConversationTurnNotFound("conversation_not_found")
        return conversation

    async def _load_retry_target(
        self,
        *,
        conversation_id: UUID,
        retry_of_message_id: UUID | None,
        mode: str,
    ) -> RetryTarget | None:
        if retry_of_message_id is None:
            return None
        if mode != "google_search":
            raise ConversationTurnNotFound("retry_not_supported_for_mode")

        assistant_message = await self.conversations.get_message_for_update(
            conversation_id=conversation_id,
            message_id=retry_of_message_id,
        )
        if assistant_message is None or assistant_message.role != "assistant":
            raise ConversationTurnNotFound("retry_target_not_found")

        search_metadata = assistant_message.message_metadata.get("search", {})
        if not isinstance(search_metadata, dict):
            raise ConversationTurnNotFound("retry_target_not_search")
        state = search_metadata.get("state")
        if state not in RETRYABLE_SEARCH_STATES:
            raise ConversationTurnNotFound("retry_target_not_retryable")

        previous_user = await self.conversations.get_message_by_sequence_no(
            conversation_id=conversation_id,
            sequence_no=assistant_message.sequence_no - 1,
        )
        if previous_user is None or previous_user.role != "user":
            raise ConversationTurnNotFound("retry_parent_user_not_found")

        return RetryTarget(
            user_message=previous_user,
            assistant_message=assistant_message,
        )

    async def _append_user_message(self, *, conversation_id: UUID, prompt: str) -> Message:
        sequence_no = await self.conversations.next_sequence_no(conversation_id=conversation_id)
        return await self.conversations.add_message(
            conversation_id=conversation_id,
            sequence_no=sequence_no,
            role="user",
            content=prompt,
            metadata={},
        )

    async def _append_direct_chat_placeholder(self, *, conversation_id: UUID) -> Message:
        sequence_no = await self.conversations.next_sequence_no(conversation_id=conversation_id)
        return await self.conversations.add_message(
            conversation_id=conversation_id,
            sequence_no=sequence_no,
            role="assistant",
            content=DIRECT_CHAT_PLACEHOLDER,
            metadata={},
        )

    async def _handle_guardrail_turn(
        self,
        *,
        conversation_id: UUID,
        decision: SafetyDecision,
        retry_target: RetryTarget | None,
    ) -> Message:
        metadata = {
            "guardrail": {
                "enabled": decision.enabled,
                "allowed": decision.allowed,
                "reason": decision.reason,
            }
        }
        content = decision.response or "Yêu cầu này bị chặn bởi Guardrail/Safety Agent."
        if retry_target is not None:
            return await self.conversations.update_message(
                retry_target.assistant_message,
                content=content,
                metadata=metadata,
            )
        sequence_no = await self.conversations.next_sequence_no(conversation_id=conversation_id)
        return await self.conversations.add_message(
            conversation_id=conversation_id,
            sequence_no=sequence_no,
            role="assistant",
            content=content,
            metadata=metadata,
        )

    async def _append_search_message(
        self,
        *,
        conversation_id: UUID,
        content: str,
        persisted_search_metadata: dict[str, Any],
    ) -> Message:
        sequence_no = await self.conversations.next_sequence_no(conversation_id=conversation_id)
        return await self.conversations.add_message(
            conversation_id=conversation_id,
            sequence_no=sequence_no,
            role="assistant",
            content=content,
            metadata={"search": persisted_search_metadata},
        )

    async def _update_search_message(
        self,
        *,
        message: Message,
        content: str,
        persisted_search_metadata: dict[str, Any],
    ) -> Message:
        return await self.conversations.update_message(
            message,
            content=content,
            metadata={"search": persisted_search_metadata},
        )

    async def _handle_search_turn(
        self,
        *,
        principal: AuthenticatedPrincipal,
        conversation_id: UUID,
        prompt: str,
        retry_target: RetryTarget | None,
    ) -> SearchTurnOutcome:
        started_at = perf_counter()
        search_policy = evaluate_required_scopes(
            principal_scopes=set(principal.scopes),
            required={"tool:websearch"},
        )
        if search_policy is not PolicyResult.allow:
            search = self._search_result(
                state="denied",
                provider=self.search_provider,
                tool_executed=False,
                retry_of_message_id=retry_target.assistant_message.id if retry_target else None,
            )
            metadata = self._build_persisted_search_metadata(
                search=search,
                lifecycle=self._build_lifecycle(
                    final_event="denied",
                    response_state="denied",
                    started=False,
                    previous=retry_target.assistant_message.message_metadata.get("search", {})
                    if retry_target
                    else None,
                ),
            )
            return SearchTurnOutcome(
                assistant_content=SEARCH_DENIED_COPY,
                search=search,
                persisted_search_metadata=metadata,
                tool_status=TOOL_STATUS_BY_STATE["denied"],
                output_summary="denied",
                duration_ms=0,
            )

        if self.search_status not in SEARCH_READY_STATES or self.search_worker is None:
            search = self._search_result(
                state="search_unavailable",
                provider=self.search_provider,
                tool_executed=False,
                retry_of_message_id=retry_target.assistant_message.id if retry_target else None,
            )
            metadata = self._build_persisted_search_metadata(
                search=search,
                lifecycle=self._build_lifecycle(
                    final_event="failed",
                    response_state="search_unavailable",
                    started=False,
                    previous=retry_target.assistant_message.message_metadata.get("search", {})
                    if retry_target
                    else None,
                ),
            )
            return SearchTurnOutcome(
                assistant_content=SEARCH_UNAVAILABLE_COPY,
                search=search,
                persisted_search_metadata=metadata,
                tool_status=TOOL_STATUS_BY_STATE["search_unavailable"],
                output_summary="search_unavailable",
                duration_ms=0,
            )

        capability_token = mint_search_capability(
            user_id=principal.user_id,
            conversation_id=conversation_id,
            correlation_id=self.correlation_id,
            settings=self.settings,
            now=self.now,
        )
        worker_result = await self.search_worker.run(
            user_id=str(principal.user_id),
            conversation_id=str(conversation_id),
            prompt=prompt,
            correlation_id=self.correlation_id,
            capability_token=capability_token,
        )
        normalized = self._normalize_worker_result(worker_result)
        duration_ms = max(0, int((perf_counter() - started_at) * 1000))
        search = self._search_result(
            state=normalized.state,
            provider=normalized.provider,
            google_grounded=normalized.google_grounded,
            tool_executed=normalized.tool_executed,
            retry_of_message_id=retry_target.assistant_message.id if retry_target else None,
            sources=normalized.sources,
            citations=normalized.citations,
            suggestions=normalized.suggestions,
        )
        metadata = self._build_persisted_search_metadata(
            search=search,
            lifecycle=self._build_lifecycle(
                final_event=TOOL_STATUS_BY_STATE[normalized.state],
                response_state=normalized.state,
                started=True,
                previous=retry_target.assistant_message.message_metadata.get("search", {})
                if retry_target
                else None,
            ),
            web_search_queries=normalized.web_search_queries,
        )
        return SearchTurnOutcome(
            assistant_content=normalized.answer_markdown,
            search=search,
            persisted_search_metadata=metadata,
            tool_status=TOOL_STATUS_BY_STATE[normalized.state],
            output_summary=normalized.output_summary or normalized.state,
            duration_ms=duration_ms,
        )

    async def _guardrail_decision(self, *, prompt: str) -> SafetyDecision:
        enabled = await self.agent_settings.is_guardrail_enabled(
            default=self.settings.guardrail_safety_enabled_default,
        )
        orchestration = CoordinatorAgent(
            guardrail_enabled=enabled,
            max_loop_iterations=self.settings.agent_loop_max_iterations,
        )
        orchestration.trace.add("CoordinatorAgent", "receive", "accepted")
        return await orchestration.guardrail.check(
            prompt=prompt,
            messages=[ChatTurn(role="user", content=prompt)],
        )

    def _normalize_worker_result(self, result: SearchWorkerResult) -> SearchWorkerResult:
        if result.state == "grounded":
            if (result.provider == "gemini" and not result.google_grounded) or not result.sources or not result.citations:
                return SearchWorkerResult(
                    provider=result.provider,
                    state="missing_grounding",
                    answer_markdown=result.answer_markdown,
                    google_grounded=False,
                    tool_executed=result.tool_executed,
                    web_search_queries=result.web_search_queries,
                    output_summary=result.output_summary or "missing_grounding",
                )
            return result

        if result.state == "missing_grounding":
            return SearchWorkerResult(
                provider=result.provider,
                state="missing_grounding",
                answer_markdown=result.answer_markdown,
                google_grounded=False,
                tool_executed=result.tool_executed,
                web_search_queries=result.web_search_queries,
                output_summary=result.output_summary or "missing_grounding",
            )

        if result.state == "provider_failed":
            return SearchWorkerResult(
                provider=result.provider,
                state="provider_failed",
                answer_markdown=result.answer_markdown or SEARCH_PROVIDER_FAILED_COPY,
                google_grounded=False,
                tool_executed=result.tool_executed,
                web_search_queries=result.web_search_queries,
                output_summary=result.output_summary or "provider_failed",
            )

        if result.state == "timeout":
            return SearchWorkerResult(
                provider=result.provider,
                state="timeout",
                answer_markdown=result.answer_markdown or SEARCH_TIMEOUT_COPY,
                google_grounded=False,
                tool_executed=result.tool_executed,
                web_search_queries=result.web_search_queries,
                output_summary=result.output_summary or "timeout",
            )

        if result.state == "search_unavailable":
            return SearchWorkerResult(
                provider=result.provider,
                state="search_unavailable",
                answer_markdown=result.answer_markdown or SEARCH_UNAVAILABLE_COPY,
                google_grounded=False,
                tool_executed=False,
                web_search_queries=[],
                output_summary=result.output_summary or "search_unavailable",
            )

        return result

    def _search_result(
        self,
        *,
        state: str,
        provider: str,
        tool_executed: bool,
        retry_of_message_id: UUID | None,
        google_grounded: bool = False,
        sources: list | None = None,
        citations: list | None = None,
        suggestions=None,
    ) -> SearchTurnResult:
        return SearchTurnResult(
            provider=provider if provider in {"gemini", "firecrawl"} else "gemini",
            state=state,
            google_grounded=google_grounded,
            tool_executed=tool_executed,
            correlation_id=self.correlation_id,
            sources=sources or [],
            citations=citations or [],
            suggestions=suggestions,
            retry_of_message_id=retry_of_message_id,
        )

    def _build_lifecycle(
        self,
        *,
        final_event: str,
        response_state: str,
        started: bool,
        previous: dict[str, Any] | None,
    ) -> list[dict[str, Any]]:
        existing = []
        if isinstance(previous, dict):
            raw_existing = previous.get("lifecycle", [])
            if isinstance(raw_existing, list):
                existing = [item for item in raw_existing if isinstance(item, dict)]

        lifecycle = [*existing, self._lifecycle_event("requested", response_state)]
        if started:
            lifecycle.append(self._lifecycle_event("started", response_state))
        lifecycle.append(self._lifecycle_event(final_event, response_state))
        return lifecycle

    def _lifecycle_event(self, event: str, response_state: str) -> dict[str, Any]:
        return {
            "event": event,
            "response_state": response_state,
            "at": self.now.isoformat(),
            "correlation_id": self.correlation_id,
        }

    def _build_persisted_search_metadata(
        self,
        *,
        search: SearchTurnResult,
        lifecycle: list[dict[str, Any]],
        web_search_queries: list[str] | None = None,
    ) -> dict[str, Any]:
        payload = search.model_dump(mode="json", exclude_none=True)
        payload["lifecycle"] = lifecycle
        if web_search_queries:
            payload["web_search_queries"] = web_search_queries[:5]
        return allowlist_search_metadata(payload)

    def _derive_conversation_title(self, prompt: str) -> str:
        normalized = " ".join(prompt.strip().split())
        return (normalized or "Cuộc trò chuyện mới")[:80]

    def _message_response(self, message: Message, search: SearchTurnResult | None = None) -> MessageResponse:
        return MessageResponse(
            id=message.id,
            conversation_id=message.conversation_id,
            sequence_no=message.sequence_no,
            role=message.role,
            content=message.content,
            created_at=message.created_at,
            search=search,
        )

    def _tool_execution_response(self, execution: ToolExecution) -> ToolExecutionResponse:
        return ToolExecutionResponse(
            id=execution.id,
            tool_name=execution.tool_name,
            status=execution.status,
            correlation_id=execution.correlation_id,
            duration_ms=execution.duration_ms,
        )

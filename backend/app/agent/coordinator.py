from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from time import perf_counter
from typing import Any, Literal, Protocol
from uuid import UUID, uuid4

from sqlalchemy.ext.asyncio import AsyncSession

from app.agent.decisions import OpenAIPythonPlanner, PythonToolPlan
from app.agent.orchestration import CoordinatorAgent, OrchestrationTrace
from app.agent.policy import (
    build_denied_result,
    collapse_text,
    prompt_requests_python,
    prompt_requests_search,
    prompt_requires_external_search,
    python_scope_allowed,
    select_python_profile,
    tool_execution_output_summary,
    tool_execution_terminal_status,
)
from app.ai.search_worker.service import build_search_worker_service
from app.ai.chat_adapter import ChatProviderError
from app.ai.schemas import ChatCompletionResult, ChatTurn
from app.authorization.policy import PolicyResult, Scope, evaluate_required_scopes
from app.db.repositories.agent_settings import AgentRuntimeSettingsRepository
from app.core.provider_status import resolve_search_provider, search_status as resolve_search_status
from app.models.domain import ToolExecution
from app.python_contract import PythonDeniedReason, PythonExecutionProfile, PythonExecutionStatus
from app.schemas.python import PythonExecutionResult
from app.schemas.search import (
    SEARCH_DENIED_COPY,
    SEARCH_PROVIDER_FAILED_COPY,
    SEARCH_TIMEOUT_COPY,
    SEARCH_UNAVAILABLE_COPY,
    SearchTurnResult,
    SearchWorkerResult,
)
from app.security.search_capability import mint_search_capability
from app.security.tool_capabilities import issue_python_capability
from app.services.python_sessions import PythonSessionsService
from app.tools.python_client import PythonClient, PythonExecutionInvocation, PythonExecutionResponse


TOOL_STATUS_BY_SEARCH_STATE = {
    "grounded": "succeeded",
    "missing_grounding": "succeeded",
    "denied": "denied",
    "search_unavailable": "failed",
    "provider_failed": "failed",
    "timeout": "timed_out",
}
SEARCH_READY_STATES = {"ready"}
SUMMARIZABLE_SEARCH_STATES = {"grounded", "missing_grounding"}
SUMMARIZABLE_PYTHON_STATUSES = {
    PythonExecutionStatus.succeeded,
    PythonExecutionStatus.failed,
    PythonExecutionStatus.limit_reached,
}
RequestedTool = Literal["google_search", "python"]


class ChatAdapterLike(Protocol):
    async def complete(self, *, messages: list[ChatTurn]) -> ChatCompletionResult: ...


class PythonPlannerLike(Protocol):
    async def plan(
        self,
        *,
        messages: list[ChatTurn],
        prompt: str,
        state_binding_names: tuple[str, ...],
    ) -> PythonToolPlan: ...


class PythonClientLike(Protocol):
    async def execute(self, invocation: PythonExecutionInvocation) -> PythonExecutionResponse: ...


class SearchWorkerLike(Protocol):
    async def run(
        self,
        *,
        user_id: str,
        conversation_id: str,
        prompt: str,
        correlation_id: str | None,
        capability_token: str | None = None,
    ) -> SearchWorkerResult: ...


@dataclass(frozen=True, slots=True)
class CoordinatedAssistantTurn:
    content: str
    metadata: dict[str, Any]


class ChatCoordinator:
    def __init__(
        self,
        session: AsyncSession,
        *,
        settings,
        clock,
        principal_scopes: set[str],
        chat_adapter_factory,
        python_planner: PythonPlannerLike | None = None,
        python_client: PythonClientLike | None = None,
        search_worker: SearchWorkerLike | None = None,
        search_provider: str = "gemini",
        search_status: str = "unconfigured",
        search_runtime_worker_factory=None,
        guardrail_enabled: bool | None = None,
        agent_settings: AgentRuntimeSettingsRepository | None = None,
    ) -> None:
        self.session = session
        self.settings = settings
        self.clock = clock
        self.principal_scopes = set(principal_scopes)
        self.chat_adapter_factory = chat_adapter_factory
        self._python_planner = python_planner
        self._python_client = python_client
        self.search_worker = search_worker
        self.search_provider = search_provider if search_provider in {"gemini", "firecrawl"} else "gemini"
        self._startup_search_provider = self.search_provider
        self.search_status = search_status
        self.search_runtime_worker_factory = search_runtime_worker_factory
        self._guardrail_enabled = guardrail_enabled
        self.agent_settings = agent_settings or AgentRuntimeSettingsRepository(session)
        self.python_sessions = PythonSessionsService(session, settings=settings, clock=clock)

    async def complete(
        self,
        *,
        user_id: UUID,
        conversation_id: UUID,
        messages: list[ChatTurn],
        correlation_id: str | None,
        requested_tool: RequestedTool | None = None,
    ) -> CoordinatedAssistantTurn:
        prompt = messages[-1].content if messages else ""
        orchestration = CoordinatorAgent(
            guardrail_enabled=await self._resolve_guardrail_enabled(),
            max_loop_iterations=self.settings.agent_loop_max_iterations,
        )
        trace = orchestration.trace
        trace.add("CoordinatorAgent", "receive", "accepted")

        decision = await orchestration.guardrail.check(prompt=prompt, messages=messages)
        if not decision.allowed:
            trace.add("GuardrailSafetyAgent", "check", "denied", decision.reason)
            trace.add("ReportWriterAgent", "write", "completed")
            return CoordinatedAssistantTurn(
                content=decision.response
                or "Yêu cầu này bị chặn bởi Guardrail/Safety Agent.",
                metadata=orchestration.report_writer.blocked_response_metadata(
                    trace=trace,
                    decision=decision,
                ),
            )
        trace.add(
            "GuardrailSafetyAgent",
            "check",
            "disabled" if not decision.enabled else "allowed",
        )

        if requested_tool == "google_search":
            trace.add("CoordinatorAgent", "route", "google_search", "explicit")
            trace.add("WebSearchAgent", "selected", "ready")
            trace.add("LoopAgent", "iterate", "started", f"max={orchestration.loop.max_iterations}")
            return await self._complete_search(
                user_id=user_id,
                conversation_id=conversation_id,
                prompt=prompt,
                correlation_id=correlation_id,
                trace=trace,
            )

        if requested_tool == "python":
            trace.add("CoordinatorAgent", "route", "python", "explicit")
            trace.add("CodeSandboxAgent", "selected", "ready")
            trace.add("LoopAgent", "iterate", "started", f"max={orchestration.loop.max_iterations}")
            return await self._complete_python(
                user_id=user_id,
                conversation_id=conversation_id,
                messages=messages,
                prompt=prompt,
                correlation_id=correlation_id,
                trace=trace,
            )

        if prompt_requests_search(prompt):
            trace.add("CoordinatorAgent", "route", "google_search")
            trace.add("WebSearchAgent", "selected", "ready")
            trace.add("LoopAgent", "iterate", "started", f"max={orchestration.loop.max_iterations}")
            return await self._complete_search(
                user_id=user_id,
                conversation_id=conversation_id,
                prompt=prompt,
                correlation_id=correlation_id,
                trace=trace,
            )

        if prompt_requests_python(prompt):
            trace.add("CoordinatorAgent", "route", "python")
            trace.add("CodeSandboxAgent", "selected", "ready")
            trace.add("LoopAgent", "iterate", "started", f"max={orchestration.loop.max_iterations}")
            return await self._complete_python(
                user_id=user_id,
                conversation_id=conversation_id,
                messages=messages,
                prompt=prompt,
                correlation_id=correlation_id,
                trace=trace,
            )

        return await self._complete_direct(messages=messages, trace=trace)

    @property
    def python_planner(self) -> PythonPlannerLike:
        if self._python_planner is None:
            self._python_planner = OpenAIPythonPlanner(settings=self.settings)
        return self._python_planner

    @property
    def python_client(self) -> PythonClientLike:
        if self._python_client is None:
            self._python_client = PythonClient(settings=self.settings)
        return self._python_client

    async def _resolve_guardrail_enabled(self) -> bool:
        if self._guardrail_enabled is not None:
            return self._guardrail_enabled
        return await self.agent_settings.is_guardrail_enabled(
            default=self.settings.guardrail_safety_enabled_default,
        )

    async def _complete_direct(
        self,
        *,
        messages: list[ChatTurn],
        trace: OrchestrationTrace,
    ) -> CoordinatedAssistantTurn:
        trace.add("CoordinatorAgent", "route", "direct_chat")
        adapter = (
            self.chat_adapter_factory()
            if callable(self.chat_adapter_factory)
            else self.chat_adapter_factory
        )
        result = await adapter.complete(messages=messages)
        trace.add("ReportWriterAgent", "write", "completed")
        metadata = {
            "provider_request_id": result.provider_request_id,
            "prompt_tokens": result.prompt_tokens,
            "completion_tokens": result.completion_tokens,
            "finish_reason": result.finish_reason,
            "orchestration": trace.as_metadata(),
        }
        return CoordinatedAssistantTurn(content=result.content, metadata=metadata)

    async def _complete_search(
        self,
        *,
        user_id: UUID,
        conversation_id: UUID,
        prompt: str,
        correlation_id: str | None,
        trace: OrchestrationTrace,
    ) -> CoordinatedAssistantTurn:
        await self._refresh_search_runtime()
        started_at = perf_counter()
        if not self._search_scope_allowed():
            trace.add("WebSearchAgent", "authorize", "denied", "missing tool:websearch")
            search = SearchTurnResult(
                provider=self.search_provider,
                state="denied",
                google_grounded=False,
                tool_executed=False,
                correlation_id=correlation_id,
            )
            await self._record_search_tool_execution(
                user_id=user_id,
                conversation_id=conversation_id,
                prompt=prompt,
                status=TOOL_STATUS_BY_SEARCH_STATE["denied"],
                output_summary="denied",
                duration_ms=0,
                correlation_id=correlation_id,
            )
            trace.add("ReportWriterAgent", "write", "completed", "denied")
            return _search_assistant_turn(
                content=SEARCH_DENIED_COPY,
                search=search,
                worker_result=None,
                trace=trace,
            )

        if self.search_status not in SEARCH_READY_STATES or self.search_worker is None:
            trace.add("WebSearchAgent", "execute", "failed", "search_unavailable")
            search = SearchTurnResult(
                provider=self.search_provider,
                state="search_unavailable",
                google_grounded=False,
                tool_executed=False,
                correlation_id=correlation_id,
            )
            await self._record_search_tool_execution(
                user_id=user_id,
                conversation_id=conversation_id,
                prompt=prompt,
                status=TOOL_STATUS_BY_SEARCH_STATE["search_unavailable"],
                output_summary="search_unavailable",
                duration_ms=0,
                correlation_id=correlation_id,
            )
            trace.add("ReportWriterAgent", "write", "completed", "search_unavailable")
            return _search_assistant_turn(
                content=SEARCH_UNAVAILABLE_COPY,
                search=search,
                worker_result=None,
                trace=trace,
            )

        capability_token = mint_search_capability(
            user_id=user_id,
            conversation_id=conversation_id,
            correlation_id=correlation_id,
            settings=self.settings,
            now=self._current_datetime(),
        )
        worker_result = await self.search_worker.run(
            user_id=str(user_id),
            conversation_id=str(conversation_id),
            prompt=prompt,
            correlation_id=correlation_id,
            capability_token=capability_token,
        )
        normalized = _normalize_search_result(worker_result)
        duration_ms = max(0, int((perf_counter() - started_at) * 1000))
        tool_status = TOOL_STATUS_BY_SEARCH_STATE[normalized.state]
        trace.add("WebSearchAgent", "execute", tool_status, normalized.state)
        search = SearchTurnResult(
            provider=normalized.provider,
            state=normalized.state,
            google_grounded=normalized.google_grounded,
            tool_executed=normalized.tool_executed,
            correlation_id=correlation_id,
            sources=normalized.sources,
            citations=normalized.citations,
            suggestions=normalized.suggestions,
        )
        await self._record_search_tool_execution(
            user_id=user_id,
            conversation_id=conversation_id,
            prompt=prompt,
            status=tool_status,
            output_summary=normalized.output_summary or normalized.state,
            duration_ms=duration_ms,
            correlation_id=correlation_id,
        )
        content = normalized.answer_markdown
        report_writer_metadata: dict[str, Any] | None = None
        if normalized.state in SUMMARIZABLE_SEARCH_STATES:
            content, report_writer_metadata = await self._summarize_agent_result(
                agent_name="WebSearchAgent",
                user_prompt=prompt,
                reviewed_output=normalized.answer_markdown,
                trace=trace,
                extra_context=None,
            )
        trace.add("ReportWriterAgent", "write", "completed", normalized.state)
        return _search_assistant_turn(
            content=content,
            search=search,
            worker_result=normalized,
            trace=trace,
            report_writer=report_writer_metadata,
        )

    async def _complete_python(
        self,
        *,
        user_id: UUID,
        conversation_id: UUID,
        messages: list[ChatTurn],
        prompt: str,
        correlation_id: str | None,
        trace: OrchestrationTrace,
    ) -> CoordinatedAssistantTurn:
        if prompt_requires_external_search(prompt):
            denied = await self._record_denied_python_turn(
                user_id=user_id,
                conversation_id=conversation_id,
                prompt=prompt,
                denial_reason=PythonDeniedReason.search_required,
                correlation_id=correlation_id,
            )
            trace.add("CodeSandboxAgent", "authorize", "denied", "search_required")
            trace.add("ReportWriterAgent", "write", "completed", "python_denied")
            return _python_assistant_turn(denied, trace=trace)

        if not python_scope_allowed(self.principal_scopes):
            denied = await self._record_denied_python_turn(
                user_id=user_id,
                conversation_id=conversation_id,
                prompt=prompt,
                denial_reason=PythonDeniedReason.missing_permission,
                correlation_id=correlation_id,
            )
            trace.add("CodeSandboxAgent", "authorize", "denied", "missing tool:python")
            trace.add("ReportWriterAgent", "write", "completed", "python_denied")
            return _python_assistant_turn(denied, trace=trace)

        active_session = await self.python_sessions.get_active_session(
            conversation_id=conversation_id,
            user_id=user_id,
        )
        plan = await self.python_planner.plan(
            messages=messages,
            prompt=prompt,
            state_binding_names=active_session.binding_names if active_session is not None else (),
        )
        trace.add("LoopAgent", "plan", "completed")
        if plan.needs_search or not plan.code:
            denied = await self._record_denied_python_turn(
                user_id=user_id,
                conversation_id=conversation_id,
                prompt=prompt,
                denial_reason=PythonDeniedReason.search_required,
                correlation_id=correlation_id,
            )
            trace.add("CodeSandboxAgent", "authorize", "denied", "planner_needs_search")
            trace.add("ReportWriterAgent", "write", "completed", "python_denied")
            return _python_assistant_turn(denied, trace=trace)

        profile_name = select_python_profile(
            prompt=prompt,
            requested_artifacts=plan.requested_artifacts,
            active_profile=active_session.profile_name if active_session is not None else None,
        )
        execution = ToolExecution(
            id=uuid4(),
            user_id=user_id,
            conversation_id=conversation_id,
            tool_name="python",
            input_summary=collapse_text(prompt),
            output_summary=None,
            status="queued",
            duration_ms=None,
            correlation_id=correlation_id,
        )
        self.session.add(execution)
        await self.session.flush()
        await self.session.commit()

        if not python_scope_allowed(self.principal_scopes):
            denied = build_denied_result(
                execution_id=execution.id,
                reason=PythonDeniedReason.missing_permission,
                correlation_id=correlation_id,
            )
            execution.status = "denied"
            execution.output_summary = tool_execution_output_summary(denied)
            execution.duration_ms = None
            await self.session.commit()
            trace.add("CodeSandboxAgent", "authorize", "denied", "missing tool:python")
            trace.add("ReportWriterAgent", "write", "completed", "python_denied")
            return _python_assistant_turn(denied, trace=trace)

        execution.status = "running"
        await self.session.flush()
        await self.session.commit()

        now = self.clock()
        invocation = PythonExecutionInvocation(
            execution_id=execution.id,
            capability=issue_python_capability(
                execution_id=execution.id,
                profile_name=profile_name,
                code=plan.code,
                settings=self.settings,
                now=now if isinstance(now, datetime) else self._current_datetime(),
                state_snapshot=active_session.snapshot_blob if active_session is not None else None,
            ),
            profile_name=profile_name,
            code=plan.code,
            correlation_id=correlation_id,
            state_snapshot=active_session.snapshot_blob if active_session is not None else None,
        )
        response = await self.python_client.execute(invocation)
        result = await self.python_sessions.persist_execution_response(
            conversation_id=conversation_id,
            user_id=user_id,
            tool_execution_id=execution.id,
            profile_name=profile_name,
            response=response,
        )

        execution.status = tool_execution_terminal_status(result)
        execution.output_summary = tool_execution_output_summary(result)
        execution.duration_ms = result.duration_ms
        await self.session.flush()
        await self.session.commit()
        trace.add("CodeSandboxAgent", "execute", execution.status)
        content = _python_assistant_content(result)
        report_writer_metadata: dict[str, Any] | None = None
        if result.status in SUMMARIZABLE_PYTHON_STATUSES:
            content, report_writer_metadata = await self._summarize_agent_result(
                agent_name="CodeSandboxAgent",
                user_prompt=prompt,
                reviewed_output=content,
                trace=trace,
                extra_context=_python_summary_context(result),
            )
        trace.add("ReportWriterAgent", "write", "completed", execution.status)
        return _python_assistant_turn(
            result,
            content=content,
            trace=trace,
            report_writer=report_writer_metadata,
        )

    async def _record_denied_python_turn(
        self,
        *,
        user_id: UUID,
        conversation_id: UUID,
        prompt: str,
        denial_reason: PythonDeniedReason,
        correlation_id: str | None,
    ) -> PythonExecutionResult:
        execution = ToolExecution(
            id=uuid4(),
            user_id=user_id,
            conversation_id=conversation_id,
            tool_name="python",
            input_summary=collapse_text(prompt),
            output_summary=None,
            status="denied",
            duration_ms=None,
            correlation_id=correlation_id,
        )
        result = build_denied_result(
            execution_id=execution.id,
            reason=denial_reason,
            correlation_id=correlation_id,
        )
        execution.output_summary = tool_execution_output_summary(result)
        self.session.add(execution)
        await self.session.flush()
        await self.session.commit()
        return result

    async def _record_search_tool_execution(
        self,
        *,
        user_id: UUID,
        conversation_id: UUID,
        prompt: str,
        status: str,
        output_summary: str | None,
        duration_ms: int,
        correlation_id: str | None,
    ) -> ToolExecution:
        execution = ToolExecution(
            id=uuid4(),
            user_id=user_id,
            conversation_id=conversation_id,
            tool_name="google_search",
            input_summary=prompt[: self.settings.search_max_prompt_chars],
            output_summary=output_summary,
            status=status,
            duration_ms=duration_ms,
            correlation_id=correlation_id,
        )
        self.session.add(execution)
        await self.session.flush()
        await self.session.commit()
        return execution

    def _search_scope_allowed(self) -> bool:
        result = evaluate_required_scopes(
            principal_scopes=self.principal_scopes,
            required={Scope.tool_websearch.value},
        )
        return result is PolicyResult.allow

    async def _refresh_search_runtime(self) -> None:
        provider_override = await self.agent_settings.get_websearch_provider_override()
        if (
            provider_override is None
            and self.search_worker is not None
            and self.search_status in SEARCH_READY_STATES
            and self.search_provider in {"gemini", "firecrawl"}
        ):
            return

        resolved_provider = resolve_search_provider(self.settings, runtime_override=provider_override)
        if resolved_provider is None:
            self.search_status = "invalid_provider"
            self.search_worker = None
            return

        self.search_provider = resolved_provider
        self.search_status = resolve_search_status(self.settings, runtime_override=provider_override)
        if self.search_status not in SEARCH_READY_STATES:
            self.search_worker = None
            return

        if callable(self.search_runtime_worker_factory):
            self.search_worker = self.search_runtime_worker_factory(resolved_provider, self.settings)
            return
        if resolved_provider == self._startup_search_provider and self.search_worker is not None:
            return
        self.search_worker = build_search_worker_service(
            self.settings,
            runtime_override=resolved_provider,
        )

    def _current_datetime(self) -> datetime:
        now = self.clock()
        return now if isinstance(now, datetime) else self.settings.now_utc()

    async def _summarize_agent_result(
        self,
        *,
        agent_name: str,
        user_prompt: str,
        reviewed_output: str,
        trace: OrchestrationTrace,
        extra_context: str | None = None,
    ) -> tuple[str, dict[str, Any]]:
        prompt = _agent_summary_prompt(
            agent_name=agent_name,
            user_prompt=user_prompt,
            reviewed_output=reviewed_output,
            extra_context=extra_context,
        )
        try:
            adapter = (
                self.chat_adapter_factory()
                if callable(self.chat_adapter_factory)
                else self.chat_adapter_factory
            )
            result = await adapter.complete(messages=[ChatTurn(role="user", content=prompt)])
        except ChatProviderError as exc:
            trace.add("ReportWriterAgent", "summarize", "failed", exc.code)
            return reviewed_output, {
                "summarized": False,
                "fallback": "raw_agent_output",
                "error": exc.to_safe_metadata(),
            }

        trace.add("ReportWriterAgent", "summarize", "completed", agent_name)
        return result.content, {
            "summarized": True,
            "agent": agent_name,
            "provider_request_id": result.provider_request_id,
            "prompt_tokens": result.prompt_tokens,
            "completion_tokens": result.completion_tokens,
            "finish_reason": result.finish_reason,
        }


def _normalize_search_result(result: SearchWorkerResult) -> SearchWorkerResult:
    if result.state == "grounded" and (
        (result.provider == "gemini" and not result.google_grounded) or not result.sources or not result.citations
    ):
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


def _python_assistant_turn(
    result: PythonExecutionResult,
    *,
    trace: OrchestrationTrace,
    content: str | None = None,
    report_writer: dict[str, Any] | None = None,
) -> CoordinatedAssistantTurn:
    metadata: dict[str, Any] = {
        "tool_name": "python",
        "tool_status": result.status.value,
        "correlation_id": result.correlation_id,
        "python_result": result.model_dump(mode="json"),
        "orchestration": trace.as_metadata(),
    }
    if report_writer is not None:
        metadata["report_writer"] = report_writer
    return CoordinatedAssistantTurn(
        content=content if content is not None else _python_assistant_content(result),
        metadata=metadata,
    )


def _python_assistant_content(result: PythonExecutionResult) -> str:
    stdout = (result.stdout_excerpt or "").strip()
    stderr = (result.stderr_excerpt or "").strip()
    artifact_count = len(result.artifacts)

    if result.status is PythonExecutionStatus.succeeded:
        parts: list[str] = []
        if stdout:
            parts.append(f"Kết quả Python:\n\n```text\n{stdout}\n```")
        else:
            parts.append(result.summary)
        if artifact_count:
            parts.append(f"Đã tạo {artifact_count} tệp kết quả có thể tải xuống.")
        return "\n\n".join(parts)

    if result.status is PythonExecutionStatus.failed and stderr:
        return f"{result.summary}\n\n```text\n{stderr}\n```"

    if result.status is PythonExecutionStatus.limit_reached:
        parts = [result.summary]
        if stdout:
            parts.append(f"Stdout trước khi dừng:\n\n```text\n{stdout}\n```")
        if stderr:
            parts.append(f"Stderr:\n\n```text\n{stderr}\n```")
        return "\n\n".join(parts)

    return result.summary


def _search_assistant_turn(
    *,
    content: str,
    search: SearchTurnResult,
    worker_result: SearchWorkerResult | None,
    trace: OrchestrationTrace,
    report_writer: dict[str, Any] | None = None,
) -> CoordinatedAssistantTurn:
    metadata: dict[str, Any] = {
        "tool_name": "google_search",
        "tool_status": TOOL_STATUS_BY_SEARCH_STATE[search.state],
        "correlation_id": search.correlation_id,
        "search": search.model_dump(mode="json", exclude_none=True),
        "orchestration": trace.as_metadata(),
    }
    if worker_result is not None:
        metadata["search_result"] = worker_result.model_dump(mode="json", exclude_none=True)
    if report_writer is not None:
        metadata["report_writer"] = report_writer
    return CoordinatedAssistantTurn(content=content, metadata=metadata)


def _agent_summary_prompt(
    *,
    agent_name: str,
    user_prompt: str,
    reviewed_output: str,
    extra_context: str | None,
) -> str:
    parts = [
        "Summarize the reviewed agent result for the signed-in user.",
        f"Agent: {agent_name}",
        "Rules:",
        "- Use Vietnamese unless the user clearly asked for another language.",
        "- Use only the bounded reviewed output and context below.",
        "- Preserve exact numbers, code output, errors, citations, and download mentions.",
        (
            "- Do not invent sources, tool calls, hidden metadata, credentials, "
            "or internal policy details."
        ),
        "- Keep the answer concise and directly useful.",
        "- Answer the user's question directly; do not explain review process or confidence unless the reviewed output itself says so.",
        "- Do not mention internal tool-state labels, hidden metadata fields, citation availability, or source arrays unless they appear in the reviewed output.",
        "",
        "USER_PROMPT_START",
        user_prompt,
        "USER_PROMPT_END",
    ]
    if extra_context:
        parts.extend(
            [
                "",
                "REVIEWED_CONTEXT_START",
                extra_context,
                "REVIEWED_CONTEXT_END",
            ]
        )
    parts.extend(
        [
            "",
            "REVIEWED_OUTPUT_START",
            reviewed_output,
            "REVIEWED_OUTPUT_END",
        ]
    )
    return "\n".join(parts)


def _python_summary_context(result: PythonExecutionResult) -> str:
    return "\n".join(
        part
        for part in (
            f"status: {result.status.value}",
            f"profile: {result.profile_name.value if result.profile_name else 'none'}",
            f"duration_ms: {result.duration_ms}" if result.duration_ms is not None else None,
            f"artifacts: {len(result.artifacts)}",
        )
        if part is not None
    )

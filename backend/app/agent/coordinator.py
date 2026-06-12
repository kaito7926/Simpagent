from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Protocol
from uuid import UUID, uuid4

from sqlalchemy.ext.asyncio import AsyncSession

from app.agent.decisions import OpenAIPythonPlanner, PythonToolPlan
from app.agent.policy import (
    build_denied_result,
    collapse_text,
    prompt_requests_python,
    prompt_requires_external_search,
    python_scope_allowed,
    select_python_profile,
    tool_execution_output_summary,
    tool_execution_terminal_status,
)
from app.ai.schemas import ChatCompletionResult, ChatTurn
from app.models.domain import ToolExecution
from app.python_contract import PythonDeniedReason, PythonExecutionProfile
from app.schemas.python import PythonExecutionResult
from app.security.tool_capabilities import issue_python_capability
from app.services.python_sessions import PythonSessionsService
from app.tools.python_client import PythonClient, PythonExecutionInvocation, PythonExecutionResponse


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
    ) -> None:
        self.session = session
        self.settings = settings
        self.clock = clock
        self.principal_scopes = set(principal_scopes)
        self.chat_adapter_factory = chat_adapter_factory
        self._python_planner = python_planner
        self._python_client = python_client
        self.python_sessions = PythonSessionsService(session, settings=settings, clock=clock)

    async def complete(
        self,
        *,
        user_id: UUID,
        conversation_id: UUID,
        messages: list[ChatTurn],
        correlation_id: str | None,
    ) -> CoordinatedAssistantTurn:
        prompt = messages[-1].content if messages else ""
        if not prompt_requests_python(prompt):
            return await self._complete_direct(messages=messages)

        if prompt_requires_external_search(prompt):
            denied = await self._record_denied_turn(
                user_id=user_id,
                conversation_id=conversation_id,
                prompt=prompt,
                denial_reason=PythonDeniedReason.search_required,
                correlation_id=correlation_id,
            )
            return _python_assistant_turn(denied)

        if not python_scope_allowed(self.principal_scopes):
            denied = await self._record_denied_turn(
                user_id=user_id,
                conversation_id=conversation_id,
                prompt=prompt,
                denial_reason=PythonDeniedReason.missing_permission,
                correlation_id=correlation_id,
            )
            return _python_assistant_turn(denied)

        active_session = await self.python_sessions.get_active_session(
            conversation_id=conversation_id,
            user_id=user_id,
        )
        plan = await self.python_planner.plan(
            messages=messages,
            prompt=prompt,
            state_binding_names=active_session.binding_names if active_session is not None else (),
        )
        if plan.needs_search or not plan.code:
            denied = await self._record_denied_turn(
                user_id=user_id,
                conversation_id=conversation_id,
                prompt=prompt,
                denial_reason=PythonDeniedReason.search_required,
                correlation_id=correlation_id,
            )
            return _python_assistant_turn(denied)

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
            return _python_assistant_turn(denied)

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
                now=now if isinstance(now, datetime) else self.clock(),
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
        return _python_assistant_turn(result)

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

    async def _complete_direct(self, *, messages: list[ChatTurn]) -> CoordinatedAssistantTurn:
        adapter = self.chat_adapter_factory() if callable(self.chat_adapter_factory) else self.chat_adapter_factory
        result = await adapter.complete(messages=messages)
        metadata = {
            "provider_request_id": result.provider_request_id,
            "prompt_tokens": result.prompt_tokens,
            "completion_tokens": result.completion_tokens,
            "finish_reason": result.finish_reason,
        }
        return CoordinatedAssistantTurn(content=result.content, metadata=metadata)

    async def _record_denied_turn(
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


def _python_assistant_turn(result: PythonExecutionResult) -> CoordinatedAssistantTurn:
    return CoordinatedAssistantTurn(
        content=result.summary,
        metadata={
            "tool_name": "python",
            "tool_status": result.status.value,
            "correlation_id": result.correlation_id,
            "python_result": result.model_dump(mode="json"),
        },
    )

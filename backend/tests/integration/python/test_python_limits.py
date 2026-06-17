from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import UUID

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.agent.decisions import PythonToolPlan
from app.db.repositories.accounts import AccountsRepository
from app.models.domain import AgentRuntimeSetting, ToolExecution
from app.python_contract import PythonExecutionProfile, PythonExecutionStatus, PythonLimitName
from app.schemas.auth import STANDARD_USER_SCOPES
from app.schemas.python import PythonExecutionResult
from app.security.access_tokens import issue_access_token
from app.tools.python_client import PythonExecutionInvocation, PythonExecutionResponse


class StaticPythonPlanner:
    def __init__(self, plan: PythonToolPlan) -> None:
        self.planned = plan

    async def plan(self, *, messages, prompt: str, state_binding_names: tuple[str, ...]) -> PythonToolPlan:
        return self.planned


class RecordingPythonClient:
    def __init__(self, response: PythonExecutionResponse) -> None:
        self.response = response
        self.calls: list[PythonExecutionInvocation] = []

    async def execute(self, invocation: PythonExecutionInvocation) -> PythonExecutionResponse:
        self.calls.append(invocation)
        return self.response


async def _create_user_token(
    db_session: AsyncSession,
    settings,
    *,
    email: str,
    scopes: list[str] | None = None,
) -> str:
    selected_scopes = scopes or STANDARD_USER_SCOPES
    async with db_session.begin():
        accounts = AccountsRepository(db_session)
        bundle = await accounts.create_user_with_local_credentials(
            email=email,
            password_hash="not-used-in-python-tests",
        )
        if selected_scopes != STANDARD_USER_SCOPES:
            await accounts.replace_user_scopes(bundle.user.id, selected_scopes)
    return issue_access_token(
        user_id=bundle.user.id,
        role=bundle.user.role,
        scopes=selected_scopes,
        settings=settings,
        now=datetime.now(UTC),
    )


def _auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


async def _enable_trusted_supervisor(db_session: AsyncSession) -> None:
    db_session.add(
        AgentRuntimeSetting(
            key="trusted_supervisor_agent",
            enabled=True,
            updated_by_user_id=None,
        )
    )
    await db_session.commit()


@pytest.mark.integration
@pytest.mark.asyncio
async def test_exact_limit_name_is_returned_to_chat_and_persisted_on_tool_execution(
    app,
    client,
    db_session,
    settings,
) -> None:
    token = await _create_user_token(db_session, settings, email="python-limit@example.test")
    await _enable_trusted_supervisor(db_session)
    app.state.python_planner = StaticPythonPlanner(
        PythonToolPlan(code="print('x' * 50000)")
    )
    python_client = RecordingPythonClient(
        PythonExecutionResponse(
            result=PythonExecutionResult(
                execution_id=UUID("00000000-0000-0000-0000-000000000010"),
                status=PythonExecutionStatus.limit_reached,
                summary="Execution stopped because stdout/stderr exceeded the reviewed output limit.",
                duration_ms=1304,
                profile_name=PythonExecutionProfile.basic,
                stdout_excerpt="matrix shape=(5000, 5000)\nprinting halted...",
                stderr_excerpt=None,
                artifacts=[],
                limit_triggered=PythonLimitName.output_size,
                denial_reason=None,
                policy_error_code=None,
                infra_failure_reason=None,
                retryable=False,
                correlation_id="corr-limit",
            ),
            snapshot_blob=b'{"version":1,"binding_names":[],"pickle_b64":"gAR9lC4="}',
        )
    )
    app.state.python_client = python_client

    response = await client.post(
        "/api/conversations",
        headers=_auth(token),
        json={
            "initial_message": {
                "client_message_id": "python-limit",
                "content": "Use Python to create a huge matrix and print all of it in chat.",
            }
        },
    )

    assert response.status_code == 201
    body = response.json()
    python_result = body["messages"][1]["metadata"]["python_result"]

    assert python_result["status"] == "limit_reached"
    assert python_result["limit_triggered"] == "output_size"
    assert python_result["duration_ms"] == 1304
    assert python_client.calls[0].profile_name is PythonExecutionProfile.basic

    row = await db_session.scalar(select(ToolExecution).where(ToolExecution.conversation_id == UUID(body["id"])))
    assert row is not None
    assert row.status == "limit_reached"
    assert row.duration_ms == 1304
    assert row.output_summary is not None
    assert "output_size" in row.output_summary

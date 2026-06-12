from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any
from uuid import UUID

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.agent.decisions import PythonToolPlan
from app.db.repositories.accounts import AccountsRepository
from app.db.repositories.python_state import PythonStateRepository
from app.models.domain import Conversation, ToolExecution
from app.python_contract import PythonArtifactType, PythonExecutionProfile, PythonExecutionStatus
from app.schemas.auth import STANDARD_USER_SCOPES
from app.schemas.python import PythonExecutionResult
from app.security.access_tokens import issue_access_token
from app.tools.python_client import PythonArtifactPayload, PythonExecutionInvocation, PythonExecutionResponse


class StaticPythonPlanner:
    def __init__(self, plan: PythonToolPlan) -> None:
        self.planned = plan
        self.calls: list[dict[str, Any]] = []

    async def plan(
        self,
        *,
        messages,
        prompt: str,
        state_binding_names: tuple[str, ...],
    ) -> PythonToolPlan:
        self.calls.append(
            {
                "messages": list(messages),
                "prompt": prompt,
                "state_binding_names": state_binding_names,
            }
        )
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
    now: datetime | None = None,
) -> tuple[UUID, str]:
    selected_scopes = scopes or STANDARD_USER_SCOPES
    async with db_session.begin():
        accounts = AccountsRepository(db_session)
        bundle = await accounts.create_user_with_local_credentials(
            email=email,
            password_hash="not-used-in-python-tests",
        )
        if selected_scopes != STANDARD_USER_SCOPES:
            await accounts.replace_user_scopes(bundle.user.id, selected_scopes)
    token = issue_access_token(
        user_id=bundle.user.id,
        role=bundle.user.role,
        scopes=selected_scopes,
        settings=settings,
        now=now or datetime.now(UTC),
    )
    return bundle.user.id, token


def _auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def _success_result(
    *,
    execution_id: UUID,
    profile_name: PythonExecutionProfile,
    correlation_id: str | None = None,
) -> PythonExecutionResult:
    return PythonExecutionResult(
        execution_id=execution_id,
        status=PythonExecutionStatus.succeeded,
        summary="Reviewed Python execution completed successfully.",
        duration_ms=84,
        profile_name=profile_name,
        stdout_excerpt="ok",
        stderr_excerpt=None,
        artifacts=[],
        limit_triggered=None,
        denial_reason=None,
        policy_error_code=None,
        infra_failure_reason=None,
        retryable=False,
        correlation_id=correlation_id,
    )


@pytest.mark.integration
@pytest.mark.asyncio
async def test_missing_tool_python_scope_returns_denied_card_and_never_calls_supervisor(
    app,
    client,
    db_session,
    settings,
) -> None:
    _, token = await _create_user_token(
        db_session,
        settings,
        email="python-no-scope@example.test",
        scopes=["chat:read", "chat:write"],
    )
    planner = StaticPythonPlanner(PythonToolPlan(code="print(sum([1, 2, 3]))"))
    python_client = RecordingPythonClient(
        PythonExecutionResponse(
            result=_success_result(
                execution_id=UUID("00000000-0000-0000-0000-000000000001"),
                profile_name=PythonExecutionProfile.basic,
            )
        )
    )
    app.state.python_planner = planner
    app.state.python_client = python_client

    response = await client.post(
        "/api/conversations",
        headers=_auth(token),
        json={
            "initial_message": {
                "client_message_id": "python-missing-scope",
                "content": "Use Python to calculate the sum of 1, 2, and 3 for me.",
            }
        },
    )

    assert response.status_code == 201
    body = response.json()
    python_result = body["messages"][1]["metadata"]["python_result"]

    assert python_result["status"] == "denied"
    assert python_result["denial_reason"] == "missing_permission"
    assert body["messages"][1]["status"] == "completed"
    assert python_client.calls == []
    assert planner.calls == []

    rows = list(
        (
            await db_session.execute(
                select(ToolExecution).where(ToolExecution.conversation_id == UUID(body["id"]))
            )
        ).scalars()
    )
    assert len(rows) == 1
    assert rows[0].tool_name == "python"
    assert rows[0].status == "denied"


@pytest.mark.integration
@pytest.mark.asyncio
async def test_search_plus_python_prompt_is_denied_without_touching_planner_or_supervisor(
    app,
    client,
    db_session,
    settings,
) -> None:
    _, token = await _create_user_token(db_session, settings, email="python-search-deny@example.test")
    planner = StaticPythonPlanner(PythonToolPlan(code="print('should not plan')"))
    python_client = RecordingPythonClient(
        PythonExecutionResponse(
            result=_success_result(
                execution_id=UUID("00000000-0000-0000-0000-000000000002"),
                profile_name=PythonExecutionProfile.basic,
            )
        )
    )
    app.state.python_planner = planner
    app.state.python_client = python_client

    response = await client.post(
        "/api/conversations",
        headers=_auth(token),
        json={
            "initial_message": {
                "client_message_id": "python-search-required",
                "content": "Tìm dữ liệu giá vàng hôm nay trên web rồi dùng Python tính trung bình cho tôi.",
            }
        },
    )

    assert response.status_code == 201
    body = response.json()
    python_result = body["messages"][1]["metadata"]["python_result"]

    assert python_result["status"] == "denied"
    assert python_result["denial_reason"] == "search_required"
    assert python_client.calls == []
    assert planner.calls == []

    rows = list(
        (
            await db_session.execute(
                select(ToolExecution).where(ToolExecution.conversation_id == UUID(body["id"]))
            )
        ).scalars()
    )
    assert len(rows) == 1
    assert rows[0].status == "denied"


@pytest.mark.integration
@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("content", "plan", "expected_profile"),
    [
        (
            "Use Python to calculate 2 + 2 and give me the answer only.",
            PythonToolPlan(
                code="print(2 + 2)",
                suggested_profile=PythonExecutionProfile.data,
            ),
            PythonExecutionProfile.basic,
        ),
        (
            "Clean this dataset, group it by quarter, and give me a CSV file to download.",
            PythonToolPlan(
                code="from pathlib import Path\nPath('artifacts').mkdir(exist_ok=True)\nPath('artifacts/report.csv').write_text('quarter,total\\nQ1,10\\n', encoding='utf-8')",
                requested_artifacts=(PythonArtifactType.csv,),
                suggested_profile=PythonExecutionProfile.basic,
            ),
            PythonExecutionProfile.data,
        ),
    ],
)
async def test_backend_owns_profile_selection_and_only_elevates_narrowly(
    app,
    client,
    db_session,
    settings,
    content: str,
    plan: PythonToolPlan,
    expected_profile: PythonExecutionProfile,
) -> None:
    _, token = await _create_user_token(db_session, settings, email=f"profile-{expected_profile.value}@example.test")
    planner = StaticPythonPlanner(plan)
    python_client = RecordingPythonClient(
        PythonExecutionResponse(
            result=_success_result(
                execution_id=UUID("00000000-0000-0000-0000-000000000003"),
                profile_name=expected_profile,
                correlation_id="corr-profile",
            ),
            artifacts=(
                PythonArtifactPayload(
                    name="report.csv",
                    artifact_type=PythonArtifactType.csv,
                    size_bytes=20,
                    sha256="1" * 64,
                    content=b"quarter,total\nQ1,10\n",
                ),
            )
            if expected_profile is PythonExecutionProfile.data
            else (),
            snapshot_blob=b'{"version":1,"binding_names":[],"pickle_b64":"gAR9lC4="}',
        )
    )
    app.state.python_planner = planner
    app.state.python_client = python_client

    response = await client.post(
        "/api/conversations",
        headers=_auth(token),
        json={
            "initial_message": {
                "client_message_id": f"profile-{expected_profile.value}",
                "content": content,
            }
        },
    )

    assert response.status_code == 201
    body = response.json()
    python_result = body["messages"][1]["metadata"]["python_result"]

    assert planner.calls != []
    assert len(python_client.calls) == 1
    assert python_client.calls[0].profile_name is expected_profile
    assert python_result["status"] == "succeeded"
    assert python_result["profile_name"] == expected_profile.value

    if expected_profile is PythonExecutionProfile.data:
        assert python_result["artifacts"][0]["artifact_type"] == "csv"
        assert python_result["artifacts"][0]["download_path"].startswith("/api/python/artifacts/")
    else:
        assert python_result["artifacts"] == []


@pytest.mark.integration
@pytest.mark.asyncio
async def test_expired_python_artifact_download_returns_gone_without_cross_owner_leakage(
    app,
    client,
    db_session,
    settings,
    tmp_path: Path,
) -> None:
    frozen_now = datetime(2026, 6, 12, 8, 0, tzinfo=UTC)
    owner_id, owner_token = await _create_user_token(
        db_session,
        settings,
        email="artifact-owner@example.test",
        now=frozen_now,
    )
    _, attacker_token = await _create_user_token(
        db_session,
        settings,
        email="artifact-attacker@example.test",
        now=frozen_now,
    )

    app.state.settings = settings.model_copy(update={"python_artifact_storage_dir": str(tmp_path)})
    app.state.clock = lambda: frozen_now

    conversation = Conversation(user_id=owner_id, title="Artifacts")
    db_session.add(conversation)
    await db_session.flush()

    execution = ToolExecution(
        user_id=owner_id,
        conversation_id=conversation.id,
        tool_name="python",
        input_summary="write csv",
        output_summary="limit=none",
        status="succeeded",
        duration_ms=45,
    )
    db_session.add(execution)
    await db_session.flush()

    storage_key = "artifact-expired.csv"
    (tmp_path / storage_key).write_text("quarter,total\nQ1,10\n", encoding="utf-8")

    repository = PythonStateRepository(db_session)
    artifact = await repository.create_artifact(
        user_id=owner_id,
        conversation_id=conversation.id,
        tool_execution_id=execution.id,
        artifact_type=PythonArtifactType.csv,
        name="report.csv",
        storage_key=storage_key,
        size_bytes=20,
        sha256="2" * 64,
        expires_at=frozen_now - timedelta(seconds=1),
    )
    await db_session.commit()

    owner_response = await client.get(f"/api/python/artifacts/{artifact.id}", headers=_auth(owner_token))
    attacker_response = await client.get(f"/api/python/artifacts/{artifact.id}", headers=_auth(attacker_token))

    assert owner_response.status_code == 410
    assert owner_response.json()["error"]["code"] == "artifact_expired"
    assert not (tmp_path / storage_key).exists()
    assert attacker_response.status_code == 404
    assert attacker_response.json()["error"]["code"] == "python_artifact_not_found"

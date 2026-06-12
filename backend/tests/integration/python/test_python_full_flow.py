from __future__ import annotations

import base64
import json
import pickle
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any
from uuid import UUID

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.agent.decisions import PythonToolPlan
from app.db.repositories.accounts import AccountsRepository
from app.models.domain import ToolExecution
from app.models.python_state import PythonArtifactRecord, PythonSessionState
from app.python_contract import PythonArtifactType, PythonExecutionProfile, PythonExecutionStatus
from app.schemas.auth import STANDARD_USER_SCOPES
from app.schemas.python import PythonExecutionResult
from app.security.access_tokens import issue_access_token
from app.tools.python_client import PythonArtifactPayload, PythonExecutionInvocation, PythonExecutionResponse


class SequencePythonPlanner:
    def __init__(self, plans: list[PythonToolPlan]) -> None:
        self._plans = list(plans)
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
        return self._plans.pop(0)


class SequencePythonClient:
    def __init__(self, responses: list[PythonExecutionResponse]) -> None:
        self._responses = list(responses)
        self.calls: list[PythonExecutionInvocation] = []

    async def execute(self, invocation: PythonExecutionInvocation) -> PythonExecutionResponse:
        self.calls.append(invocation)
        return self._responses.pop(0)


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


def _snapshot_blob(*binding_names: str) -> bytes:
    payload = {
        "version": 1,
        "binding_names": list(binding_names),
        "pickle_b64": base64.b64encode(pickle.dumps({}, protocol=pickle.HIGHEST_PROTOCOL)).decode("ascii"),
    }
    return json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8")


def _binding_names(snapshot_blob: bytes) -> tuple[str, ...]:
    payload = json.loads(snapshot_blob.decode("utf-8"))
    return tuple(payload.get("binding_names", ()))


def _result(
    *,
    execution_id: UUID,
    status: PythonExecutionStatus,
    profile_name: PythonExecutionProfile,
    summary: str,
    duration_ms: int | None,
    stdout_excerpt: str | None = None,
    stderr_excerpt: str | None = None,
    correlation_id: str | None = None,
) -> PythonExecutionResult:
    return PythonExecutionResult(
        execution_id=execution_id,
        status=status,
        summary=summary,
        duration_ms=duration_ms,
        profile_name=profile_name,
        stdout_excerpt=stdout_excerpt,
        stderr_excerpt=stderr_excerpt,
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
async def test_successful_python_turn_persists_artifacts_reuses_state_and_extends_sliding_expiry(
    app,
    client,
    db_session,
    settings,
    tmp_path: Path,
) -> None:
    frozen_now = {"value": datetime(2026, 6, 13, 1, 0, tzinfo=UTC)}
    _, token = await _create_user_token(
        db_session,
        settings,
        email="python-full-flow@example.test",
        now=frozen_now["value"],
    )
    app.state.settings = settings.model_copy(update={"python_artifact_storage_dir": str(tmp_path)})
    app.state.clock = lambda: frozen_now["value"]

    snapshot_one = _snapshot_blob("sales_rows")
    snapshot_two = _snapshot_blob("quarter_totals", "sales_rows")
    planner = SequencePythonPlanner(
        [
            PythonToolPlan(
                code="print('first run')",
                requested_artifacts=(PythonArtifactType.csv,),
            ),
            PythonToolPlan(
                code="print('second run')",
            ),
        ]
    )
    python_client = SequencePythonClient(
        [
            PythonExecutionResponse(
                result=_result(
                    execution_id=UUID("00000000-0000-0000-0000-000000000101"),
                    status=PythonExecutionStatus.succeeded,
                    profile_name=PythonExecutionProfile.data,
                    summary="Reviewed Python execution completed successfully.",
                    duration_ms=84,
                    stdout_excerpt="first run",
                    correlation_id="corr-python-1",
                ),
                artifacts=(
                    PythonArtifactPayload(
                        name="report.csv",
                        artifact_type=PythonArtifactType.csv,
                        size_bytes=20,
                        sha256="1" * 64,
                        content=b"quarter,total\nQ1,10\n",
                    ),
                ),
                snapshot_blob=snapshot_one,
            ),
            PythonExecutionResponse(
                result=_result(
                    execution_id=UUID("00000000-0000-0000-0000-000000000102"),
                    status=PythonExecutionStatus.succeeded,
                    profile_name=PythonExecutionProfile.data,
                    summary="Reviewed Python execution completed successfully.",
                    duration_ms=91,
                    stdout_excerpt="second run",
                    correlation_id="corr-python-2",
                ),
                snapshot_blob=snapshot_two,
            ),
        ]
    )
    app.state.python_planner = planner
    app.state.python_client = python_client

    created = await client.post(
        "/api/conversations",
        headers=_auth(token),
        json={
            "initial_message": {
                "client_message_id": "python-flow-1",
                "content": "Use Python to clean this dataset and give me a CSV download.",
            }
        },
    )

    assert created.status_code == 201
    body = created.json()
    conversation_id = UUID(body["id"])
    first_python = body["messages"][1]["metadata"]["python_result"]
    artifact_path = first_python["artifacts"][0]["download_path"]

    assert first_python["status"] == "succeeded"
    assert planner.calls[0]["state_binding_names"] == ()
    assert python_client.calls[0].state_snapshot is None
    assert python_client.calls[0].profile_name is PythonExecutionProfile.data

    state_after_first = await db_session.scalar(
        select(PythonSessionState).where(PythonSessionState.conversation_id == conversation_id)
    )
    assert state_after_first is not None
    assert state_after_first.profile_name == PythonExecutionProfile.data.value
    assert state_after_first.snapshot_blob == snapshot_one
    first_state_expiry = state_after_first.expires_at

    artifact_record = await db_session.scalar(
        select(PythonArtifactRecord).where(PythonArtifactRecord.conversation_id == conversation_id)
    )
    assert artifact_record is not None
    first_expiry = artifact_record.expires_at
    assert (tmp_path / artifact_record.storage_key).read_bytes() == b"quarter,total\nQ1,10\n"

    download = await client.get(artifact_path, headers=_auth(token))
    assert download.status_code == 200
    assert download.content == b"quarter,total\nQ1,10\n"

    frozen_now["value"] = frozen_now["value"] + timedelta(minutes=5)
    follow_up = await client.post(
        f"/api/conversations/{conversation_id}/messages",
        headers=_auth(token),
        json={
            "client_message_id": "python-flow-2",
            "content": "Use Python to group the dataset by quarter and summarize it again.",
        },
    )

    assert follow_up.status_code == 200
    follow_up_body = follow_up.json()
    second_python = follow_up_body["messages"][-1]["metadata"]["python_result"]

    assert second_python["status"] == "succeeded"
    assert second_python["artifacts"] == []
    assert planner.calls[1]["state_binding_names"] == ("sales_rows",)
    assert python_client.calls[1].state_snapshot == snapshot_one
    assert python_client.calls[1].profile_name is PythonExecutionProfile.data

    state_after_second = await db_session.scalar(
        select(PythonSessionState).where(PythonSessionState.conversation_id == conversation_id)
    )
    assert state_after_second is not None
    await db_session.refresh(state_after_second)
    assert set(_binding_names(state_after_second.snapshot_blob)) == {"quarter_totals", "sales_rows"}
    assert state_after_second.expires_at > first_state_expiry

    artifact_after_second = await db_session.scalar(
        select(PythonArtifactRecord).where(PythonArtifactRecord.id == artifact_record.id)
    )
    assert artifact_after_second is not None
    await db_session.refresh(artifact_after_second)
    assert artifact_after_second.expires_at > first_expiry

    tool_rows = list(
        (
            await db_session.execute(
                select(ToolExecution)
                .where(ToolExecution.conversation_id == conversation_id)
                .order_by(ToolExecution.created_at.asc(), ToolExecution.id.asc())
            )
        ).scalars()
    )
    assert [row.status for row in tool_rows] == ["succeeded", "succeeded"]


@pytest.mark.integration
@pytest.mark.asyncio
async def test_user_code_exception_stays_completed_and_not_infra_failure(
    app,
    client,
    db_session,
    settings,
    tmp_path: Path,
) -> None:
    frozen_now = datetime(2026, 6, 13, 2, 0, tzinfo=UTC)
    _, token = await _create_user_token(
        db_session,
        settings,
        email="python-user-exception@example.test",
        now=frozen_now,
    )
    app.state.settings = settings.model_copy(update={"python_artifact_storage_dir": str(tmp_path)})
    app.state.clock = lambda: frozen_now
    app.state.python_planner = SequencePythonPlanner([PythonToolPlan(code="raise ValueError('boom')")])
    app.state.python_client = SequencePythonClient(
        [
            PythonExecutionResponse(
                result=_result(
                    execution_id=UUID("00000000-0000-0000-0000-000000000103"),
                    status=PythonExecutionStatus.succeeded,
                    profile_name=PythonExecutionProfile.basic,
                    summary="Execution completed with a Python exception from user code.",
                    duration_ms=37,
                    stderr_excerpt="Traceback (most recent call last):\nValueError: boom",
                    correlation_id="corr-user-exception",
                ),
                snapshot_blob=_snapshot_blob(),
            )
        ]
    )

    response = await client.post(
        "/api/conversations",
        headers=_auth(token),
        json={
            "initial_message": {
                "client_message_id": "python-user-exception",
                "content": "Use Python to run this failing snippet and show me the bounded traceback.",
            }
        },
    )

    assert response.status_code == 201
    body = response.json()
    python_result = body["messages"][1]["metadata"]["python_result"]

    assert python_result["status"] == "succeeded"
    assert python_result["infra_failure_reason"] is None
    assert "Traceback" in (python_result["stderr_excerpt"] or "")
    assert body["messages"][1]["status"] == "completed"

    tool_row = await db_session.scalar(select(ToolExecution).where(ToolExecution.conversation_id == UUID(body["id"])))
    assert tool_row is not None
    assert tool_row.status == "succeeded"
    assert tool_row.output_summary is not None
    assert "status=succeeded" in tool_row.output_summary
    assert "infra=" not in tool_row.output_summary

    state_row = await db_session.scalar(
        select(PythonSessionState).where(PythonSessionState.conversation_id == UUID(body["id"]))
    )
    assert state_row is not None
    assert state_row.profile_name == PythonExecutionProfile.basic.value

from __future__ import annotations

import base64
import importlib.util
import json
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.agent.decisions import PythonToolPlan
from app.db.repositories.accounts import AccountsRepository
from app.models.domain import AgentRuntimeSetting, ToolExecution
from app.models.python_state import PythonArtifactRecord, PythonSessionState
from app.python_contract import PythonExecutionProfile, PythonExecutionStatus, PythonPolicyErrorCode
from app.schemas.auth import STANDARD_USER_SCOPES
from app.schemas.python import PythonExecutionResult
from app.security.access_tokens import issue_access_token
from app.security.tool_capabilities import issue_python_capability
from app.tools.python_client import PythonExecutionInvocation, PythonExecutionResponse


def sandbox_root() -> Path:
    local_root = Path(__file__).resolve().parents[3] / "sandbox"
    if local_root.exists():
        return local_root
    mounted_root = Path("/workspace/sandbox")
    assert mounted_root.exists()
    return mounted_root


def load_module(relative_path: str, module_name: str):
    module_path = sandbox_root() / relative_path
    module_dir = str(module_path.parent)
    if module_dir not in sys.path:
        sys.path.insert(0, module_dir)
    spec = importlib.util.spec_from_file_location(module_name, module_path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


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


@pytest.mark.security
@pytest.mark.asyncio
async def test_policy_error_creates_execution_evidence_without_session_or_artifact_side_effects(
    app,
    client,
    db_session,
    settings,
    tmp_path: Path,
) -> None:
    token = await _create_user_token(db_session, settings, email="python-policy-side-effect@example.test")
    await _enable_trusted_supervisor(db_session)
    app.state.settings = settings.model_copy(update={"python_artifact_storage_dir": str(tmp_path)})
    app.state.python_planner = StaticPythonPlanner(PythonToolPlan(code="import requests\nprint('blocked')"))
    python_client = RecordingPythonClient(
        PythonExecutionResponse(
            result=PythonExecutionResult(
                execution_id=UUID("00000000-0000-0000-0000-000000000120"),
                status=PythonExecutionStatus.policy_error,
                summary="Execution stopped before running because the code requested behavior outside the reviewed sandbox policy.",
                duration_ms=0,
                profile_name=PythonExecutionProfile.basic,
                stdout_excerpt=None,
                stderr_excerpt="Import 'requests' is not in the reviewed Python allowlist.",
                artifacts=[],
                limit_triggered=None,
                denial_reason=None,
                policy_error_code=PythonPolicyErrorCode.blocked_import,
                infra_failure_reason=None,
                retryable=False,
                correlation_id="corr-policy-side-effect",
            )
        )
    )
    app.state.python_client = python_client

    response = await client.post(
        "/api/conversations",
        headers=_auth(token),
        json={
            "initial_message": {
                "client_message_id": "python-policy-side-effect",
                "content": "Use Python to import requests and fetch a URL for me.",
            }
        },
    )

    assert response.status_code == 201
    body = response.json()
    python_result = body["messages"][1]["metadata"]["python_result"]

    assert python_result["status"] == "policy_error"
    assert python_client.calls != []
    assert python_client.calls[0].state_snapshot is None

    tool_row = await db_session.scalar(select(ToolExecution).where(ToolExecution.conversation_id == UUID(body["id"])))
    assert tool_row is not None
    assert tool_row.status == "policy_error"
    assert await db_session.scalar(
        select(PythonSessionState).where(PythonSessionState.conversation_id == UUID(body["id"]))
    ) is None
    artifact_rows = list((await db_session.execute(select(PythonArtifactRecord))).scalars())
    assert artifact_rows == []
    assert list(tmp_path.iterdir()) == []


def test_supervisor_timeout_kills_and_removes_runtime_container(settings, monkeypatch) -> None:
    monkeypatch.setenv("SIMPAGENT_SANDBOX_CAPABILITY_PUBLIC_KEY", settings.jwt_public_key_value)
    server = load_module("server.py", "sandbox_server_side_effects")
    execution_id = UUID("00000000-0000-0000-0000-000000000301")
    code = "print('slow')"
    request = server.ExecutionRequest(
        execution_id=str(execution_id),
        capability=issue_python_capability(
            execution_id=execution_id,
            profile_name=PythonExecutionProfile.basic,
            code=code,
            settings=settings,
            now=datetime.now(UTC),
        ),
        profile_name=PythonExecutionProfile.basic.value,
        code=code,
    )
    spec = server.build_runtime_launch_spec(request)
    commands: list[list[str]] = []

    def fake_run(command: list[str], *, check: bool = True, timeout: int | None = None):
        commands.append(command)
        action = command[1]
        if action in {"create", "start", "kill", "rm"}:
            return subprocess.CompletedProcess(command, 0, "", "")
        if action == "wait":
            raise subprocess.TimeoutExpired(command, timeout)
        raise AssertionError(f"Unexpected docker command: {command}")

    monkeypatch.setattr(server, "ensure_runtime_image", lambda: None)
    monkeypatch.setattr(server, "_run_docker_command", fake_run)

    result = server.execute_request(request)

    assert result["status"] == "limit_reached"
    assert result["limit_triggered"] == "wall_time"
    assert [server.DOCKER_BIN, "kill", spec.container_name] in commands
    assert [server.DOCKER_BIN, "rm", "-f", spec.container_name] in commands


def test_supervisor_prefers_runtime_result_marker_from_logs() -> None:
    server = load_module("server.py", "sandbox_server_log_result")
    payload = {
        "execution_id": "exec-log-001",
        "status": "succeeded",
        "summary": "Reviewed Python execution completed successfully.",
        "duration_ms": 12,
        "profile_name": "python-basic-v1",
        "stdout_excerpt": "4\n",
        "stderr_excerpt": None,
        "artifacts": [],
        "limit_triggered": None,
        "denial_reason": None,
        "policy_error_code": None,
        "infra_failure_reason": None,
        "retryable": False,
        "correlation_id": "corr-log-001",
    }
    encoded = base64.b64encode(json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8")).decode("ascii")

    result = server._result_from_logs(f"noise\n{server.RESULT_LOG_PREFIX}{encoded}\n")

    assert result == payload

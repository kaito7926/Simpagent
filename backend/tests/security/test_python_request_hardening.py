from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from uuid import UUID

import pytest
from pydantic import ValidationError

from app.python_contract import PythonExecutionProfile
from app.security.tool_capabilities import issue_python_capability
from app.tools.python_client import SupervisorExecutionRequest


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


def _valid_payload() -> dict[str, str]:
    return {
        "execution_id": "00000000-0000-0000-0000-000000000111",
        "capability": "signed-capability",
        "profile_name": "python-basic-v1",
        "code": "print('ok')",
        "correlation_id": "corr-python-hardening",
    }


@pytest.mark.security
@pytest.mark.parametrize(
    ("field_name", "value"),
    [
        ("image", "python:3.13"),
        ("network_mode", "host"),
        ("bind_mounts", ["C:\\", "/var/run/docker.sock"]),
        ("command", ["bash", "-lc", "pip install requests"]),
        ("packages", ["requests"]),
    ],
)
def test_supervisor_request_rejects_caller_controlled_runtime_mutation(field_name: str, value) -> None:
    payload = _valid_payload()
    payload[field_name] = value

    with pytest.raises(ValidationError):
        SupervisorExecutionRequest.model_validate(payload)


@pytest.mark.security
def test_supervisor_request_accepts_only_reviewed_profile_names() -> None:
    payload = _valid_payload()
    payload["profile_name"] = "python-unreviewed-v99"

    with pytest.raises(ValidationError):
        SupervisorExecutionRequest.model_validate(payload)


@pytest.mark.security
def test_supervisor_rejects_replayed_asymmetric_python_capability(settings, monkeypatch) -> None:
    monkeypatch.setenv("SIMPAGENT_SANDBOX_CAPABILITY_PUBLIC_KEY", settings.jwt_public_key_value)
    server = load_module("server.py", "sandbox_server_capability_replay")
    execution_id = UUID("00000000-0000-0000-0000-000000000222")
    code = "print('ok')"
    token = issue_python_capability(
        execution_id=execution_id,
        profile_name=PythonExecutionProfile.basic,
        code=code,
        settings=settings,
        now=settings.now_utc(),
    )
    request = server.ExecutionRequest(
        execution_id=str(execution_id),
        capability=token,
        profile_name=PythonExecutionProfile.basic.value,
        code=code,
    )

    server.verify_capability_token(token, request=request)
    with pytest.raises(ValueError, match="replay|already used"):
        server.verify_capability_token(token, request=request)


@pytest.mark.security
def test_supervisor_rejects_legacy_symmetric_python_capability(settings, monkeypatch) -> None:
    monkeypatch.setenv("SIMPAGENT_SANDBOX_CAPABILITY_PUBLIC_KEY", settings.jwt_public_key_value)
    server = load_module("server.py", "sandbox_server_capability_legacy")
    code = "print('legacy')"
    legacy_token = server.issue_capability_token(
        execution_id="exec-legacy-001",
        profile_name="python-basic-v1",
        code=code,
    )
    request = server.ExecutionRequest(
        execution_id="exec-legacy-001",
        capability=legacy_token,
        profile_name="python-basic-v1",
        code=code,
    )

    with pytest.raises(ValueError):
        server.verify_capability_token(legacy_token, request=request)

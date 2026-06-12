from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.tools.python_client import SupervisorExecutionRequest


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

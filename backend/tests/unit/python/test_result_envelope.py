from __future__ import annotations

from uuid import uuid4

import pytest
from pydantic import ValidationError

from app.schemas.python import (
    PythonArtifactType,
    PythonDeniedReason,
    PythonExecutionArtifact,
    PythonExecutionProfile,
    PythonExecutionResult,
    PythonExecutionStatus,
    PythonInfraFailureReason,
    PythonLimitName,
    PythonPolicyErrorCode,
)


def build_result(**overrides) -> PythonExecutionResult:
    payload = {
        "execution_id": uuid4(),
        "status": PythonExecutionStatus.succeeded,
        "summary": "Created a reviewed CSV artifact.",
        "duration_ms": 420,
        "profile_name": PythonExecutionProfile.basic,
        "stdout_excerpt": "rows=12",
        "stderr_excerpt": None,
        "artifacts": [
            {
                "artifact_id": uuid4(),
                "name": "report.csv",
                "artifact_type": PythonArtifactType.csv,
                "size_bytes": 128,
                "download_path": f"/api/python/artifacts/{uuid4()}",
            }
        ],
        "limit_triggered": None,
        "denial_reason": None,
        "policy_error_code": None,
        "infra_failure_reason": None,
        "retryable": False,
        "correlation_id": "corr-123",
    }
    payload.update(overrides)
    return PythonExecutionResult.model_validate(payload)


def test_python_result_uses_phase_four_status_taxonomy() -> None:
    assert {status.value for status in PythonExecutionStatus} == {
        "accepted",
        "running",
        "succeeded",
        "denied",
        "policy_error",
        "limit_reached",
        "infra_failure",
    }


def test_python_result_schema_hides_runtime_internals() -> None:
    schema = PythonExecutionResult.model_json_schema()
    properties = set(schema["properties"])

    assert schema["title"] == "PythonExecutionResult"
    assert "container_id" not in properties
    assert "host_path" not in properties
    assert "runtime_command" not in properties
    assert "mounts" not in properties


def test_limit_reached_requires_exact_limit_name() -> None:
    with pytest.raises(ValidationError):
        build_result(
            status=PythonExecutionStatus.limit_reached,
            artifacts=[],
            stdout_excerpt=None,
            summary="Execution stopped by a hard limit.",
        )

    result = build_result(
        status=PythonExecutionStatus.limit_reached,
        artifacts=[],
        stdout_excerpt=None,
        summary="Execution stopped by a hard limit.",
        limit_triggered=PythonLimitName.memory,
    )

    assert result.limit_triggered is PythonLimitName.memory


def test_denied_state_requires_a_specific_denial_reason() -> None:
    with pytest.raises(ValidationError):
        build_result(status=PythonExecutionStatus.denied, artifacts=[])

    result = build_result(
        status=PythonExecutionStatus.denied,
        summary="Python is not available for this account.",
        duration_ms=None,
        stdout_excerpt=None,
        stderr_excerpt=None,
        artifacts=[],
        denial_reason=PythonDeniedReason.missing_permission,
    )

    assert result.denial_reason is PythonDeniedReason.missing_permission


def test_policy_error_requires_a_reviewed_policy_code() -> None:
    with pytest.raises(ValidationError):
        build_result(status=PythonExecutionStatus.policy_error, artifacts=[])

    result = build_result(
        status=PythonExecutionStatus.policy_error,
        summary="The requested import is blocked by policy.",
        artifacts=[],
        stdout_excerpt=None,
        stderr_excerpt="ImportError: blocked import",
        policy_error_code=PythonPolicyErrorCode.blocked_import,
    )

    assert result.policy_error_code is PythonPolicyErrorCode.blocked_import


def test_infrastructure_failure_is_the_only_retryable_terminal_state() -> None:
    with pytest.raises(ValidationError):
        build_result(status=PythonExecutionStatus.succeeded, retryable=True)

    result = build_result(
        status=PythonExecutionStatus.infra_failure,
        summary="Sandbox worker could not start.",
        artifacts=[],
        stdout_excerpt=None,
        stderr_excerpt=None,
        duration_ms=None,
        retryable=True,
        infra_failure_reason=PythonInfraFailureReason.worker_start_failed,
    )

    assert result.retryable is True
    assert result.infra_failure_reason is PythonInfraFailureReason.worker_start_failed


def test_python_artifact_metadata_is_bounded_and_reviewed() -> None:
    artifact = PythonExecutionArtifact.model_validate(
        {
            "artifact_id": uuid4(),
            "name": "chart.png",
            "artifact_type": PythonArtifactType.png,
            "size_bytes": 4096,
            "download_path": f"/api/python/artifacts/{uuid4()}",
        }
    )

    assert artifact.artifact_type is PythonArtifactType.png

    with pytest.raises(ValidationError):
        PythonExecutionArtifact.model_validate(
            {
                "artifact_id": uuid4(),
                "name": "report.pdf",
                "artifact_type": "pdf",
                "size_bytes": 32,
                "download_path": f"/api/python/artifacts/{uuid4()}",
            }
        )

    with pytest.raises(ValidationError):
        PythonExecutionArtifact.model_validate(
            {
                "artifact_id": uuid4(),
                "name": "chart.png",
                "artifact_type": PythonArtifactType.png,
                "size_bytes": 32,
                "download_path": "C:/temp/chart.png",
            }
        )

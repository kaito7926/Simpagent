from __future__ import annotations

from urllib.parse import urlparse
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.python_contract import (
    PYTHON_ARTIFACT_MAX_BYTES,
    PYTHON_OUTPUT_EXCERPT_MAX_CHARS,
    PYTHON_SUMMARY_MAX_CHARS,
    PythonArtifactType,
    PythonDeniedReason,
    PythonExecutionProfile,
    PythonExecutionStatus,
    PythonInfraFailureReason,
    PythonLimitName,
    PythonPolicyErrorCode,
    SAFE_ARTIFACT_NAME_RE,
)


class PythonExecutionArtifact(BaseModel):
    model_config = ConfigDict(extra="forbid")

    artifact_id: UUID
    name: str = Field(min_length=1, max_length=128)
    artifact_type: PythonArtifactType
    size_bytes: int = Field(ge=1, le=PYTHON_ARTIFACT_MAX_BYTES)
    download_path: str = Field(min_length=1, max_length=255)

    @field_validator("name")
    @classmethod
    def validate_name(cls, value: str) -> str:
        if not SAFE_ARTIFACT_NAME_RE.fullmatch(value):
            raise ValueError("Artifact names must be safe reviewed filenames.")
        return value

    @field_validator("download_path")
    @classmethod
    def validate_download_path(cls, value: str) -> str:
        parsed = urlparse(value)
        if parsed.scheme or parsed.netloc:
            raise ValueError("Artifact download paths must stay API-relative.")
        if not value.startswith("/api/python/artifacts/"):
            raise ValueError("Artifact download paths must use the approved Python artifact route.")
        return value


class PythonExecutionResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    execution_id: UUID
    status: PythonExecutionStatus
    summary: str = Field(min_length=1, max_length=PYTHON_SUMMARY_MAX_CHARS)
    duration_ms: int | None = Field(default=None, ge=0)
    profile_name: PythonExecutionProfile | None = None
    stdout_excerpt: str | None = Field(default=None, max_length=PYTHON_OUTPUT_EXCERPT_MAX_CHARS)
    stderr_excerpt: str | None = Field(default=None, max_length=PYTHON_OUTPUT_EXCERPT_MAX_CHARS)
    artifacts: list[PythonExecutionArtifact] = Field(default_factory=list, max_length=4)
    limit_triggered: PythonLimitName | None = None
    denial_reason: PythonDeniedReason | None = None
    policy_error_code: PythonPolicyErrorCode | None = None
    infra_failure_reason: PythonInfraFailureReason | None = None
    retryable: bool = False
    correlation_id: str | None = Field(default=None, max_length=64)

    @model_validator(mode="after")
    def validate_state_specific_fields(self) -> "PythonExecutionResult":
        terminal_artifact_statuses = {
            PythonExecutionStatus.succeeded,
            PythonExecutionStatus.limit_reached,
        }

        if self.profile_name is None and self.status is not PythonExecutionStatus.denied:
            raise ValueError("Non-denied Python states must carry a reviewed profile name.")

        if self.status is PythonExecutionStatus.denied:
            if self.denial_reason is None:
                raise ValueError("Denied results must name the denial reason.")
            if self.duration_ms is not None:
                raise ValueError("Denied results must not report execution duration.")
            if self.stdout_excerpt is not None or self.stderr_excerpt is not None:
                raise ValueError("Denied results must not expose runtime output.")
        elif self.denial_reason is not None:
            raise ValueError("Only denied results may include a denial reason.")

        if self.status is PythonExecutionStatus.policy_error:
            if self.policy_error_code is None:
                raise ValueError("Policy error results must include a reviewed policy error code.")
        elif self.policy_error_code is not None:
            raise ValueError("Only policy error results may include a policy error code.")

        if self.status is PythonExecutionStatus.infra_failure:
            if self.infra_failure_reason is None:
                raise ValueError("Infrastructure failures must include a reviewed failure reason.")
        elif self.infra_failure_reason is not None:
            raise ValueError("Only infrastructure failures may include an infrastructure failure reason.")

        if self.retryable and self.status is not PythonExecutionStatus.infra_failure:
            raise ValueError("Only infrastructure failures may be retryable.")

        if self.status is PythonExecutionStatus.limit_reached:
            if self.limit_triggered is None:
                raise ValueError("Limit-reached results must identify the exact terminating limit.")
            if self.duration_ms is None:
                raise ValueError("Limit-reached results must report bounded duration.")
        elif self.limit_triggered is not None:
            raise ValueError("Only limit-reached results may expose a terminating limit.")

        if self.status is PythonExecutionStatus.succeeded and self.duration_ms is None:
            raise ValueError("Succeeded results must report bounded duration.")

        if self.status in {
            PythonExecutionStatus.accepted,
            PythonExecutionStatus.running,
            PythonExecutionStatus.denied,
            PythonExecutionStatus.policy_error,
            PythonExecutionStatus.infra_failure,
        } and self.artifacts:
            raise ValueError("Artifacts are allowed only after a bounded execution produces reviewed output.")

        if self.status not in terminal_artifact_statuses and self.limit_triggered is not None:
            raise ValueError("Only bounded terminal states may expose a terminating limit.")

        return self

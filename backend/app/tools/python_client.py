from __future__ import annotations

import base64
from dataclasses import dataclass
from typing import Any
from uuid import UUID

import httpx
from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator

from app.core.config import Settings
from app.python_contract import (
    PYTHON_ARTIFACT_MAX_BYTES,
    PYTHON_OUTPUT_EXCERPT_MAX_CHARS,
    PYTHON_STATE_MAX_BYTES,
    PYTHON_SUMMARY_MAX_CHARS,
    SAFE_ARTIFACT_NAME_RE,
    PythonArtifactType,
    PythonDeniedReason,
    PythonExecutionProfile,
    PythonExecutionStatus,
    PythonInfraFailureReason,
    PythonLimitName,
    PythonPolicyErrorCode,
)
from app.schemas.python import PythonExecutionResult


STATE_SNAPSHOT_B64_MAX_CHARS = 400_000
CAPABILITY_MAX_CHARS = 4_096


class SupervisorExecutionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    execution_id: UUID
    capability: str = Field(min_length=1, max_length=CAPABILITY_MAX_CHARS)
    profile_name: PythonExecutionProfile
    code: str = Field(min_length=1, max_length=16_000)
    correlation_id: str | None = Field(default=None, max_length=64)
    state_snapshot_b64: str | None = Field(default=None, max_length=STATE_SNAPSHOT_B64_MAX_CHARS)

    @field_validator("state_snapshot_b64")
    @classmethod
    def validate_state_snapshot(cls, value: str | None) -> str | None:
        if value is None:
            return None
        raw = base64.b64decode(value.encode("ascii"), validate=True)
        if len(raw) > PYTHON_STATE_MAX_BYTES:
            raise ValueError("state_snapshot_b64 exceeds the reviewed state size limit.")
        return value


class SupervisorArtifactPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    artifact_id: str = Field(min_length=1, max_length=64)
    name: str = Field(min_length=1, max_length=128)
    artifact_type: PythonArtifactType
    size_bytes: int = Field(ge=1, le=PYTHON_ARTIFACT_MAX_BYTES)
    sha256: str = Field(min_length=64, max_length=64)
    content_base64: str = Field(min_length=1)

    @field_validator("name")
    @classmethod
    def validate_name(cls, value: str) -> str:
        if not SAFE_ARTIFACT_NAME_RE.fullmatch(value):
            raise ValueError("Artifact names must be safe reviewed filenames.")
        return value

    @field_validator("content_base64")
    @classmethod
    def validate_content_base64(cls, value: str, info) -> str:
        raw = base64.b64decode(value.encode("ascii"), validate=True)
        size_bytes = info.data.get("size_bytes")
        if isinstance(size_bytes, int) and len(raw) != size_bytes:
            raise ValueError("Artifact size did not match the reviewed payload size.")
        return value


class SupervisorExecutionResponseEnvelope(BaseModel):
    model_config = ConfigDict(extra="forbid")

    execution_id: UUID
    status: PythonExecutionStatus
    summary: str = Field(min_length=1, max_length=PYTHON_SUMMARY_MAX_CHARS)
    duration_ms: int | None = Field(default=None, ge=0)
    profile_name: PythonExecutionProfile | None = None
    stdout_excerpt: str | None = Field(default=None, max_length=PYTHON_OUTPUT_EXCERPT_MAX_CHARS)
    stderr_excerpt: str | None = Field(default=None, max_length=PYTHON_OUTPUT_EXCERPT_MAX_CHARS)
    artifacts: list[SupervisorArtifactPayload] = Field(default_factory=list, max_length=4)
    limit_triggered: PythonLimitName | None = None
    denial_reason: PythonDeniedReason | None = None
    policy_error_code: PythonPolicyErrorCode | None = None
    infra_failure_reason: PythonInfraFailureReason | None = None
    retryable: bool = False
    correlation_id: str | None = Field(default=None, max_length=64)
    state_snapshot_b64: str | None = Field(default=None, max_length=STATE_SNAPSHOT_B64_MAX_CHARS)

    @field_validator("state_snapshot_b64")
    @classmethod
    def validate_state_snapshot(cls, value: str | None) -> str | None:
        if value is None:
            return None
        raw = base64.b64decode(value.encode("ascii"), validate=True)
        if len(raw) > PYTHON_STATE_MAX_BYTES:
            raise ValueError("state_snapshot_b64 exceeds the reviewed state size limit.")
        return value


@dataclass(frozen=True, slots=True)
class PythonExecutionInvocation:
    execution_id: UUID
    capability: str
    profile_name: PythonExecutionProfile
    code: str
    correlation_id: str | None = None
    state_snapshot: bytes | None = None


@dataclass(frozen=True, slots=True)
class PythonArtifactPayload:
    name: str
    artifact_type: PythonArtifactType
    size_bytes: int
    sha256: str
    content: bytes


@dataclass(frozen=True, slots=True)
class PythonExecutionResponse:
    result: PythonExecutionResult
    artifacts: tuple[PythonArtifactPayload, ...] = ()
    snapshot_blob: bytes | None = None


class PythonClient:
    def __init__(self, *, settings: Settings) -> None:
        self._settings = settings
        self._execute_url = f"{settings.python_supervisor_base_url.rstrip('/')}/execute"

    async def execute(self, invocation: PythonExecutionInvocation) -> PythonExecutionResponse:
        first_attempt = await self._execute_once(invocation)
        if self._should_retry(first_attempt):
            return await self._execute_once(invocation)
        return first_attempt

    async def _execute_once(self, invocation: PythonExecutionInvocation) -> PythonExecutionResponse:
        payload = SupervisorExecutionRequest.model_validate(
            {
                "execution_id": invocation.execution_id,
                "capability": invocation.capability,
                "profile_name": invocation.profile_name,
                "code": invocation.code,
                "correlation_id": invocation.correlation_id,
                "state_snapshot_b64": (
                    base64.b64encode(invocation.state_snapshot).decode("ascii")
                    if invocation.state_snapshot is not None
                    else None
                ),
            }
        )

        try:
            async with httpx.AsyncClient(timeout=self._settings.python_supervisor_request_timeout_seconds) as client:
                response = await client.post(self._execute_url, json=payload.model_dump(mode="json"))
        except httpx.RequestError as exc:
            return _infra_failure_response(
                execution_id=invocation.execution_id,
                profile_name=invocation.profile_name,
                correlation_id=invocation.correlation_id,
                reason=PythonInfraFailureReason.worker_unavailable,
                retryable=False,
                stderr_excerpt=str(exc),
            )

        if response.status_code == 200:
            return self._translate_success_payload(
                response=response,
                fallback_execution_id=invocation.execution_id,
                fallback_profile=invocation.profile_name,
                correlation_id=invocation.correlation_id,
            )

        retryable = response.status_code == 503
        reason = PythonInfraFailureReason.worker_start_failed if retryable else PythonInfraFailureReason.worker_unavailable
        return _infra_failure_response(
            execution_id=invocation.execution_id,
            profile_name=invocation.profile_name,
            correlation_id=invocation.correlation_id,
            reason=reason,
            retryable=retryable,
            stderr_excerpt=_safe_error_excerpt(response),
        )

    def _translate_success_payload(
        self,
        *,
        response: httpx.Response,
        fallback_execution_id: UUID,
        fallback_profile: PythonExecutionProfile,
        correlation_id: str | None,
    ) -> PythonExecutionResponse:
        try:
            envelope = SupervisorExecutionResponseEnvelope.model_validate(response.json())
        except (ValidationError, ValueError) as exc:
            return _infra_failure_response(
                execution_id=fallback_execution_id,
                profile_name=fallback_profile,
                correlation_id=correlation_id,
                reason=PythonInfraFailureReason.worker_unavailable,
                retryable=False,
                stderr_excerpt=str(exc),
            )

        artifacts = tuple(
            PythonArtifactPayload(
                name=artifact.name,
                artifact_type=artifact.artifact_type,
                size_bytes=artifact.size_bytes,
                sha256=artifact.sha256,
                content=base64.b64decode(artifact.content_base64.encode("ascii"), validate=True),
            )
            for artifact in envelope.artifacts
        )
        snapshot_blob = (
            base64.b64decode(envelope.state_snapshot_b64.encode("ascii"), validate=True)
            if envelope.state_snapshot_b64
            else None
        )
        result = PythonExecutionResult(
            execution_id=envelope.execution_id,
            status=envelope.status,
            summary=envelope.summary,
            duration_ms=envelope.duration_ms,
            profile_name=envelope.profile_name,
            stdout_excerpt=envelope.stdout_excerpt,
            stderr_excerpt=envelope.stderr_excerpt,
            artifacts=[],
            limit_triggered=envelope.limit_triggered,
            denial_reason=envelope.denial_reason,
            policy_error_code=envelope.policy_error_code,
            infra_failure_reason=envelope.infra_failure_reason,
            retryable=envelope.retryable,
            correlation_id=envelope.correlation_id,
        )
        return PythonExecutionResponse(result=result, artifacts=artifacts, snapshot_blob=snapshot_blob)

    @staticmethod
    def _should_retry(response: PythonExecutionResponse) -> bool:
        return (
            response.result.status is PythonExecutionStatus.infra_failure
            and response.result.infra_failure_reason is PythonInfraFailureReason.worker_start_failed
            and response.result.retryable
        )


def _infra_failure_response(
    *,
    execution_id: UUID,
    profile_name: PythonExecutionProfile,
    correlation_id: str | None,
    reason: PythonInfraFailureReason,
    retryable: bool,
    stderr_excerpt: str | None,
) -> PythonExecutionResponse:
    result = PythonExecutionResult(
        execution_id=execution_id,
        status=PythonExecutionStatus.infra_failure,
        summary="Trusted supervisor could not complete the reviewed Python execution.",
        duration_ms=None,
        profile_name=profile_name,
        stdout_excerpt=None,
        stderr_excerpt=_trim_text(stderr_excerpt),
        artifacts=[],
        limit_triggered=None,
        denial_reason=None,
        policy_error_code=None,
        infra_failure_reason=reason,
        retryable=retryable,
        correlation_id=correlation_id,
    )
    return PythonExecutionResponse(result=result)


def _safe_error_excerpt(response: httpx.Response) -> str | None:
    try:
        payload: Any = response.json()
    except ValueError:
        payload = response.text

    if isinstance(payload, dict):
        message = payload.get("message") or payload.get("error")
        if isinstance(message, str):
            return _trim_text(message)
        return _trim_text(str(payload))
    return _trim_text(str(payload))


def _trim_text(value: str | None) -> str | None:
    if value is None:
        return None
    if len(value) <= PYTHON_OUTPUT_EXCERPT_MAX_CHARS:
        return value
    return value[: PYTHON_OUTPUT_EXCERPT_MAX_CHARS - 3] + "..."

from __future__ import annotations

import re
from typing import Iterable
from uuid import UUID

from app.authorization.policy import PolicyResult, Scope, evaluate_required_scopes
from app.python_contract import PythonArtifactType, PythonDeniedReason, PythonExecutionProfile
from app.schemas.python import PythonExecutionResult


PYTHON_INTENT_PATTERNS = (
    r"\bpython\b",
    r"\bcalculate\b",
    r"\bcompute\b",
    r"\bsum\b",
    r"\baverage\b",
    r"\bmedian\b",
    r"\bmatrix\b",
    r"\bdataframe\b",
    r"\bdataset\b",
    r"\bcsv\b",
    r"\bjson\b",
    r"\bpng\b",
    r"\bplot\b",
    r"\bchart\b",
    r"\bgraph\b",
    r"\btransform\b",
    r"\bclean\b",
    r"\bparse\b",
    r"\bexport\b",
    r"\btính\b",
    r"\bdữ liệu\b",
    r"\bbiểu đồ\b",
    r"\blàm sạch\b",
    r"\bnhóm\b",
)
EXTERNAL_DATA_PATTERNS = (
    r"\bsearch\b",
    r"\bweb\b",
    r"\binternet\b",
    r"\blook up\b",
    r"\blatest\b",
    r"\bcurrent\b",
    r"\btoday\b",
    r"\bnews\b",
    r"\bweather\b",
    r"\bprice\b",
    r"\bapi\b",
    r"\bmới nhất\b",
    r"\bhôm nay\b",
    r"\btìm\b",
    r"\btra cứu\b",
    r"\bweb\b",
    r"\binternet\b",
    r"\bapi ngoài\b",
)
DATA_PROFILE_PATTERNS = (
    r"\bcsv\b",
    r"\bjson\b",
    r"\bpng\b",
    r"\bdataframe\b",
    r"\bdataset\b",
    r"\bpandas\b",
    r"\bnumpy\b",
    r"\bgroup\b",
    r"\baggregate\b",
    r"\bchart\b",
    r"\bplot\b",
    r"\bgraph\b",
    r"\brows\b",
    r"\bcolumns\b",
    r"\bdữ liệu\b",
    r"\bbiểu đồ\b",
    r"\bnhóm\b",
    r"\btập tin\b",
)
WHITESPACE_RE = re.compile(r"\s+")


def collapse_text(value: str, *, max_chars: int = 240) -> str:
    collapsed = WHITESPACE_RE.sub(" ", value).strip()
    if len(collapsed) <= max_chars:
        return collapsed
    return f"{collapsed[: max_chars - 3].rstrip()}..."


def prompt_requests_python(prompt: str) -> bool:
    lowered = prompt.lower()
    return any(re.search(pattern, lowered) for pattern in PYTHON_INTENT_PATTERNS) or "```" in prompt


def prompt_requires_external_search(prompt: str) -> bool:
    lowered = prompt.lower()
    return prompt_requests_python(prompt) and any(re.search(pattern, lowered) for pattern in EXTERNAL_DATA_PATTERNS)


def python_scope_allowed(principal_scopes: set[str]) -> bool:
    result = evaluate_required_scopes(principal_scopes=principal_scopes, required={Scope.tool_python.value})
    return result is PolicyResult.allow


def select_python_profile(
    *,
    prompt: str,
    requested_artifacts: Iterable[PythonArtifactType],
    active_profile: PythonExecutionProfile | None = None,
) -> PythonExecutionProfile:
    requested_set = set(requested_artifacts)
    if requested_set & {PythonArtifactType.csv, PythonArtifactType.json, PythonArtifactType.png}:
        return PythonExecutionProfile.data

    lowered = prompt.lower()
    if any(re.search(pattern, lowered) for pattern in DATA_PROFILE_PATTERNS):
        return PythonExecutionProfile.data

    if active_profile is PythonExecutionProfile.data and requested_set:
        return PythonExecutionProfile.data

    return PythonExecutionProfile.basic


def build_denied_result(
    *,
    execution_id: UUID,
    reason: PythonDeniedReason,
    correlation_id: str | None,
) -> PythonExecutionResult:
    summary = {
        PythonDeniedReason.missing_permission: (
            "Python execution was denied because this account does not have the required tool permission."
        ),
        PythonDeniedReason.search_required: (
            "This request needs search data before Python can run, and v1 allows only one tool per turn."
        ),
        PythonDeniedReason.policy_denied: "Python execution was denied by backend policy before the sandbox started.",
    }[reason]
    return PythonExecutionResult(
        execution_id=execution_id,
        status="denied",
        summary=summary,
        duration_ms=None,
        profile_name=None,
        stdout_excerpt=None,
        stderr_excerpt=None,
        artifacts=[],
        limit_triggered=None,
        denial_reason=reason,
        policy_error_code=None,
        infra_failure_reason=None,
        retryable=False,
        correlation_id=correlation_id,
    )


def tool_execution_terminal_status(result: PythonExecutionResult) -> str:
    return result.status.value


def tool_execution_output_summary(result: PythonExecutionResult) -> str:
    parts = [collapse_text(result.summary, max_chars=320), f"status={result.status.value}"]
    if result.limit_triggered is not None:
        parts.append(f"limit={result.limit_triggered.value}")
    if result.denial_reason is not None:
        parts.append(f"denial={result.denial_reason.value}")
    if result.policy_error_code is not None:
        parts.append(f"policy={result.policy_error_code.value}")
    if result.infra_failure_reason is not None:
        parts.append(f"infra={result.infra_failure_reason.value}")
    return " | ".join(parts)

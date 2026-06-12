from __future__ import annotations

import ast
import base64
import io
import json
import os
import pickle
import sys
import time
import traceback
from contextlib import redirect_stderr, redirect_stdout
from dataclasses import dataclass
from pathlib import Path
from typing import Any


CURRENT_DIR = Path(__file__).resolve().parent
if str(CURRENT_DIR) not in sys.path:
    sys.path.insert(0, str(CURRENT_DIR))

from allowed_artifacts import (  # noqa: E402
    ArtifactCountLimitExceeded,
    ArtifactPolicyError,
    ArtifactSizeLimitExceeded,
    collect_reviewed_artifacts,
)


APPROVED_IMPORT_ROOTS = {
    "collections",
    "csv",
    "datetime",
    "decimal",
    "fractions",
    "functools",
    "io",
    "itertools",
    "json",
    "math",
    "matplotlib",
    "numpy",
    "os",
    "pandas",
    "pathlib",
    "random",
    "re",
    "statistics",
    "string",
    "textwrap",
}
BLOCKED_IMPORT_ROOTS = {
    "asyncio",
    "ctypes",
    "ensurepip",
    "ftplib",
    "http",
    "importlib",
    "multiprocessing",
    "pip",
    "requests",
    "socket",
    "ssl",
    "subprocess",
    "telnetlib",
    "urllib",
    "venv",
}
FORBIDDEN_NAME_CALLS = {"compile", "eval", "exec", "__import__"}
FORBIDDEN_ATTRIBUTE_CHAINS = {
    ("os", "popen"),
    ("os", "system"),
    ("socket", "create_connection"),
    ("socket", "socket"),
    ("subprocess", "Popen"),
    ("subprocess", "call"),
    ("subprocess", "check_call"),
    ("subprocess", "check_output"),
    ("subprocess", "run"),
    ("urllib", "request", "urlopen"),
}
MAX_STDIO_EXCERPT_CHARS = 8_192
MAX_STATE_SNAPSHOT_BYTES = 256 * 1024
RESULT_LOG_PREFIX = "SIMPAGENT_RESULT_JSON="


class OutputLimitExceeded(RuntimeError):
    pass


@dataclass(frozen=True)
class RunSpec:
    execution_id: str
    profile_name: str
    code: str
    workspace_dir: str
    artifact_dir: str
    result_path: str
    output_limit_bytes: int
    artifact_limit_bytes: int
    max_artifacts: int
    state_snapshot_b64: str | None = None

    @classmethod
    def from_payload(cls, payload: dict[str, Any]) -> "RunSpec":
        return cls(
            execution_id=str(payload["execution_id"]),
            profile_name=str(payload["profile_name"]),
            code=str(payload["code"]),
            workspace_dir=str(payload["workspace_dir"]),
            artifact_dir=str(payload["artifact_dir"]),
            result_path=str(payload["result_path"]),
            output_limit_bytes=int(payload["output_limit_bytes"]),
            artifact_limit_bytes=int(payload["artifact_limit_bytes"]),
            max_artifacts=int(payload["max_artifacts"]),
            state_snapshot_b64=str(payload["state_snapshot_b64"]) if payload.get("state_snapshot_b64") else None,
        )


@dataclass(frozen=True)
class PolicyReview:
    allowed: bool
    policy_error_code: str | None = None
    message: str | None = None
    blocked_symbol: str | None = None


def _attribute_chain(node: ast.AST) -> tuple[str, ...]:
    parts: list[str] = []
    current = node
    while isinstance(current, ast.Attribute):
        parts.append(current.attr)
        current = current.value
    if isinstance(current, ast.Name):
        parts.append(current.id)
    return tuple(reversed(parts))


class PolicyVisitor(ast.NodeVisitor):
    def __init__(self) -> None:
        self.review = PolicyReview(allowed=True)

    def _set_review(self, review: PolicyReview) -> None:
        if self.review.allowed:
            self.review = review

    def visit_Import(self, node: ast.Import) -> None:
        for alias in node.names:
            root = alias.name.split(".", 1)[0]
            if root in BLOCKED_IMPORT_ROOTS or root not in APPROVED_IMPORT_ROOTS:
                self._set_review(
                    PolicyReview(
                        allowed=False,
                        policy_error_code="blocked_import",
                        blocked_symbol=root,
                        message=f"Import '{root}' is not in the reviewed Python allowlist.",
                    )
                )
        self.generic_visit(node)

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        if node.module:
            root = node.module.split(".", 1)[0]
            if root in BLOCKED_IMPORT_ROOTS or root not in APPROVED_IMPORT_ROOTS:
                self._set_review(
                    PolicyReview(
                        allowed=False,
                        policy_error_code="blocked_import",
                        blocked_symbol=root,
                        message=f"Import '{root}' is not in the reviewed Python allowlist.",
                    )
                )
        self.generic_visit(node)

    def visit_Call(self, node: ast.Call) -> None:
        if isinstance(node.func, ast.Name) and node.func.id in FORBIDDEN_NAME_CALLS:
            self._set_review(
                PolicyReview(
                    allowed=False,
                    policy_error_code="disallowed_behavior",
                    blocked_symbol=node.func.id,
                    message=f"Calling '{node.func.id}' is not permitted in the reviewed Python sandbox.",
                )
            )
        else:
            chain = _attribute_chain(node.func)
            if chain in FORBIDDEN_ATTRIBUTE_CHAINS:
                self._set_review(
                    PolicyReview(
                        allowed=False,
                        policy_error_code="disallowed_behavior",
                        blocked_symbol=".".join(chain),
                        message=f"Calling '{'.'.join(chain)}' is not permitted in the reviewed Python sandbox.",
                    )
                )
        self.generic_visit(node)


class SharedOutputBudget:
    def __init__(self, limit_bytes: int) -> None:
        self.remaining = limit_bytes


class BoundedTextBuffer(io.TextIOBase):
    def __init__(self, budget: SharedOutputBudget) -> None:
        self._budget = budget
        self._chunks: list[str] = []

    def write(self, text: str) -> int:
        encoded = text.encode("utf-8", errors="replace")
        if self._budget.remaining <= 0:
            raise OutputLimitExceeded("Combined stdout/stderr output exceeded the reviewed limit.")

        if len(encoded) > self._budget.remaining:
            partial = encoded[: self._budget.remaining].decode("utf-8", errors="ignore")
            if partial:
                self._chunks.append(partial)
            self._budget.remaining = 0
            raise OutputLimitExceeded("Combined stdout/stderr output exceeded the reviewed limit.")

        self._chunks.append(text)
        self._budget.remaining -= len(encoded)
        return len(text)

    def flush(self) -> None:
        return

    def getvalue(self) -> str:
        return "".join(self._chunks)


def trim_text(value: str | None, *, limit: int = MAX_STDIO_EXCERPT_CHARS) -> str | None:
    if value is None:
        return None
    if len(value) <= limit:
        return value
    return value[: limit - 3] + "..."


def review_python_source(source: str) -> PolicyReview:
    visitor = PolicyVisitor()
    visitor.visit(ast.parse(source, filename="<sandbox-user-code>"))
    return visitor.review


def build_result(
    *,
    spec: RunSpec,
    status: str,
    summary: str,
    stdout_excerpt: str | None,
    stderr_excerpt: str | None,
    artifacts: list[dict[str, Any]],
    limit_triggered: str | None = None,
    policy_error_code: str | None = None,
    state_snapshot_b64: str | None = None,
) -> dict[str, Any]:
    return {
        "execution_id": spec.execution_id,
        "status": status,
        "summary": summary,
        "duration_ms": None,
        "profile_name": spec.profile_name,
        "stdout_excerpt": trim_text(stdout_excerpt),
        "stderr_excerpt": trim_text(stderr_excerpt),
        "artifacts": artifacts,
        "limit_triggered": limit_triggered,
        "denial_reason": None,
        "policy_error_code": policy_error_code,
        "infra_failure_reason": None,
        "retryable": False,
        "correlation_id": None,
        "state_snapshot_b64": state_snapshot_b64,
    }


def execute_run_spec(spec: RunSpec) -> dict[str, Any]:
    started_at = time.perf_counter()
    workspace_dir = Path(spec.workspace_dir)
    artifact_dir = Path(spec.artifact_dir)
    workspace_dir.mkdir(parents=True, exist_ok=True)
    artifact_dir.mkdir(parents=True, exist_ok=True)
    previous_cwd = Path.cwd()
    os.chdir(workspace_dir)

    try:
        review = review_python_source(spec.code)
        if not review.allowed:
            result = build_result(
                spec=spec,
                status="policy_error",
                summary="Execution stopped before running because the code requested behavior outside the reviewed sandbox policy.",
                stdout_excerpt=None,
                stderr_excerpt=review.message,
                artifacts=[],
                policy_error_code=review.policy_error_code,
                state_snapshot_b64=None,
            )
            result["duration_ms"] = int((time.perf_counter() - started_at) * 1000)
            return result

        budget = SharedOutputBudget(spec.output_limit_bytes)
        stdout_buffer = BoundedTextBuffer(budget)
        stderr_buffer = BoundedTextBuffer(budget)
        namespace = {"__name__": "__main__", **_restore_state_namespace(spec.state_snapshot_b64)}

        try:
            with redirect_stdout(stdout_buffer), redirect_stderr(stderr_buffer):
                compiled = compile(spec.code, "<sandbox-user-code>", "exec")
                exec(compiled, namespace, namespace)

            reviewed_artifacts = [
                artifact.as_payload()
                for artifact in collect_reviewed_artifacts(
                    artifact_dir,
                    max_artifacts=spec.max_artifacts,
                    max_bytes=spec.artifact_limit_bytes,
                )
            ]
            summary = (
                f"Reviewed Python execution completed and produced {len(reviewed_artifacts)} approved artifacts."
                if reviewed_artifacts
                else "Reviewed Python execution completed successfully."
            )
            result = build_result(
                spec=spec,
                status="succeeded",
                summary=summary,
                stdout_excerpt=stdout_buffer.getvalue() or None,
                stderr_excerpt=stderr_buffer.getvalue() or None,
                artifacts=reviewed_artifacts,
                state_snapshot_b64=_encode_state_snapshot(namespace),
            )
        except OutputLimitExceeded:
            result = build_result(
                spec=spec,
                status="limit_reached",
                summary="Execution stopped because stdout/stderr exceeded the reviewed output limit.",
                stdout_excerpt=stdout_buffer.getvalue() or None,
                stderr_excerpt=stderr_buffer.getvalue() or None,
                artifacts=[],
                limit_triggered="output_size",
                state_snapshot_b64=_encode_state_snapshot(namespace),
            )
        except (ArtifactSizeLimitExceeded, ArtifactCountLimitExceeded, ArtifactPolicyError) as exc:
            result = build_result(
                spec=spec,
                status="limit_reached",
                summary="Execution stopped because a reviewed artifact exceeded the sandbox file boundary.",
                stdout_excerpt=stdout_buffer.getvalue() or None,
                stderr_excerpt=str(exc),
                artifacts=[],
                limit_triggered="file_size",
                state_snapshot_b64=_encode_state_snapshot(namespace),
            )
        except Exception:
            try:
                traceback.print_exc(file=stderr_buffer)
                stderr_excerpt = stderr_buffer.getvalue() or None
                stdout_excerpt = stdout_buffer.getvalue() or None
                result = build_result(
                    spec=spec,
                    status="succeeded",
                    summary="Execution completed with a Python exception from user code.",
                    stdout_excerpt=stdout_excerpt,
                    stderr_excerpt=stderr_excerpt,
                    artifacts=[],
                    state_snapshot_b64=_encode_state_snapshot(namespace),
                )
            except OutputLimitExceeded:
                result = build_result(
                    spec=spec,
                    status="limit_reached",
                    summary="Execution stopped because stdout/stderr exceeded the reviewed output limit.",
                    stdout_excerpt=stdout_buffer.getvalue() or None,
                    stderr_excerpt=stderr_buffer.getvalue() or None,
                    artifacts=[],
                    limit_triggered="output_size",
                    state_snapshot_b64=_encode_state_snapshot(namespace),
                )

        result["duration_ms"] = int((time.perf_counter() - started_at) * 1000)
        return result
    finally:
        os.chdir(previous_cwd)


def load_run_spec_from_env() -> RunSpec:
    encoded_spec = os.environ["SIMPAGENT_RUN_SPEC_B64"]
    payload = json.loads(
        __import__("base64").urlsafe_b64decode(encoded_spec + "=" * (-len(encoded_spec) % 4)).decode(
            "utf-8"
        )
    )
    return RunSpec.from_payload(payload)


def write_result(result_path: Path, payload: dict[str, Any]) -> None:
    result_path.parent.mkdir(parents=True, exist_ok=True)
    result_path.write_text(json.dumps(payload), encoding="utf-8")


def emit_result_log(payload: dict[str, Any]) -> None:
    encoded = base64.b64encode(
        json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8")
    ).decode("ascii")
    print(f"{RESULT_LOG_PREFIX}{encoded}", flush=True)


def _restore_state_namespace(encoded_snapshot: str | None) -> dict[str, Any]:
    if not encoded_snapshot:
        return {}

    try:
        snapshot_blob = base64.b64decode(encoded_snapshot.encode("ascii"), validate=True)
        if len(snapshot_blob) > MAX_STATE_SNAPSHOT_BYTES:
            return {}
        payload = json.loads(snapshot_blob.decode("utf-8"))
        pickle_b64 = payload.get("pickle_b64")
        restored = pickle.loads(base64.b64decode(pickle_b64.encode("ascii"), validate=True))
        if not isinstance(restored, dict):
            return {}
    except Exception:
        return {}

    namespace: dict[str, Any] = {}
    for name, value in restored.items():
        if _eligible_state_name(name):
            namespace[name] = value
    return namespace


def _encode_state_snapshot(namespace: dict[str, Any]) -> str:
    snapshot_values: dict[str, Any] = {}
    for name in sorted(namespace):
        value = namespace[name]
        if not _eligible_state_name(name):
            continue
        candidate = dict(snapshot_values)
        candidate[name] = value
        try:
            candidate_pickle = pickle.dumps(candidate, protocol=pickle.HIGHEST_PROTOCOL)
        except Exception:
            continue

        encoded_pickle = base64.b64encode(candidate_pickle).decode("ascii")
        envelope = json.dumps(
            {
                "version": 1,
                "binding_names": sorted(candidate.keys()),
                "pickle_b64": encoded_pickle,
            },
            separators=(",", ":"),
            sort_keys=True,
        ).encode("utf-8")
        if len(envelope) > MAX_STATE_SNAPSHOT_BYTES:
            continue
        snapshot_values = candidate

    payload = json.dumps(
        {
            "version": 1,
            "binding_names": sorted(snapshot_values.keys()),
            "pickle_b64": base64.b64encode(
                pickle.dumps(snapshot_values, protocol=pickle.HIGHEST_PROTOCOL)
            ).decode("ascii"),
        },
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
    return base64.b64encode(payload).decode("ascii")


def _eligible_state_name(name: str) -> bool:
    return isinstance(name, str) and name.isidentifier() and not name.startswith("_")


def main() -> None:
    spec = load_run_spec_from_env()
    result = execute_run_spec(spec)
    write_result(Path(spec.result_path), result)
    emit_result_log(result)


if __name__ == "__main__":
    main()

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import subprocess
import tempfile
import time
from dataclasses import asdict, dataclass, field
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from uuid import uuid4


HEALTH_STATUS = "foundation_ready"
RUNTIME_IMAGE = os.getenv("SIMPAGENT_SANDBOX_RUNTIME_IMAGE", "simpagent-python-runtime:local")
DOCKER_BIN = os.getenv("SIMPAGENT_SANDBOX_DOCKER_BIN", "docker")
CAPABILITY_AUDIENCE = "sandbox-worker"
CAPABILITY_TYPE = "tool-capability+jwt"
CAPABILITY_SECRET_FILE = os.getenv("SIMPAGENT_SANDBOX_CAPABILITY_SECRET_FILE")


def _read_secret_file(path: str | None) -> str | None:
    if not path:
        return None
    candidate = Path(path)
    if not candidate.exists():
        return None
    return candidate.read_text(encoding="utf-8").strip()


CAPABILITY_SECRET = (
    os.getenv("SIMPAGENT_SANDBOX_CAPABILITY_SECRET")
    or _read_secret_file(CAPABILITY_SECRET_FILE)
    or "sandbox-dev-secret"
)
CAPABILITY_TTL_SECONDS = 60
MAX_CODE_CHARS = 16_000
MAX_REQUEST_BYTES = 96 * 1024
MAX_STDIO_EXCERPT_CHARS = 8_192
RUNTIME_SOURCE_ROOT = Path(__file__).resolve().parent / "runtime"
RESULT_LOG_PREFIX = "SIMPAGENT_RESULT_JSON="
SECCOMP_PROFILE_NAME = "docker-default"
SECCOMP_PROFILE_PATH: Path | None = None
# Docker already applies its default seccomp profile when no seccomp override is provided.
SECURITY_OPTS = ("no-new-privileges",)
CONTAINER_LABEL_PREFIX = "simpagent.python"
WORKSPACE_DIR = "/workspace"
ARTIFACT_DIR = f"{WORKSPACE_DIR}/artifacts"
RESULT_PATH = f"{WORKSPACE_DIR}/result.json"
STARTUP_GRACE_SECONDS = 2


def _sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _base64url_encode(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode("ascii")


def _base64url_decode(value: str) -> bytes:
    padding = "=" * (-len(value) % 4)
    return base64.urlsafe_b64decode(f"{value}{padding}")


def _json_dumps(payload: Any) -> str:
    return json.dumps(payload, separators=(",", ":"), sort_keys=True)


def trim_text(value: str | None, *, limit: int = MAX_STDIO_EXCERPT_CHARS) -> str | None:
    if value is None:
        return None
    if len(value) <= limit:
        return value
    return value[: limit - 3] + "..."


@dataclass(frozen=True)
class RuntimeProfile:
    name: str
    wall_time_seconds: int
    cpu_limit: float
    memory_bytes: int
    pids_limit: int
    workspace_tmpfs_size_mb: int
    output_limit_bytes: int
    artifact_limit_bytes: int
    max_artifacts: int

    @property
    def nano_cpus(self) -> int:
        return int(self.cpu_limit * 1_000_000_000)

    @property
    def workspace_tmpfs(self) -> str:
        return (
            f"{WORKSPACE_DIR}:rw,noexec,nosuid,nodev,size={self.workspace_tmpfs_size_mb}m"
        )


PROFILES: dict[str, RuntimeProfile] = {
    "python-basic-v1": RuntimeProfile(
        name="python-basic-v1",
        wall_time_seconds=8,
        cpu_limit=1.0,
        memory_bytes=384 * 1024 * 1024,
        pids_limit=32,
        workspace_tmpfs_size_mb=64,
        output_limit_bytes=16 * 1024,
        artifact_limit_bytes=128 * 1024,
        max_artifacts=4,
    ),
    "python-data-v1": RuntimeProfile(
        name="python-data-v1",
        wall_time_seconds=15,
        cpu_limit=2.0,
        memory_bytes=768 * 1024 * 1024,
        pids_limit=64,
        workspace_tmpfs_size_mb=128,
        output_limit_bytes=32 * 1024,
        artifact_limit_bytes=512 * 1024,
        max_artifacts=4,
    ),
}


@dataclass(frozen=True)
class ExecutionRequest:
    execution_id: str
    capability: str
    profile_name: str
    code: str
    correlation_id: str | None = None
    state_snapshot_b64: str | None = None

    @classmethod
    def from_payload(cls, payload: dict[str, Any]) -> "ExecutionRequest":
        expected_fields = {"execution_id", "capability", "profile_name", "code", "correlation_id", "state_snapshot_b64"}
        unknown_fields = set(payload) - expected_fields
        if unknown_fields:
            raise ValueError(f"Unknown supervisor request fields: {sorted(unknown_fields)}")

        execution_id = payload.get("execution_id")
        capability = payload.get("capability")
        profile_name = payload.get("profile_name")
        code = payload.get("code")
        correlation_id = payload.get("correlation_id")
        state_snapshot_b64 = payload.get("state_snapshot_b64")

        if not isinstance(execution_id, str) or not execution_id.strip():
            raise ValueError("execution_id is required.")
        if not isinstance(capability, str) or not capability.strip():
            raise ValueError("capability is required.")
        if not isinstance(profile_name, str) or profile_name not in PROFILES:
            raise ValueError("profile_name must be one of the reviewed backend-owned profiles.")
        if not isinstance(code, str) or not code.strip():
            raise ValueError("code is required.")
        if len(code) > MAX_CODE_CHARS:
            raise ValueError("code exceeds the reviewed sandbox input limit.")
        if correlation_id is not None and not isinstance(correlation_id, str):
            raise ValueError("correlation_id must be a string when provided.")
        if state_snapshot_b64 is not None and not isinstance(state_snapshot_b64, str):
            raise ValueError("state_snapshot_b64 must be a base64 string when provided.")

        return cls(
            execution_id=execution_id.strip(),
            capability=capability.strip(),
            profile_name=profile_name,
            code=code,
            correlation_id=correlation_id.strip() if correlation_id else None,
            state_snapshot_b64=state_snapshot_b64.strip() if state_snapshot_b64 else None,
        )


@dataclass(frozen=True)
class RuntimeLaunchSpec:
    container_name: str
    image: str
    profile_name: str
    command: tuple[str, ...]
    environment: dict[str, str]
    labels: dict[str, str]
    network_mode: str = "none"
    read_only_rootfs: bool = True
    user: str = "10002:10002"
    tmpfs_mounts: tuple[str, ...] = field(default_factory=tuple)
    cap_drop: tuple[str, ...] = ("ALL",)
    security_opt: tuple[str, ...] = SECURITY_OPTS
    pids_limit: int = 0
    memory_bytes: int = 0
    nano_cpus: int = 0
    bind_mounts: tuple[str, ...] = field(default_factory=tuple)
    devices: tuple[str, ...] = field(default_factory=tuple)
    dns: tuple[str, ...] = field(default_factory=tuple)
    extra_hosts: tuple[str, ...] = field(default_factory=tuple)


def issue_capability_token(
    *,
    execution_id: str,
    profile_name: str,
    code: str,
    state_snapshot_b64: str | None = None,
    now: int | None = None,
    ttl_seconds: int = CAPABILITY_TTL_SECONDS,
    secret: str = CAPABILITY_SECRET,
) -> str:
    issued_at = int(time.time() if now is None else now)
    payload = {
        "typ": CAPABILITY_TYPE,
        "aud": CAPABILITY_AUDIENCE,
        "jti": str(uuid4()),
        "execution_id": execution_id,
        "profile_name": profile_name,
        "code_hash": _sha256_text(code),
        "state_snapshot_hash": _sha256_text(state_snapshot_b64 or ""),
        "iat": issued_at,
        "exp": issued_at + ttl_seconds,
    }
    body = _base64url_encode(_json_dumps(payload).encode("utf-8"))
    signature = hmac.new(secret.encode("utf-8"), body.encode("ascii"), hashlib.sha256).digest()
    return f"{body}.{_base64url_encode(signature)}"


def verify_capability_token(
    token: str,
    *,
    request: ExecutionRequest,
    now: int | None = None,
    secret: str = CAPABILITY_SECRET,
) -> None:
    try:
        body, signature = token.split(".", 1)
    except ValueError as exc:
        raise ValueError("Malformed capability token.") from exc

    expected_signature = hmac.new(secret.encode("utf-8"), body.encode("ascii"), hashlib.sha256).digest()
    actual_signature = _base64url_decode(signature)
    if not hmac.compare_digest(expected_signature, actual_signature):
        raise ValueError("Capability signature mismatch.")

    payload = json.loads(_base64url_decode(body).decode("utf-8"))
    current_time = int(time.time() if now is None else now)

    if payload.get("typ") != CAPABILITY_TYPE:
        raise ValueError("Capability type mismatch.")
    if payload.get("aud") != CAPABILITY_AUDIENCE:
        raise ValueError("Capability audience mismatch.")
    if payload.get("execution_id") != request.execution_id:
        raise ValueError("Capability execution_id mismatch.")
    if payload.get("profile_name") != request.profile_name:
        raise ValueError("Capability profile_name mismatch.")
    if payload.get("code_hash") != _sha256_text(request.code):
        raise ValueError("Capability code hash mismatch.")
    if payload.get("state_snapshot_hash") != _sha256_text(request.state_snapshot_b64 or ""):
        raise ValueError("Capability state snapshot hash mismatch.")
    if not isinstance(payload.get("exp"), int) or payload["exp"] < current_time:
        raise ValueError("Capability token expired.")


def build_runtime_launch_spec(
    request: ExecutionRequest,
    profile: RuntimeProfile | None = None,
) -> RuntimeLaunchSpec:
    resolved_profile = profile or PROFILES[request.profile_name]
    run_spec = {
        "execution_id": request.execution_id,
        "profile_name": resolved_profile.name,
        "code": request.code,
        "workspace_dir": WORKSPACE_DIR,
        "artifact_dir": ARTIFACT_DIR,
        "result_path": RESULT_PATH,
        "output_limit_bytes": resolved_profile.output_limit_bytes,
        "artifact_limit_bytes": resolved_profile.artifact_limit_bytes,
        "max_artifacts": resolved_profile.max_artifacts,
        "state_snapshot_b64": request.state_snapshot_b64,
    }
    encoded_spec = _base64url_encode(_json_dumps(run_spec).encode("utf-8"))
    container_name = f"simpagent-python-{request.execution_id}"
    return RuntimeLaunchSpec(
        container_name=container_name,
        image=RUNTIME_IMAGE,
        profile_name=resolved_profile.name,
        command=("python", "/runtime/runner.py"),
        environment={
            "HOME": WORKSPACE_DIR,
            "MPLBACKEND": "Agg",
            "MPLCONFIGDIR": f"{WORKSPACE_DIR}/.matplotlib",
            "PYTHONUNBUFFERED": "1",
            "SIMPAGENT_RUN_SPEC_B64": encoded_spec,
        },
        labels={
            f"{CONTAINER_LABEL_PREFIX}.execution_id": request.execution_id,
            f"{CONTAINER_LABEL_PREFIX}.profile_name": resolved_profile.name,
        },
        tmpfs_mounts=(resolved_profile.workspace_tmpfs,),
        pids_limit=resolved_profile.pids_limit,
        memory_bytes=resolved_profile.memory_bytes,
        nano_cpus=resolved_profile.nano_cpus,
    )


def build_docker_create_command(spec: RuntimeLaunchSpec) -> list[str]:
    command = [
        DOCKER_BIN,
        "create",
        "--name",
        spec.container_name,
        "--network",
        spec.network_mode,
        "--user",
        spec.user,
        "--pids-limit",
        str(spec.pids_limit),
        "--memory",
        str(spec.memory_bytes),
        "--cpus",
        f"{spec.nano_cpus / 1_000_000_000:.2f}",
    ]

    if spec.read_only_rootfs:
        command.append("--read-only")

    for value in spec.cap_drop:
        command.extend(["--cap-drop", value])
    for value in spec.security_opt:
        command.extend(["--security-opt", value])
    for value in spec.tmpfs_mounts:
        command.extend(["--tmpfs", value])
    for value in spec.bind_mounts:
        command.extend(["--volume", value])
    for value in spec.devices:
        command.extend(["--device", value])
    for value in spec.dns:
        command.extend(["--dns", value])
    for value in spec.extra_hosts:
        command.extend(["--add-host", value])
    for key, value in spec.environment.items():
        command.extend(["--env", f"{key}={value}"])
    for key, value in spec.labels.items():
        command.extend(["--label", f"{key}={value}"])

    command.append(spec.image)
    command.extend(spec.command)
    return command


def build_runtime_image_command() -> list[str]:
    return [
        DOCKER_BIN,
        "build",
        "-f",
        str(RUNTIME_SOURCE_ROOT / "Dockerfile"),
        "-t",
        RUNTIME_IMAGE,
        str(RUNTIME_SOURCE_ROOT),
    ]


def _run_docker_command(
    command: list[str],
    *,
    check: bool = True,
    timeout: int | None = None,
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        command,
        check=check,
        capture_output=True,
        text=True,
        timeout=timeout,
    )


def ensure_runtime_image() -> None:
    inspect = _run_docker_command(
        [DOCKER_BIN, "image", "inspect", RUNTIME_IMAGE],
        check=False,
        timeout=10,
    )
    if inspect.returncode == 0:
        return
    _run_docker_command(build_runtime_image_command(), timeout=180)


def _read_result_payload(result_path: Path) -> dict[str, Any]:
    payload = json.loads(result_path.read_text(encoding="utf-8"))
    payload["stdout_excerpt"] = trim_text(payload.get("stdout_excerpt"))
    payload["stderr_excerpt"] = trim_text(payload.get("stderr_excerpt"))
    return payload


def _result_from_logs(output: str) -> dict[str, Any] | None:
    for line in reversed(output.splitlines()):
        if not line.startswith(RESULT_LOG_PREFIX):
            continue
        try:
            payload = json.loads(
                base64.b64decode(line.removeprefix(RESULT_LOG_PREFIX).encode("ascii")).decode("utf-8")
            )
        except Exception:
            continue
        payload["stdout_excerpt"] = trim_text(payload.get("stdout_excerpt"))
        payload["stderr_excerpt"] = trim_text(payload.get("stderr_excerpt"))
        return payload
    return None


def _load_runtime_result(container_name: str) -> dict[str, Any] | None:
    logs = _run_docker_command([DOCKER_BIN, "logs", container_name], check=False, timeout=10)
    payload = _result_from_logs(logs.stdout or "")
    if payload is not None:
        return payload

    with tempfile.TemporaryDirectory(prefix="simpagent-sandbox-result-") as temp_dir:
        result_path = Path(temp_dir) / "result.json"
        copy_result = _run_docker_command(
            [DOCKER_BIN, "cp", f"{container_name}:{RESULT_PATH}", str(result_path)],
            check=False,
            timeout=15,
        )
        if copy_result.returncode != 0 or not result_path.exists():
            return None
        return _read_result_payload(result_path)


def _infra_failure_result(
    *,
    execution_id: str,
    profile_name: str,
    correlation_id: str | None,
    reason: str,
    retryable: bool,
    stderr_excerpt: str | None,
) -> dict[str, Any]:
    return {
        "execution_id": execution_id,
        "status": "infra_failure",
        "summary": "Trusted supervisor could not complete the reviewed Python execution.",
        "duration_ms": None,
        "profile_name": profile_name,
        "stdout_excerpt": None,
        "stderr_excerpt": trim_text(stderr_excerpt),
        "artifacts": [],
        "limit_triggered": None,
        "denial_reason": None,
        "policy_error_code": None,
        "infra_failure_reason": reason,
        "retryable": retryable,
        "correlation_id": correlation_id,
    }


def _wall_time_limit_result(
    *,
    execution_id: str,
    profile_name: str,
    correlation_id: str | None,
    wall_time_seconds: int,
) -> dict[str, Any]:
    return {
        "execution_id": execution_id,
        "status": "limit_reached",
        "summary": "Execution stopped because it hit the reviewed wall-time limit.",
        "duration_ms": wall_time_seconds * 1000,
        "profile_name": profile_name,
        "stdout_excerpt": None,
        "stderr_excerpt": None,
        "artifacts": [],
        "limit_triggered": "wall_time",
        "denial_reason": None,
        "policy_error_code": None,
        "infra_failure_reason": None,
        "retryable": False,
        "correlation_id": correlation_id,
    }


def execute_request(request: ExecutionRequest) -> dict[str, Any]:
    try:
        verify_capability_token(request.capability, request=request)
    except ValueError as exc:
        raise PermissionError(str(exc)) from exc
    profile = PROFILES[request.profile_name]
    ensure_runtime_image()
    spec = build_runtime_launch_spec(request, profile)
    create_command = build_docker_create_command(spec)
    created = False

    try:
        _run_docker_command(create_command, timeout=20)
        created = True

        _run_docker_command([DOCKER_BIN, "start", spec.container_name], timeout=10)
        try:
            _run_docker_command(
                [DOCKER_BIN, "wait", spec.container_name],
                timeout=profile.wall_time_seconds + STARTUP_GRACE_SECONDS,
            )
        except subprocess.TimeoutExpired:
            _run_docker_command([DOCKER_BIN, "kill", spec.container_name], check=False, timeout=5)
            return _wall_time_limit_result(
                execution_id=request.execution_id,
                profile_name=profile.name,
                correlation_id=request.correlation_id,
                wall_time_seconds=profile.wall_time_seconds,
            )

        result = _load_runtime_result(spec.container_name)
        if result is not None:
            return result

        logs = _run_docker_command([DOCKER_BIN, "logs", spec.container_name], check=False, timeout=10)
        return _infra_failure_result(
            execution_id=request.execution_id,
            profile_name=profile.name,
            correlation_id=request.correlation_id,
            reason="worker_start_failed",
            retryable=True,
            stderr_excerpt=logs.stderr or logs.stdout,
        )
    except subprocess.CalledProcessError as exc:
        return _infra_failure_result(
            execution_id=request.execution_id,
            profile_name=profile.name,
            correlation_id=request.correlation_id,
            reason="worker_start_failed" if not created else "worker_unavailable",
            retryable=not created,
            stderr_excerpt=exc.stderr or exc.stdout,
        )
    finally:
        if created:
            _run_docker_command([DOCKER_BIN, "rm", "-f", spec.container_name], check=False, timeout=10)


def _health_payload() -> dict[str, Any]:
    docker_socket_present = Path("/var/run/docker.sock").exists()
    try:
        docker_control_ready = _run_docker_command(
            [DOCKER_BIN, "version"],
            check=False,
            timeout=3,
        ).returncode == 0
    except (OSError, subprocess.TimeoutExpired):
        docker_control_ready = False
    return {
        "status": HEALTH_STATUS if docker_control_ready else "runtime_unavailable",
        "mode": "trusted_supervisor",
        "runtime_image": RUNTIME_IMAGE,
        "profiles": [asdict(profile) for profile in PROFILES.values()],
        "docker_socket_present": docker_socket_present,
        "docker_control_ready": docker_control_ready,
        "seccomp_profile_name": SECCOMP_PROFILE_NAME,
        "seccomp_profile_path": str(SECCOMP_PROFILE_PATH) if SECCOMP_PROFILE_PATH is not None else None,
    }


class Handler(BaseHTTPRequestHandler):
    server_version = "SimpAgentSandbox/0.2"

    def do_GET(self) -> None:  # noqa: N802
        if self.path != "/health":
            self._send_json(HTTPStatus.NOT_FOUND, {"error": "not_found"})
            return
        self._send_json(HTTPStatus.OK, _health_payload())

    def do_POST(self) -> None:  # noqa: N802
        if self.path != "/execute":
            self._send_json(HTTPStatus.NOT_FOUND, {"error": "not_found"})
            return

        try:
            payload = self._read_json_body()
            request = ExecutionRequest.from_payload(payload)
            result = execute_request(request)
        except ValueError as exc:
            self._send_json(
                HTTPStatus.BAD_REQUEST,
                {"error": "invalid_request", "message": str(exc)},
            )
            return
        except PermissionError as exc:
            self._send_json(
                HTTPStatus.FORBIDDEN,
                {"error": "invalid_capability", "message": str(exc)},
            )
            return
        except subprocess.TimeoutExpired:
            self._send_json(
                HTTPStatus.SERVICE_UNAVAILABLE,
                {
                    "error": "worker_timeout",
                    "message": "Supervisor timed out while preparing the runtime worker.",
                },
            )
            return
        except Exception as exc:  # pragma: no cover - final guard for the supervisor HTTP surface
            self._send_json(
                HTTPStatus.INTERNAL_SERVER_ERROR,
                {"error": "supervisor_failure", "message": trim_text(str(exc), limit=512)},
            )
            return

        self._send_json(HTTPStatus.OK, result)

    def _read_json_body(self) -> dict[str, Any]:
        header = self.headers.get("Content-Length")
        if header is None:
            raise ValueError("Content-Length is required.")

        length = int(header)
        if length <= 0 or length > MAX_REQUEST_BYTES:
            raise ValueError("Request body size is outside the reviewed sandbox limit.")
        raw = self.rfile.read(length)
        return json.loads(raw.decode("utf-8"))

    def _send_json(self, status: HTTPStatus, payload: dict[str, Any]) -> None:
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status.value)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format: str, *args) -> None:  # noqa: A003
        return


def main() -> None:
    port = int(os.getenv("PORT", "8080"))
    ThreadingHTTPServer(("0.0.0.0", port), Handler).serve_forever()


if __name__ == "__main__":
    main()

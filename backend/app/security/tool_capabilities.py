from __future__ import annotations

import base64
import hashlib
import hmac
import json
from datetime import UTC, datetime
from uuid import UUID, uuid4

from app.core.config import Settings
from app.python_contract import PythonExecutionProfile


CAPABILITY_AUDIENCE = "sandbox-worker"
CAPABILITY_TYPE = "tool-capability+jwt"


def _base64url_encode(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode("ascii")


def _json_dumps(payload: dict[str, object]) -> str:
    return json.dumps(payload, separators=(",", ":"), sort_keys=True)


def _sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _timestamp(moment: datetime) -> int:
    return int(moment.astimezone(UTC).timestamp())


def issue_python_capability(
    *,
    execution_id: UUID,
    profile_name: PythonExecutionProfile,
    code: str,
    settings: Settings,
    now: datetime,
    state_snapshot: bytes | None = None,
) -> str:
    issued_at = _timestamp(now)
    expires_at = issued_at + settings.python_capability_ttl_seconds
    state_snapshot_b64 = base64.b64encode(state_snapshot).decode("ascii") if state_snapshot else ""
    payload = {
        "typ": CAPABILITY_TYPE,
        "aud": CAPABILITY_AUDIENCE,
        "jti": str(uuid4()),
        "execution_id": str(execution_id),
        "profile_name": profile_name.value,
        "code_hash": _sha256_text(code),
        "state_snapshot_hash": _sha256_text(state_snapshot_b64),
        "iat": issued_at,
        "exp": expires_at,
    }
    body = _base64url_encode(_json_dumps(payload).encode("utf-8"))
    signature = hmac.new(
        settings.python_capability_secret_value.encode("utf-8"),
        body.encode("ascii"),
        hashlib.sha256,
    ).digest()
    return f"{body}.{_base64url_encode(signature)}"

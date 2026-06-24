from __future__ import annotations

import base64
import hashlib
from datetime import UTC, datetime
from uuid import UUID, uuid4

import jwt

from app.core.config import Settings
from app.python_contract import PythonExecutionProfile


CAPABILITY_AUDIENCE = "sandbox-worker"
CAPABILITY_TYPE = "tool-capability+jwt"
CAPABILITY_ALGORITHM = "RS256"
CAPABILITY_TOOL = "python"


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
        "iss": settings.jwt_issuer,
        "aud": CAPABILITY_AUDIENCE,
        "tool": CAPABILITY_TOOL,
        "jti": str(uuid4()),
        "execution_id": str(execution_id),
        "profile_name": profile_name.value,
        "code_hash": _sha256_text(code),
        "state_snapshot_hash": _sha256_text(state_snapshot_b64),
        "iat": issued_at,
        "nbf": issued_at,
        "exp": expires_at,
    }
    headers = {
        "typ": CAPABILITY_TYPE,
        "kid": settings.jwt_active_kid,
        "alg": CAPABILITY_ALGORITHM,
    }
    return jwt.encode(
        payload,
        settings.jwt_private_key_value,
        algorithm=CAPABILITY_ALGORITHM,
        headers=headers,
    )

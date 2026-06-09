from __future__ import annotations

import base64
import hashlib
import hmac
import secrets
from datetime import datetime, timedelta
from uuid import UUID, uuid4

from app.core.config import Settings


REFRESH_COOKIE_NAME = "__Host-simpagent_refresh"
CSRF_COOKIE_NAME = "__Host-simpagent_csrf"
REFRESH_TOKEN_BYTES = 32


def _b64url(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def _unb64url(data: str) -> bytes:
    padding = "=" * ((4 - len(data) % 4) % 4)
    return base64.urlsafe_b64decode(f"{data}{padding}".encode("ascii"))


def generate_refresh_token() -> str:
    return _b64url(secrets.token_bytes(REFRESH_TOKEN_BYTES))


def lookup_digest(raw_token: str, settings: Settings) -> bytes:
    return hmac.digest(settings.refresh_hmac_key_value, raw_token.encode("utf-8"), hashlib.sha256)


def issue_refresh_expiry(*, now: datetime, settings: Settings, absolute_expires_at: datetime | None = None) -> datetime:
    candidate = now + timedelta(seconds=settings.refresh_idle_ttl_seconds)
    if absolute_expires_at is None:
        return candidate
    return min(candidate, absolute_expires_at)


def issue_family_absolute_expiry(*, now: datetime, settings: Settings) -> datetime:
    return now + timedelta(seconds=settings.refresh_absolute_ttl_seconds)


def issue_token_jti() -> str:
    return str(uuid4())


def parse_token(raw_token: str) -> bytes:
    return _unb64url(raw_token)

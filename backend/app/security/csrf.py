from __future__ import annotations

import base64
import hashlib
import hmac
import secrets
from uuid import UUID

from app.core.config import Settings


class CsrfValidationError(ValueError):
    pass


def _b64url(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def _unb64url(data: str) -> bytes:
    padding = "=" * ((4 - len(data) % 4) % 4)
    return base64.urlsafe_b64decode(f"{data}{padding}".encode("ascii"))


def issue_csrf_token(*, family_id: UUID, settings: Settings) -> str:
    nonce = secrets.token_bytes(32)
    mac = hmac.digest(settings.csrf_hmac_key_value, family_id.bytes + nonce, hashlib.sha256)
    return f"{_b64url(nonce)}.{_b64url(mac)}"


def validate_csrf_token(*, csrf_cookie: str | None, csrf_header: str | None, family_id: UUID, settings: Settings) -> None:
    if not csrf_cookie or not csrf_header or csrf_cookie != csrf_header:
        raise CsrfValidationError("Missing or mismatched CSRF token")
    try:
        nonce_raw, mac_raw = csrf_cookie.split(".", 1)
        nonce = _unb64url(nonce_raw)
        mac = _unb64url(mac_raw)
    except Exception as exc:  # pragma: no cover
        raise CsrfValidationError("Malformed CSRF token") from exc
    expected = hmac.digest(settings.csrf_hmac_key_value, family_id.bytes + nonce, hashlib.sha256)
    if not hmac.compare_digest(mac, expected):
        raise CsrfValidationError("Invalid CSRF token")


def require_allowed_origin(origin: str | None, settings: Settings) -> None:
    if origin not in set(settings.allowed_origins):
        raise CsrfValidationError("Origin is not allowed")

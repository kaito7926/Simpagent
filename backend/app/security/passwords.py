from __future__ import annotations

import hashlib
import hmac
import unicodedata
from dataclasses import dataclass

from app.core.config import COMMON_PASSWORD_BLOCKLIST

try:
    from pwdlib import PasswordHash
except ImportError:  # pragma: no cover
    PasswordHash = None  # type: ignore[assignment]


PASSWORD_MIN_CODEPOINTS = 15
PASSWORD_MAX_CODEPOINTS = 128
PASSWORD_MAX_UTF8_BYTES = 1024


@dataclass(frozen=True)
class PasswordValidationResult:
    normalized: str
    codepoints: int
    utf8_bytes: int


_PASSWORD_HASHER = PasswordHash.recommended() if PasswordHash is not None else None
_DUMMY_PASSWORD = "dummy-passphrase-for-simpagent"
_DUMMY_HASH = _PASSWORD_HASHER.hash(_DUMMY_PASSWORD) if _PASSWORD_HASHER is not None else "$argon2id$dummy"


def normalize_password(password: str) -> PasswordValidationResult:
    normalized = unicodedata.normalize("NFC", password)
    codepoints = len(normalized)
    utf8_bytes = len(normalized.encode("utf-8"))
    return PasswordValidationResult(normalized=normalized, codepoints=codepoints, utf8_bytes=utf8_bytes)


def validate_password(password: str, *, email_hint: str | None = None) -> PasswordValidationResult:
    result = normalize_password(password)
    if result.codepoints < PASSWORD_MIN_CODEPOINTS:
        raise ValueError("Password must be at least 15 characters.")
    if result.codepoints > PASSWORD_MAX_CODEPOINTS:
        raise ValueError("Password must not exceed 128 characters.")
    if result.utf8_bytes > PASSWORD_MAX_UTF8_BYTES:
        raise ValueError("Password is too large after normalization.")
    lowered = result.normalized.casefold()
    blocked = set(COMMON_PASSWORD_BLOCKLIST)
    if email_hint:
        blocked.add(email_hint.casefold())
    if lowered in blocked:
        raise ValueError("Password is too common or predictable.")
    return result


def hash_password(password: str, *, email_hint: str | None = None) -> str:
    result = validate_password(password, email_hint=email_hint)
    if _PASSWORD_HASHER is None:
        digest = hashlib.sha256(result.normalized.encode("utf-8")).hexdigest()
        return f"$argon2id$fallback${digest}"
    return _PASSWORD_HASHER.hash(result.normalized)


def verify_password(password: str, encoded_hash: str) -> bool:
    normalized = normalize_password(password).normalized
    if _PASSWORD_HASHER is None or encoded_hash.startswith("$argon2id$fallback$"):
        candidate = f"$argon2id$fallback${hashlib.sha256(normalized.encode('utf-8')).hexdigest()}"
        return hmac.compare_digest(candidate, encoded_hash)
    return bool(_PASSWORD_HASHER.verify(normalized, encoded_hash))


def verify_password_or_dummy(password: str, encoded_hash: str | None) -> bool:
    if encoded_hash is None:
        return verify_password(password, _DUMMY_HASH)
    return verify_password(password, encoded_hash)


def dummy_hash() -> str:
    return _DUMMY_HASH

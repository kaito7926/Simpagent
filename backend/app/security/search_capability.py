from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any
from uuid import UUID, uuid4

import jwt

from app.core.config import Settings

SEARCH_CAPABILITY_TYPE = "search-capability+jwt"
SEARCH_CAPABILITY_ALGORITHM = "RS256"
SEARCH_CAPABILITY_TOOL = "google_search"
SEARCH_CAPABILITY_LEEWAY_SECONDS = 5


@dataclass(frozen=True)
class SearchCapabilityClaims:
    sub: UUID
    aud: str
    iss: str
    iat: int
    nbf: int
    exp: int
    jti: UUID
    tool: str
    conversation_id: UUID
    correlation_id: str | None


class SearchCapabilityError(ValueError):
    pass


def _timestamp(moment: datetime) -> int:
    return int(moment.replace(tzinfo=UTC).timestamp())


def mint_search_capability(
    *,
    user_id: UUID,
    conversation_id: UUID,
    correlation_id: str | None,
    settings: Settings,
    now: datetime,
) -> str:
    issued_at = _timestamp(now)
    expires_at = issued_at + settings.search_capability_ttl_seconds
    payload = {
        "iss": settings.jwt_issuer,
        "aud": settings.search_capability_audience,
        "sub": str(user_id),
        "tool": SEARCH_CAPABILITY_TOOL,
        "conversation_id": str(conversation_id),
        "correlation_id": correlation_id,
        "iat": issued_at,
        "nbf": issued_at,
        "exp": expires_at,
        "jti": str(uuid4()),
    }
    headers = {
        "typ": SEARCH_CAPABILITY_TYPE,
        "kid": settings.jwt_active_kid,
        "alg": SEARCH_CAPABILITY_ALGORITHM,
    }
    return jwt.encode(
        payload,
        settings.jwt_private_key_value,
        algorithm=SEARCH_CAPABILITY_ALGORITHM,
        headers=headers,
    )


def validate_search_capability(
    token: str,
    *,
    settings: Settings,
    now: datetime | None = None,
) -> SearchCapabilityClaims:
    try:
        header = jwt.get_unverified_header(token)
    except jwt.InvalidTokenError as exc:  # pragma: no cover - library detail
        raise SearchCapabilityError("Malformed capability token header") from exc
    if header.get("alg") != SEARCH_CAPABILITY_ALGORITHM:
        raise SearchCapabilityError("Unexpected JWT algorithm")
    if header.get("typ") != SEARCH_CAPABILITY_TYPE:
        raise SearchCapabilityError("Unexpected capability token type")
    if header.get("kid") != settings.jwt_active_kid:
        raise SearchCapabilityError("Unexpected key id")

    try:
        payload: dict[str, Any] = jwt.decode(
            token,
            settings.jwt_public_key_value,
            algorithms=[SEARCH_CAPABILITY_ALGORITHM],
            audience=settings.search_capability_audience,
            issuer=settings.jwt_issuer,
            leeway=SEARCH_CAPABILITY_LEEWAY_SECONDS,
            options={
                "require": [
                    "iss",
                    "aud",
                    "sub",
                    "tool",
                    "conversation_id",
                    "exp",
                    "iat",
                    "nbf",
                    "jti",
                ],
                "verify_signature": True,
                "verify_exp": True,
                "verify_iat": True,
                "verify_nbf": True,
                "verify_aud": True,
                "verify_iss": True,
            },
        )
    except jwt.InvalidTokenError as exc:
        raise SearchCapabilityError("Invalid capability token") from exc

    if payload.get("tool") != SEARCH_CAPABILITY_TOOL:
        raise SearchCapabilityError("Unexpected tool binding")
    if payload.get("correlation_id") is not None and not isinstance(payload["correlation_id"], str):
        raise SearchCapabilityError("Invalid correlation id")

    try:
        sub = UUID(str(payload["sub"]))
        conversation_id = UUID(str(payload["conversation_id"]))
        jti = UUID(str(payload["jti"]))
    except ValueError as exc:
        raise SearchCapabilityError("Invalid UUID claim") from exc

    for claim_name in ("iat", "nbf", "exp"):
        if not isinstance(payload.get(claim_name), int):
            raise SearchCapabilityError(f"{claim_name} must be an integer numeric date")

    if payload["exp"] <= payload["iat"]:
        raise SearchCapabilityError("Invalid expiry ordering")
    if payload["exp"] - payload["iat"] > settings.search_capability_ttl_seconds:
        raise SearchCapabilityError("Capability lifetime exceeds policy")
    if payload["nbf"] > payload["iat"] + SEARCH_CAPABILITY_LEEWAY_SECONDS:
        raise SearchCapabilityError("nbf is too far after iat")
    if now is not None and payload["iat"] > _timestamp(now) + SEARCH_CAPABILITY_LEEWAY_SECONDS:
        raise SearchCapabilityError("Capability iat is too far in the future")

    return SearchCapabilityClaims(
        sub=sub,
        aud=str(payload["aud"]),
        iss=str(payload["iss"]),
        iat=int(payload["iat"]),
        nbf=int(payload["nbf"]),
        exp=int(payload["exp"]),
        jti=jti,
        tool=str(payload["tool"]),
        conversation_id=conversation_id,
        correlation_id=payload.get("correlation_id"),
    )

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any
from uuid import UUID, uuid4

import jwt
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.config import Settings
from app.db.repositories.sessions import SessionsRepository

SEARCH_CAPABILITY_TYPE = "search-capability+jwt"
SEARCH_CAPABILITY_ALGORITHM = "RS256"
SEARCH_CAPABILITY_TOOL = "google_search"
SEARCH_CAPABILITY_LEEWAY_SECONDS = 5
SEARCH_CAPABILITY_REPLAY_ARTIFACT = "search_capability"
SEARCH_CAPABILITY_REPLAY_EVENT = "search_capability_replay"


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


class SearchCapabilityReplayError(SearchCapabilityError):
    pass


def _timestamp(moment: datetime) -> int:
    return int(moment.replace(tzinfo=UTC).timestamp())


def _datetime_from_numeric_date(value: int) -> datetime:
    return datetime.fromtimestamp(value, UTC)


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
    reference_now = now or settings.now_utc()
    reference_timestamp = _timestamp(reference_now)

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
                "verify_exp": False,
                "verify_iat": False,
                "verify_nbf": False,
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
    if payload["nbf"] > reference_timestamp + SEARCH_CAPABILITY_LEEWAY_SECONDS:
        raise SearchCapabilityError("Capability is not yet valid")
    if payload["exp"] <= reference_timestamp - SEARCH_CAPABILITY_LEEWAY_SECONDS:
        raise SearchCapabilityError("Capability has expired")
    if payload["iat"] > reference_timestamp + SEARCH_CAPABILITY_LEEWAY_SECONDS:
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


async def consume_search_capability_once(
    token: str,
    *,
    settings: Settings,
    session_factory: async_sessionmaker[AsyncSession],
    expected_user_id: UUID,
    expected_conversation_id: UUID,
    expected_correlation_id: str | None,
    now: datetime | None = None,
) -> SearchCapabilityClaims:
    reference_now = now or settings.now_utc()
    claims = validate_search_capability(token, settings=settings, now=reference_now)
    if claims.sub != expected_user_id:
        await _record_search_capability_mismatch(
            settings=settings,
            session_factory=session_factory,
            claims=claims,
            event_type="search_capability_subject_mismatch",
            correlation_id=expected_correlation_id,
        )
        raise SearchCapabilityError("Capability subject does not match the user")
    if claims.conversation_id != expected_conversation_id:
        await _record_search_capability_mismatch(
            settings=settings,
            session_factory=session_factory,
            claims=claims,
            event_type="search_capability_conversation_mismatch",
            correlation_id=expected_correlation_id,
        )
        raise SearchCapabilityError("Capability conversation does not match")
    if claims.correlation_id != expected_correlation_id:
        await _record_search_capability_mismatch(
            settings=settings,
            session_factory=session_factory,
            claims=claims,
            event_type="search_capability_correlation_mismatch",
            correlation_id=expected_correlation_id,
        )
        raise SearchCapabilityError("Capability correlation does not match")

    if not settings.capability_replay_protection_enabled:
        return claims

    async with session_factory() as session:
        repository = SessionsRepository(session)
        result = await repository.consume_security_artifact_once(
            artifact_type=SEARCH_CAPABILITY_REPLAY_ARTIFACT,
            jti=str(claims.jti),
            subject=str(claims.sub),
            audience=claims.aud,
            conversation_id=str(claims.conversation_id),
            binding_key_thumbprint=None,
            expires_at=_datetime_from_numeric_date(claims.exp),
            now=reference_now,
            correlation_id=claims.correlation_id,
            replay_event_type=SEARCH_CAPABILITY_REPLAY_EVENT,
        )
        await session.commit()
        if not result.accepted:
            raise SearchCapabilityReplayError("Capability has already been consumed")
    return claims


async def _record_search_capability_mismatch(
    *,
    settings: Settings,
    session_factory: async_sessionmaker[AsyncSession],
    claims: SearchCapabilityClaims,
    event_type: str,
    correlation_id: str | None,
) -> None:
    if not settings.capability_replay_protection_enabled:
        return
    async with session_factory() as session:
        repository = SessionsRepository(session)
        await repository.add_security_event(
            event_type=event_type,
            severity="medium",
            user_id=None,
            description="Search capability context binding failed.",
            correlation_id=correlation_id or claims.correlation_id,
            metadata={
                "artifact_type": SEARCH_CAPABILITY_REPLAY_ARTIFACT,
                "jti": str(claims.jti),
                "subject": str(claims.sub),
                "audience": claims.aud,
                "conversation_id": str(claims.conversation_id),
                "expected_binding": "redacted",
            },
        )
        await session.commit()

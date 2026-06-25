from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID, uuid4

import jwt

from app.core.config import Settings
from app.schemas.auth import KNOWN_ROLES, KNOWN_SCOPES


@dataclass(frozen=True)
class AccessTokenClaims:
    sub: UUID
    role: str
    scopes: tuple[str, ...]
    iss: str
    aud: str
    iat: int
    nbf: int
    exp: int
    kid: str
    jti: UUID
    cnf_jkt: str | None = None


class AccessTokenError(ValueError):
    pass


JWT_TYPE = "at+jwt"
JWT_ALGORITHM = "RS256"
JWT_LEEWAY_SECONDS = 30


def _timestamp(moment: datetime) -> int:
    if moment.tzinfo is None:
        moment = moment.replace(tzinfo=UTC)
    else:
        moment = moment.astimezone(UTC)
    return int(moment.timestamp())


def _validate_numeric_date(payload: dict[str, Any], claim_name: str) -> int:
    value = payload.get(claim_name)
    if not isinstance(value, int):
        raise AccessTokenError(f"{claim_name} must be an integer numeric date")
    return value


def _validate_temporal_claims(payload: dict[str, Any], *, now: datetime | None) -> tuple[int, int, int]:
    reference_now = (now or datetime.now(UTC)).astimezone(UTC).timestamp()
    iat = _validate_numeric_date(payload, "iat")
    nbf = _validate_numeric_date(payload, "nbf")
    exp = _validate_numeric_date(payload, "exp")

    if iat > reference_now + JWT_LEEWAY_SECONDS:
        raise AccessTokenError("Token iat is too far in the future")
    if nbf > reference_now + JWT_LEEWAY_SECONDS:
        raise AccessTokenError("Token nbf is too far in the future")
    if exp <= reference_now - JWT_LEEWAY_SECONDS:
        raise AccessTokenError("Token has expired")
    return iat, nbf, exp


def issue_access_token(
    *,
    user_id: UUID,
    role: str,
    scopes: list[str],
    settings: Settings,
    now: datetime,
    key_thumbprint: str | None = None,
) -> str:
    canonical_scopes = sorted(dict.fromkeys(scopes))
    if role not in KNOWN_ROLES:
        raise AccessTokenError("Unknown role")
    if set(canonical_scopes) - KNOWN_SCOPES:
        raise AccessTokenError("Unknown scopes")
    issued_at = _timestamp(now)
    expires_at = issued_at + settings.access_token_ttl_seconds
    payload = {
        "iss": settings.jwt_issuer,
        "aud": settings.jwt_audience,
        "sub": str(user_id),
        "role": role,
        "scopes": canonical_scopes,
        "iat": issued_at,
        "nbf": issued_at,
        "exp": expires_at,
        "jti": str(uuid4()),
    }
    if key_thumbprint:
        payload["cnf"] = {"jkt": key_thumbprint}
    headers = {"typ": JWT_TYPE, "kid": settings.jwt_active_kid, "alg": JWT_ALGORITHM}
    return jwt.encode(payload, settings.jwt_private_key_value, algorithm=JWT_ALGORITHM, headers=headers)


def decode_access_token(token: str, *, settings: Settings, now: datetime | None = None) -> AccessTokenClaims:
    try:
        header = jwt.get_unverified_header(token)
    except jwt.InvalidTokenError as exc:  # pragma: no cover - library detail
        raise AccessTokenError("Malformed token header") from exc
    if header.get("alg") != JWT_ALGORITHM:
        raise AccessTokenError("Unexpected JWT algorithm")
    if header.get("typ") != JWT_TYPE:
        raise AccessTokenError("Unexpected token type")
    if header.get("kid") != settings.jwt_active_kid:
        raise AccessTokenError("Unexpected key id")

    try:
        payload: dict[str, Any] = jwt.decode(
            token,
            settings.jwt_public_key_value,
            algorithms=[JWT_ALGORITHM],
            audience=settings.jwt_audience,
            issuer=settings.jwt_issuer,
            leeway=JWT_LEEWAY_SECONDS,
            options={
                "require": ["iss", "aud", "sub", "role", "scopes", "exp", "iat", "nbf", "jti"],
                "verify_signature": True,
                "verify_exp": False,
                "verify_iat": False,
                "verify_nbf": False,
                "verify_aud": True,
                "verify_iss": True,
            },
        )
    except jwt.InvalidTokenError as exc:
        raise AccessTokenError("Invalid access token") from exc

    role = payload.get("role")
    scopes = payload.get("scopes")
    if role not in KNOWN_ROLES:
        raise AccessTokenError("Unknown role")
    if not isinstance(scopes, list) or any(not isinstance(item, str) for item in scopes):
        raise AccessTokenError("Invalid scopes claim")
    canonical_scopes = tuple(sorted(dict.fromkeys(scopes)))
    if tuple(scopes) != canonical_scopes:
        raise AccessTokenError("Scopes must be sorted and unique")
    if set(canonical_scopes) - KNOWN_SCOPES:
        raise AccessTokenError("Unknown scopes")
    cnf_jkt: str | None = None
    cnf = payload.get("cnf")
    if cnf is not None:
        if not isinstance(cnf, dict) or set(cnf) != {"jkt"} or not isinstance(cnf.get("jkt"), str) or not cnf["jkt"]:
            raise AccessTokenError("Invalid cnf claim")
        cnf_jkt = cnf["jkt"]
    try:
        sub = UUID(str(payload["sub"]))
        jti = UUID(str(payload["jti"]))
    except ValueError as exc:
        raise AccessTokenError("Invalid UUID claim") from exc
    iat, nbf, exp = _validate_temporal_claims(payload, now=now)
    if exp <= iat:
        raise AccessTokenError("Invalid expiry ordering")
    if nbf > iat + JWT_LEEWAY_SECONDS:
        raise AccessTokenError("nbf is too far after iat")
    if exp - iat > settings.access_token_ttl_seconds:
        raise AccessTokenError("Token lifetime exceeds policy")
    return AccessTokenClaims(
        sub=sub,
        role=role,
        scopes=canonical_scopes,
        iss=str(payload["iss"]),
        aud=str(payload["aud"]),
        iat=iat,
        nbf=nbf,
        exp=exp,
        kid=str(header["kid"]),
        jti=jti,
        cnf_jkt=cnf_jkt,
    )

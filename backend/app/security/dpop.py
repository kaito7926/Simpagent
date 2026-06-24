from __future__ import annotations

import base64
import hashlib
import json
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any

import jwt
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings
from app.db.repositories.sessions import SessionsRepository

DPoP_TYPE = "dpop+jwt"
DPoP_REPLAY_ARTIFACT = "dpop_proof"
DPoP_REPLAY_EVENT = "dpop_proof_replay"
DPoP_AUDIENCE = "simpagent-api-dpop"
SUPPORTED_DPOP_ALGORITHMS = ("RS256",)


class DPoPError(ValueError):
    pass


@dataclass(frozen=True)
class DPoPProof:
    jti: str
    key_thumbprint: str
    method: str
    url: str
    issued_at: int


def _b64u(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode("ascii")


def jwk_thumbprint(jwk: dict[str, Any]) -> str:
    kty = jwk.get("kty")
    if kty == "RSA":
        required = {"e", "kty", "n"}
    elif kty == "EC":
        required = {"crv", "kty", "x", "y"}
    else:
        raise DPoPError("Unsupported DPoP key type")
    if any(not isinstance(jwk.get(key), str) or not jwk[key] for key in required):
        raise DPoPError("Invalid DPoP JWK")
    canonical = json.dumps(
        {key: jwk[key] for key in sorted(required)},
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
    return _b64u(hashlib.sha256(canonical).digest())


async def validate_dpop_request(
    *,
    proof_token: str | None,
    method: str,
    url: str,
    settings: Settings,
    session: AsyncSession,
    now: datetime,
    correlation_id: str | None,
    expected_key_thumbprint: str | None = None,
    subject: str | None = None,
) -> DPoPProof:
    if not proof_token:
        raise DPoPError("DPoP proof is required")
    proof = parse_dpop_proof(
        proof_token,
        method=method,
        url=url,
        settings=settings,
        now=now,
        expected_key_thumbprint=expected_key_thumbprint,
    )
    if not settings.capability_replay_protection_enabled:
        return proof

    repository = SessionsRepository(session)
    consumed = await repository.consume_security_artifact_once(
        artifact_type=DPoP_REPLAY_ARTIFACT,
        jti=proof.jti,
        subject=subject,
        audience=DPoP_AUDIENCE,
        conversation_id=None,
        binding_key_thumbprint=proof.key_thumbprint,
        expires_at=now + timedelta(seconds=settings.dpop_nonce_ttl_seconds),
        now=now,
        correlation_id=correlation_id,
        replay_event_type=DPoP_REPLAY_EVENT,
    )
    if not consumed.accepted:
        raise DPoPError("DPoP proof replay detected")
    return proof


def parse_dpop_proof(
    proof_token: str,
    *,
    method: str,
    url: str,
    settings: Settings,
    now: datetime,
    expected_key_thumbprint: str | None = None,
) -> DPoPProof:
    try:
        header = jwt.get_unverified_header(proof_token)
    except jwt.InvalidTokenError as exc:
        raise DPoPError("Malformed DPoP proof header") from exc
    if header.get("typ") != DPoP_TYPE:
        raise DPoPError("Unexpected DPoP proof type")
    algorithm = header.get("alg")
    if algorithm not in SUPPORTED_DPOP_ALGORITHMS:
        raise DPoPError("Unexpected DPoP proof algorithm")
    jwk = header.get("jwk")
    if not isinstance(jwk, dict):
        raise DPoPError("DPoP proof JWK is required")
    key_thumbprint = jwk_thumbprint(jwk)
    if expected_key_thumbprint and key_thumbprint != expected_key_thumbprint:
        raise DPoPError("DPoP key binding mismatch")

    try:
        public_key = jwt.algorithms.RSAAlgorithm.from_jwk(json.dumps(jwk))
        payload: dict[str, Any] = jwt.decode(
            proof_token,
            public_key,
            algorithms=[str(algorithm)],
            options={
                "require": ["htu", "htm", "iat", "jti"],
                "verify_signature": True,
                "verify_exp": False,
                "verify_iat": False,
                "verify_nbf": False,
                "verify_aud": False,
                "verify_iss": False,
            },
        )
    except jwt.InvalidTokenError as exc:
        raise DPoPError("Invalid DPoP proof") from exc

    if payload.get("htm") != method.upper():
        raise DPoPError("DPoP method binding mismatch")
    if payload.get("htu") != url:
        raise DPoPError("DPoP URL binding mismatch")
    if not isinstance(payload.get("jti"), str) or not payload["jti"].strip():
        raise DPoPError("DPoP jti is required")
    if not isinstance(payload.get("iat"), int):
        raise DPoPError("DPoP iat must be an integer numeric date")

    reference_timestamp = int(now.astimezone(UTC).timestamp())
    if payload["iat"] > reference_timestamp + settings.dpop_proof_leeway_seconds:
        raise DPoPError("DPoP proof iat is too far in the future")
    if payload["iat"] < reference_timestamp - settings.dpop_nonce_ttl_seconds:
        raise DPoPError("DPoP proof has expired")

    return DPoPProof(
        jti=str(payload["jti"]),
        key_thumbprint=key_thumbprint,
        method=method.upper(),
        url=url,
        issued_at=int(payload["iat"]),
    )

from __future__ import annotations

import base64
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
import hashlib
import hmac
import json
import secrets
from typing import Literal
from uuid import uuid4

from app.core.config import Settings


OAuthTransactionProvider = Literal["google", "github"]
PKCE_CHALLENGE_METHOD = "S256"


class OAuthTransactionError(ValueError):
    pass


@dataclass(frozen=True)
class OAuthTransaction:
    provider: OAuthTransactionProvider
    state: str
    jti: str
    code_verifier: str
    code_challenge: str
    dpop_key_thumbprint: str | None
    issued_at: datetime
    expires_at: datetime


def _b64url(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def _unb64url(data: str) -> bytes:
    padding = "=" * ((4 - len(data) % 4) % 4)
    return base64.urlsafe_b64decode(f"{data}{padding}".encode("ascii"))


def _timestamp(moment: datetime) -> int:
    return int(moment.astimezone(UTC).timestamp())


def _pkce_challenge(code_verifier: str) -> str:
    return _b64url(hashlib.sha256(code_verifier.encode("ascii")).digest())


def issue_oauth_transaction(
    *,
    provider: OAuthTransactionProvider,
    settings: Settings,
    now: datetime,
    dpop_key_thumbprint: str | None = None,
) -> OAuthTransaction:
    code_verifier = secrets.token_urlsafe(64)[:96]
    issued_at = now.astimezone(UTC)
    return OAuthTransaction(
        provider=provider,
        state=secrets.token_urlsafe(32),
        jti=str(uuid4()),
        code_verifier=code_verifier,
        code_challenge=_pkce_challenge(code_verifier),
        dpop_key_thumbprint=dpop_key_thumbprint,
        issued_at=issued_at,
        expires_at=issued_at + timedelta(seconds=settings.oauth_transaction_ttl_seconds),
    )


def seal_oauth_transaction(*, transaction: OAuthTransaction, settings: Settings) -> str:
    payload = {
        "provider": transaction.provider,
        "state": transaction.state,
        "jti": transaction.jti,
        "code_verifier": transaction.code_verifier,
        "code_challenge": transaction.code_challenge,
        "dpop_key_thumbprint": transaction.dpop_key_thumbprint,
        "iat": _timestamp(transaction.issued_at),
        "exp": _timestamp(transaction.expires_at),
    }
    payload_json = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    payload_part = _b64url(payload_json)
    signature = hmac.digest(settings.csrf_hmac_key_value, payload_part.encode("ascii"), hashlib.sha256)
    return f"{payload_part}.{_b64url(signature)}"


def unseal_oauth_transaction(
    *,
    cookie_value: str | None,
    provider: OAuthTransactionProvider,
    state: str | None,
    settings: Settings,
    now: datetime,
) -> OAuthTransaction:
    if not cookie_value or not state:
        raise OAuthTransactionError("OAuth transaction is missing.")
    try:
        payload_part, signature_part = cookie_value.rsplit(".", 1)
        signature = _unb64url(signature_part)
        payload = json.loads(_unb64url(payload_part))
    except (ValueError, json.JSONDecodeError) as exc:
        raise OAuthTransactionError("OAuth transaction is malformed.") from exc

    expected_signature = hmac.digest(settings.csrf_hmac_key_value, payload_part.encode("ascii"), hashlib.sha256)
    if not hmac.compare_digest(signature, expected_signature):
        raise OAuthTransactionError("OAuth transaction signature is invalid.")
    if payload.get("provider") != provider:
        raise OAuthTransactionError("OAuth transaction provider mismatch.")
    if payload.get("state") != state:
        raise OAuthTransactionError("OAuth transaction state mismatch.")

    try:
        issued_at = datetime.fromtimestamp(int(payload["iat"]), UTC)
        expires_at = datetime.fromtimestamp(int(payload["exp"]), UTC)
        transaction = OAuthTransaction(
            provider=provider,
            state=str(payload["state"]),
            jti=str(payload["jti"]),
            code_verifier=str(payload["code_verifier"]),
            code_challenge=str(payload["code_challenge"]),
            dpop_key_thumbprint=(
                str(payload["dpop_key_thumbprint"]) if payload.get("dpop_key_thumbprint") is not None else None
            ),
            issued_at=issued_at,
            expires_at=expires_at,
        )
    except (KeyError, TypeError, ValueError) as exc:
        raise OAuthTransactionError("OAuth transaction payload is invalid.") from exc

    if transaction.expires_at <= now.astimezone(UTC):
        raise OAuthTransactionError("OAuth transaction expired.")
    if _pkce_challenge(transaction.code_verifier) != transaction.code_challenge:
        raise OAuthTransactionError("OAuth transaction PKCE challenge is invalid.")
    return transaction

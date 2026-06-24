from __future__ import annotations

import base64
from datetime import UTC, datetime
from uuid import uuid4

import jwt
import pytest
from sqlalchemy import select

from app.models.evidence import SecurityEvent
from app.models.session import RefreshToken, RefreshTokenFamily
from app.security.dpop import jwk_thumbprint
from app.security.refresh_tokens import CSRF_COOKIE_NAME, REFRESH_COOKIE_NAME

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa


ORIGIN = "http://localhost:3000"
TESTSERVER = "http://testserver"


def _b64u(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode("ascii")


def _dpop_keypair() -> tuple[object, dict[str, str]]:
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    public_numbers = private_key.public_key().public_numbers()
    jwk = {
        "kty": "RSA",
        "n": _b64u(public_numbers.n.to_bytes((public_numbers.n.bit_length() + 7) // 8, "big")),
        "e": _b64u(public_numbers.e.to_bytes((public_numbers.e.bit_length() + 7) // 8, "big")),
    }
    return private_key, jwk


def _dpop_proof(
    *,
    private_key,
    jwk: dict[str, str],
    method: str,
    url: str,
    jti: str | None = None,
) -> str:
    key_pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    )
    issued_at = int(datetime.now(UTC).timestamp())
    return jwt.encode(
        {
            "htu": url,
            "htm": method.upper(),
            "iat": issued_at,
            "jti": jti or str(uuid4()),
        },
        key_pem,
        algorithm="RS256",
        headers={"typ": "dpop+jwt", "alg": "RS256", "jwk": jwk},
    )


async def _register(client, *, email: str, password: str) -> None:
    response = await client.post(
        "/api/auth/register",
        headers={"Origin": ORIGIN},
        json={"email": email, "password": password},
    )
    assert response.status_code == 202


async def _login(client, *, email: str, password: str) -> tuple[str, str, str]:
    response = await client.post(
        "/api/auth/login",
        headers={"Origin": ORIGIN},
        json={"email": email, "password": password},
    )
    assert response.status_code == 200
    refresh_token = response.cookies.get(REFRESH_COOKIE_NAME) or client.cookies.get(REFRESH_COOKIE_NAME)
    csrf_token = response.cookies.get(CSRF_COOKIE_NAME) or client.cookies.get(CSRF_COOKIE_NAME)
    assert refresh_token
    assert csrf_token
    return str(response.json()["access_token"]), str(refresh_token), str(csrf_token)


async def _login_with_dpop(client, *, email: str, password: str, private_key, jwk) -> tuple[str, str, str]:
    response = await client.post(
        "/api/auth/login",
        headers={
            "Origin": ORIGIN,
            "DPoP": _dpop_proof(
                private_key=private_key,
                jwk=jwk,
                method="POST",
                url=f"{TESTSERVER}/api/auth/login",
            ),
        },
        json={"email": email, "password": password},
    )
    assert response.status_code == 200
    refresh_token = response.cookies.get(REFRESH_COOKIE_NAME) or client.cookies.get(REFRESH_COOKIE_NAME)
    csrf_token = response.cookies.get(CSRF_COOKIE_NAME) or client.cookies.get(CSRF_COOKIE_NAME)
    assert refresh_token
    assert csrf_token
    return str(response.json()["access_token"]), str(refresh_token), str(csrf_token)


def _set_session_cookies(client, *, refresh_token: str, csrf_token: str) -> None:
    client.cookies.clear()
    client.cookies.set(REFRESH_COOKIE_NAME, refresh_token)
    client.cookies.set(CSRF_COOKIE_NAME, csrf_token)


async def _refresh(
    client,
    *,
    refresh_token: str,
    csrf_token: str,
    correlation_id: str,
    extra_headers: dict[str, str] | None = None,
) -> tuple[object, str | None, str | None]:
    _set_session_cookies(client, refresh_token=refresh_token, csrf_token=csrf_token)
    headers = {
        "Origin": ORIGIN,
        "X-CSRF-Token": csrf_token,
        "X-Correlation-Id": correlation_id,
    }
    headers.update(extra_headers or {})
    response = await client.post(
        "/api/auth/refresh",
        headers=headers,
    )
    rotated_refresh = response.cookies.get(REFRESH_COOKIE_NAME) or client.cookies.get(REFRESH_COOKIE_NAME)
    rotated_csrf = response.cookies.get(CSRF_COOKIE_NAME) or client.cookies.get(CSRF_COOKIE_NAME)
    return response, rotated_refresh, rotated_csrf


@pytest.mark.asyncio
async def test_sender_constrained_access_token_requires_matching_dpop_proof(app, client) -> None:
    app.state.settings = app.state.settings.model_copy(update={"dpop_enabled": True})
    private_key, jwk = _dpop_keypair()
    await _register(
        client,
        email="dpop-access@example.test",
        password="MatKhauDpopAccess123",
    )
    access_token, _, _ = await _login_with_dpop(
        client,
        email="dpop-access@example.test",
        password="MatKhauDpopAccess123",
        private_key=private_key,
        jwk=jwk,
    )

    missing_proof = await client.get("/api/auth/me", headers={"Authorization": f"Bearer {access_token}"})
    valid_proof = await client.get(
        "/api/auth/me",
        headers={
            "Authorization": f"Bearer {access_token}",
            "DPoP": _dpop_proof(
                private_key=private_key,
                jwk=jwk,
                method="GET",
                url=f"{TESTSERVER}/api/auth/me",
            ),
        },
    )

    assert missing_proof.status_code == 401
    assert missing_proof.json()["error"]["code"] == "invalid_dpop_proof"
    assert valid_proof.status_code == 200
    assert valid_proof.json()["email"] == "dpop-access@example.test"


@pytest.mark.asyncio
async def test_refresh_with_mismatched_dpop_key_is_denied_and_recorded(app, client, db_session) -> None:
    app.state.settings = app.state.settings.model_copy(update={"dpop_enabled": True})
    private_key, jwk = _dpop_keypair()
    other_private_key, other_jwk = _dpop_keypair()
    await _register(
        client,
        email="dpop-refresh-mismatch@example.test",
        password="MatKhauDpopRefresh123",
    )
    _, refresh_token, csrf_token = await _login_with_dpop(
        client,
        email="dpop-refresh-mismatch@example.test",
        password="MatKhauDpopRefresh123",
        private_key=private_key,
        jwk=jwk,
    )

    mismatch, _, _ = await _refresh(
        client,
        refresh_token=refresh_token,
        csrf_token=csrf_token,
        correlation_id="corr-dpop-refresh-mismatch",
        extra_headers={
            "DPoP": _dpop_proof(
                private_key=other_private_key,
                jwk=other_jwk,
                method="POST",
                url=f"{TESTSERVER}/api/auth/refresh",
            )
        },
    )

    assert mismatch.status_code == 401
    assert mismatch.json()["error"]["code"] == "session_invalid"

    family = await db_session.scalar(select(RefreshTokenFamily))
    assert family is not None
    assert family.auth_binding_method == "dpop"
    assert family.key_thumbprint == jwk_thumbprint(jwk)
    event = await db_session.scalar(
        select(SecurityEvent).where(SecurityEvent.correlation_id == "corr-dpop-refresh-mismatch")
    )
    assert event is not None
    assert event.event_type == "dpop_key_mismatch"


@pytest.mark.asyncio
async def test_refresh_rotation_replay_revokes_family_and_records_security_event(client, db_session) -> None:
    await _register(
        client,
        email="refresh-rotation@example.test",
        password="MatKhauRefreshRotation123",
    )
    access_token, refresh_token, csrf_token = await _login(
        client,
        email="refresh-rotation@example.test",
        password="MatKhauRefreshRotation123",
    )

    me = await client.get("/api/auth/me", headers={"Authorization": f"Bearer {access_token}"})
    assert me.status_code == 200
    assert me.json()["email"] == "refresh-rotation@example.test"

    rotated, rotated_refresh_token, rotated_csrf_token = await _refresh(
        client,
        refresh_token=refresh_token,
        csrf_token=csrf_token,
        correlation_id="corr-auth-refresh-rotate",
    )
    assert rotated.status_code == 200
    assert rotated.json()["access_token"] != access_token
    assert rotated_refresh_token
    assert rotated_refresh_token != refresh_token
    assert rotated_csrf_token
    assert rotated_csrf_token != csrf_token

    tokens = list((await db_session.execute(select(RefreshToken).order_by(RefreshToken.created_at.asc()))).scalars())
    assert len(tokens) == 2
    original = next(token for token in tokens if token.parent_token_id is None)
    rotated_token = next(token for token in tokens if token.parent_token_id is not None)
    assert original.used_at is not None
    assert original.replaced_by_id == rotated_token.id
    assert rotated_token.parent_token_id == original.id

    family = await db_session.scalar(select(RefreshTokenFamily))
    assert family is not None
    assert family.revoked_at is None
    assert family.auth_binding_method == "bearer"
    assert family.key_thumbprint is None

    replay, _, _ = await _refresh(
        client,
        refresh_token=refresh_token,
        csrf_token=csrf_token,
        correlation_id="corr-auth-refresh-replay",
    )
    assert replay.status_code == 401
    assert replay.json()["error"]["code"] == "session_invalid"

    follow_up, _, _ = await _refresh(
        client,
        refresh_token=str(rotated_refresh_token),
        csrf_token=str(rotated_csrf_token),
        correlation_id="corr-auth-refresh-after-replay",
    )
    assert follow_up.status_code == 401
    assert follow_up.json()["error"]["code"] == "session_invalid"

    await db_session.refresh(family)
    assert family.revoked_at is not None
    assert family.revoke_reason == "refresh_reuse"

    event = await db_session.scalar(
        select(SecurityEvent).where(SecurityEvent.correlation_id == "corr-auth-refresh-replay")
    )
    assert event is not None
    assert event.event_type == "refresh_reuse"
    assert event.severity == "high"
    assert event.event_metadata["family_id"] == str(family.id)
    assert event.event_metadata["auth_binding_method"] == "bearer"


@pytest.mark.asyncio
async def test_logout_revokes_refresh_family_and_blocks_followup_refresh(client, db_session) -> None:
    await _register(
        client,
        email="logout-flow@example.test",
        password="MatKhauLogoutFlow123",
    )
    access_token, refresh_token, csrf_token = await _login(
        client,
        email="logout-flow@example.test",
        password="MatKhauLogoutFlow123",
    )

    me = await client.get("/api/auth/me", headers={"Authorization": f"Bearer {access_token}"})
    assert me.status_code == 200
    assert me.json()["email"] == "logout-flow@example.test"

    _set_session_cookies(client, refresh_token=refresh_token, csrf_token=csrf_token)
    logout = await client.post(
        "/api/auth/logout",
        headers={
            "Origin": ORIGIN,
            "X-CSRF-Token": csrf_token,
        },
    )
    assert logout.status_code == 204

    replay_after_logout, _, _ = await _refresh(
        client,
        refresh_token=refresh_token,
        csrf_token=csrf_token,
        correlation_id="corr-auth-refresh-after-logout",
    )
    assert replay_after_logout.status_code == 401
    assert replay_after_logout.json()["error"]["code"] == "session_invalid"

    family = await db_session.scalar(select(RefreshTokenFamily))
    assert family is not None
    assert family.revoked_at is not None
    assert family.revoke_reason == "logout"

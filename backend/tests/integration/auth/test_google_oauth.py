from __future__ import annotations

from dataclasses import dataclass
from urllib.parse import parse_qs, urlparse

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select

from app.identity.providers.google import GOOGLE_ISSUER, GoogleOAuthIdentity
from app.main import create_app
from app.models.account import Identity, User
from app.models.evidence import SecurityEvent
from app.security.refresh_tokens import CSRF_COOKIE_NAME, REFRESH_COOKIE_NAME


@dataclass(frozen=True)
class FakeGoogleProvider:
    identity: GoogleOAuthIdentity

    def authorization_url(self, *, state: str, code_challenge: str | None = None) -> str:
        return (
            "https://accounts.google.com/o/oauth2/v2/auth"
            f"?state={state}&client_id=test&code_challenge={code_challenge}"
            "&code_challenge_method=S256"
        )

    async def authenticate(self, request) -> GoogleOAuthIdentity:
        assert request.code_verifier
        return self.identity


@pytest.fixture
def google_settings(settings):
    return settings.model_copy(
        update={
            "google_client_id": "google-client-id",
            "google_client_secret": "google-client-secret",
            "google_redirect_uri": "http://testserver/api/auth/oauth/google/callback",
            "public_app_origin": "http://testserver",
        }
    )


async def _client_with_identity(settings, session_factory, identity: GoogleOAuthIdentity):
    app = create_app(settings=settings, session_factory=session_factory)
    app.state.google_oauth_provider = FakeGoogleProvider(identity)
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://testserver",
        follow_redirects=False,
    ) as http_client:
        yield http_client


async def _oauth_roundtrip(client: AsyncClient):
    start = await client.get("/api/auth/oauth/google/start")
    assert start.status_code in {302, 303, 307}
    state = parse_qs(urlparse(start.headers["location"]).query)["state"][0]
    return await client.get(
        "/api/auth/oauth/google/callback",
        params={"state": state, "code": "auth-code"},
    )


@pytest.mark.asyncio
async def test_google_callback_provisions_verified_new_user_and_sets_first_party_cookies(
    google_settings,
    session_factory,
    clean_database,
    db_session,
) -> None:
    identity = GoogleOAuthIdentity(
        issuer=GOOGLE_ISSUER,
        subject="google-subject-1",
        email="oauth-user@example.com",
        email_verified=True,
    )
    async for client in _client_with_identity(google_settings, session_factory, identity):
        response = await _oauth_roundtrip(client)

    assert response.status_code in {302, 303, 307}
    assert response.headers["location"] == "http://testserver/?oauth=success"
    assert "access_token" not in response.headers["location"]
    assert REFRESH_COOKIE_NAME in response.cookies
    assert CSRF_COOKIE_NAME in response.cookies

    user = (await db_session.execute(select(User).where(User.email_key == "oauth-user@example.com"))).scalar_one()
    linked_identity = (
        await db_session.execute(
            select(Identity).where(Identity.issuer == GOOGLE_ISSUER, Identity.subject == "google-subject-1")
        )
    ).scalar_one()
    assert linked_identity.user_id == user.id


@pytest.mark.asyncio
async def test_google_callback_reuses_existing_identity_without_duplicate_user(
    google_settings,
    session_factory,
    clean_database,
    db_session,
) -> None:
    identity = GoogleOAuthIdentity(
        issuer=GOOGLE_ISSUER,
        subject="stable-google-subject",
        email="stable@example.com",
        email_verified=True,
    )
    async for client in _client_with_identity(google_settings, session_factory, identity):
        first = await _oauth_roundtrip(client)
        second = await _oauth_roundtrip(client)

    assert first.status_code in {302, 303, 307}
    assert second.status_code in {302, 303, 307}
    users = (await db_session.execute(select(User).where(User.email_key == "stable@example.com"))).scalars().all()
    identities = (
        await db_session.execute(
            select(Identity).where(Identity.issuer == GOOGLE_ISSUER, Identity.subject == "stable-google-subject")
        )
    ).scalars().all()
    assert len(users) == 1
    assert len(identities) == 1


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "identity",
    [
        GoogleOAuthIdentity(
            issuer=GOOGLE_ISSUER,
            subject="missing-email",
            email=None,
            email_verified=True,
        ),
        GoogleOAuthIdentity(
            issuer=GOOGLE_ISSUER,
            subject="unverified-email",
            email="unverified@example.com",
            email_verified=False,
        ),
    ],
)
async def test_google_callback_fails_closed_for_missing_or_unverified_email(
    google_settings,
    session_factory,
    clean_database,
    db_session,
    identity,
) -> None:
    async for client in _client_with_identity(google_settings, session_factory, identity):
        response = await _oauth_roundtrip(client)

    assert response.status_code in {400, 401}
    assert (await db_session.execute(select(User))).scalars().all() == []
    assert (await db_session.execute(select(Identity))).scalars().all() == []
    assert "google-client-secret" not in response.text


@pytest.mark.asyncio
async def test_google_callback_replay_is_denied_with_security_evidence(
    google_settings,
    session_factory,
    clean_database,
    db_session,
) -> None:
    identity = GoogleOAuthIdentity(
        issuer=GOOGLE_ISSUER,
        subject="google-replay-subject",
        email="replay@example.com",
        email_verified=True,
    )
    async for client in _client_with_identity(google_settings, session_factory, identity):
        start = await client.get("/api/auth/oauth/google/start")
        state = parse_qs(urlparse(start.headers["location"]).query)["state"][0]
        first = await client.get(
            "/api/auth/oauth/google/callback",
            params={"state": state, "code": "auth-code"},
        )
        replay = await client.get(
            "/api/auth/oauth/google/callback",
            params={"state": state, "code": "auth-code"},
        )

    assert first.status_code in {302, 303, 307}
    assert replay.status_code in {400, 401}
    assert replay.json()["error"]["code"] == "oauth_state_invalid"

    event = await db_session.scalar(
        select(SecurityEvent).where(SecurityEvent.event_type == "oauth_transaction_replay")
    )
    assert event is not None
    assert event.event_metadata["artifact_type"] == "oauth_transaction"

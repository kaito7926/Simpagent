from __future__ import annotations

from dataclasses import dataclass
from urllib.parse import parse_qs, urlparse

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select

from app.identity.providers.github import GITHUB_ISSUER, GitHubOAuthIdentity
from app.main import create_app
from app.models.account import Identity, User
from app.security.refresh_tokens import CSRF_COOKIE_NAME, REFRESH_COOKIE_NAME


@dataclass(frozen=True)
class FakeGitHubProvider:
    identity: GitHubOAuthIdentity

    def authorization_url(self, *, state: str, code_challenge: str | None = None) -> str:
        return (
            "https://github.com/login/oauth/authorize"
            f"?state={state}&client_id=test&code_challenge={code_challenge}"
            "&code_challenge_method=S256"
        )

    async def authenticate(self, request) -> GitHubOAuthIdentity:
        assert request.code_verifier
        return self.identity


@pytest.fixture
def github_settings(settings):
    return settings.model_copy(
        update={
            "github_client_id": "github-client-id",
            "github_client_secret": "github-client-secret",
            "github_redirect_uri": "http://testserver/api/auth/oauth/github/callback",
            "public_app_origin": "http://testserver",
            "cookie_secure": False,
        }
    )


async def _client_with_identity(settings, session_factory, identity: GitHubOAuthIdentity):
    app = create_app(settings=settings, session_factory=session_factory)
    app.state.github_oauth_provider = FakeGitHubProvider(identity)
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://testserver",
        follow_redirects=False,
    ) as http_client:
        yield http_client


async def _oauth_roundtrip(client: AsyncClient):
    start = await client.get("/api/auth/oauth/github/start")
    assert start.status_code in {302, 303, 307}
    state = parse_qs(urlparse(start.headers["location"]).query)["state"][0]
    return await client.get(
        "/api/auth/oauth/github/callback",
        params={"state": state, "code": "github-auth-code"},
    )


@pytest.mark.asyncio
async def test_github_start_rejects_unconfigured_provider_without_secret_leak(settings, session_factory) -> None:
    app = create_app(
        settings=settings.model_copy(
            update={
                "github_client_id": None,
                "github_client_secret": None,
                "github_redirect_uri": None,
            }
        ),
        session_factory=session_factory,
    )
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://testserver",
        follow_redirects=False,
    ) as client:
        response = await client.get("/api/auth/oauth/github/start")

    assert response.status_code == 503
    payload = response.json()
    assert payload["error"]["code"] == "oauth_provider_unconfigured"
    assert "github-client-secret" not in response.text
    assert "client_secret" not in response.text


@pytest.mark.asyncio
async def test_github_start_redirects_only_when_configured(github_settings, session_factory, clean_database) -> None:
    app = create_app(settings=github_settings, session_factory=session_factory)
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://testserver",
        follow_redirects=False,
    ) as client:
        response = await client.get("/api/auth/oauth/github/start")

    assert response.status_code in {302, 303, 307}
    location = response.headers["location"]
    parsed = urlparse(location)
    assert parsed.scheme == "https"
    assert "github.com" in parsed.netloc
    query = parse_qs(parsed.query)
    assert query.get("state")
    assert query.get("code_challenge")
    assert query.get("code_challenge_method") == ["S256"]


@pytest.mark.asyncio
async def test_github_start_requires_dpop_binding_when_enabled(github_settings, session_factory, clean_database) -> None:
    app = create_app(settings=github_settings.model_copy(update={"dpop_enabled": True}), session_factory=session_factory)
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://testserver",
        follow_redirects=False,
    ) as client:
        response = await client.get("/api/auth/oauth/github/start")

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "invalid_dpop_binding"


@pytest.mark.asyncio
async def test_github_callback_provisions_verified_new_user_and_sets_first_party_cookies(
    github_settings,
    session_factory,
    clean_database,
    db_session,
) -> None:
    identity = GitHubOAuthIdentity(
        issuer=GITHUB_ISSUER,
        subject="github-user-1",
        email="github-user@example.com",
        email_verified=True,
    )
    async for client in _client_with_identity(github_settings, session_factory, identity):
        response = await _oauth_roundtrip(client)

    assert response.status_code in {302, 303, 307}
    assert response.headers["location"] == "http://testserver/?oauth=success"
    assert "access_token" not in response.headers["location"]
    assert REFRESH_COOKIE_NAME in response.cookies
    assert CSRF_COOKIE_NAME in response.cookies

    user = (await db_session.execute(select(User).where(User.email_key == "github-user@example.com"))).scalar_one()
    linked_identity = (
        await db_session.execute(
            select(Identity).where(Identity.issuer == GITHUB_ISSUER, Identity.subject == "github-user-1")
        )
    ).scalar_one()
    assert linked_identity.user_id == user.id
    assert linked_identity.email_verified is True


@pytest.mark.asyncio
async def test_github_callback_reuses_existing_subject_even_when_provider_email_changes(
    github_settings,
    session_factory,
    clean_database,
    db_session,
) -> None:
    initial_identity = GitHubOAuthIdentity(
        issuer=GITHUB_ISSUER,
        subject="stable-github-subject",
        email="stable@example.com",
        email_verified=True,
    )
    async for client in _client_with_identity(github_settings, session_factory, initial_identity):
        first = await _oauth_roundtrip(client)

    changed_identity = GitHubOAuthIdentity(
        issuer=GITHUB_ISSUER,
        subject="stable-github-subject",
        email="changed@example.com",
        email_verified=True,
    )
    async for client in _client_with_identity(github_settings, session_factory, changed_identity):
        second = await _oauth_roundtrip(client)

    assert first.status_code in {302, 303, 307}
    assert second.status_code in {302, 303, 307}
    users = (await db_session.execute(select(User))).scalars().all()
    identities = (
        await db_session.execute(
            select(Identity).where(Identity.issuer == GITHUB_ISSUER, Identity.subject == "stable-github-subject")
        )
    ).scalars().all()
    assert len(users) == 1
    assert users[0].email_key == "stable@example.com"
    assert len(identities) == 1


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "identity",
    [
        GitHubOAuthIdentity(
            issuer=GITHUB_ISSUER,
            subject="missing-email",
            email=None,
            email_verified=True,
        ),
        GitHubOAuthIdentity(
            issuer=GITHUB_ISSUER,
            subject="unverified-email",
            email="unverified@example.com",
            email_verified=False,
        ),
    ],
)
async def test_github_callback_fails_closed_for_missing_or_unverified_email(
    github_settings,
    session_factory,
    clean_database,
    db_session,
    identity,
) -> None:
    async for client in _client_with_identity(github_settings, session_factory, identity):
        response = await _oauth_roundtrip(client)

    assert response.status_code in {400, 401}
    assert (await db_session.execute(select(User))).scalars().all() == []
    assert (await db_session.execute(select(Identity))).scalars().all() == []
    assert "github-client-secret" not in response.text

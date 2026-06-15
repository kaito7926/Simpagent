from __future__ import annotations

from urllib.parse import parse_qs, urlparse

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import func, select

from app.main import create_app
from app.models.account import Identity, User


@pytest.fixture
def google_settings(settings):
    return settings.model_copy(
        update={
            "google_client_id": "google-client-id",
            "google_client_secret": "google-client-secret",
            "google_redirect_uri": "http://testserver/api/auth/oauth/google/callback",
        }
    )


@pytest.fixture
def google_app(google_settings, session_factory):
    return create_app(settings=google_settings, session_factory=session_factory)


@pytest.fixture
async def google_client(google_app, clean_database):
    async with AsyncClient(
        transport=ASGITransport(app=google_app),
        base_url="http://testserver",
        follow_redirects=False,
    ) as http_client:
        yield http_client


async def _count_rows(db_session, model) -> int:
    result = await db_session.execute(select(func.count()).select_from(model))
    return int(result.scalar_one())


@pytest.mark.asyncio
async def test_google_start_rejects_unconfigured_provider_without_secret_leak(client) -> None:
    response = await client.get("/api/auth/oauth/google/start")

    assert response.status_code == 503
    payload = response.json()
    assert payload["error"]["code"] == "oauth_provider_unconfigured"
    assert "google-client-secret" not in response.text
    assert "client_secret" not in response.text


@pytest.mark.asyncio
async def test_google_callback_invalid_state_creates_no_account_or_identity(
    google_client,
    db_session,
) -> None:
    response = await google_client.get(
        "/api/auth/oauth/google/callback",
        params={"state": "missing", "code": "auth-code"},
    )

    assert response.status_code in {400, 401}
    assert await _count_rows(db_session, User) == 0
    assert await _count_rows(db_session, Identity) == 0
    assert "google-client-secret" not in response.text


@pytest.mark.asyncio
async def test_google_start_redirects_only_when_configured(google_client) -> None:
    response = await google_client.get("/api/auth/oauth/google/start")

    assert response.status_code in {302, 303, 307}
    location = response.headers["location"]
    parsed = urlparse(location)
    assert parsed.scheme == "https"
    assert "accounts.google.com" in parsed.netloc
    assert parse_qs(parsed.query).get("state")

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

import pytest

from app.identity.providers.github import (
    GITHUB_EMAILS_URL,
    GITHUB_ISSUER,
    GITHUB_TOKEN_URL,
    GITHUB_USER_URL,
    GitHubOAuthProvider,
    GitHubOAuthRequest,
)
from app.identity.providers.google import (
    GOOGLE_ISSUER,
    GOOGLE_TOKEN_URL,
    GOOGLE_USERINFO_URL,
    GoogleOAuthProvider,
    GoogleOAuthRequest,
)


class FakeResponse:
    def __init__(self, payload: Any) -> None:
        self._payload = payload

    def raise_for_status(self) -> None:
        return None

    def json(self) -> Any:
        return self._payload


class RecordingOAuthClient:
    instances: list["RecordingOAuthClient"] = []
    response_map: dict[str, Any] = {}

    def __init__(self, **kwargs: Any) -> None:
        self.kwargs = kwargs
        self.fetch_token_calls: list[dict[str, Any]] = []
        self.get_calls: list[dict[str, Any]] = []
        self.token = None
        RecordingOAuthClient.instances.append(self)

    async def __aenter__(self) -> "RecordingOAuthClient":
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        return None

    async def fetch_token(self, url: str, **kwargs: Any) -> dict[str, str]:
        self.fetch_token_calls.append({"url": url, **kwargs})
        self.token = {"access_token": "test-access-token", "token_type": "Bearer"}
        return self.token

    async def get(self, url: str, **kwargs: Any) -> FakeResponse:
        self.get_calls.append({"url": url, **kwargs})
        if self.token is None:
            raise AssertionError("GET was called before fetch_token stored a token on the client")
        if "token" in kwargs:
            raise AssertionError("Provider passed unsupported token kwarg to AsyncOAuth2Client.get()")
        return FakeResponse(self.response_map[url])


@pytest.fixture(autouse=True)
def reset_recording_client_state() -> None:
    RecordingOAuthClient.instances.clear()
    RecordingOAuthClient.response_map = {}


@pytest.mark.asyncio
async def test_google_provider_uses_client_token_for_userinfo_request(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("app.identity.providers.google.AsyncOAuth2Client", RecordingOAuthClient)
    RecordingOAuthClient.response_map = {
        GOOGLE_USERINFO_URL: {
            "sub": "google-subject-1",
            "iss": GOOGLE_ISSUER,
            "email": "oauth-user@example.com",
            "email_verified": True,
        }
    }
    provider = GoogleOAuthProvider(
        client_id="google-client-id",
        client_secret="google-client-secret",
        redirect_uri="http://testserver/api/auth/oauth/google/callback",
        timeout_seconds=2.0,
    )

    identity = await provider.authenticate(
        GoogleOAuthRequest(
            code="auth-code",
            redirect_uri="http://testserver/api/auth/oauth/google/callback",
        )
    )

    assert identity.subject == "google-subject-1"
    client = RecordingOAuthClient.instances[0]
    assert client.fetch_token_calls == [
        {
            "url": GOOGLE_TOKEN_URL,
            "code": "auth-code",
            "grant_type": "authorization_code",
        }
    ]
    assert client.get_calls == [{"url": GOOGLE_USERINFO_URL}]


@pytest.mark.asyncio
async def test_github_provider_uses_client_token_for_user_and_email_requests(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("app.identity.providers.github.AsyncOAuth2Client", RecordingOAuthClient)
    RecordingOAuthClient.response_map = {
        GITHUB_USER_URL: {"id": 12345},
        GITHUB_EMAILS_URL: [
            {"email": "github-user@example.com", "primary": True, "verified": True}
        ],
    }
    provider = GitHubOAuthProvider(
        client_id="github-client-id",
        client_secret="github-client-secret",
        redirect_uri="http://testserver/api/auth/oauth/github/callback",
        timeout_seconds=2.0,
    )

    identity = await provider.authenticate(
        GitHubOAuthRequest(
            code="github-auth-code",
            redirect_uri="http://testserver/api/auth/oauth/github/callback",
        )
    )

    assert identity.subject == "12345"
    assert identity.issuer == GITHUB_ISSUER
    assert identity.email == "github-user@example.com"
    client = RecordingOAuthClient.instances[0]
    assert client.fetch_token_calls == [
        {
            "url": GITHUB_TOKEN_URL,
            "code": "github-auth-code",
            "grant_type": "authorization_code",
        }
    ]
    assert client.get_calls == [
        {"url": GITHUB_USER_URL},
        {"url": GITHUB_EMAILS_URL},
    ]

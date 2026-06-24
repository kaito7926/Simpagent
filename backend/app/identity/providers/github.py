from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from authlib.integrations.httpx_client import AsyncOAuth2Client

from app.core.config import Settings


GITHUB_ISSUER = "https://github.com"
GITHUB_AUTHORIZATION_URL = "https://github.com/login/oauth/authorize"
GITHUB_TOKEN_URL = "https://github.com/login/oauth/access_token"
GITHUB_USER_URL = "https://api.github.com/user"
GITHUB_EMAILS_URL = "https://api.github.com/user/emails"
GITHUB_SCOPE = "read:user user:email"


@dataclass(frozen=True)
class GitHubOAuthRequest:
    code: str
    redirect_uri: str
    code_verifier: str | None = None


@dataclass(frozen=True)
class GitHubOAuthIdentity:
    issuer: str
    subject: str
    email: str | None
    email_verified: bool


class GitHubOAuthProvider:
    def __init__(
        self,
        *,
        client_id: str,
        client_secret: str,
        redirect_uri: str,
        timeout_seconds: float = 10.0,
    ) -> None:
        self.client_id = client_id
        self.client_secret = client_secret
        self.redirect_uri = redirect_uri
        self.timeout_seconds = timeout_seconds

    @classmethod
    def from_settings(cls, settings: Settings) -> "GitHubOAuthProvider":
        secret = settings.github_client_secret
        secret_value = secret.get_secret_value() if hasattr(secret, "get_secret_value") else str(secret or "")
        if not settings.github_client_id or not secret_value or not settings.github_redirect_uri:
            raise ValueError("GitHub OAuth is not configured.")
        return cls(
            client_id=settings.github_client_id,
            client_secret=secret_value,
            redirect_uri=settings.github_redirect_uri,
            timeout_seconds=float(settings.provider_check_timeout_seconds),
        )

    def authorization_url(self, *, state: str, code_challenge: str | None = None) -> str:
        client = AsyncOAuth2Client(
            client_id=self.client_id,
            client_secret=self.client_secret,
            scope=GITHUB_SCOPE,
            redirect_uri=self.redirect_uri,
            timeout=self.timeout_seconds,
        )
        authorization_url, _ = client.create_authorization_url(
            GITHUB_AUTHORIZATION_URL,
            state=state,
            allow_signup="true",
            code_challenge=code_challenge,
            code_challenge_method="S256" if code_challenge else None,
        )
        return str(authorization_url)

    async def authenticate(self, request: GitHubOAuthRequest) -> GitHubOAuthIdentity:
        async with AsyncOAuth2Client(
            client_id=self.client_id,
            client_secret=self.client_secret,
            scope=GITHUB_SCOPE,
            redirect_uri=request.redirect_uri,
            timeout=self.timeout_seconds,
        ) as client:
            await client.fetch_token(
                GITHUB_TOKEN_URL,
                code=request.code,
                grant_type="authorization_code",
                code_verifier=request.code_verifier,
            )
            user_response = await client.get(GITHUB_USER_URL)
            user_response.raise_for_status()
            user_payload: dict[str, Any] = user_response.json()
            email_response = await client.get(GITHUB_EMAILS_URL)
            email_response.raise_for_status()
            emails_payload = email_response.json()

        subject = str(user_payload.get("id") or "")
        if not subject:
            raise ValueError("GitHub response did not include a stable subject.")
        email = _primary_verified_email(emails_payload)
        return GitHubOAuthIdentity(
            issuer=GITHUB_ISSUER,
            subject=subject,
            email=email,
            email_verified=email is not None,
        )


def _primary_verified_email(payload: Any) -> str | None:
    if not isinstance(payload, list):
        return None
    for item in payload:
        if not isinstance(item, dict):
            continue
        if item.get("primary") is True and item.get("verified") is True and isinstance(item.get("email"), str):
            return item["email"]
    return None

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from authlib.integrations.httpx_client import AsyncOAuth2Client

from app.core.config import Settings


GOOGLE_ISSUER = "https://accounts.google.com"
GOOGLE_AUTHORIZATION_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_USERINFO_URL = "https://openidconnect.googleapis.com/v1/userinfo"
GOOGLE_SCOPE = "openid email profile"


@dataclass(frozen=True)
class GoogleOAuthRequest:
    code: str
    redirect_uri: str


@dataclass(frozen=True)
class GoogleOAuthIdentity:
    issuer: str
    subject: str
    email: str | None
    email_verified: bool


class GoogleOAuthProvider:
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
    def from_settings(cls, settings: Settings) -> "GoogleOAuthProvider":
        secret = settings.google_client_secret
        secret_value = secret.get_secret_value() if hasattr(secret, "get_secret_value") else str(secret or "")
        if not settings.google_client_id or not secret_value or not settings.google_redirect_uri:
            raise ValueError("Google OAuth is not configured.")
        return cls(
            client_id=settings.google_client_id,
            client_secret=secret_value,
            redirect_uri=settings.google_redirect_uri,
            timeout_seconds=float(settings.provider_check_timeout_seconds),
        )

    def authorization_url(self, *, state: str) -> str:
        client = AsyncOAuth2Client(
            client_id=self.client_id,
            client_secret=self.client_secret,
            scope=GOOGLE_SCOPE,
            redirect_uri=self.redirect_uri,
            timeout=self.timeout_seconds,
        )
        authorization_url, _ = client.create_authorization_url(
            GOOGLE_AUTHORIZATION_URL,
            state=state,
            access_type="online",
            prompt="select_account",
        )
        return str(authorization_url)

    async def authenticate(self, request: GoogleOAuthRequest) -> GoogleOAuthIdentity:
        async with AsyncOAuth2Client(
            client_id=self.client_id,
            client_secret=self.client_secret,
            scope=GOOGLE_SCOPE,
            redirect_uri=request.redirect_uri,
            timeout=self.timeout_seconds,
        ) as client:
            token = await client.fetch_token(
                GOOGLE_TOKEN_URL,
                code=request.code,
                grant_type="authorization_code",
            )
            response = await client.get(GOOGLE_USERINFO_URL, token=token)
            response.raise_for_status()
            payload: dict[str, Any] = response.json()

        subject = str(payload.get("sub") or "")
        if not subject:
            raise ValueError("Google response did not include a stable subject.")
        issuer = str(payload.get("iss") or GOOGLE_ISSUER)
        return GoogleOAuthIdentity(
            issuer=issuer,
            subject=subject,
            email=payload.get("email") if isinstance(payload.get("email"), str) else None,
            email_verified=payload.get("email_verified") is True,
        )

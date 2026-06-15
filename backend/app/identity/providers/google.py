from __future__ import annotations

from dataclasses import dataclass


GOOGLE_ISSUER = "https://accounts.google.com"


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
    def authorization_url(self, *, state: str) -> str:
        raise NotImplementedError("Google authorization URL creation is implemented with the route slice.")

    async def authenticate(self, request: GoogleOAuthRequest) -> GoogleOAuthIdentity:
        raise NotImplementedError("Google token exchange is implemented with the route slice.")

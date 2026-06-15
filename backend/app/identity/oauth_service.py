from __future__ import annotations

from dataclasses import dataclass
from typing import Literal
from uuid import UUID

from app.schemas.auth import CurrentUserResponse


OAuthProviderName = Literal["google"]


@dataclass(frozen=True)
class OAuthLoginOutcome:
    access_token: str
    expires_in: int
    refresh_token: str
    csrf_token: str
    family_id: UUID
    current_user: CurrentUserResponse


class OAuthAuthenticationError(ValueError):
    pass


class OAuthService:
    async def complete_login(self, *args, **kwargs) -> OAuthLoginOutcome:
        raise NotImplementedError("OAuth login completion is implemented with the route slice.")

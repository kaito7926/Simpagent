from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings
from app.db.repositories.accounts import AccountsRepository
from app.db.repositories.sessions import SessionsRepository
from app.identity.local_provider import LocalAuthRequest, LocalIdentityProvider
from app.schemas.auth import CurrentUserResponse
from app.security.access_tokens import issue_access_token
from app.security.csrf import require_allowed_origin
from app.security.refresh_tokens import (
    generate_refresh_token,
    issue_family_absolute_expiry,
    issue_refresh_expiry,
    issue_token_jti,
    lookup_digest,
)


@dataclass(frozen=True)
class LoginOutcome:
    access_token: str
    expires_in: int
    refresh_token: str
    csrf_token: str
    family_id: UUID
    current_user: CurrentUserResponse


class AuthenticationFailed(ValueError):
    pass


class AuthenticationService:
    def __init__(self, session: AsyncSession, settings: Settings) -> None:
        self.session = session
        self.settings = settings
        self.accounts = AccountsRepository(session)
        self.sessions = SessionsRepository(session)
        self.provider = LocalIdentityProvider(session)

    async def login(self, *, email: str, password: str, origin: str | None, now: datetime) -> LoginOutcome:
        require_allowed_origin(origin, self.settings)
        async with self.session.begin():
            decision = await self.provider.check_credentials(LocalAuthRequest(email=email, password=password))
            if decision.verified_identity is None or decision.user_id is None:
                raise AuthenticationFailed("Invalid credentials")

            bundle = await self.accounts.get_user_bundle_by_id(decision.user_id)
            if bundle is None or not bundle.user.is_active:
                raise AuthenticationFailed("Invalid credentials")

            scopes = sorted(scope.scope for scope in bundle.scopes)
            role = bundle.user.role
            access_token = issue_access_token(
                user_id=bundle.user.id,
                role=role,
                scopes=scopes,
                settings=self.settings,
                now=now,
            )
            family = await self.sessions.create_family(
                user_id=bundle.user.id,
                absolute_expires_at=issue_family_absolute_expiry(now=now, settings=self.settings),
            )
            refresh_token = generate_refresh_token()
            await self.sessions.create_token(
                family_id=family.id,
                jti=issue_token_jti(),
                token_hash=lookup_digest(refresh_token, self.settings),
                expires_at=issue_refresh_expiry(
                    now=now,
                    settings=self.settings,
                    absolute_expires_at=family.absolute_expires_at,
                ),
            )
        from app.security.csrf import issue_csrf_token

        csrf_token = issue_csrf_token(family_id=family.id, settings=self.settings)
        return LoginOutcome(
            access_token=access_token,
            expires_in=self.settings.access_token_ttl_seconds,
            refresh_token=refresh_token,
            csrf_token=csrf_token,
            family_id=family.id,
            current_user=CurrentUserResponse(
                id=bundle.user.id,
                email=bundle.user.email,
                role=bundle.user.role,
                scopes=scopes,
                is_active=bundle.user.is_active,
            ),
        )

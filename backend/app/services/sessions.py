from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings
from app.db.repositories.accounts import AccountsRepository
from app.db.repositories.sessions import SessionsRepository
from app.schemas.auth import CurrentUserResponse
from app.security.access_tokens import issue_access_token
from app.security.csrf import CsrfValidationError, require_allowed_origin, validate_csrf_token
from app.security.refresh_tokens import (
    CSRF_COOKIE_NAME,
    REFRESH_COOKIE_NAME,
    generate_refresh_token,
    issue_refresh_expiry,
    issue_token_jti,
    lookup_digest,
)


class RefreshStatus(str, Enum):
    rotated = "rotated"
    invalid = "invalid"
    replay = "replay"
    expired = "expired"


@dataclass(frozen=True)
class RefreshOutcome:
    status: RefreshStatus
    access_token: str | None = None
    expires_in: int | None = None
    refresh_token: str | None = None
    csrf_token: str | None = None
    current_user: CurrentUserResponse | None = None


class SessionsService:
    def __init__(self, session: AsyncSession, settings: Settings) -> None:
        self.session = session
        self.settings = settings
        self.sessions = SessionsRepository(session)
        self.accounts = AccountsRepository(session)

    async def refresh(
        self,
        *,
        refresh_token: str | None,
        csrf_cookie: str | None,
        csrf_header: str | None,
        origin: str | None,
        now: datetime,
        correlation_id: str | None,
    ) -> RefreshOutcome:
        require_allowed_origin(origin, self.settings)
        if not refresh_token:
            return RefreshOutcome(status=RefreshStatus.invalid)
        token_hash = lookup_digest(refresh_token, self.settings)
        async with self.session.begin():
            token = await self.sessions.get_token_by_hash_for_update(token_hash)
            if token is None:
                return RefreshOutcome(status=RefreshStatus.invalid)
            family = await self.sessions.get_family_for_update(token.family_id)
            if family is None:
                return RefreshOutcome(status=RefreshStatus.invalid)
            validate_csrf_token(
                csrf_cookie=csrf_cookie,
                csrf_header=csrf_header,
                family_id=family.id,
                settings=self.settings,
            )
            if family.revoked_at is not None or family.absolute_expires_at <= now or token.revoked_at is not None:
                return RefreshOutcome(status=RefreshStatus.invalid)
            if token.used_at is not None or token.replaced_by_id is not None:
                await self.sessions.revoke_family(family, now=now, reason="refresh_reuse")
                await self.sessions.add_security_event(
                    event_type="refresh_reuse",
                    severity="high",
                    user_id=family.user_id,
                    description="Refresh-token replay detected.",
                    correlation_id=correlation_id,
                    metadata={"family_id": str(family.id)},
                )
                return RefreshOutcome(status=RefreshStatus.replay)
            if token.expires_at <= now:
                return RefreshOutcome(status=RefreshStatus.expired)
            bundle = await self.accounts.get_user_bundle_by_id(family.user_id)
            if bundle is None or not bundle.user.is_active:
                await self.sessions.revoke_family(family, now=now, reason="inactive_user")
                return RefreshOutcome(status=RefreshStatus.invalid)
            new_refresh_token = generate_refresh_token()
            child = await self.sessions.create_token(
                family_id=family.id,
                jti=issue_token_jti(),
                token_hash=lookup_digest(new_refresh_token, self.settings),
                expires_at=issue_refresh_expiry(
                    now=now,
                    settings=self.settings,
                    absolute_expires_at=family.absolute_expires_at,
                ),
                parent_token_id=token.id,
            )
            await self.sessions.mark_token_used(token, now=now, replacement=child)
            family.last_rotated_at = now
            scopes = sorted(scope.scope for scope in bundle.scopes)
            access_token = issue_access_token(
                user_id=bundle.user.id,
                role=bundle.user.role,
                scopes=scopes,
                settings=self.settings,
                now=now,
            )
        from app.security.csrf import issue_csrf_token

        return RefreshOutcome(
            status=RefreshStatus.rotated,
            access_token=access_token,
            expires_in=self.settings.access_token_ttl_seconds,
            refresh_token=new_refresh_token,
            csrf_token=issue_csrf_token(family_id=family.id, settings=self.settings),
            current_user=CurrentUserResponse(
                id=bundle.user.id,
                email=bundle.user.email,
                role=bundle.user.role,
                scopes=scopes,
                is_active=bundle.user.is_active,
            ),
        )

    async def logout(
        self,
        *,
        refresh_token: str | None,
        csrf_cookie: str | None,
        csrf_header: str | None,
        origin: str | None,
        now: datetime,
    ) -> None:
        require_allowed_origin(origin, self.settings)
        if not refresh_token:
            return None
        token_hash = lookup_digest(refresh_token, self.settings)
        async with self.session.begin():
            token = await self.sessions.get_token_by_hash_for_update(token_hash)
            if token is None:
                return None
            family = await self.sessions.get_family_for_update(token.family_id)
            if family is None:
                return None
            validate_csrf_token(
                csrf_cookie=csrf_cookie,
                csrf_header=csrf_header,
                family_id=family.id,
                settings=self.settings,
            )
            if family.revoked_at is None:
                await self.sessions.revoke_family(family, now=now, reason="logout")
        return None

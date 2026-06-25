from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Literal
from uuid import UUID

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings
from app.db.repositories.accounts import AccountsRepository, DuplicateEmailError, normalize_email
from app.db.repositories.sessions import SessionsRepository
from app.identity.providers.github import GitHubOAuthIdentity
from app.identity.providers.google import GoogleOAuthIdentity
from app.schemas.auth import CurrentUserResponse
from app.security.access_tokens import issue_access_token
from app.security.refresh_tokens import (
    generate_refresh_token,
    issue_family_absolute_expiry,
    issue_refresh_expiry,
    issue_token_jti,
    lookup_digest,
)


OAuthProviderName = Literal["google", "github"]
OAuthIdentity = GoogleOAuthIdentity | GitHubOAuthIdentity


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
    def __init__(self, session: AsyncSession, settings: Settings) -> None:
        self.session = session
        self.settings = settings
        self.accounts = AccountsRepository(session)
        self.sessions = SessionsRepository(session)

    async def complete_login(
        self,
        *,
        provider_name: OAuthProviderName,
        identity: OAuthIdentity,
        now: datetime,
        key_thumbprint: str | None = None,
    ) -> OAuthLoginOutcome:
        if provider_name not in {"google", "github"}:
            raise OAuthAuthenticationError("Unsupported OAuth provider.")
        if not identity.subject or not identity.issuer:
            raise OAuthAuthenticationError("OAuth identity is incomplete.")
        if not identity.email or not identity.email_verified:
            raise OAuthAuthenticationError("OAuth email identity is not verified.")

        normalized_email, _ = normalize_email(identity.email)
        try:
            async with self.session.begin():
                bundle = await self.accounts.get_user_bundle_by_identity_subject(
                    issuer=identity.issuer,
                    subject=identity.subject,
                )
                if bundle is None:
                    bundle = await self._link_or_provision_verified_identity(
                        identity=identity,
                        normalized_email=normalized_email,
                    )
                if not bundle.user.is_active:
                    raise OAuthAuthenticationError("OAuth account is inactive.")

                scopes = sorted(scope.scope for scope in bundle.scopes)
                access_token = issue_access_token(
                    user_id=bundle.user.id,
                    role=bundle.user.role,
                    scopes=scopes,
                    settings=self.settings,
                    now=now,
                    key_thumbprint=key_thumbprint,
                )
                family = await self.sessions.create_family(
                    user_id=bundle.user.id,
                    absolute_expires_at=issue_family_absolute_expiry(now=now, settings=self.settings),
                )
                family.auth_binding_method = "dpop" if key_thumbprint else "bearer"
                family.key_thumbprint = key_thumbprint
                family.binding_created_at = now
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
        except (DuplicateEmailError, IntegrityError) as exc:
            raise OAuthAuthenticationError("OAuth identity could not be linked safely.") from exc

        from app.security.csrf import issue_csrf_token

        csrf_token = issue_csrf_token(family_id=family.id, settings=self.settings)
        return OAuthLoginOutcome(
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

    async def _link_or_provision_verified_identity(
        self,
        *,
        identity: OAuthIdentity,
        normalized_email: str,
    ):
        bundle = await self.accounts.get_user_bundle_by_email(normalized_email)
        if bundle is not None:
            conflicting_identity = next(
                (
                    item
                    for item in bundle.identities
                    if item.issuer == identity.issuer and item.subject != identity.subject
                ),
                None,
            )
            if conflicting_identity is not None:
                raise OAuthAuthenticationError("OAuth identity conflicts with an existing account.")
        else:
            bundle = await self.accounts.create_user_without_local_credentials(
                email=normalized_email,
                role="user",
                is_demo=False,
            )

        linked_identity = await self.accounts.create_identity(
            user_id=bundle.user.id,
            issuer=identity.issuer,
            subject=identity.subject,
            email_at_provider=normalized_email,
            email_verified=True,
        )
        bundle.identities.append(linked_identity)
        return bundle

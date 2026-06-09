from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.repositories.accounts import AccountsRepository
from app.identity.contracts import IdentityProvider, VerifiedIdentity
from app.security.passwords import verify_password_or_dummy


LOCAL_ISSUER = "local"


@dataclass(frozen=True)
class LocalAuthRequest:
    email: str
    password: str


@dataclass(frozen=True)
class AuthenticationDecision:
    verified_identity: VerifiedIdentity | None
    user_id: object | None
    password_hash: str | None
    is_active: bool


class LocalIdentityProvider(IdentityProvider):
    def __init__(self, session: AsyncSession) -> None:
        self._repository = AccountsRepository(session)

    async def authenticate(self, request: object) -> VerifiedIdentity:
        if not isinstance(request, LocalAuthRequest):
            raise TypeError("LocalIdentityProvider expects LocalAuthRequest")
        decision = await self.check_credentials(request=request)
        if decision.verified_identity is None:
            raise ValueError("Invalid credentials")
        return decision.verified_identity

    async def check_credentials(self, request: LocalAuthRequest) -> AuthenticationDecision:
        bundle = await self._repository.get_user_bundle_by_email(request.email)
        password_hash = bundle.local_credential.password_hash if bundle and bundle.local_credential else None
        password_ok = verify_password_or_dummy(request.password, password_hash)
        if not bundle or not bundle.local_credential or not password_ok or not bundle.user.is_active:
            return AuthenticationDecision(
                verified_identity=None,
                user_id=bundle.user.id if bundle else None,
                password_hash=password_hash,
                is_active=bool(bundle.user.is_active) if bundle else False,
            )
        identity = next((item for item in bundle.identities if item.issuer == LOCAL_ISSUER), None)
        if identity is None:
            return AuthenticationDecision(verified_identity=None, user_id=bundle.user.id, password_hash=password_hash, is_active=bundle.user.is_active)
        return AuthenticationDecision(
            verified_identity=VerifiedIdentity(
                issuer=identity.issuer,
                subject=identity.subject,
                email=bundle.user.email,
                email_verified=True,
                authentication_method="password",
            ),
            user_id=bundle.user.id,
            password_hash=password_hash,
            is_active=bundle.user.is_active,
        )

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID, uuid4

from email_validator import validate_email
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.account import Identity, LocalCredential, User, UserScope
from app.schemas.auth import ADMIN_SCOPES, STANDARD_USER_SCOPES


@dataclass(slots=True)
class UserBundle:
    user: User
    scopes: list[UserScope]
    identities: list[Identity]
    local_credential: LocalCredential | None


class DuplicateEmailError(ValueError):
    pass


def normalize_email(email: str) -> tuple[str, str]:
    normalized = validate_email(email, check_deliverability=False, test_environment=True).normalized
    email_key = normalized.casefold()
    return normalized, email_key


class AccountsRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_user_bundle_by_email(self, email: str) -> UserBundle | None:
        _, email_key = normalize_email(email)
        stmt = (
            select(User)
            .options(
                selectinload(User.scopes),
                selectinload(User.identities),
                selectinload(User.local_credential),
            )
            .where(User.email_key == email_key)
        )
        result = await self.session.execute(stmt)
        user = result.scalar_one_or_none()
        if user is None:
            return None
        return UserBundle(user=user, scopes=list(user.scopes), identities=list(user.identities), local_credential=user.local_credential)

    async def get_user_bundle_by_id(self, user_id: UUID) -> UserBundle | None:
        stmt = (
            select(User)
            .options(
                selectinload(User.scopes),
                selectinload(User.identities),
                selectinload(User.local_credential),
            )
            .where(User.id == user_id)
        )
        result = await self.session.execute(stmt)
        user = result.scalar_one_or_none()
        if user is None:
            return None
        return UserBundle(user=user, scopes=list(user.scopes), identities=list(user.identities), local_credential=user.local_credential)

    async def get_user_bundle_by_identity(self, *, issuer: str, subject: str) -> UserBundle | None:
        stmt = (
            select(User)
            .join(Identity, Identity.user_id == User.id)
            .options(
                selectinload(User.scopes),
                selectinload(User.identities),
                selectinload(User.local_credential),
            )
            .where(Identity.issuer == issuer, Identity.subject == subject)
        )
        result = await self.session.execute(stmt)
        user = result.scalar_one_or_none()
        if user is None:
            return None
        return UserBundle(user=user, scopes=list(user.scopes), identities=list(user.identities), local_credential=user.local_credential)

    async def get_user_bundle_by_identity_subject(self, *, issuer: str, subject: str) -> UserBundle | None:
        return await self.get_user_bundle_by_identity(issuer=issuer, subject=subject)

    async def create_user_with_local_credentials(self, *, email: str, password_hash: str, role: str = "user", is_demo: bool = False) -> UserBundle:
        normalized, email_key = normalize_email(email)
        user = User(id=uuid4(), email=normalized, email_key=email_key, role=role, is_active=True, is_demo=is_demo)
        scopes = ADMIN_SCOPES if role == "admin" else STANDARD_USER_SCOPES
        scope_rows = [UserScope(user_id=user.id, scope=scope) for scope in scopes]
        credential = LocalCredential(user_id=user.id, password_hash=password_hash)
        self.session.add(user)
        self.session.add_all(scope_rows)
        self.session.add(credential)
        try:
            await self.session.flush()
        except IntegrityError as exc:
            raise DuplicateEmailError("Duplicate email") from exc
        return UserBundle(user=user, scopes=scope_rows, identities=[], local_credential=credential)

    async def create_user_without_local_credentials(self, *, email: str, role: str = "user", is_demo: bool = False) -> UserBundle:
        normalized, email_key = normalize_email(email)
        user = User(id=uuid4(), email=normalized, email_key=email_key, role=role, is_active=True, is_demo=is_demo)
        scopes = ADMIN_SCOPES if role == "admin" else STANDARD_USER_SCOPES
        scope_rows = [UserScope(user_id=user.id, scope=scope) for scope in scopes]
        self.session.add(user)
        self.session.add_all(scope_rows)
        try:
            await self.session.flush()
        except IntegrityError as exc:
            raise DuplicateEmailError("Duplicate email") from exc
        return UserBundle(user=user, scopes=scope_rows, identities=[], local_credential=None)

    async def create_identity(self, *, user_id: UUID, issuer: str, subject: str, email_at_provider: str | None, email_verified: bool) -> Identity:
        identity = Identity(
            user_id=user_id,
            issuer=issuer,
            subject=subject,
            email_at_provider=email_at_provider,
            email_verified=email_verified,
        )
        self.session.add(identity)
        await self.session.flush()
        return identity

    async def set_user_active(self, user_id: UUID, *, is_active: bool) -> None:
        bundle = await self.get_user_bundle_by_id(user_id)
        if bundle is None:
            raise ValueError("User not found")
        bundle.user.is_active = is_active
        await self.session.flush()

    async def replace_user_scopes(self, user_id: UUID, scopes: list[str]) -> None:
        bundle = await self.get_user_bundle_by_id(user_id)
        if bundle is None:
            raise ValueError("User not found")
        await self.replace_bundle_scopes(bundle, scopes)

    async def replace_bundle_scopes(self, bundle: UserBundle, scopes: list[str]) -> None:
        expected_scopes = list(dict.fromkeys(scopes))
        current_by_scope = {row.scope: row for row in bundle.scopes}

        for scope, row in list(current_by_scope.items()):
            if scope in expected_scopes:
                continue
            await self.session.delete(row)
            bundle.scopes.remove(row)

        for scope in expected_scopes:
            if scope in current_by_scope:
                continue
            scope_row = UserScope(user_id=bundle.user.id, scope=scope)
            self.session.add(scope_row)
            bundle.scopes.append(scope_row)
        await self.session.flush()

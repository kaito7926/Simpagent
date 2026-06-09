from __future__ import annotations

from contextlib import asynccontextmanager
from dataclasses import dataclass
from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import SecretStr
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings
from app.db.repositories.accounts import AccountsRepository
from app.identity.account_linker import AccountLinker
from app.identity.local_provider import LOCAL_ISSUER
from app.models.account import LocalCredential, User
from app.models.session import RefreshTokenFamily
from app.schemas.auth import ADMIN_SCOPES, STANDARD_USER_SCOPES
from app.security.passwords import hash_password, verify_password

DEMO_SEED_LOCK_KEY = 101_001
ADMIN_BOOTSTRAP_LOCK_KEY = 101_002


class ProvisioningError(RuntimeError):
    pass


@dataclass(frozen=True, slots=True)
class DemoSeedResult:
    status: Literal["noop", "seeded"]
    created: int = 0
    updated: int = 0
    revoked_families: int = 0


@dataclass(frozen=True, slots=True)
class BootstrapAdminResult:
    status: Literal["created", "promoted"]
    user_id: UUID
    email: str


class ProvisioningRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.accounts = AccountsRepository(session)
        self.linker = AccountLinker(session)

    @asynccontextmanager
    async def _transaction(self):
        if self.session.in_transaction():
            yield
            return
        async with self.session.begin():
            yield

    async def ensure_demo_accounts(self, *, settings: Settings, now: datetime) -> DemoSeedResult:
        if not settings.demo_seed_enabled:
            return DemoSeedResult(status="noop")
        if settings.app_env != "development":
            raise ProvisioningError("Demo seed is allowed only when APP_ENV=development.")

        user_password = _secret_value(settings.demo_user_password)
        admin_password = _secret_value(settings.demo_admin_password)
        if not user_password or not admin_password:
            raise ProvisioningError("Demo seed requires both demo user and admin passwords.")

        async with self._transaction():
            await self._acquire_lock(DEMO_SEED_LOCK_KEY)
            created = 0
            updated = 0
            revoked_families = 0
            for email, password, role in (
                (settings.demo_user_email, user_password, "user"),
                (settings.demo_admin_email, admin_password, "admin"),
            ):
                change = await self._upsert_local_account(
                    email=email,
                    password=password,
                    role=role,
                    is_demo=True,
                    now=now,
                    revoke_reason="demo_password_changed",
                )
                created += int(change.created)
                updated += int(change.updated)
                revoked_families += change.revoked_families
        return DemoSeedResult(
            status="seeded",
            created=created,
            updated=updated,
            revoked_families=revoked_families,
        )

    async def bootstrap_admin(
        self,
        *,
        settings: Settings,
        email: str,
        now: datetime,
        password: str | None,
    ) -> BootstrapAdminResult:
        if settings.app_env == "development":
            raise ProvisioningError("Bootstrap admin is intended for production or an explicit non-development operator mode.")

        async with self._transaction():
            await self._acquire_lock(ADMIN_BOOTSTRAP_LOCK_KEY)
            existing_admin = await self._find_existing_admin()
            if existing_admin is not None:
                raise ProvisioningError("An admin account already exists. Bootstrap can only run once.")

            bundle = await self.accounts.get_user_bundle_by_email(email)
            if bundle is None:
                if not password:
                    raise ProvisioningError("A password is required to create the first admin account.")
                password_hash = hash_password(password, email_hint=email)
                created = await self.accounts.create_user_with_local_credentials(
                    email=email,
                    password_hash=password_hash,
                    role="admin",
                    is_demo=False,
                )
                if not any(identity.issuer == LOCAL_ISSUER for identity in created.identities):
                    await self.linker.link_local_identity(
                        user_id=created.user.id,
                        email=created.user.email,
                        email_key=created.user.email_key,
                    )
                result = BootstrapAdminResult(
                    status="created",
                    user_id=created.user.id,
                    email=created.user.email,
                )
            else:
                bundle.user.role = "admin"
                bundle.user.is_demo = False
                bundle.user.is_active = True
                await self.accounts.replace_user_scopes(bundle.user.id, list(ADMIN_SCOPES))
                if bundle.local_credential is None:
                    if not password:
                        raise ProvisioningError("A password is required to add local credentials for the first admin account.")
                    self.session.add(
                        LocalCredential(
                            user_id=bundle.user.id,
                            password_hash=hash_password(password, email_hint=bundle.user.email),
                        )
                    )
                if not any(identity.issuer == LOCAL_ISSUER for identity in bundle.identities):
                    await self.linker.link_local_identity(
                        user_id=bundle.user.id,
                        email=bundle.user.email,
                        email_key=bundle.user.email_key,
                    )
                await self.session.flush()
                result = BootstrapAdminResult(
                    status="promoted",
                    user_id=bundle.user.id,
                    email=bundle.user.email,
                )

            await self._record_security_event(
                event_type="admin_bootstrap",
                user_id=result.user_id,
                correlation_id=None,
                description="First admin bootstrap completed.",
                metadata={"status": result.status, "email": "redacted"},
            )
        return result

    async def bootstrap_password_required(self, *, email: str) -> bool:
        bundle = await self.accounts.get_user_bundle_by_email(email)
        return bundle is None or bundle.local_credential is None

    async def _acquire_lock(self, key: int) -> None:
        await self.session.execute(text("SELECT pg_advisory_xact_lock(:key)"), {"key": key})

    async def _find_existing_admin(self) -> User | None:
        stmt = select(User).where(User.role == "admin").limit(1)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def _record_security_event(
        self,
        *,
        event_type: str,
        user_id: UUID | None,
        correlation_id: str | None,
        description: str,
        metadata: dict[str, str],
    ) -> None:
        from app.db.repositories.sessions import SessionsRepository

        events = SessionsRepository(self.session)
        await events.add_security_event(
            event_type=event_type,
            severity="info",
            user_id=user_id,
            description=description,
            correlation_id=correlation_id,
            metadata=metadata,
        )

    async def _upsert_local_account(
        self,
        *,
        email: str,
        password: str,
        role: Literal["user", "admin"],
        is_demo: bool,
        now: datetime,
        revoke_reason: str,
    ) -> _AccountChange:
        bundle = await self.accounts.get_user_bundle_by_email(email)
        expected_scopes = list(ADMIN_SCOPES if role == "admin" else STANDARD_USER_SCOPES)
        expected_scope_set = set(expected_scopes)

        if bundle is None:
            password_hash = hash_password(password, email_hint=email)
            created = await self.accounts.create_user_with_local_credentials(
                email=email,
                password_hash=password_hash,
                role=role,
                is_demo=is_demo,
            )
            await self.linker.link_local_identity(
                user_id=created.user.id,
                email=created.user.email,
                email_key=created.user.email_key,
            )
            return _AccountChange(created=True, updated=False, revoked_families=0)

        updated = False
        revoked_families = 0
        if bundle.user.role != role:
            bundle.user.role = role
            updated = True
        if bundle.user.is_demo != is_demo:
            bundle.user.is_demo = is_demo
            updated = True
        if not bundle.user.is_active:
            bundle.user.is_active = True
            updated = True
        current_scopes = {scope.scope for scope in bundle.scopes}
        if current_scopes != expected_scope_set:
            await self.accounts.replace_user_scopes(bundle.user.id, expected_scopes)
            updated = True
        if not any(identity.issuer == LOCAL_ISSUER for identity in bundle.identities):
            await self.linker.link_local_identity(
                user_id=bundle.user.id,
                email=bundle.user.email,
                email_key=bundle.user.email_key,
            )
            updated = True

        password_hash = hash_password(password, email_hint=bundle.user.email)
        password_changed = (
            bundle.local_credential is None
            or not verify_password(password, bundle.local_credential.password_hash)
        )
        if password_changed:
            if bundle.local_credential is None:
                self.session.add(LocalCredential(user_id=bundle.user.id, password_hash=password_hash))
            else:
                bundle.local_credential.password_hash = password_hash
                bundle.local_credential.password_updated_at = now
            revoked_families = await self._revoke_active_families_for_user(
                bundle.user.id,
                now=now,
                reason=revoke_reason,
            )
            updated = True

        await self.session.flush()
        return _AccountChange(created=False, updated=updated, revoked_families=revoked_families)

    async def _revoke_active_families_for_user(self, user_id: UUID, *, now: datetime, reason: str) -> int:
        stmt = (
            select(RefreshTokenFamily)
            .where(RefreshTokenFamily.user_id == user_id, RefreshTokenFamily.revoked_at.is_(None))
            .with_for_update()
        )
        families = list((await self.session.execute(stmt)).scalars().all())
        for family in families:
            family.revoked_at = now
            family.revoke_reason = reason
        if families:
            await self.session.flush()
        return len(families)


@dataclass(frozen=True, slots=True)
class _AccountChange:
    created: bool
    updated: bool
    revoked_families: int


def _secret_value(value: SecretStr | str | None) -> str | None:
    if value is None:
        return None
    if isinstance(value, SecretStr):
        return value.get_secret_value()
    return value

from __future__ import annotations

import hmac
from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.repositories.accounts import AccountsRepository, DuplicateEmailError, normalize_email
from app.identity.account_linker import AccountLinker
from app.security.csrf import require_allowed_origin
from app.security.passwords import hash_password


@dataclass(frozen=True)
class RegistrationOutcome:
    created: bool
    normalized_email: str


class RegistrationInviteRejected(ValueError):
    pass


class RegistrationService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.accounts = AccountsRepository(session)
        self.linker = AccountLinker(session)

    async def register(
        self,
        *,
        email: str,
        password: str,
        invite_code: str | None,
        origin: str | None,
        settings,
    ) -> RegistrationOutcome:
        require_allowed_origin(origin, settings)
        expected_invite_code = settings.registration_invite_code_value
        if expected_invite_code and not hmac.compare_digest(
            (invite_code or "").strip().encode("utf-8"),
            expected_invite_code.encode("utf-8"),
        ):
            raise RegistrationInviteRejected("Invalid registration invite code")
        normalized_email, email_key = normalize_email(email)
        password_hash = hash_password(password, email_hint=normalized_email)
        created = False
        async with self.session.begin():
            try:
                bundle = await self.accounts.create_user_with_local_credentials(
                    email=normalized_email,
                    password_hash=password_hash,
                    role="user",
                    is_demo=False,
                )
            except DuplicateEmailError:
                bundle = None
            else:
                created = True
                await self.linker.link_local_identity(
                    user_id=bundle.user.id,
                    email=normalized_email,
                    email_key=email_key,
                )
        return RegistrationOutcome(created=created, normalized_email=normalized_email)

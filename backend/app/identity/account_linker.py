from __future__ import annotations

from uuid import uuid4

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.repositories.accounts import AccountsRepository
from app.identity.contracts import VerifiedIdentity
from app.identity.local_provider import LOCAL_ISSUER


def local_subject_for_email(email_key: str) -> str:
    return f"local:{email_key}:{uuid4()}"


class AccountLinker:
    def __init__(self, session: AsyncSession) -> None:
        self._repository = AccountsRepository(session)

    async def link_local_identity(self, *, user_id, email: str, email_key: str) -> VerifiedIdentity:
        subject = local_subject_for_email(email_key)
        identity = await self._repository.create_identity(
            user_id=user_id,
            issuer=LOCAL_ISSUER,
            subject=subject,
            email_at_provider=email,
            email_verified=True,
        )
        return VerifiedIdentity(
            issuer=identity.issuer,
            subject=identity.subject,
            email=email,
            email_verified=True,
            authentication_method="password",
        )

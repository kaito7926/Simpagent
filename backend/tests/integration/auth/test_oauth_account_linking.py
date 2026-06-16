from __future__ import annotations

from datetime import UTC, datetime

import pytest
from sqlalchemy import func, select

from app.db.repositories.accounts import AccountsRepository
from app.identity.oauth_service import OAuthAuthenticationError, OAuthService
from app.identity.providers.github import GITHUB_ISSUER, GitHubOAuthIdentity
from app.models.account import Identity, User
from app.models.session import RefreshTokenFamily


NOW = datetime(2026, 6, 16, 4, 0, tzinfo=UTC)


async def _count_rows(db_session, model) -> int:
    result = await db_session.execute(select(func.count()).select_from(model))
    return int(result.scalar_one())


async def _create_local_user(db_session, email: str):
    async with db_session.begin():
        return await AccountsRepository(db_session).create_user_with_local_credentials(
            email=email,
            password_hash="not-used-in-oauth-linking-tests",
        )


async def _create_github_identity(db_session, *, email: str, subject: str):
    async with db_session.begin():
        accounts = AccountsRepository(db_session)
        bundle = await accounts.create_user_without_local_credentials(email=email)
        identity = await accounts.create_identity(
            user_id=bundle.user.id,
            issuer=GITHUB_ISSUER,
            subject=subject,
            email_at_provider=email,
            email_verified=True,
        )
        return bundle, identity


@pytest.mark.asyncio
async def test_verified_github_email_auto_links_matching_local_account(settings, db_session, clean_database) -> None:
    local = await _create_local_user(db_session, "Owner@Example.com")

    outcome = await OAuthService(db_session, settings).complete_login(
        provider_name="github",
        identity=GitHubOAuthIdentity(
            issuer=GITHUB_ISSUER,
            subject="github-safe-link",
            email="owner@example.com",
            email_verified=True,
        ),
        now=NOW,
    )

    assert outcome.current_user.id == local.user.id
    linked_identity = (
        await db_session.execute(
            select(Identity).where(Identity.issuer == GITHUB_ISSUER, Identity.subject == "github-safe-link")
        )
    ).scalar_one()
    assert linked_identity.user_id == local.user.id
    assert linked_identity.email_at_provider == "owner@example.com"
    assert await _count_rows(db_session, RefreshTokenFamily) == 1


@pytest.mark.asyncio
async def test_verified_new_github_email_auto_provisions_standard_user(settings, db_session, clean_database) -> None:
    outcome = await OAuthService(db_session, settings).complete_login(
        provider_name="github",
        identity=GitHubOAuthIdentity(
            issuer=GITHUB_ISSUER,
            subject="github-new-user",
            email="new-github-user@example.com",
            email_verified=True,
        ),
        now=NOW,
    )

    user = (await db_session.execute(select(User).where(User.email_key == "new-github-user@example.com"))).scalar_one()
    assert outcome.current_user.id == user.id
    assert outcome.current_user.role == "user"
    assert sorted(outcome.current_user.scopes) == ["chat:read", "chat:write", "tool:python", "tool:websearch"]
    assert await _count_rows(db_session, Identity) == 1
    assert await _count_rows(db_session, RefreshTokenFamily) == 1


@pytest.mark.asyncio
async def test_existing_github_subject_resolves_before_email_linking(settings, db_session, clean_database) -> None:
    existing, _ = await _create_github_identity(
        db_session,
        email="original@example.com",
        subject="github-stable-subject",
    )
    await _create_local_user(db_session, "changed@example.com")

    outcome = await OAuthService(db_session, settings).complete_login(
        provider_name="github",
        identity=GitHubOAuthIdentity(
            issuer=GITHUB_ISSUER,
            subject="github-stable-subject",
            email="changed@example.com",
            email_verified=True,
        ),
        now=NOW,
    )

    assert outcome.current_user.id == existing.user.id
    assert await _count_rows(db_session, User) == 2
    assert await _count_rows(db_session, Identity) == 1
    assert await _count_rows(db_session, RefreshTokenFamily) == 1


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "identity",
    [
        GitHubOAuthIdentity(
            issuer=GITHUB_ISSUER,
            subject="missing-email",
            email=None,
            email_verified=True,
        ),
        GitHubOAuthIdentity(
            issuer=GITHUB_ISSUER,
            subject="unverified-email",
            email="unsafe@example.com",
            email_verified=False,
        ),
    ],
)
async def test_ambiguous_github_identity_creates_no_identity_or_session(
    settings,
    db_session,
    clean_database,
    identity,
) -> None:
    with pytest.raises(OAuthAuthenticationError):
        await OAuthService(db_session, settings).complete_login(
            provider_name="github",
            identity=identity,
            now=NOW,
        )

    assert await _count_rows(db_session, User) == 0
    assert await _count_rows(db_session, Identity) == 0
    assert await _count_rows(db_session, RefreshTokenFamily) == 0


@pytest.mark.asyncio
async def test_conflicting_github_subject_for_existing_email_fails_closed(
    settings,
    db_session,
    clean_database,
) -> None:
    await _create_github_identity(
        db_session,
        email="claimed@example.com",
        subject="already-linked-subject",
    )

    with pytest.raises(OAuthAuthenticationError):
        await OAuthService(db_session, settings).complete_login(
            provider_name="github",
            identity=GitHubOAuthIdentity(
                issuer=GITHUB_ISSUER,
                subject="different-subject",
                email="claimed@example.com",
                email_verified=True,
            ),
            now=NOW,
        )

    assert await _count_rows(db_session, User) == 1
    assert await _count_rows(db_session, Identity) == 1
    assert await _count_rows(db_session, RefreshTokenFamily) == 0

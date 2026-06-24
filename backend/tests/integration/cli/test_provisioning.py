from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest
from sqlalchemy import select

from app.core.config import Settings
from app.db.repositories.provisioning import ProvisioningError, ProvisioningRepository
from app.models.account import LocalCredential, User, UserScope


@pytest.mark.integration
@pytest.mark.asyncio
async def test_demo_seed_is_idempotent_and_creates_expected_roles(db_session, settings: Settings) -> None:
    seeded_settings = settings.model_copy(
        update={
            "app_env": "development",
            "demo_seed_enabled": True,
            "demo_user_password": "ThayDoiMatKhauDemoUser123",
            "demo_admin_password": "ThayDoiMatKhauDemoAdmin123",
        }
    )
    repo = ProvisioningRepository(db_session)
    now = datetime.now(UTC)

    result = await repo.ensure_demo_accounts(settings=seeded_settings, now=now)
    await db_session.commit()
    assert result.status == "seeded"
    assert result.created == 2

    result_again = await repo.ensure_demo_accounts(settings=seeded_settings, now=now)
    await db_session.commit()
    assert result_again.status == "seeded"

    users = list((await db_session.execute(select(User).order_by(User.email))).scalars())
    assert [user.email for user in users] == [
        "demo.admin@simpagent.test",
        "demo.user@simpagent.test",
    ]
    assert [user.role for user in users] == ["admin", "user"]
    assert all(user.is_demo for user in users)

    scopes = list((await db_session.execute(select(UserScope))).scalars())
    assert len(scopes) == 10


@pytest.mark.integration
@pytest.mark.asyncio
async def test_demo_seed_rejected_outside_development(db_session, settings: Settings) -> None:
    seeded_settings = settings.model_copy(
        update={
            "app_env": "production",
            "demo_seed_enabled": True,
            "demo_user_password": "ThayDoiMatKhauDemoUser123",
            "demo_admin_password": "ThayDoiMatKhauDemoAdmin123",
        }
    )
    repo = ProvisioningRepository(db_session)

    with pytest.raises(ProvisioningError):
        await repo.ensure_demo_accounts(settings=seeded_settings, now=datetime.now(UTC))

    users = list((await db_session.execute(select(User))).scalars())
    assert users == []


@pytest.mark.integration
@pytest.mark.asyncio
async def test_bootstrap_admin_creates_once(db_session, settings: Settings) -> None:
    repo = ProvisioningRepository(db_session)
    bootstrap_settings = settings.model_copy(update={"app_env": "production"})

    result = await repo.bootstrap_admin(
        settings=bootstrap_settings,
        email="admin@example.com",
        now=datetime.now(UTC),
        password="MatKhauAdminBaoMat123",
    )
    await db_session.commit()
    assert result.status == "created"

    user = (await db_session.execute(select(User).where(User.email == "admin@example.com"))).scalar_one()
    assert user.role == "admin"
    assert user.is_demo is False

    credential = (await db_session.execute(select(LocalCredential).where(LocalCredential.user_id == user.id))).scalar_one()
    assert credential.password_hash.startswith("$argon2id$")

    await db_session.rollback()
    with pytest.raises(ProvisioningError):
        await repo.bootstrap_admin(
            settings=bootstrap_settings,
            email="another-admin@example.com",
            now=datetime.now(UTC),
            password="MatKhauAdminBaoMat456",
        )


@pytest.mark.integration
def test_init_dev_secrets_creates_expected_files(tmp_path: Path) -> None:
    from app.cli.init_dev_secrets import init_dev_secrets

    result = init_dev_secrets(secrets_dir=tmp_path)
    assert result["jwt_private_key"] is True
    assert result["jwt_public_key"] is True
    assert result["refresh_hmac_key"] is True
    assert result["csrf_hmac_key"] is True
    assert result["message_encryption_key"] is True
    assert result["python_capability_secret"] is True

    assert (tmp_path / "jwt_private_key").exists()
    assert (tmp_path / "jwt_public_key").exists()
    assert (tmp_path / "refresh_hmac_key").exists()
    assert (tmp_path / "csrf_hmac_key").exists()
    assert (tmp_path / "message_encryption_key").exists()
    assert (tmp_path / "python_capability_secret").exists()


@pytest.mark.integration
def test_demo_seed_cli_reports_safe_message(settings: Settings, monkeypatch, capsys) -> None:
    from app.cli import seed_demo

    test_settings = settings.model_copy(
        update={
            "app_env": "development",
            "demo_seed_enabled": False,
        }
    )
    monkeypatch.setattr(seed_demo, "Settings", lambda: test_settings)
    exit_code = seed_demo.main([])
    captured = capsys.readouterr()
    assert exit_code == 0
    assert "disabled" in captured.out.lower()
    assert "password" not in captured.out.lower()


def test_bootstrap_admin_cli_documents_required_email_without_secret_echo() -> None:
    from app.cli.bootstrap_admin import build_parser

    help_text = build_parser().format_help()
    assert "--email" in help_text
    assert "password" not in help_text.lower()

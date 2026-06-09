from __future__ import annotations

import pytest

from app.core.config import Settings


def test_settings_require_postgresql_url() -> None:
    with pytest.raises(ValueError):
        Settings(
            app_env="test",
            database_url="sqlite+aiosqlite:///tmp/test.db",
            allowed_origins=["http://localhost:3000"],
            jwt_private_key="secret",
            jwt_public_key="secret",
            refresh_hmac_key="refresh",
            csrf_hmac_key="csrf",
        )


def test_production_rejects_demo_seed() -> None:
    with pytest.raises(ValueError):
        Settings(
            app_env="production",
            database_url="postgresql+psycopg://postgres:postgres@db:5432/app",
            allowed_origins=["https://example.com"],
            demo_seed_enabled=True,
            cookie_secure=True,
            jwt_private_key="secret",
            jwt_public_key="secret",
            refresh_hmac_key="refresh-refresh-refresh-refresh",
            csrf_hmac_key="csrf-csrf-csrf-csrf-csrf-csrf-csrf",
        )


def test_repr_redacts_database_url(settings: Settings) -> None:
    assert "postgres-test" not in repr(settings)

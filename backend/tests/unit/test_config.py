from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

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


def test_env_value_overrides_missing_secret_file_for_llm_api_key() -> None:
    settings = Settings(
        app_env="test",
        database_url="postgresql+psycopg://postgres:postgres@db:5432/app",
        allowed_origins=["http://localhost:3000"],
        jwt_private_key="secret",
        jwt_public_key="secret",
        refresh_hmac_key="refresh-refresh-refresh-refresh",
        csrf_hmac_key="csrf-csrf-csrf-csrf-csrf-csrf-csrf",
        llm_api_key="env-priority-key",
        llm_api_key_file="/tmp/does-not-exist",
    )

    assert settings.llm_api_key_value == "env-priority-key"


def test_llm_api_key_falls_back_to_secret_file(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("SIMPAGENT_LLM_API_KEY", raising=False)
    monkeypatch.delenv("LLM_API_KEY", raising=False)

    secret_file = tmp_path / "llm_api_key"
    secret_file.write_text("file-secret-key\n", encoding="utf-8")

    settings = Settings(
        app_env="test",
        database_url="postgresql+psycopg://postgres:postgres@db:5432/app",
        allowed_origins=["http://localhost:3000"],
        jwt_private_key="secret",
        jwt_public_key="secret",
        refresh_hmac_key="refresh-refresh-refresh-refresh",
        csrf_hmac_key="csrf-csrf-csrf-csrf-csrf-csrf-csrf",
        llm_api_key_file=str(secret_file),
    )

    assert settings.llm_api_key_value == "file-secret-key"


def test_missing_optional_llm_api_key_file_returns_none(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("SIMPAGENT_LLM_API_KEY", raising=False)
    monkeypatch.delenv("LLM_API_KEY", raising=False)

    settings = Settings(
        app_env="test",
        database_url="postgresql+psycopg://postgres:postgres@db:5432/app",
        allowed_origins=["http://localhost:3000"],
        jwt_private_key="secret",
        jwt_public_key="secret",
        refresh_hmac_key="refresh-refresh-refresh-refresh",
        csrf_hmac_key="csrf-csrf-csrf-csrf-csrf-csrf-csrf",
        llm_api_key_file="/tmp/does-not-exist",
    )

    assert settings.llm_api_key_value is None


def test_google_api_key_env_value_overrides_missing_secret_file() -> None:
    settings = Settings(
        app_env="test",
        database_url="postgresql+psycopg://postgres:postgres@db:5432/app",
        allowed_origins=["http://localhost:3000"],
        jwt_private_key="secret",
        jwt_public_key="secret",
        refresh_hmac_key="refresh-refresh-refresh-refresh",
        csrf_hmac_key="csrf-csrf-csrf-csrf-csrf-csrf-csrf",
        google_api_key="google-env-priority-key",
        google_api_key_file="/tmp/does-not-exist",
    )

    assert settings.google_api_key_value == "google-env-priority-key"


def test_google_api_key_falls_back_to_secret_file(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("SIMPAGENT_GOOGLE_API_KEY", raising=False)
    monkeypatch.delenv("GOOGLE_API_KEY", raising=False)

    secret_file = tmp_path / "google_api_key"
    secret_file.write_text("google-file-secret\n", encoding="utf-8")

    settings = Settings(
        app_env="test",
        database_url="postgresql+psycopg://postgres:postgres@db:5432/app",
        allowed_origins=["http://localhost:3000"],
        jwt_private_key="secret",
        jwt_public_key="secret",
        refresh_hmac_key="refresh-refresh-refresh-refresh",
        csrf_hmac_key="csrf-csrf-csrf-csrf-csrf-csrf-csrf",
        google_api_key_file=str(secret_file),
    )

    assert settings.google_api_key_value == "google-file-secret"


def test_missing_optional_google_api_key_file_returns_none(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("SIMPAGENT_GOOGLE_API_KEY", raising=False)
    monkeypatch.delenv("GOOGLE_API_KEY", raising=False)

    settings = Settings(
        app_env="test",
        database_url="postgresql+psycopg://postgres:postgres@db:5432/app",
        allowed_origins=["http://localhost:3000"],
        jwt_private_key="secret",
        jwt_public_key="secret",
        refresh_hmac_key="refresh-refresh-refresh-refresh",
        csrf_hmac_key="csrf-csrf-csrf-csrf-csrf-csrf-csrf",
        google_api_key_file="/tmp/does-not-exist",
    )

    assert settings.google_api_key_value is None


def test_settings_parse_compose_rendered_test_now() -> None:
    settings = Settings(
        app_env="test",
        database_url="postgresql+psycopg://postgres:postgres@db:5432/app",
        allowed_origins=["http://localhost:3000"],
        jwt_private_key="secret",
        jwt_public_key="secret",
        refresh_hmac_key="refresh",
        csrf_hmac_key="csrf",
        test_now="2026-06-09 00:00:00 +0000 +0000",
    )

    assert settings.test_now == datetime(2026, 6, 9, 0, 0, tzinfo=UTC)
    assert settings.now_utc() == datetime(2026, 6, 9, 0, 0, tzinfo=UTC)

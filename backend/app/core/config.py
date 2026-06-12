from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Literal
from urllib.parse import urlparse

from pydantic import AliasChoices, Field, SecretStr, computed_field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


AppEnv = Literal["development", "test", "production"]
CookieSameSite = Literal["strict", "lax", "none"]


COMMON_PASSWORD_BLOCKLIST = {
    "passwordpassword",
    "123456789012345",
    "simpagentdemoaccount",
    "demo.admin@simpagent.test",
    "demo.user@simpagent.test",
}


def _read_secret_file(path: str | None) -> str | None:
    if not path:
        return None
    return Path(path).read_text(encoding="utf-8").strip()


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="SIMPAGENT_",
        extra="ignore",
        frozen=True,
        enable_decoding=False,
        populate_by_name=True,
    )

    app_env: AppEnv = "development"
    debug: bool = False
    database_url: SecretStr | None = None
    database_url_file: str | None = None
    allowed_origins: list[str] = Field(default_factory=lambda: ["http://localhost:3000"])

    jwt_issuer: str = "simpagent.local"
    jwt_audience: str = "simpagent-api"
    jwt_active_kid: str = "local-key"
    jwt_private_key: SecretStr | None = None
    jwt_private_key_file: str | None = None
    jwt_public_key: SecretStr | None = None
    jwt_public_key_file: str | None = None

    refresh_hmac_key: SecretStr | None = None
    refresh_hmac_key_file: str | None = None
    csrf_hmac_key: SecretStr | None = None
    csrf_hmac_key_file: str | None = None

    access_token_ttl_seconds: int = 600
    refresh_idle_ttl_seconds: int = 7 * 24 * 60 * 60
    refresh_absolute_ttl_seconds: int = 30 * 24 * 60 * 60
    cookie_secure: bool = True
    cookie_samesite: CookieSameSite = "strict"

    demo_seed_enabled: bool = False
    demo_user_email: str = "demo.user@simpagent.test"
    demo_user_password: SecretStr | None = None
    demo_admin_email: str = "demo.admin@simpagent.test"
    demo_admin_password: SecretStr | None = None

    llm_api_base: str | None = Field(
        default=None,
        validation_alias=AliasChoices("SIMPAGENT_LLM_API_BASE", "LLM_API_BASE"),
    )
    llm_api_key: SecretStr | None = Field(
        default=None,
        validation_alias=AliasChoices("SIMPAGENT_LLM_API_KEY", "LLM_API_KEY"),
    )
    llm_api_key_file: str | None = Field(
        default=None,
        validation_alias=AliasChoices("SIMPAGENT_LLM_API_KEY_FILE", "LLM_API_KEY_FILE"),
    )
    llm_model: str | None = Field(
        default=None,
        validation_alias=AliasChoices("SIMPAGENT_LLM_MODEL", "LLM_MODEL"),
    )
    llm_timeout_seconds: int = Field(
        default=30,
        validation_alias=AliasChoices("SIMPAGENT_LLM_TIMEOUT_SECONDS", "LLM_TIMEOUT_SECONDS"),
    )
    llm_max_retries: int = Field(
        default=1,
        validation_alias=AliasChoices("SIMPAGENT_LLM_MAX_RETRIES", "LLM_MAX_RETRIES"),
    )
    google_api_key: SecretStr | None = None
    google_api_key_file: str | None = None
    search_model: str | None = None
    provider_check_timeout_seconds: int = 2
    test_now: str | None = None

    @model_validator(mode="before")
    @classmethod
    def _parse_origins(cls, values: dict):
        raw = values.get("allowed_origins")
        if isinstance(raw, str):
            values["allowed_origins"] = [item.strip() for item in raw.split(",") if item.strip()]
        return values

    @model_validator(mode="after")
    def _validate_security(self) -> "Settings":
        db_url = self.resolved_database_url
        if not db_url.startswith("postgresql+psycopg://"):
            raise ValueError("Only PostgreSQL URLs using psycopg are allowed.")
        if not self.allowed_origins:
            raise ValueError("At least one exact allowed origin is required.")
        for origin in self.allowed_origins:
            parsed = urlparse(origin)
            if not parsed.scheme or not parsed.netloc or parsed.path not in ("", "/"):
                raise ValueError("Allowed origins must be exact origins without path/query/fragment.")
        if self.app_env == "production":
            if self.debug:
                raise ValueError("Debug mode is forbidden in production.")
            if self.demo_seed_enabled:
                raise ValueError("Demo seed is forbidden in production.")
            if not self.cookie_secure:
                raise ValueError("Secure cookies are required in production.")
            if "*" in self.allowed_origins:
                raise ValueError("Wildcard origins are forbidden in production.")
            if not self.database_url_file:
                raise ValueError("Production requires DATABASE_URL_FILE.")
            if not self.jwt_private_key_file or not self.jwt_public_key_file:
                raise ValueError("Production requires JWT key files.")
            if not self.refresh_hmac_key_file or not self.csrf_hmac_key_file:
                raise ValueError("Production requires refresh and CSRF key files.")
            for candidate in (self.llm_api_base,):
                if candidate and (candidate.startswith("http://127.") or candidate.startswith("http://localhost")):
                    raise ValueError("Loopback provider URLs are forbidden in production.")
        return self

    @computed_field  # type: ignore[misc]
    @property
    def resolved_database_url(self) -> str:
        value = self.database_url.get_secret_value() if self.database_url else _read_secret_file(self.database_url_file)
        if not value:
            raise ValueError("Database URL is required.")
        return value

    @property
    def jwt_private_key_value(self) -> str:
        value = self.jwt_private_key.get_secret_value() if self.jwt_private_key else _read_secret_file(self.jwt_private_key_file)
        if not value:
            raise ValueError("JWT private key is required.")
        return value

    @property
    def jwt_public_key_value(self) -> str:
        value = self.jwt_public_key.get_secret_value() if self.jwt_public_key else _read_secret_file(self.jwt_public_key_file)
        if not value:
            raise ValueError("JWT public key is required.")
        return value

    @property
    def refresh_hmac_key_value(self) -> bytes:
        value = self.refresh_hmac_key.get_secret_value() if self.refresh_hmac_key else _read_secret_file(self.refresh_hmac_key_file)
        if not value:
            raise ValueError("Refresh HMAC key is required.")
        return value.encode("utf-8")

    @property
    def csrf_hmac_key_value(self) -> bytes:
        value = self.csrf_hmac_key.get_secret_value() if self.csrf_hmac_key else _read_secret_file(self.csrf_hmac_key_file)
        if not value:
            raise ValueError("CSRF HMAC key is required.")
        return value.encode("utf-8")

    @property
    def llm_api_key_value(self) -> str | None:
        if self.llm_api_key:
            return self.llm_api_key.get_secret_value()
        return _read_secret_file(self.llm_api_key_file)

    @property
    def google_api_key_value(self) -> str | None:
        if self.google_api_key:
            return self.google_api_key.get_secret_value()
        return _read_secret_file(self.google_api_key_file)

    def __repr__(self) -> str:
        return (
            "Settings(app_env={!r}, debug={!r}, allowed_origins={!r}, demo_seed_enabled={!r}, "
            "access_token_ttl_seconds={!r}, refresh_idle_ttl_seconds={!r}, refresh_absolute_ttl_seconds={!r})"
        ).format(
            self.app_env,
            self.debug,
            self.allowed_origins,
            self.demo_seed_enabled,
            self.access_token_ttl_seconds,
            self.refresh_idle_ttl_seconds,
            self.refresh_absolute_ttl_seconds,
        )


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()

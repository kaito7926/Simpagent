from __future__ import annotations

from datetime import UTC, datetime
from functools import lru_cache
from ipaddress import ip_network
from pathlib import Path
from typing import Literal
from urllib.parse import urlparse
import base64
import binascii

from pydantic import AliasChoices, Field, SecretStr, computed_field, field_validator, model_validator
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
    candidate = Path(path)
    if not candidate.exists():
        return None
    return candidate.read_text(encoding="utf-8").strip()


def _resolve_secret_value(secret: SecretStr | None, file_path: str | None) -> str | None:
    if secret is not None:
        value = secret.get_secret_value()
        if value:
            return value
    return _read_secret_file(file_path)


def _decode_urlsafe_b64_secret(value: str, *, field_name: str) -> bytes:
    try:
        padding = "=" * ((4 - len(value) % 4) % 4)
        decoded = base64.urlsafe_b64decode(f"{value}{padding}".encode("ascii"))
    except (binascii.Error, ValueError) as exc:
        raise ValueError(f"{field_name} must be valid URL-safe base64.") from exc
    if len(decoded) != 32:
        raise ValueError(f"{field_name} must decode to exactly 32 bytes.")
    return decoded


def _looks_like_utc_offset(value: str) -> bool:
    return len(value) == 5 and value[0] in "+-" and value[1:].isdigit()


def _with_colonized_utc_offset(value: str) -> str:
    suffix = value[-5:]
    if _looks_like_utc_offset(suffix):
        return f"{value[:-5]}{suffix[:3]}:{suffix[3:]}"
    return value


def _normalize_test_now(value: str | datetime | None) -> datetime | None:
    if value in (None, ""):
        return None
    if isinstance(value, datetime):
        return value if value.tzinfo is not None else value.replace(tzinfo=UTC)
    if not isinstance(value, str):
        raise ValueError("test_now must be a datetime or string.")

    candidate = value.strip()
    if not candidate:
        return None

    variants: list[str] = [candidate]
    if candidate.endswith("Z"):
        variants.append(f"{candidate[:-1]}+00:00")

    parts = candidate.split()
    if len(parts) >= 3 and parts[-1] == parts[-2] and _looks_like_utc_offset(parts[-1]):
        variants.append(" ".join(parts[:-1]))

    seen: set[str] = set()
    for variant in variants:
        for normalized in (variant, _with_colonized_utc_offset(variant)):
            if normalized in seen:
                continue
            seen.add(normalized)
            try:
                moment = datetime.fromisoformat(normalized)
            except ValueError:
                continue
            return moment if moment.tzinfo is not None else moment.replace(tzinfo=UTC)

    raise ValueError("test_now must be a valid ISO 8601 datetime.")


def _parse_csv_list(value: list[str] | str | None) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        return [item.strip() for item in value.split(",") if item.strip()]
    return value


def _is_exact_origin(value: str, *, require_https: bool) -> bool:
    parsed = urlparse(value)
    if not parsed.scheme or not parsed.netloc:
        return False
    if parsed.path not in ("", "/") or parsed.query or parsed.fragment:
        return False
    if require_https and parsed.scheme != "https":
        return False
    return True


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
    log_level: str = "INFO"
    log_file_path: str | None = None
    otel_tracing_enabled: bool = False
    otel_service_name: str = "simpagent-backend"
    otel_exporter_otlp_traces_endpoint: str | None = None
    otel_exporter_otlp_timeout_seconds: int = Field(default=5, ge=1, le=60)
    otel_sample_ratio: float = Field(default=1.0, ge=0.0, le=1.0)
    database_url: SecretStr | None = None
    database_url_file: str | None = None
    allowed_origins: list[str] = Field(default_factory=lambda: ["http://localhost:3000"])
    public_app_origin: str | None = None
    public_api_origin: str | None = None
    trusted_proxy_cidrs: list[str] = Field(default_factory=list)

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
    message_encryption_key: SecretStr | None = None
    message_encryption_key_file: str | None = None

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
    google_api_key: SecretStr | None = Field(
        default=None,
        validation_alias=AliasChoices("SIMPAGENT_GOOGLE_API_KEY", "GOOGLE_API_KEY"),
    )
    google_api_key_file: str | None = Field(
        default=None,
        validation_alias=AliasChoices("SIMPAGENT_GOOGLE_API_KEY_FILE", "GOOGLE_API_KEY_FILE"),
    )
    google_client_id: str | None = Field(
        default=None,
        validation_alias=AliasChoices("SIMPAGENT_GOOGLE_CLIENT_ID", "GOOGLE_CLIENT_ID"),
    )
    google_client_secret: SecretStr | None = Field(
        default=None,
        validation_alias=AliasChoices("SIMPAGENT_GOOGLE_CLIENT_SECRET", "GOOGLE_CLIENT_SECRET"),
    )
    google_redirect_uri: str | None = Field(
        default=None,
        validation_alias=AliasChoices("SIMPAGENT_GOOGLE_REDIRECT_URI", "GOOGLE_REDIRECT_URI"),
    )
    github_client_id: str | None = Field(
        default=None,
        validation_alias=AliasChoices("SIMPAGENT_GITHUB_CLIENT_ID", "GITHUB_CLIENT_ID"),
    )
    github_client_secret: SecretStr | None = Field(
        default=None,
        validation_alias=AliasChoices("SIMPAGENT_GITHUB_CLIENT_SECRET", "GITHUB_CLIENT_SECRET"),
    )
    github_redirect_uri: str | None = Field(
        default=None,
        validation_alias=AliasChoices("SIMPAGENT_GITHUB_REDIRECT_URI", "GITHUB_REDIRECT_URI"),
    )
    search_model: str | None = None
    search_worker_timeout_seconds: float = Field(default=8.0, gt=0)
    search_max_prompt_chars: int = Field(default=2000, ge=128, le=4000)
    search_max_output_tokens: int = Field(default=1536, ge=128, le=4096)
    search_max_output_chars: int = Field(default=4000, ge=256, le=12000)
    search_capability_ttl_seconds: int = Field(default=30, ge=5, le=300)
    search_capability_audience: str = "simpagent-search-worker"
    guardrail_safety_enabled_default: bool = True
    agent_loop_max_iterations: int = Field(default=2, ge=1, le=5)
    provider_check_timeout_seconds: int = 2
    python_supervisor_base_url: str = "http://sandbox:8080"
    python_supervisor_request_timeout_seconds: int = 30
    python_capability_secret: SecretStr | None = None
    python_capability_secret_file: str | None = None
    python_capability_ttl_seconds: int = 60
    python_session_ttl_seconds: int = 15 * 60
    python_artifact_storage_dir: str = "/tmp/simpagent-python-artifacts"
    test_now: datetime | None = None

    @model_validator(mode="before")
    @classmethod
    def _parse_origins(cls, values: dict):
        raw = values.get("allowed_origins")
        if isinstance(raw, str):
            values["allowed_origins"] = [item.strip() for item in raw.split(",") if item.strip()]
        if "trusted_proxy_cidrs" in values:
            values["trusted_proxy_cidrs"] = _parse_csv_list(values.get("trusted_proxy_cidrs"))
        return values

    @field_validator("test_now", mode="before")
    @classmethod
    def _parse_test_now(cls, value: str | datetime | None) -> datetime | None:
        return _normalize_test_now(value)

    @model_validator(mode="after")
    def _validate_security(self) -> "Settings":
        db_url = self.resolved_database_url
        if not db_url.startswith("postgresql+psycopg://"):
            raise ValueError("Only PostgreSQL URLs using psycopg are allowed.")
        if self.otel_tracing_enabled:
            if not self.otel_exporter_otlp_traces_endpoint:
                raise ValueError("Tracing requires an OTLP traces endpoint.")
            if not self.otel_service_name.strip():
                raise ValueError("Tracing requires a non-empty OTEL service name.")
        if not self.allowed_origins:
            raise ValueError("At least one exact allowed origin is required.")
        for origin in self.allowed_origins:
            if not _is_exact_origin(origin, require_https=False):
                raise ValueError("Allowed origins must be exact origins without path/query/fragment.")
        for cidr in self.trusted_proxy_cidrs:
            try:
                ip_network(cidr, strict=False)
            except ValueError as exc:
                raise ValueError("trusted proxy CIDRs must be valid IP networks.") from exc
        if self.app_env == "production":
            if self.debug:
                raise ValueError("Debug mode is forbidden in production.")
            if self.demo_seed_enabled:
                raise ValueError("Demo seed is forbidden in production.")
            if not self.cookie_secure:
                raise ValueError("Secure cookies are required in production.")
            if "*" in self.allowed_origins:
                raise ValueError("Wildcard origins are forbidden in production.")
            if not self.public_app_origin:
                raise ValueError("Production requires a public app origin.")
            if not self.public_api_origin:
                raise ValueError("Production requires a public API origin.")
            if not _is_exact_origin(self.public_app_origin, require_https=True):
                raise ValueError("Production public app origin must be an exact HTTPS origin.")
            if not _is_exact_origin(self.public_api_origin, require_https=True):
                raise ValueError("Production public API origin must be an exact HTTPS origin.")
            if not self.trusted_proxy_cidrs:
                raise ValueError("Production requires trusted proxy CIDRs.")
            if not self.database_url_file:
                raise ValueError("Production requires DATABASE_URL_FILE.")
            if not self.jwt_private_key_file or not self.jwt_public_key_file:
                raise ValueError("Production requires JWT key files.")
            if not self.refresh_hmac_key_file or not self.csrf_hmac_key_file:
                raise ValueError("Production requires refresh and CSRF key files.")
            if not self.message_encryption_key and not self.message_encryption_key_file:
                raise ValueError("Production requires a message encryption key.")
            if not self.python_capability_secret and not self.python_capability_secret_file:
                raise ValueError("Production requires a Python capability secret.")
            for candidate in (self.llm_api_base,):
                if candidate and (candidate.startswith("http://127.") or candidate.startswith("http://localhost")):
                    raise ValueError("Loopback provider URLs are forbidden in production.")
        if self.python_supervisor_request_timeout_seconds <= 0:
            raise ValueError("Python supervisor timeout must be positive.")
        if self.python_capability_ttl_seconds <= 0:
            raise ValueError("Python capability TTL must be positive.")
        if self.python_session_ttl_seconds <= 0:
            raise ValueError("Python session TTL must be positive.")
        if not self.python_artifact_storage_dir.strip():
            raise ValueError("Python artifact storage directory is required.")
        return self

    @computed_field  # type: ignore[misc]
    @property
    def resolved_database_url(self) -> str:
        value = _resolve_secret_value(self.database_url, self.database_url_file)
        if not value:
            raise ValueError("Database URL is required.")
        return value

    @property
    def jwt_private_key_value(self) -> str:
        value = _resolve_secret_value(self.jwt_private_key, self.jwt_private_key_file)
        if not value:
            raise ValueError("JWT private key is required.")
        return value

    @property
    def jwt_public_key_value(self) -> str:
        value = _resolve_secret_value(self.jwt_public_key, self.jwt_public_key_file)
        if not value:
            raise ValueError("JWT public key is required.")
        return value

    @property
    def refresh_hmac_key_value(self) -> bytes:
        value = _resolve_secret_value(self.refresh_hmac_key, self.refresh_hmac_key_file)
        if not value:
            raise ValueError("Refresh HMAC key is required.")
        return value.encode("utf-8")

    @property
    def csrf_hmac_key_value(self) -> bytes:
        value = _resolve_secret_value(self.csrf_hmac_key, self.csrf_hmac_key_file)
        if not value:
            raise ValueError("CSRF HMAC key is required.")
        return value.encode("utf-8")

    @property
    def message_encryption_key_value(self) -> bytes:
        value = _resolve_secret_value(self.message_encryption_key, self.message_encryption_key_file)
        if not value:
            raise ValueError("Message encryption key is required.")
        return _decode_urlsafe_b64_secret(value, field_name="message_encryption_key")

    @property
    def llm_api_key_value(self) -> str | None:
        return _resolve_secret_value(self.llm_api_key, self.llm_api_key_file)

    @property
    def google_api_key_value(self) -> str | None:
        return _resolve_secret_value(self.google_api_key, self.google_api_key_file)

    @property
    def google_oauth_configured(self) -> bool:
        secret = self.google_client_secret
        secret_value = secret.get_secret_value() if isinstance(secret, SecretStr) else secret
        return bool(
            self.google_client_id
            and secret_value
            and self.google_redirect_uri
        )

    @property
    def github_oauth_configured(self) -> bool:
        secret = self.github_client_secret
        secret_value = secret.get_secret_value() if isinstance(secret, SecretStr) else secret
        return bool(
            self.github_client_id
            and secret_value
            and self.github_redirect_uri
        )

    @property
    def python_capability_secret_value(self) -> str:
        if self.python_capability_secret:
            return self.python_capability_secret.get_secret_value()
        value = _read_secret_file(self.python_capability_secret_file)
        if value:
            return value
        if self.app_env in {"development", "test"}:
            return "sandbox-dev-secret"
        raise ValueError("Python capability secret is required.")

    def now_utc(self) -> datetime:
        return self.test_now or datetime.now(UTC)

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

from __future__ import annotations

import os
from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient

from app.core.config import Settings
from app.main import create_app

pytest_plugins = ["tests.fixtures.postgres", "tests.fixtures.auth"]


ROOT = Path(__file__).resolve().parents[1]
SECRETS = ROOT / "tests" / "fixtures" / "secrets"


@pytest.fixture(scope="session")
def settings() -> Settings:
    return Settings(
        app_env=os.getenv("SIMPAGENT_APP_ENV", "test"),
        database_url=os.getenv(
            "SIMPAGENT_DATABASE_URL",
            "postgresql+psycopg://postgres:postgres@postgres-test:5432/simpagent_test",
        ),
        allowed_origins=os.getenv(
            "SIMPAGENT_ALLOWED_ORIGINS",
            "http://localhost:3000,http://localhost:8000",
        ),
        jwt_issuer=os.getenv("SIMPAGENT_JWT_ISSUER", "simpagent.test"),
        jwt_audience=os.getenv("SIMPAGENT_JWT_AUDIENCE", "simpagent-api"),
        jwt_active_kid=os.getenv("SIMPAGENT_JWT_ACTIVE_KID", "test-kid"),
        jwt_private_key=os.getenv("SIMPAGENT_JWT_PRIVATE_KEY"),
        jwt_private_key_file=os.getenv("SIMPAGENT_JWT_PRIVATE_KEY_FILE", str(SECRETS / "test_jwt_private.pem")),
        jwt_public_key=os.getenv("SIMPAGENT_JWT_PUBLIC_KEY"),
        jwt_public_key_file=os.getenv("SIMPAGENT_JWT_PUBLIC_KEY_FILE", str(SECRETS / "test_jwt_public.pem")),
        refresh_hmac_key=os.getenv("SIMPAGENT_REFRESH_HMAC_KEY"),
        refresh_hmac_key_file=os.getenv("SIMPAGENT_REFRESH_HMAC_KEY_FILE", str(SECRETS / "test_refresh_hmac_key")),
        csrf_hmac_key=os.getenv("SIMPAGENT_CSRF_HMAC_KEY"),
        csrf_hmac_key_file=os.getenv("SIMPAGENT_CSRF_HMAC_KEY_FILE", str(SECRETS / "test_csrf_hmac_key")),
        cookie_secure=os.getenv("SIMPAGENT_COOKIE_SECURE", "true").lower() == "true",
        cookie_samesite=os.getenv("SIMPAGENT_COOKIE_SAMESITE", "strict"),
        access_token_ttl_seconds=int(os.getenv("SIMPAGENT_ACCESS_TOKEN_TTL_SECONDS", "600")),
        refresh_idle_ttl_seconds=int(os.getenv("SIMPAGENT_REFRESH_IDLE_TTL_SECONDS", "604800")),
        refresh_absolute_ttl_seconds=int(os.getenv("SIMPAGENT_REFRESH_ABSOLUTE_TTL_SECONDS", "2592000")),
        demo_seed_enabled=os.getenv("SIMPAGENT_DEMO_SEED_ENABLED", "false").lower() == "true",
        llm_api_base=os.getenv("SIMPAGENT_LLM_API_BASE", "https://api.example.test/v1"),
        llm_model=os.getenv("SIMPAGENT_LLM_MODEL", "fake-model"),
        search_model=os.getenv("SIMPAGENT_SEARCH_MODEL", "configured-search-model"),
        google_api_key=os.getenv("SIMPAGENT_GOOGLE_API_KEY"),
        google_api_key_file=os.getenv("SIMPAGENT_GOOGLE_API_KEY_FILE"),
        provider_check_timeout_seconds=int(os.getenv("SIMPAGENT_PROVIDER_CHECK_TIMEOUT_SECONDS", "2")),
    )


@pytest.fixture
def app(settings: Settings, session_factory):
    return create_app(settings=settings, session_factory=session_factory)


@pytest.fixture
async def client(app) -> AsyncClient:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as http_client:
        yield http_client


@pytest.fixture(scope="session")
def secret_canary() -> str:
    return "simpagent-canary-secret"

from __future__ import annotations

import asyncio
import os
from pathlib import Path
import sys

import pytest
from httpx import ASGITransport, AsyncClient

ROOT = Path(__file__).resolve().parents[1]
SECRETS = ROOT / "tests" / "fixtures" / "secrets"

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

# `app.main` creates a module-level FastAPI app during import, so tests need a
# minimal settings baseline in the environment before importing it.
os.environ.setdefault(
    "SIMPAGENT_DATABASE_URL",
    "postgresql+psycopg://postgres:postgres@postgres-test:5432/simpagent_test",
)
os.environ.setdefault("SIMPAGENT_APP_ENV", "test")
os.environ.setdefault("SIMPAGENT_LLM_API_BASE", "https://api.example.test/v1")
os.environ.setdefault("SIMPAGENT_LLM_MODEL", "fake-model")
os.environ.setdefault("SIMPAGENT_SEARCH_MODEL", "configured-search-model")
os.environ.setdefault("SIMPAGENT_JWT_PRIVATE_KEY_FILE", str(SECRETS / "test_jwt_private.pem"))
os.environ.setdefault("SIMPAGENT_JWT_PUBLIC_KEY_FILE", str(SECRETS / "test_jwt_public.pem"))
os.environ.setdefault("SIMPAGENT_REFRESH_HMAC_KEY_FILE", str(SECRETS / "test_refresh_hmac_key"))
os.environ.setdefault("SIMPAGENT_CSRF_HMAC_KEY_FILE", str(SECRETS / "test_csrf_hmac_key"))
os.environ.setdefault("SIMPAGENT_MESSAGE_ENCRYPTION_KEY_FILE", str(SECRETS / "test_message_encryption_key"))

from app.core.config import Settings
from app.main import create_app

pytest_plugins = ["tests.fixtures.postgres", "tests.fixtures.auth"]


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
        message_encryption_key=os.getenv("SIMPAGENT_MESSAGE_ENCRYPTION_KEY"),
        message_encryption_key_file=os.getenv(
            "SIMPAGENT_MESSAGE_ENCRYPTION_KEY_FILE",
            str(SECRETS / "test_message_encryption_key"),
        ),
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
        python_supervisor_base_url=os.getenv("SIMPAGENT_PYTHON_SUPERVISOR_BASE_URL", "http://sandbox:8080"),
        python_supervisor_request_timeout_seconds=int(
            os.getenv("SIMPAGENT_PYTHON_SUPERVISOR_REQUEST_TIMEOUT_SECONDS", "30")
        ),
        python_capability_secret=os.getenv("SIMPAGENT_PYTHON_CAPABILITY_SECRET", "sandbox-dev-secret"),
        python_capability_secret_file=os.getenv("SIMPAGENT_PYTHON_CAPABILITY_SECRET_FILE"),
        python_capability_ttl_seconds=int(os.getenv("SIMPAGENT_PYTHON_CAPABILITY_TTL_SECONDS", "60")),
        python_session_ttl_seconds=int(os.getenv("SIMPAGENT_PYTHON_SESSION_TTL_SECONDS", "900")),
        python_artifact_storage_dir=os.getenv(
            "SIMPAGENT_PYTHON_ARTIFACT_STORAGE_DIR",
            "/tmp/simpagent-python-artifacts",
        ),
    )


@pytest.fixture
def app(settings: Settings, session_factory):
    return create_app(settings=settings, session_factory=session_factory)


@pytest.fixture
async def client(app, clean_database) -> AsyncClient:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as http_client:
        yield http_client


@pytest.fixture(scope="session")
def secret_canary() -> str:
    return "simpagent-canary-secret"

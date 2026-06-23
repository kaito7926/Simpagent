from __future__ import annotations

from pydantic import SecretStr

from app.db.repositories.agent_settings import WEBSEARCH_PROVIDER_OVERRIDE_KEY
from app.models.domain import AgentRuntimeSetting
from app.core.provider_status import (
    compute_provider_snapshot,
    resolve_search_provider,
    search_status,
    supports_google_search_model,
)
from app.main import create_app
from tests.integration.search._helpers import (
    RecordingSearchWorker,
    create_conversation,
    create_user,
    grounded_result,
    issue_token,
)
from tests.integration.search._worker_fakes import make_search_settings


def test_supported_google_search_model_family_is_explicit() -> None:
    assert supports_google_search_model("gemini-2.5-flash")
    assert supports_google_search_model("gemini-2.5-flash-preview-06-05")
    assert supports_google_search_model("gemini-2.5-flash-lite") is False
    assert supports_google_search_model("configured-search-model") is False


def test_search_provider_allowlist_accepts_only_gemini_and_firecrawl(settings) -> None:
    assert resolve_search_provider(settings.model_copy(update={"websearch_provider": "gemini"})) == "gemini"
    assert resolve_search_provider(settings.model_copy(update={"websearch_provider": "firecrawl"})) == "firecrawl"

    invalid = settings.model_copy(update={"websearch_provider": "serpapi"})

    assert resolve_search_provider(invalid) is None
    assert search_status(invalid) == "invalid_provider"


def test_runtime_provider_override_takes_precedence_and_clear_returns_to_environment_default(settings) -> None:
    configured = make_search_settings(
        settings,
        websearch_provider="gemini",
        firecrawl_api_key=SecretStr("test-firecrawl-key"),
    )

    assert resolve_search_provider(configured) == "gemini"
    assert resolve_search_provider(configured, runtime_override="firecrawl") == "firecrawl"
    assert search_status(configured, runtime_override="firecrawl") == "ready"
    assert resolve_search_provider(configured, runtime_override=None) == "gemini"


def test_search_status_is_unconfigured_without_google_credentials(settings) -> None:
    snapshot = compute_provider_snapshot(settings)
    assert snapshot.search == "unconfigured"


def test_search_status_reports_model_unavailable_for_unsupported_model(settings) -> None:
    unsupported = settings.model_copy(
        update={
            "search_model": "gemini-1.5-pro",
            "google_api_key": SecretStr("test-google-key"),
        }
    )

    assert search_status(unsupported) == "model_unavailable"


def test_create_app_wires_search_worker_only_when_supported_and_configured(settings) -> None:
    search_settings = make_search_settings(settings)

    app = create_app(settings=search_settings, session_factory=object())

    assert app.state.search_status == "ready"
    assert app.state.search_provider == "gemini"
    assert app.state.search_ready is True
    assert app.state.search_worker is not None


def test_firecrawl_status_requires_firecrawl_key_and_does_not_fallback_to_gemini(settings) -> None:
    firecrawl_without_key = make_search_settings(
        settings,
        websearch_provider="firecrawl",
        firecrawl_api_key=None,
    )

    app = create_app(settings=firecrawl_without_key, session_factory=object())

    assert search_status(firecrawl_without_key) == "unconfigured"
    assert app.state.search_provider == "firecrawl"
    assert app.state.search_ready is False
    assert app.state.search_worker is None


def test_create_app_wires_firecrawl_worker_when_firecrawl_is_configured(settings) -> None:
    configured = settings.model_copy(
        update={
            "websearch_provider": "firecrawl",
            "firecrawl_api_key": SecretStr("test-firecrawl-key"),
        }
    )

    app = create_app(settings=configured, session_factory=object())

    assert app.state.search_status == "ready"
    assert app.state.search_provider == "firecrawl"
    assert app.state.search_ready is True
    assert app.state.search_worker is not None
    assert app.state.search_worker.__class__.__name__ == "FirecrawlSearchWorkerService"


async def test_live_search_execution_uses_persisted_override_and_clear(
    client,
    app,
    db_session,
    settings,
) -> None:
    configured = make_search_settings(
        settings,
        websearch_provider="gemini",
        firecrawl_api_key=SecretStr("test-firecrawl-key"),
    )
    app.state.settings = configured

    def worker_factory(provider: str, _settings):
        result = grounded_result()
        if provider == "firecrawl":
            result = result.model_copy(update={"provider": "firecrawl", "google_grounded": False})
        return RecordingSearchWorker(result)

    app.state.search_runtime_worker_factory = worker_factory

    user = await create_user(
        db_session,
        email="runtime-provider@example.test",
        scopes=["chat:read", "chat:write", "tool:websearch"],
    )
    firecrawl_conversation = await create_conversation(db_session, user_id=user.id)
    gemini_conversation = await create_conversation(db_session, user_id=user.id)
    db_session.add(
        AgentRuntimeSetting(
            key=WEBSEARCH_PROVIDER_OVERRIDE_KEY,
            enabled=True,
            value="firecrawl",
            updated_by_user_id=user.id,
        )
    )
    await db_session.commit()

    token = issue_token(
        user=user,
        scopes=["chat:read", "chat:write", "tool:websearch"],
        settings=settings,
    )
    firecrawl_response = await client.post(
        f"/api/conversations/{firecrawl_conversation.id}/turns",
        headers={"Authorization": f"Bearer {token}"},
        json={"mode": "google_search", "prompt": "Use override"},
    )

    assert firecrawl_response.status_code == 200
    assert firecrawl_response.json()["assistant_message"]["search"]["provider"] == "firecrawl"

    await db_session.rollback()
    setting = await db_session.get(AgentRuntimeSetting, WEBSEARCH_PROVIDER_OVERRIDE_KEY)
    assert setting is not None
    setting.value = None
    await db_session.commit()

    gemini_response = await client.post(
        f"/api/conversations/{gemini_conversation.id}/turns",
        headers={"Authorization": f"Bearer {token}"},
        json={"mode": "google_search", "prompt": "After clear"},
    )

    assert gemini_response.status_code == 200
    assert gemini_response.json()["assistant_message"]["search"]["provider"] == "gemini"

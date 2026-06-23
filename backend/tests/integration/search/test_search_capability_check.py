from __future__ import annotations

from pydantic import SecretStr

from app.core.provider_status import (
    compute_provider_snapshot,
    resolve_search_provider,
    search_status,
    supports_google_search_model,
)
from app.main import create_app
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

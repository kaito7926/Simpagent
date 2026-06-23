from __future__ import annotations

from dataclasses import dataclass
from typing import Awaitable, Callable, Literal

from app.core.config import Settings


ProviderChecker = Callable[[], Awaitable[str]]
SearchProvider = Literal["gemini", "firecrawl"]
SEARCH_PROVIDER_ALLOWLIST: frozenset[str] = frozenset({"gemini", "firecrawl"})


@dataclass(frozen=True)
class ProviderSnapshot:
    llm: str
    search: str
    sandbox: str
    oauth_google: str
    oauth_github: str


SUPPORTED_SEARCH_MODELS = {"gemini-2.5-flash"}
SUPPORTED_SEARCH_MODEL_PREVIEW_PREFIXES = ("gemini-2.5-flash-preview-",)


def resolve_search_provider(settings: Settings) -> SearchProvider | None:
    provider = settings.websearch_provider.strip().casefold()
    if provider not in SEARCH_PROVIDER_ALLOWLIST:
        return None
    return provider  # type: ignore[return-value]


def llm_status(settings: Settings, *, override: str | None = None) -> str:
    if override:
        return override
    if not settings.llm_api_base or not settings.llm_model or not settings.llm_api_key_value:
        return "unconfigured"
    return "ready"


def supports_google_search_model(model: str | None) -> bool:
    if not model:
        return False
    return model in SUPPORTED_SEARCH_MODELS or any(
        model.startswith(prefix) for prefix in SUPPORTED_SEARCH_MODEL_PREVIEW_PREFIXES
    )


def search_status(settings: Settings, *, override: str | None = None) -> str:
    if override:
        return override
    provider = resolve_search_provider(settings)
    if provider is None:
        return "invalid_provider"
    if provider == "firecrawl":
        if not settings.firecrawl_api_key_value:
            return "unconfigured"
        return "ready"
    if not settings.search_model or not settings.google_api_key_value:
        return "unconfigured"
    if not supports_google_search_model(settings.search_model):
        return "model_unavailable"
    return "ready"


def sandbox_status() -> str:
    return "foundation_ready"


def oauth_google_status(settings: Settings, *, override: str | None = None) -> str:
    if override:
        return override
    if not settings.google_oauth_configured:
        return "unconfigured"
    return "ready"


def oauth_github_status(settings: Settings, *, override: str | None = None) -> str:
    if override:
        return override
    if not settings.github_oauth_configured:
        return "unconfigured"
    return "ready"


def compute_provider_snapshot(
    settings: Settings,
    *,
    llm_override: str | None = None,
    search_override: str | None = None,
    sandbox_override: str | None = None,
    oauth_google_override: str | None = None,
    oauth_github_override: str | None = None,
) -> ProviderSnapshot:
    return ProviderSnapshot(
        llm=llm_status(settings, override=llm_override),
        search=search_status(settings, override=search_override),
        sandbox=sandbox_override or sandbox_status(),
        oauth_google=oauth_google_status(settings, override=oauth_google_override),
        oauth_github=oauth_github_status(settings, override=oauth_github_override),
    )

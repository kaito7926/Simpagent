from __future__ import annotations

from dataclasses import dataclass
from typing import Awaitable, Callable

from app.core.config import Settings


ProviderChecker = Callable[[], Awaitable[str]]


@dataclass(frozen=True)
class ProviderSnapshot:
    llm: str
    search: str
    sandbox: str


SUPPORTED_SEARCH_MODELS = {"gemini-2.5-flash"}
SUPPORTED_SEARCH_MODEL_PREVIEW_PREFIXES = ("gemini-2.5-flash-preview-",)


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
    if not settings.search_model or not settings.google_api_key_value:
        return "unconfigured"
    if not supports_google_search_model(settings.search_model):
        return "model_unavailable"
    return "ready"


def sandbox_status() -> str:
    return "foundation_ready"


def compute_provider_snapshot(
    settings: Settings,
    *,
    llm_override: str | None = None,
    search_override: str | None = None,
    sandbox_override: str | None = None,
) -> ProviderSnapshot:
    return ProviderSnapshot(
        llm=llm_status(settings, override=llm_override),
        search=search_status(settings, override=search_override),
        sandbox=sandbox_override or sandbox_status(),
    )

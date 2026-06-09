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


def llm_status(settings: Settings) -> str:
    if not settings.llm_api_base or not settings.llm_model or not settings.llm_api_key_value:
        return "unconfigured"
    return "ready"


def search_status(settings: Settings) -> str:
    if not settings.search_model or not settings.google_api_key_value:
        return "unconfigured"
    return "ready"


def sandbox_status() -> str:
    return "foundation_ready"


def compute_provider_snapshot(settings: Settings) -> ProviderSnapshot:
    return ProviderSnapshot(
        llm=llm_status(settings),
        search=search_status(settings),
        sandbox=sandbox_status(),
    )

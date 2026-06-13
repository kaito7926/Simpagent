from __future__ import annotations

import asyncio
from collections.abc import AsyncGenerator
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from google.adk.events.event import Event
from pydantic import SecretStr

from app.security.search_capability import mint_search_capability


def make_search_settings(settings, **overrides):
    defaults = {
        "search_model": "gemini-2.5-flash",
        "google_api_key": SecretStr("test-google-key"),
    }
    defaults.update(overrides)
    return settings.model_copy(update=defaults)


def mint_capability_token(settings, *, correlation_id: str | None = "corr-test"):
    user_id = uuid4()
    conversation_id = uuid4()
    now = settings.now_utc()
    token = mint_search_capability(
        user_id=user_id,
        conversation_id=conversation_id,
        correlation_id=correlation_id,
        settings=settings,
        now=now,
    )
    return token, user_id, conversation_id


class FakeRunner:
    def __init__(
        self,
        *,
        events: list[Event] | None = None,
        exc: Exception | None = None,
        delay_seconds: float = 0.0,
    ) -> None:
        self.events = events or []
        self.exc = exc
        self.delay_seconds = delay_seconds
        self.calls = 0
        self.prompts: list[str] = []
        self.closed = False

    def run_async(
        self,
        *,
        user_id: str,
        session_id: str,
        invocation_id: str | None = None,
        new_message=None,
        state_delta: dict[str, Any] | None = None,
        run_config: Any | None = None,
        yield_user_message: bool = False,
    ) -> AsyncGenerator[Event, None]:
        self.calls += 1
        if new_message and new_message.parts:
            self.prompts.append("".join(part.text or "" for part in new_message.parts))

        async def _events() -> AsyncGenerator[Event, None]:
            if self.delay_seconds:
                await asyncio.sleep(self.delay_seconds)
            if self.exc is not None:
                raise self.exc
            for event in self.events:
                yield event

        return _events()

    async def close(self) -> None:
        self.closed = True

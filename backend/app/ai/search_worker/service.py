from __future__ import annotations

import asyncio
from contextlib import aclosing
from datetime import UTC, datetime
import json
import os
from typing import Any, Protocol
from uuid import UUID

from google.adk.agents import Agent
from google.adk.events.event import Event
from google.adk.runners import InMemoryRunner
from google.genai import types

from app.ai.search_worker.agent import build_google_search_agent
from app.ai.search_worker.firecrawl_client import FirecrawlSearchClient
from app.ai.search_worker.grounding import grounding_to_search_result
from app.ai.search_worker.schemas import SearchWorkerReply
from app.core.config import Settings
from app.core.provider_status import resolve_search_provider
from app.db.session import SessionFactory, create_session_factory
from app.schemas.search import (
    SEARCH_PROVIDER_FAILED_COPY,
    SEARCH_TIMEOUT_COPY,
    SEARCH_UNAVAILABLE_COPY,
    SearchWorkerResult,
)
from app.security.search_capability import SearchCapabilityError, consume_search_capability_once


class SearchRunner(Protocol):
    def run_async(
        self,
        *,
        user_id: str,
        session_id: str,
        invocation_id: str | None = None,
        new_message: types.Content | None = None,
        state_delta: dict[str, Any] | None = None,
        run_config: Any | None = None,
        yield_user_message: bool = False,
    ): ...

    async def close(self) -> None: ...


class SearchRunnerFactory(Protocol):
    def __call__(self, agent: Agent) -> SearchRunner: ...


class SearchAgentFactory(Protocol):
    def __call__(self, settings: Settings) -> Agent: ...


class FirecrawlClientFactory(Protocol):
    def __call__(self, settings: Settings) -> FirecrawlSearchClient: ...


def _default_runner_factory(agent: Agent) -> SearchRunner:
    runner = InMemoryRunner(agent=agent, app_name=agent.name)
    runner.auto_create_session = True
    return runner


def _parse_worker_reply_text(
    value: str | None,
    *,
    bounded_prompt: str,
    max_output_chars: int,
) -> SearchWorkerReply | None:
    if not value:
        return None
    candidate = value.strip()
    if not candidate:
        return None

    if candidate.startswith("```"):
        stripped = candidate.removeprefix("```").strip()
        if stripped.lower().startswith("json"):
            stripped = stripped[4:].strip()
        if stripped.endswith("```"):
            stripped = stripped[:-3].strip()
        candidate = stripped

    try:
        payload = json.loads(candidate)
    except (json.JSONDecodeError, TypeError, ValueError):
        return None
    if not isinstance(payload, dict):
        return None

    answer = str(payload.get("answer_markdown") or "").strip()
    query_used = str(payload.get("query_used") or bounded_prompt).strip()
    if not answer:
        return None
    return SearchWorkerReply(
        answer_markdown=answer[:max_output_chars],
        query_used=query_used[:2048] or bounded_prompt,
    )


def _collect_event_text(event: Event) -> str | None:
    if not event.content or not event.content.parts:
        return None
    text = "".join(part.text or "" for part in event.content.parts if getattr(part, "text", None))
    collapsed = text.strip()
    return collapsed or None


def _coerce_worker_reply(
    *,
    output: Any,
    fallback_text: str | None,
    bounded_prompt: str,
    max_output_chars: int,
) -> SearchWorkerReply:
    if output is not None:
        if isinstance(output, SearchWorkerReply):
            return SearchWorkerReply(
                answer_markdown=output.answer_markdown[:max_output_chars],
                query_used=output.query_used[:2048],
            )
        if isinstance(output, dict):
            answer = str(output.get("answer_markdown") or fallback_text or "").strip()
            query_used = str(output.get("query_used") or bounded_prompt).strip()
            return SearchWorkerReply(
                answer_markdown=answer[:max_output_chars] or "Không thể tạo phản hồi tìm kiếm hợp lệ.",
                query_used=query_used[:2048] or bounded_prompt,
            )
        parsed_output = _parse_worker_reply_text(str(output), bounded_prompt=bounded_prompt, max_output_chars=max_output_chars)
        if parsed_output is not None:
            return parsed_output

    parsed_fallback = _parse_worker_reply_text(
        fallback_text,
        bounded_prompt=bounded_prompt,
        max_output_chars=max_output_chars,
    )
    if parsed_fallback is not None:
        return parsed_fallback

    answer_markdown = (fallback_text or "").strip()[:max_output_chars]
    if not answer_markdown:
        answer_markdown = "Không thể tạo phản hồi tìm kiếm hợp lệ."
    return SearchWorkerReply(
        answer_markdown=answer_markdown,
        query_used=bounded_prompt,
    )


class GoogleSearchWorkerService:
    def __init__(
        self,
        *,
        settings: Settings,
        runner_factory: SearchRunnerFactory | None = None,
        agent_factory: SearchAgentFactory | None = None,
        session_factory: SessionFactory | None = None,
    ) -> None:
        self.settings = settings
        self._runner_factory = runner_factory or _default_runner_factory
        self._agent_factory = agent_factory or build_google_search_agent
        self._session_factory = session_factory

    async def run(
        self,
        *,
        user_id: str,
        conversation_id: str,
        prompt: str,
        correlation_id: str | None,
        capability_token: str | None = None,
    ) -> SearchWorkerResult:
        try:
            await _consume_worker_capability(
                settings=self.settings,
                session_factory=self._session_factory,
                capability_token=capability_token,
                user_id=user_id,
                conversation_id=conversation_id,
                correlation_id=correlation_id,
            )
        except (SearchCapabilityError, ValueError):
            return SearchWorkerResult(
                state="search_unavailable",
                answer_markdown=SEARCH_UNAVAILABLE_COPY,
                google_grounded=False,
                tool_executed=False,
                output_summary="search_unavailable",
            )

        previous_google_api_key = os.environ.get("GOOGLE_API_KEY")
        previous_gemini_api_key = os.environ.get("GEMINI_API_KEY")
        google_api_key = self.settings.google_api_key_value
        if google_api_key:
            os.environ["GOOGLE_API_KEY"] = google_api_key
            os.environ["GEMINI_API_KEY"] = google_api_key

        try:
            agent = self._agent_factory(self.settings)
            runner = self._runner_factory(agent)
            bounded_prompt = prompt.strip()[: self.settings.search_max_prompt_chars].strip()
            if not bounded_prompt:
                bounded_prompt = prompt.strip() or "Truy vấn tìm kiếm"

            output: Any = None
            fallback_text: str | None = None
            grounding_metadata: Any = None

            try:
                async with asyncio.timeout(self.settings.search_worker_timeout_seconds):
                    async with aclosing(
                        runner.run_async(
                            user_id=user_id,
                            session_id=conversation_id,
                            new_message=types.Content(
                                role="user",
                                parts=[types.Part(text=bounded_prompt)],
                            ),
                        )
                    ) as events:
                        async for event in events:
                            if event.output is not None:
                                output = event.output
                            if event.grounding_metadata is not None:
                                grounding_metadata = event.grounding_metadata
                            if text := _collect_event_text(event):
                                fallback_text = text
                            if event.error_code or event.error_message:
                                raise RuntimeError(event.error_message or event.error_code)
            except TimeoutError:
                return SearchWorkerResult(
                    state="timeout",
                    answer_markdown=SEARCH_TIMEOUT_COPY,
                    google_grounded=False,
                    tool_executed=True,
                    output_summary="timeout",
                )
            except Exception:
                return SearchWorkerResult(
                    state="provider_failed",
                    answer_markdown=SEARCH_PROVIDER_FAILED_COPY,
                    google_grounded=False,
                    tool_executed=True,
                    output_summary="provider_failed",
                )
            finally:
                await runner.close()

            reply = _coerce_worker_reply(
                output=output,
                fallback_text=fallback_text,
                bounded_prompt=bounded_prompt,
                max_output_chars=self.settings.search_max_output_chars,
            )
            return grounding_to_search_result(
                reply,
                grounding_metadata,
                max_output_chars=self.settings.search_max_output_chars,
            )
        finally:
            if previous_google_api_key is None:
                os.environ.pop("GOOGLE_API_KEY", None)
            else:
                os.environ["GOOGLE_API_KEY"] = previous_google_api_key
            if previous_gemini_api_key is None:
                os.environ.pop("GEMINI_API_KEY", None)
            else:
                os.environ["GEMINI_API_KEY"] = previous_gemini_api_key


class FirecrawlSearchWorkerService:
    def __init__(
        self,
        *,
        settings: Settings,
        client_factory: FirecrawlClientFactory | None = None,
        session_factory: SessionFactory | None = None,
    ) -> None:
        self.settings = settings
        self._client_factory = client_factory or FirecrawlSearchClient
        self._session_factory = session_factory

    async def run(
        self,
        *,
        user_id: str,
        conversation_id: str,
        prompt: str,
        correlation_id: str | None,
        capability_token: str | None = None,
    ) -> SearchWorkerResult:
        try:
            await _consume_worker_capability(
                settings=self.settings,
                session_factory=self._session_factory,
                capability_token=capability_token,
                user_id=user_id,
                conversation_id=conversation_id,
                correlation_id=correlation_id,
            )
        except (SearchCapabilityError, ValueError):
            return SearchWorkerResult(
                provider="firecrawl",
                state="search_unavailable",
                answer_markdown=SEARCH_UNAVAILABLE_COPY,
                google_grounded=False,
                tool_executed=False,
                output_summary="search_unavailable",
            )

        client = self._client_factory(self.settings)
        return await client.search(query=prompt)


def build_search_worker_service(
    settings: Settings,
    *,
    runtime_override: str | None = None,
    session_factory: SessionFactory | None = None,
):
    provider = resolve_search_provider(settings, runtime_override=runtime_override)
    if provider == "firecrawl":
        return FirecrawlSearchWorkerService(settings=settings, session_factory=session_factory)
    if provider == "gemini":
        return GoogleSearchWorkerService(settings=settings, session_factory=session_factory)
    return None


async def _consume_worker_capability(
    *,
    settings: Settings,
    session_factory: SessionFactory | None,
    capability_token: str | None,
    user_id: str,
    conversation_id: str,
    correlation_id: str | None,
) -> None:
    resolved_session_factory = session_factory or create_session_factory(settings)
    owns_factory = session_factory is None
    try:
        await consume_search_capability_once(
            capability_token or "",
            settings=settings,
            session_factory=resolved_session_factory,
            expected_user_id=UUID(user_id),
            expected_conversation_id=UUID(conversation_id),
            expected_correlation_id=correlation_id,
            now=settings.now_utc(),
        )
    finally:
        if owns_factory:
            bind = resolved_session_factory.kw.get("bind")
            if bind is not None:
                await bind.dispose()

from __future__ import annotations

import asyncio
from contextlib import aclosing
from datetime import UTC, datetime
from typing import Any, Protocol
from uuid import UUID

from google.adk.agents import Agent
from google.adk.events.event import Event
from google.adk.runners import InMemoryRunner
from google.genai import types

from app.ai.search_worker.agent import build_google_search_agent
from app.ai.search_worker.grounding import grounding_to_search_result
from app.ai.search_worker.schemas import SearchWorkerReply
from app.core.config import Settings
from app.schemas.search import (
    SEARCH_PROVIDER_FAILED_COPY,
    SEARCH_TIMEOUT_COPY,
    SEARCH_UNAVAILABLE_COPY,
    SearchWorkerResult,
)
from app.security.search_capability import SearchCapabilityError, validate_search_capability


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


def _default_runner_factory(agent: Agent) -> SearchRunner:
    return InMemoryRunner(agent=agent)


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
    ) -> None:
        self.settings = settings
        self._runner_factory = runner_factory or _default_runner_factory
        self._agent_factory = agent_factory or build_google_search_agent

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
            claims = validate_search_capability(
                capability_token or "",
                settings=self.settings,
                now=datetime.now(UTC),
            )
            if claims.sub != UUID(user_id):
                raise SearchCapabilityError("Capability subject does not match the user")
            if claims.conversation_id != UUID(conversation_id):
                raise SearchCapabilityError("Capability conversation does not match")
            if claims.correlation_id != correlation_id:
                raise SearchCapabilityError("Capability correlation does not match")
        except (SearchCapabilityError, ValueError):
            return SearchWorkerResult(
                state="search_unavailable",
                answer_markdown=SEARCH_UNAVAILABLE_COPY,
                google_grounded=False,
                tool_executed=False,
                output_summary="search_unavailable",
            )

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

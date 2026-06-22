from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Any

from openai import (
    APIConnectionError,
    APIStatusError,
    APITimeoutError,
    AuthenticationError,
    AsyncOpenAI,
    PermissionDeniedError,
    RateLimitError,
)
from pydantic import BaseModel, ConfigDict, Field

from app.ai.chat_adapter import ChatProviderError
from app.ai.schemas import ChatTurn
from app.core.config import Settings
from app.python_contract import PythonArtifactType, PythonExecutionProfile


CODE_FENCE_RE = re.compile(r"```(?:python)?\s*(.*?)```", re.DOTALL | re.IGNORECASE)
INLINE_CODE_RE = re.compile(r"^\s*(from\s+\w+\s+import|import\s+\w+|print\(|[A-Za-z_]\w*\s*=)")
PLANNER_SYSTEM_PROMPT = """You are the Python planning component for SimpAgent.
Return JSON only with these fields:
- code: string or null
- requested_artifacts: array of approved artifact types from [\"csv\",\"json\",\"txt\",\"png\"]
- needs_search: boolean
- suggested_profile: optional string from [\"python-basic-v1\",\"python-data-v1\"]

Rules:
- Choose Python only for the latest user request that already contains enough data or can be solved from conversation context.
- If the request needs web search, current external data, or another tool first, set needs_search=true and code=null.
- Generate Python 3.13 code only.
- Always print the final user-facing answer or a concise result summary to stdout. For arithmetic, print the computed value directly.
- Do not rely on comments, variables, return values, or artifacts alone to communicate the answer.
- Allowed libraries are standard-library modules plus collections, csv, datetime, decimal, fractions, functools, io, itertools, json, math, matplotlib, numpy, os, pandas, pathlib, random, re, statistics, string, textwrap.
- Never use network access, requests, urllib, socket, subprocess, pip, ensurepip, importlib, multiprocessing, os.system, or os.popen.
- Never install packages or run shell commands.
- Do not read or write arbitrary host paths. If the user asks for an approved downloadable artifact, write it under Path(\"artifacts\") using a safe filename.
- Prefer concise code and keep comments minimal.
- If prior Python state bindings are available, you may reuse them by name.
"""


class PlannerPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    code: str | None = Field(default=None, max_length=16_000)
    requested_artifacts: list[PythonArtifactType] = Field(default_factory=list, max_length=4)
    needs_search: bool = False
    suggested_profile: PythonExecutionProfile | None = None


@dataclass(frozen=True, slots=True)
class PythonToolPlan:
    code: str | None
    requested_artifacts: tuple[PythonArtifactType, ...] = ()
    suggested_profile: PythonExecutionProfile | None = None
    needs_search: bool = False


class OpenAIPythonPlanner:
    def __init__(self, *, settings: Settings, client: AsyncOpenAI | None = None) -> None:
        self._settings = settings
        self._client = client

    async def plan(
        self,
        *,
        messages: list[ChatTurn],
        prompt: str,
        state_binding_names: tuple[str, ...],
    ) -> PythonToolPlan:
        embedded = _embedded_python_code(prompt)
        if embedded is not None:
            return PythonToolPlan(
                code=embedded,
                requested_artifacts=_artifact_hints(prompt),
            )

        payload = {
            "model": self._settings.llm_model,
            "messages": [
                {
                    "role": "system",
                    "content": "\n".join(
                        (
                            PLANNER_SYSTEM_PROMPT,
                            f"Available state bindings: {', '.join(state_binding_names) if state_binding_names else 'none'}",
                        )
                    ),
                },
                {
                    "role": "user",
                    "content": _planner_context(messages=messages),
                },
            ],
            "temperature": 0.1,
            "max_completion_tokens": 1200,
            "stream": False,
            "response_format": {"type": "json_object"},
        }

        try:
            completion = await self._resolved_client().chat.completions.create(**payload)
        except APITimeoutError as exc:
            raise self._provider_error("provider_timeout", exc, retryable=True) from exc
        except RateLimitError as exc:
            raise self._provider_error("provider_rate_limited", exc, retryable=True) from exc
        except (AuthenticationError, PermissionDeniedError) as exc:
            raise self._provider_error("provider_auth_error", exc, retryable=False) from exc
        except APIStatusError as exc:
            status_code = getattr(exc, "status_code", None)
            if status_code in (401, 403):
                raise self._provider_error("provider_auth_error", exc, retryable=False) from exc
            retryable = status_code in (408, 409, 429) or (isinstance(status_code, int) and status_code >= 500)
            raise self._provider_error("provider_status_error", exc, retryable=retryable) from exc
        except APIConnectionError as exc:
            raise self._provider_error("provider_unreachable", exc, retryable=True) from exc

        choices = getattr(completion, "choices", None) or []
        if not choices:
            raise ChatProviderError("provider_empty_response", retryable=True, provider_request_id=_provider_request_id(completion))
        message = getattr(choices[0], "message", None)
        content = getattr(message, "content", None) if message is not None else None
        if not content:
            raise ChatProviderError("provider_empty_response", retryable=True, provider_request_id=_provider_request_id(completion))

        try:
            parsed = PlannerPayload.model_validate(json.loads(content))
        except (json.JSONDecodeError, ValueError) as exc:
            raise ChatProviderError(
                "provider_invalid_response",
                retryable=True,
                provider_request_id=_provider_request_id(completion),
            ) from exc

        return PythonToolPlan(
            code=parsed.code.strip() if parsed.code else None,
            requested_artifacts=tuple(parsed.requested_artifacts),
            suggested_profile=parsed.suggested_profile,
            needs_search=parsed.needs_search,
        )

    @staticmethod
    def _provider_error(code: str, exc: BaseException, *, retryable: bool) -> ChatProviderError:
        return ChatProviderError(
            code,
            retryable=retryable,
            provider_request_id=_provider_request_id(exc),
        )

    def _resolved_client(self) -> AsyncOpenAI:
        if self._client is not None:
            return self._client

        try:
            api_key = self._settings.llm_api_key_value
        except OSError as exc:
            raise ChatProviderError("provider_unconfigured", retryable=False) from exc

        if not api_key or not self._settings.llm_model:
            raise ChatProviderError("provider_unconfigured", retryable=False)

        self._client = AsyncOpenAI(
            api_key=api_key,
            base_url=self._settings.llm_api_base,
            timeout=self._settings.llm_timeout_seconds,
            max_retries=self._settings.llm_max_retries,
        )
        return self._client


def _embedded_python_code(prompt: str) -> str | None:
    match = CODE_FENCE_RE.search(prompt)
    if match:
        return match.group(1).strip()
    if INLINE_CODE_RE.search(prompt):
        return prompt.strip()
    return None


def _artifact_hints(prompt: str) -> tuple[PythonArtifactType, ...]:
    lowered = prompt.lower()
    hints: list[PythonArtifactType] = []
    for name in PythonArtifactType:
        if name.value in lowered:
            hints.append(name)
    return tuple(dict.fromkeys(hints))


def _planner_context(*, messages: list[ChatTurn]) -> str:
    lines = ["Conversation context:"]
    for message in messages:
        lines.append(f"{message.role}: {message.content}")
    lines.append("Return a JSON object for the latest user request only.")
    return "\n".join(lines)


def _provider_request_id(source: Any) -> str | None:
    for attr in ("provider_request_id", "request_id", "_request_id"):
        value = getattr(source, attr, None)
        if value:
            return str(value)

    response = getattr(source, "response", None)
    headers = getattr(response, "headers", None)
    if headers is None:
        return None
    for header in ("x-request-id", "X-Request-Id", "request-id"):
        try:
            value = headers.get(header)
        except AttributeError:
            value = None
        if value:
            return str(value)
    return None

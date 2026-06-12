from __future__ import annotations

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

from app.ai.prompts import DIRECT_CHAT_SYSTEM_PROMPT
from app.ai.schemas import ChatCompletionResult, ChatTurn
from app.core.config import Settings


class ChatProviderError(RuntimeError):
    def __init__(
        self,
        code: str,
        *,
        retryable: bool,
        provider_request_id: str | None = None,
    ) -> None:
        super().__init__(code)
        self.code = code
        self.retryable = retryable
        self.provider_request_id = provider_request_id

    def to_safe_metadata(self) -> dict[str, str | bool | None]:
        return {
            "code": self.code,
            "retryable": self.retryable,
            "provider_request_id": self.provider_request_id,
        }


class OpenAIChatAdapter:
    def __init__(self, *, settings: Settings, client: AsyncOpenAI | None = None) -> None:
        api_key = settings.llm_api_key_value
        if not api_key:
            raise ChatProviderError("provider_unconfigured", retryable=False)
        if not settings.llm_model:
            raise ChatProviderError("provider_unconfigured", retryable=False)

        self._settings = settings
        self._client = client or AsyncOpenAI(
            api_key=api_key,
            base_url=settings.llm_api_base,
            timeout=settings.llm_timeout_seconds,
            max_retries=settings.llm_max_retries,
        )

    async def complete(self, *, messages: list[ChatTurn]) -> ChatCompletionResult:
        payload = {
            "model": self._settings.llm_model,
            "messages": [
                {"role": "system", "content": DIRECT_CHAT_SYSTEM_PROMPT},
                *[{"role": turn.role, "content": turn.content} for turn in messages],
            ],
            "temperature": 0.3,
            "max_completion_tokens": 800,
            "stream": False,
        }

        try:
            completion = await self._client.chat.completions.create(**payload)
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

        provider_request_id = self._provider_request_id(completion)
        choices = getattr(completion, "choices", None) or []
        if not choices:
            raise ChatProviderError(
                "provider_empty_response",
                retryable=True,
                provider_request_id=provider_request_id,
            )
        choice = choices[0]
        message = getattr(choice, "message", None)
        content = getattr(message, "content", None) if message is not None else None
        if not content:
            raise ChatProviderError(
                "provider_empty_response",
                retryable=True,
                provider_request_id=provider_request_id,
            )

        usage = getattr(completion, "usage", None)
        return ChatCompletionResult(
            content=content,
            provider_request_id=provider_request_id,
            prompt_tokens=getattr(usage, "prompt_tokens", None) if usage is not None else None,
            completion_tokens=getattr(usage, "completion_tokens", None) if usage is not None else None,
            finish_reason=getattr(choice, "finish_reason", None),
        )

    @classmethod
    def _provider_error(cls, code: str, exc: BaseException, *, retryable: bool) -> ChatProviderError:
        return ChatProviderError(
            code,
            retryable=retryable,
            provider_request_id=cls._provider_request_id(exc),
        )

    @staticmethod
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

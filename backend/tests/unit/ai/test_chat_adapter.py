from __future__ import annotations

from datetime import UTC, datetime
from types import SimpleNamespace
from typing import Any

import pytest

import app.ai.chat_adapter as chat_adapter_module
from app.ai.chat_adapter import ChatProviderError, OpenAIChatAdapter
from app.ai.schemas import ChatTurn
from app.core.config import Settings


FORBIDDEN_PROVIDER_KEYS = {
    "tools",
    "tool_choice",
    "web_search_options",
    "file_search",
    "files",
    "store",
    "previous_response_id",
    "conversation",
    "mcp",
    "code_interpreter",
}


def make_settings(**overrides: Any) -> Settings:
    values: dict[str, Any] = {
        "app_env": "test",
        "database_url": "postgresql+psycopg://postgres:postgres@postgres-test:5432/simpagent_test",
        "allowed_origins": ["http://localhost:3000"],
        "jwt_private_key": "test-private-key",
        "jwt_public_key": "test-public-key",
        "refresh_hmac_key": "refresh-refresh-refresh-refresh",
        "csrf_hmac_key": "csrf-csrf-csrf-csrf-csrf-csrf-csrf",
        "llm_api_base": "https://provider.example.test/v1",
        "llm_api_key": "sk-test-secret-value",
        "llm_model": "provider-chat-model",
        "llm_timeout_seconds": 12,
        "llm_max_retries": 1,
    }
    values.update(overrides)
    return Settings(**values)


class RecordingCompletions:
    def __init__(self, response: Any | None = None, error: BaseException | None = None) -> None:
        self.payloads: list[dict[str, Any]] = []
        self.response = response or SimpleNamespace(
            _request_id="req-success",
            choices=[
                SimpleNamespace(
                    message=SimpleNamespace(content="A safe assistant answer."),
                    finish_reason="stop",
                )
            ],
            usage=SimpleNamespace(prompt_tokens=17, completion_tokens=9),
        )
        self.error = error

    async def create(self, **payload: Any) -> Any:
        self.payloads.append(payload)
        if self.error:
            raise self.error
        return self.response


class RecordingAsyncOpenAI:
    instances: list["RecordingAsyncOpenAI"] = []
    completions: RecordingCompletions

    def __init__(self, **kwargs: Any) -> None:
        self.kwargs = kwargs
        self.chat = SimpleNamespace(completions=self.completions)
        self.instances.append(self)


def install_fake_client(
    monkeypatch: pytest.MonkeyPatch,
    *,
    response: Any | None = None,
    error: BaseException | None = None,
) -> RecordingCompletions:
    completions = RecordingCompletions(response=response, error=error)
    RecordingAsyncOpenAI.instances = []
    RecordingAsyncOpenAI.completions = completions
    monkeypatch.setattr(chat_adapter_module, "AsyncOpenAI", RecordingAsyncOpenAI)
    return completions


def test_settings_include_provider_timeout_retry_and_keep_secret_repr_safe() -> None:
    settings = make_settings()

    assert settings.llm_api_base == "https://provider.example.test/v1"
    assert settings.llm_api_key_value == "sk-test-secret-value"
    assert settings.llm_model == "provider-chat-model"
    assert settings.llm_timeout_seconds == 12
    assert settings.llm_max_retries == 1
    assert "sk-test-secret-value" not in repr(settings)
    assert "sk-test-secret-value" not in settings.model_dump_json()


def test_blank_env_key_falls_back_to_secret_file(tmp_path) -> None:
    secret_file = tmp_path / "llm_api_key"
    secret_file.write_text("file-backed-secret\n", encoding="utf-8")

    settings = make_settings(llm_api_key="", llm_api_key_file=str(secret_file))

    assert settings.llm_api_key_value == "file-backed-secret"


@pytest.mark.asyncio
async def test_adapter_constructs_async_openai_from_settings(monkeypatch: pytest.MonkeyPatch) -> None:
    install_fake_client(monkeypatch)

    adapter = OpenAIChatAdapter(settings=make_settings())
    await adapter.complete(messages=[ChatTurn(role="user", content="Hello")])

    assert len(RecordingAsyncOpenAI.instances) == 1
    assert RecordingAsyncOpenAI.instances[0].kwargs == {
        "api_key": "sk-test-secret-value",
        "base_url": "https://provider.example.test/v1",
        "timeout": 12,
        "max_retries": 1,
    }


@pytest.mark.asyncio
async def test_adapter_sends_direct_non_streaming_chat_completion_payload(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    completions = install_fake_client(monkeypatch)

    adapter = OpenAIChatAdapter(
        settings=make_settings(test_now=datetime(2026, 6, 14, 0, 0, tzinfo=UTC))
    )
    result = await adapter.complete(
        messages=[
            ChatTurn(role="user", content="Write a tiny Python list comprehension."),
            ChatTurn(role="assistant", content="Use `[x for x in range(3)]`."),
            ChatTurn(role="user", content="Make it return squares."),
        ],
    )

    assert result.content == "A safe assistant answer."
    assert result.provider_request_id == "req-success"
    assert result.prompt_tokens == 17
    assert result.completion_tokens == 9
    assert result.finish_reason == "stop"

    assert len(completions.payloads) == 1
    payload = completions.payloads[0]
    assert payload["model"] == "provider-chat-model"
    assert payload["temperature"] == 0.3
    assert payload["max_completion_tokens"] == 800
    assert payload["stream"] is False
    assert FORBIDDEN_PROVIDER_KEYS.isdisjoint(payload)

    assert payload["messages"][0]["role"] == "system"
    system_prompt = payload["messages"][0]["content"]
    assert "SimpAgent" in system_prompt
    assert "web search" in system_prompt
    assert "Current runtime date: 2026-06-14 (UTC)." in system_prompt
    assert "knowledge cutoff is 2025-08-31" in system_prompt
    assert payload["messages"][1:] == [
        {"role": "user", "content": "Write a tiny Python list comprehension."},
        {"role": "assistant", "content": "Use `[x for x in range(3)]`."},
        {"role": "user", "content": "Make it return squares."},
    ]


class TimeoutFailure(Exception):
    provider_request_id = "req-timeout"


class RateLimitFailure(Exception):
    provider_request_id = "req-rate"


class AuthFailure(Exception):
    provider_request_id = "req-auth"
    status_code = 401


class ServerFailure(Exception):
    provider_request_id = "req-server"
    status_code = 503


class ConnectionFailure(Exception):
    provider_request_id = "req-connection"


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("exception_type", "exception", "expected_code", "retryable", "provider_request_id"),
    [
        (TimeoutFailure, TimeoutFailure("timeout with sk-test-secret-value"), "provider_timeout", True, "req-timeout"),
        (RateLimitFailure, RateLimitFailure("rate limited"), "provider_rate_limited", True, "req-rate"),
        (AuthFailure, AuthFailure("401 raw provider body"), "provider_auth_error", False, "req-auth"),
        (ServerFailure, ServerFailure("503 raw provider body"), "provider_status_error", True, "req-server"),
        (ConnectionFailure, ConnectionFailure("connection failed"), "provider_unreachable", True, "req-connection"),
    ],
)
async def test_provider_failures_map_to_safe_app_owned_errors(
    monkeypatch: pytest.MonkeyPatch,
    exception_type: type[Exception],
    exception: Exception,
    expected_code: str,
    retryable: bool,
    provider_request_id: str,
) -> None:
    monkeypatch.setattr(chat_adapter_module, exception_type.__name__, exception_type, raising=False)
    exception_mapping = {
        "APITimeoutError": TimeoutFailure,
        "RateLimitError": RateLimitFailure,
        "AuthenticationError": AuthFailure,
        "APIStatusError": ServerFailure,
        "APIConnectionError": ConnectionFailure,
    }
    for name, patched_type in exception_mapping.items():
        monkeypatch.setattr(chat_adapter_module, name, patched_type, raising=False)
    install_fake_client(monkeypatch, error=exception)

    adapter = OpenAIChatAdapter(settings=make_settings())
    with pytest.raises(ChatProviderError) as raised:
        await adapter.complete(messages=[ChatTurn(role="user", content="secret prompt")])

    error = raised.value
    assert error.code == expected_code
    assert error.retryable is retryable
    assert error.provider_request_id == provider_request_id
    assert error.to_safe_metadata() == {
        "code": expected_code,
        "retryable": retryable,
        "provider_request_id": provider_request_id,
    }

    rendered_error = f"{error!s} {error!r} {error.to_safe_metadata()!r}"
    for forbidden in (
        "sk-test-secret-value",
        "Bearer",
        "cookie",
        "secret prompt",
        "assistant",
        "raw provider body",
    ):
        assert forbidden not in rendered_error


@pytest.mark.asyncio
async def test_empty_provider_response_maps_to_safe_retryable_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    install_fake_client(
        monkeypatch,
        response=SimpleNamespace(
            _request_id="req-empty",
            choices=[SimpleNamespace(message=SimpleNamespace(content=None), finish_reason="stop")],
            usage=None,
        ),
    )

    adapter = OpenAIChatAdapter(settings=make_settings())
    with pytest.raises(ChatProviderError) as raised:
        await adapter.complete(messages=[ChatTurn(role="user", content="Hello")])

    assert raised.value.code == "provider_empty_response"
    assert raised.value.retryable is True
    assert raised.value.provider_request_id == "req-empty"
    assert "Hello" not in str(raised.value)

from __future__ import annotations

from google.adk.events.event import Event
import pytest

from app.ai.search_worker.service import GoogleSearchWorkerService
from tests.integration.search._worker_fakes import FakeRunner, make_search_settings, mint_capability_token


@pytest.mark.asyncio
async def test_worker_service_clamps_prompt_and_output_to_budget(settings) -> None:
    search_settings = make_search_settings(
        settings,
        search_max_prompt_chars=12,
        search_max_output_chars=40,
    )
    token, user_id, conversation_id = mint_capability_token(
        search_settings,
        correlation_id="corr-budget",
    )
    runner = FakeRunner(
        events=[
            Event(
                author="model",
                output={
                    "answer_markdown": "x" * 200,
                    "query_used": "truy van rat dai",
                },
                groundingMetadata={
                    "grounding_chunks": [
                        {
                            "web": {
                                "title": "Nguồn kiểm thử",
                                "domain": "example.test",
                                "uri": "https://example.test/source",
                            }
                        }
                    ],
                    "grounding_supports": [
                        {
                            "grounding_chunk_indices": [0],
                            "segment": {"start_index": 0, "end_index": 1},
                        }
                    ],
                },
            )
        ]
    )
    service = GoogleSearchWorkerService(
        settings=search_settings,
        runner_factory=lambda agent: runner,
    )

    result = await service.run(
        user_id=str(user_id),
        conversation_id=str(conversation_id),
        prompt="0123456789abcdef",
        correlation_id="corr-budget",
        capability_token=token,
    )

    assert runner.prompts == ["0123456789ab"]
    assert len(result.answer_markdown) == 40


@pytest.mark.asyncio
async def test_worker_service_times_out_without_retrying_the_provider(settings) -> None:
    search_settings = make_search_settings(
        settings,
        search_worker_timeout_seconds=0.01,
    )
    token, user_id, conversation_id = mint_capability_token(
        search_settings,
        correlation_id="corr-timeout",
    )
    runner = FakeRunner(delay_seconds=0.05)
    service = GoogleSearchWorkerService(
        settings=search_settings,
        runner_factory=lambda agent: runner,
    )

    result = await service.run(
        user_id=str(user_id),
        conversation_id=str(conversation_id),
        prompt="timeout me",
        correlation_id="corr-timeout",
        capability_token=token,
    )

    assert result.state == "timeout"
    assert runner.calls == 1


@pytest.mark.asyncio
async def test_worker_service_returns_provider_failed_after_single_runner_error(settings) -> None:
    search_settings = make_search_settings(settings)
    token, user_id, conversation_id = mint_capability_token(
        search_settings,
        correlation_id="corr-provider-failed",
    )
    runner = FakeRunner(exc=RuntimeError("provider exploded"))
    service = GoogleSearchWorkerService(
        settings=search_settings,
        runner_factory=lambda agent: runner,
    )

    result = await service.run(
        user_id=str(user_id),
        conversation_id=str(conversation_id),
        prompt="provider fail",
        correlation_id="corr-provider-failed",
        capability_token=token,
    )

    assert result.state == "provider_failed"
    assert runner.calls == 1

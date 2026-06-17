from __future__ import annotations

from datetime import UTC, datetime

from google.adk.events.event import Event
import pytest

from app.ai.search_worker.agent import (
    SEARCH_WORKER_INSTRUCTION,
    build_google_search_agent,
    build_search_worker_instruction,
)
from app.ai.search_worker.service import GoogleSearchWorkerService
from tests.integration.search._worker_fakes import (
    FakeRunner,
    make_search_settings,
    mint_capability_token,
    text_event,
)


def test_google_search_agent_is_single_purpose_without_function_calling_output_schema(settings) -> None:
    search_settings = make_search_settings(settings)

    agent = build_google_search_agent(search_settings)

    assert len(agent.tools) == 1
    assert agent.tools[0].name == "google_search"
    assert agent.output_schema is None
    assert agent.code_executor is None
    assert "URL nội bộ" in SEARCH_WORKER_INSTRUCTION


def test_google_search_instruction_includes_current_runtime_date(settings) -> None:
    search_settings = make_search_settings(
        settings,
        test_now=datetime(2026, 6, 14, 8, 0, tzinfo=UTC),
    )

    instruction = build_search_worker_instruction(search_settings)
    agent = build_google_search_agent(search_settings)

    assert "Current runtime date: 2026-06-14 (UTC)." in instruction
    assert "knowledge cutoff is 2025-08-31" in instruction
    assert "hôm nay" in instruction
    assert agent.instruction == instruction


def test_default_runner_factory_enables_session_auto_creation(settings) -> None:
    from app.ai.search_worker.service import _default_runner_factory

    runner = _default_runner_factory(build_google_search_agent(make_search_settings(settings)))

    assert runner.app_name == "google_search_worker"
    assert runner.auto_create_session is True


@pytest.mark.asyncio
async def test_worker_service_normalizes_grounded_response_with_trusted_suggestions(settings) -> None:
    search_settings = make_search_settings(settings)
    token, user_id, conversation_id = mint_capability_token(
        search_settings,
        correlation_id="corr-grounded",
    )
    runner = FakeRunner(
        events=[
            Event(
                author="model",
                output={
                    "answer_markdown": "Kết quả tìm kiếm [1].",
                    "query_used": "gia vang hom nay",
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
                            "segment": {"start_index": 17, "end_index": 20},
                        }
                    ],
                    "web_search_queries": ["gia vang hom nay"],
                    "search_entry_point": {
                        "rendered_content": "<a>Giá vàng ngày mai</a><a>USD/VND hôm nay</a>",
                    },
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
        prompt="  gia vang hom nay  ",
        correlation_id="corr-grounded",
        capability_token=token,
    )

    assert result.state == "grounded"
    assert result.google_grounded is True
    assert result.tool_executed is True
    assert result.sources[0].domain == "example.test"
    assert result.citations[0].source_index == 1
    assert result.suggestions is not None
    assert result.suggestions.items == ["Giá vàng ngày mai", "USD/VND hôm nay"]
    assert result.web_search_queries == ["gia vang hom nay"]
    assert runner.prompts == ["gia vang hom nay"]
    assert runner.closed is True


@pytest.mark.asyncio
async def test_worker_service_parses_json_text_output_without_output_schema(settings) -> None:
    search_settings = make_search_settings(settings)
    token, user_id, conversation_id = mint_capability_token(
        search_settings,
        correlation_id="corr-json-text",
    )
    runner = FakeRunner(
        events=[
            text_event(
                text='{"answer_markdown":"Tóm tắt kết quả [1].","query_used":"tin ai hom nay"}',
                grounding_metadata={
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
                            "segment": {"start_index": 16, "end_index": 19},
                        }
                    ],
                    "web_search_queries": ["tin ai hom nay"],
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
        prompt="tin ai hom nay",
        correlation_id="corr-json-text",
        capability_token=token,
    )

    assert result.state == "grounded"
    assert result.answer_markdown == "Tóm tắt kết quả [1]."
    assert result.web_search_queries == ["tin ai hom nay"]


@pytest.mark.asyncio
async def test_worker_service_downgrades_to_missing_grounding_without_safe_sources(settings) -> None:
    search_settings = make_search_settings(settings)
    token, user_id, conversation_id = mint_capability_token(
        search_settings,
        correlation_id="corr-missing",
    )
    runner = FakeRunner(
        events=[
            Event(
                author="model",
                output={
                    "answer_markdown": "Câu trả lời thiếu grounding an toàn.",
                    "query_used": "noi bo",
                },
                groundingMetadata={
                    "grounding_chunks": [
                        {
                            "web": {
                                "title": "Admin nội bộ",
                                "domain": "localhost",
                                "uri": "http://localhost/admin",
                            }
                        }
                    ],
                    "grounding_supports": [
                        {
                            "grounding_chunk_indices": [0],
                            "segment": {"start_index": 0, "end_index": 8},
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
        prompt="noi bo",
        correlation_id="corr-missing",
        capability_token=token,
    )

    assert result.state == "missing_grounding"
    assert result.google_grounded is False
    assert result.sources == []
    assert result.citations == []
    assert result.suggestions is None

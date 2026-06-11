from __future__ import annotations

from google.adk.events.event import Event
import pytest

from app.ai.search_worker.agent import SEARCH_WORKER_INSTRUCTION, build_google_search_agent
from app.ai.search_worker.schemas import SearchWorkerReply
from app.ai.search_worker.service import GoogleSearchWorkerService
from tests.integration.search._worker_fakes import FakeRunner, make_search_settings, mint_capability_token


def test_google_search_agent_is_single_purpose_and_typed(settings) -> None:
    search_settings = make_search_settings(settings)

    agent = build_google_search_agent(search_settings)

    assert len(agent.tools) == 1
    assert agent.tools[0].name == "google_search"
    assert agent.output_schema is SearchWorkerReply
    assert agent.code_executor is None
    assert "URL nội bộ" in SEARCH_WORKER_INSTRUCTION


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

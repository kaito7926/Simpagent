from __future__ import annotations

from app.ai.search_worker.agent import SEARCH_WORKER_INSTRUCTION
from app.ai.search_worker.grounding import grounding_to_search_result, is_public_web_uri
from app.ai.search_worker.schemas import SearchWorkerReply


def test_internal_urls_are_never_treated_as_public_search_sources() -> None:
    assert is_public_web_uri("https://example.test/news") is True
    assert is_public_web_uri("http://localhost/admin") is False
    assert is_public_web_uri("http://127.0.0.1:8000/secret") is False
    assert is_public_web_uri("http://10.0.0.8/debug") is False
    assert is_public_web_uri("file:///etc/passwd") is False


def test_grounding_with_only_internal_urls_downgrades_to_missing_grounding() -> None:
    result = grounding_to_search_result(
        SearchWorkerReply(
            answer_markdown="Câu trả lời có vẻ được dẫn nguồn.",
            query_used="internal target",
        ),
        {
            "grounding_chunks": [
                {
                    "web": {
                        "title": "Bảng điều khiển nội bộ",
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
        max_output_chars=4000,
    )

    assert result.state == "missing_grounding"
    assert result.sources == []
    assert result.citations == []


def test_worker_instruction_explicitly_rejects_policy_override_and_internal_fetches() -> None:
    assert "URL nội bộ" in SEARCH_WORKER_INSTRUCTION
    assert "tool khác" in SEARCH_WORKER_INSTRUCTION
    assert "bí mật" in SEARCH_WORKER_INSTRUCTION

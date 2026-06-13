from __future__ import annotations

import json

from app.ai.search_worker.grounding import normalize_grounding_evidence


def test_sensitive_queries_and_suggestions_are_dropped_from_grounding(secret_canary: str) -> None:
    evidence = normalize_grounding_evidence(
        {
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
                    "segment": {"start_index": 0, "end_index": 8},
                }
            ],
            "web_search_queries": [secret_canary, "truy van an toan"],
            "search_entry_point": {
                "rendered_content": f"<a>{secret_canary}</a><a>Gợi ý an toàn</a>",
            },
        }
    )

    dumped = json.dumps(evidence.model_dump(mode="json"), ensure_ascii=False)
    assert secret_canary not in dumped
    assert evidence.web_search_queries == ["truy van an toan"]
    assert evidence.suggestions is not None
    assert evidence.suggestions.items == ["Gợi ý an toàn"]

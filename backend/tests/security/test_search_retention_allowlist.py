from __future__ import annotations

import json

from app.services.chat_turns import allowlist_search_metadata


def test_search_metadata_allowlist_keeps_only_approved_fields() -> None:
    filtered = allowlist_search_metadata(
        {
            "mode": "google_search",
            "state": "grounded",
            "google_grounded": True,
            "tool_executed": True,
            "correlation_id": "corr-allowlist",
            "sources": [
                {
                    "index": 1,
                    "title": "Nguồn kiểm thử",
                    "domain": "example.test",
                    "uri": "https://example.test/source",
                    "snippet": "forbidden",
                    "click_tracking_id": "forbidden",
                }
            ],
            "citations": [
                {
                    "index": 1,
                    "source_index": 1,
                    "start": 0,
                    "end": 8,
                    "rendered_html": "<sup>1</sup>",
                }
            ],
            "suggestions": {
                "trusted": True,
                "items": ["Gợi ý an toàn"],
                "rendered_content": "<a>forbidden</a>",
            },
            "web_search_queries": ["truy van an toan"],
            "lifecycle": [{"event": "requested"}],
            "rendered_content": "<a>forbidden</a>",
            "sdk_blob": "forbidden",
            "unexpected": "forbidden",
        }
    )

    assert set(filtered) == {
        "mode",
        "state",
        "google_grounded",
        "tool_executed",
        "correlation_id",
        "sources",
        "citations",
        "suggestions",
        "web_search_queries",
        "lifecycle",
    }
    assert set(filtered["sources"][0]) == {"index", "title", "domain", "uri"}
    assert set(filtered["citations"][0]) == {"index", "source_index", "start", "end"}
    assert set(filtered["suggestions"]) == {"trusted", "items"}
    assert "forbidden" not in json.dumps(filtered)

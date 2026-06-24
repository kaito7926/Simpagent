from __future__ import annotations

import json

from pydantic import SecretStr

from app.ai.search_worker.firecrawl_client import FirecrawlSearchClient
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


def test_firecrawl_metadata_allowlist_rejects_click_tracking_and_raw_payload_fields() -> None:
    filtered = allowlist_search_metadata(
        {
            "mode": "google_search",
            "provider": "firecrawl",
            "state": "grounded",
            "google_grounded": False,
            "tool_executed": True,
            "correlation_id": "corr-firecrawl-retention",
            "sources": [
                {
                    "index": 1,
                    "title": "Firecrawl source",
                    "domain": "example.test",
                    "uri": "https://example.test/source?utm_source=tracker&safe=1",
                    "description": "must not persist",
                    "click_tracking_id": "click-123",
                    "redirect_url": "https://tracker.example/redirect",
                    "analytics": {"campaign": "forbidden"},
                }
            ],
            "citations": [{"index": 1, "source_index": 1}],
            "web_search_queries": ["firecrawl query"],
            "lifecycle": [{"event": "requested"}],
            "firecrawl_raw": {"creditsUsed": 10, "id": "job-123"},
            "tracking": {"utm_source": "tracker"},
        }
    )

    assert filtered["provider"] == "firecrawl"
    assert set(filtered["sources"][0]) == {"index", "title", "domain", "uri"}
    assert filtered["sources"][0]["uri"] == "https://example.test/source?safe=1"
    serialized = json.dumps(filtered)
    assert "click-123" not in serialized
    assert "redirect_url" not in serialized
    assert "utm_source" not in serialized
    assert "firecrawl_raw" not in serialized


def test_firecrawl_normalizer_refuses_redirect_wrappers_and_strips_tracking_query(settings) -> None:
    client = FirecrawlSearchClient(
        settings.model_copy(
            update={
                "websearch_provider": "firecrawl",
                "firecrawl_api_key": SecretStr("test-firecrawl-key"),
            }
        )
    )

    result = client._normalize_payload(
        {
            "success": True,
            "data": {
                "web": [
                    {
                        "title": "Tracking wrapper",
                        "url": "https://tracker.example/redirect?url=https%3A%2F%2Fexample.test%2Fwrapped",
                        "description": "must be refused",
                    },
                    {
                        "title": "Clean source",
                        "url": "https://example.test/source?utm_source=tracker&safe=1",
                        "description": "kept",
                    },
                ]
            },
        },
        query="firecrawl tracking",
    )

    assert result.provider == "firecrawl"
    assert result.state == "grounded"
    assert [source.title for source in result.sources] == ["Clean source"]
    assert result.sources[0].uri == "https://example.test/source?safe=1"
    assert "[1]" not in result.answer_markdown
    assert result.citations[0].end is not None
    assert "tracker.example" not in result.model_dump_json()
    assert "utm_source" not in result.model_dump_json()

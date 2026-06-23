from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping
from urllib.parse import urlparse

import httpx

from app.ai.search_worker.grounding import is_public_web_uri, sanitize_source_uri
from app.core.config import Settings
from app.schemas.search import (
    SEARCH_PROVIDER_FAILED_COPY,
    SEARCH_TIMEOUT_COPY,
    SearchCitation,
    SearchSource,
    SearchWorkerResult,
)


@dataclass(frozen=True)
class FirecrawlSearchClient:
    settings: Settings
    client: httpx.AsyncClient | None = None

    async def search(self, *, query: str) -> SearchWorkerResult:
        api_key = self.settings.firecrawl_api_key_value
        if not api_key:
            return SearchWorkerResult(
                provider="firecrawl",
                state="search_unavailable",
                answer_markdown="Firecrawl websearch chưa được cấu hình.",
                google_grounded=False,
                tool_executed=False,
                output_summary="search_unavailable",
            )

        bounded_query = query.strip()[: min(self.settings.search_max_prompt_chars, 500)].strip()
        if not bounded_query:
            bounded_query = "websearch"

        timeout = httpx.Timeout(self.settings.search_worker_timeout_seconds)
        owns_client = self.client is None
        client = self.client or httpx.AsyncClient(
            base_url=self.settings.firecrawl_api_base.rstrip("/"),
            timeout=timeout,
        )
        try:
            response = await client.post(
                "/v2/search",
                headers={"Authorization": f"Bearer {api_key}"},
                json={
                    "query": bounded_query,
                    "limit": self.settings.firecrawl_search_limit,
                    "sources": ["web"],
                    "timeout": int(self.settings.search_worker_timeout_seconds * 1000),
                    "ignoreInvalidURLs": True,
                },
            )
            response.raise_for_status()
            payload = response.json()
        except (httpx.TimeoutException, TimeoutError):
            return SearchWorkerResult(
                provider="firecrawl",
                state="timeout",
                answer_markdown=SEARCH_TIMEOUT_COPY,
                google_grounded=False,
                tool_executed=True,
                output_summary="timeout",
            )
        except Exception:
            return SearchWorkerResult(
                provider="firecrawl",
                state="provider_failed",
                answer_markdown=SEARCH_PROVIDER_FAILED_COPY,
                google_grounded=False,
                tool_executed=True,
                output_summary="provider_failed",
            )
        finally:
            if owns_client:
                await client.aclose()

        return self._normalize_payload(payload, query=bounded_query)

    def _normalize_payload(self, payload: Any, *, query: str) -> SearchWorkerResult:
        if not isinstance(payload, Mapping) or payload.get("success") is not True:
            return SearchWorkerResult(
                provider="firecrawl",
                state="provider_failed",
                answer_markdown=SEARCH_PROVIDER_FAILED_COPY,
                google_grounded=False,
                tool_executed=True,
                output_summary="provider_failed",
            )

        data = payload.get("data")
        web_results = data.get("web") if isinstance(data, Mapping) else None
        if not isinstance(web_results, list):
            web_results = []

        sources: list[SearchSource] = []
        answer_lines: list[str] = []
        for item in web_results[: self.settings.firecrawl_search_limit]:
            if not isinstance(item, Mapping):
                continue
            source = self._source_from_item(item, index=len(sources) + 1)
            if source is None:
                continue
            sources.append(source)
            description = str(item.get("description") or "").strip()
            if description:
                answer_lines.append(f"[{source.index}] {source.title}: {description[:300]}")
            else:
                answer_lines.append(f"[{source.index}] {source.title}")

        if not sources:
            return SearchWorkerResult(
                provider="firecrawl",
                state="missing_grounding",
                answer_markdown="Firecrawl không trả về nguồn web công khai phù hợp.",
                google_grounded=False,
                tool_executed=True,
                web_search_queries=[query],
                output_summary="missing_grounding",
            )

        citations = [
            SearchCitation(index=index, source_index=source.index)
            for index, source in enumerate(sources, start=1)
        ]
        answer = "\n".join(answer_lines)[: self.settings.search_max_output_chars].strip()
        return SearchWorkerResult(
            provider="firecrawl",
            state="grounded",
            answer_markdown=answer or "Firecrawl trả về nguồn web phù hợp.",
            google_grounded=False,
            tool_executed=True,
            sources=sources,
            citations=citations,
            suggestions=None,
            web_search_queries=[query],
            output_summary="grounded",
        )

    def _source_from_item(self, item: Mapping[str, Any], *, index: int) -> SearchSource | None:
        uri = sanitize_source_uri(str(item.get("url") or "").strip() or None)
        if not is_public_web_uri(uri):
            return None
        title = str(item.get("title") or "").strip()
        if not title:
            return None
        hostname = urlparse(uri).hostname if uri else None
        domain = str(item.get("domain") or hostname or "").strip()
        if not domain:
            return None
        return SearchSource(index=index, title=title[:500], domain=domain[:255], uri=uri)

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

        timeout_seconds = max(self.settings.search_worker_timeout_seconds, 30.0)
        timeout = httpx.Timeout(timeout_seconds)
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
                    "timeout": int(timeout_seconds * 1000),
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

        source_summaries: list[tuple[SearchSource, str]] = []
        for item in web_results[: self.settings.firecrawl_search_limit]:
            if not isinstance(item, Mapping):
                continue
            source = self._source_from_item(item, index=len(source_summaries) + 1)
            if source is None:
                continue
            description = str(item.get("description") or "").strip()
            source_summaries.append((source, description))

        if not source_summaries:
            return SearchWorkerResult(
                provider="firecrawl",
                state="missing_grounding",
                answer_markdown="Firecrawl không trả về nguồn web công khai phù hợp.",
                google_grounded=False,
                tool_executed=True,
                web_search_queries=[query],
                output_summary="missing_grounding",
            )

        sources, citations, answer = self._build_sourced_answer(source_summaries)
        return SearchWorkerResult(
            provider="firecrawl",
            state="grounded",
            answer_markdown=answer,
            google_grounded=False,
            tool_executed=True,
            sources=sources,
            citations=citations,
            suggestions=None,
            web_search_queries=[query],
            output_summary="grounded",
        )

    def _build_sourced_answer(
        self,
        source_summaries: list[tuple[SearchSource, str]],
    ) -> tuple[list[SearchSource], list[SearchCitation], str]:
        max_chars = self.settings.search_max_output_chars
        answer = "Tôi tìm thấy các nguồn web liên quan. Hãy mở từng nguồn để kiểm tra chi tiết:"
        sources: list[SearchSource] = []
        citations: list[SearchCitation] = []

        for source, description in source_summaries:
            summary = " ".join(description.split())[:240].strip()
            if summary:
                line = f"\n{source.title}: {summary}"
            else:
                line = f"\n{source.title}: Nguồn này có thông tin liên quan đến truy vấn."
            if len(answer) + len(line) > max_chars:
                break
            start = len(answer) + 1
            answer += line
            sources.append(source)
            citations.append(
                SearchCitation(
                    index=len(citations) + 1,
                    source_index=source.index,
                    start=start,
                    end=len(answer),
                )
            )

        if sources:
            return sources, citations, answer

        source, description = source_summaries[0]
        summary = " ".join(description.split())[:120].strip()
        fallback = f"{source.title}: {summary}" if summary else source.title
        answer = fallback[:max_chars].strip() or "Firecrawl trả về nguồn web phù hợp."
        citations = [SearchCitation(index=1, source_index=source.index, start=0, end=len(answer))]
        return [source], citations, answer

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

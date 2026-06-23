from __future__ import annotations

from html.parser import HTMLParser
import ipaddress
from typing import Any, Mapping
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse

from app.ai.search_worker.schemas import SearchGroundingEvidence, SearchWorkerReply
from app.schemas.search import SearchCitation, SearchSource, SearchSuggestions, SearchWorkerResult

SENSITIVE_TEXT_MARKERS = (
    "secret",
    "token",
    "bearer",
    "api key",
    "apikey",
    "jwt",
    "csrf",
    "refresh token",
    "access token",
    "password",
)
TRACKING_QUERY_KEYS = {
    "fbclid",
    "gclid",
    "mc_cid",
    "mc_eid",
    "msclkid",
    "utm_campaign",
    "utm_content",
    "utm_medium",
    "utm_source",
    "utm_term",
}


def looks_sensitive_text(value: str | None) -> bool:
    if not value:
        return False
    lowered = value.casefold()
    return any(marker in lowered for marker in SENSITIVE_TEXT_MARKERS)


def is_public_web_uri(uri: str | None) -> bool:
    if not uri:
        return False

    parsed = urlparse(uri)
    if parsed.scheme not in {"http", "https"}:
        return False
    if not parsed.hostname:
        return False

    host = parsed.hostname.rstrip(".").lower()
    if host in {"localhost", "metadata.google.internal"}:
        return False
    if host.endswith(".internal") or host.endswith(".local"):
        return False

    try:
        ip_address = ipaddress.ip_address(host)
    except ValueError:
        return True

    return not (
        ip_address.is_private
        or ip_address.is_loopback
        or ip_address.is_link_local
        or ip_address.is_multicast
        or ip_address.is_reserved
        or ip_address.is_unspecified
    )


def sanitize_source_uri(uri: str | None) -> str | None:
    if not is_public_web_uri(uri):
        return None
    parsed = urlparse(uri)
    filtered_query = [
        (key, value)
        for key, value in parse_qsl(parsed.query, keep_blank_values=True)
        if key.casefold() not in TRACKING_QUERY_KEYS
    ]
    return urlunparse(
        (
            parsed.scheme,
            parsed.netloc,
            parsed.path,
            parsed.params,
            urlencode(filtered_query, doseq=True),
            "",
        )
    )


class _SuggestionParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self._capture_depth = 0
        self._current_parts: list[str] = []
        self._items: list[str] = []

    @property
    def items(self) -> list[str]:
        return self._items

    def handle_starttag(self, tag: str, attrs) -> None:  # type: ignore[override]
        if tag in {"a", "button"}:
            self._capture_depth += 1

    def handle_endtag(self, tag: str) -> None:  # type: ignore[override]
        if tag not in {"a", "button"} or self._capture_depth == 0:
            return
        self._capture_depth -= 1
        if self._capture_depth == 0:
            item = " ".join(" ".join(self._current_parts).split())
            self._current_parts.clear()
            if item and item not in self._items and not looks_sensitive_text(item):
                self._items.append(item)

    def handle_data(self, data: str) -> None:  # type: ignore[override]
        if self._capture_depth > 0:
            self._current_parts.append(data)


def extract_search_suggestions(rendered_content: str | None, *, max_items: int = 5) -> list[str]:
    if not rendered_content:
        return []

    parser = _SuggestionParser()
    parser.feed(rendered_content)
    return parser.items[:max_items]


def _to_mapping(grounding_metadata: Any) -> dict[str, Any]:
    if grounding_metadata is None:
        return {}
    if isinstance(grounding_metadata, Mapping):
        return dict(grounding_metadata)
    model_dump = getattr(grounding_metadata, "model_dump", None)
    if callable(model_dump):
        return model_dump(mode="python", exclude_none=True)
    return {}


def normalize_grounding_evidence(
    grounding_metadata: Any,
    *,
    max_suggestions: int = 5,
    max_queries: int = 5,
) -> SearchGroundingEvidence:
    payload = _to_mapping(grounding_metadata)
    source_index_map: dict[int, int] = {}
    sources: list[SearchSource] = []

    for original_index, chunk in enumerate(payload.get("grounding_chunks", [])):
        if not isinstance(chunk, Mapping):
            continue
        web = chunk.get("web")
        if not isinstance(web, Mapping):
            continue

        uri = str(web.get("uri") or "").strip() or None
        title = str(web.get("title") or "").strip()
        domain = str(web.get("domain") or "").strip()

        if looks_sensitive_text(title) or looks_sensitive_text(domain):
            continue
        uri = sanitize_source_uri(uri)
        if not title or not domain or not uri:
            continue

        source_index = len(sources) + 1
        source_index_map[original_index] = source_index
        sources.append(
            SearchSource(
                index=source_index,
                title=title[:500],
                domain=domain[:255],
                uri=uri,
            )
        )

    citations: list[SearchCitation] = []
    for support in payload.get("grounding_supports", []):
        if not isinstance(support, Mapping):
            continue

        raw_indices = support.get("grounding_chunk_indices", [])
        if not isinstance(raw_indices, list):
            continue

        mapped_source_index = next(
            (source_index_map[index] for index in raw_indices if index in source_index_map),
            None,
        )
        if mapped_source_index is None:
            continue

        segment = support.get("segment")
        start = None
        end = None
        if isinstance(segment, Mapping):
            raw_start = segment.get("start_index")
            raw_end = segment.get("end_index")
            start = raw_start if isinstance(raw_start, int) and raw_start >= 0 else None
            end = raw_end if isinstance(raw_end, int) and raw_end >= 0 else None

        citations.append(
            SearchCitation(
                index=len(citations) + 1,
                source_index=mapped_source_index,
                start=start,
                end=end,
            )
        )

    raw_suggestions = None
    search_entry_point = payload.get("search_entry_point")
    if isinstance(search_entry_point, Mapping):
        raw_suggestions = search_entry_point.get("rendered_content")

    suggestion_items = extract_search_suggestions(
        raw_suggestions if isinstance(raw_suggestions, str) else None,
        max_items=max_suggestions,
    )
    suggestions = (
        SearchSuggestions(trusted=True, items=suggestion_items)
        if suggestion_items
        else None
    )

    raw_queries = payload.get("web_search_queries", [])
    web_search_queries = [
        str(query).strip()[:512]
        for query in raw_queries[:max_queries]
        if isinstance(query, str) and query.strip() and not looks_sensitive_text(query)
    ]

    google_grounded = bool(sources and citations)
    if not google_grounded:
        suggestions = None

    return SearchGroundingEvidence(
        google_grounded=google_grounded,
        sources=sources,
        citations=citations,
        suggestions=suggestions,
        web_search_queries=web_search_queries,
    )


def grounding_to_search_result(
    reply: SearchWorkerReply,
    grounding_metadata: Any,
    *,
    max_output_chars: int,
) -> SearchWorkerResult:
    answer_markdown = reply.answer_markdown.strip()[:max_output_chars].strip()
    if not answer_markdown:
        answer_markdown = "Không thể tạo phản hồi tìm kiếm hợp lệ."

    evidence = normalize_grounding_evidence(grounding_metadata)
    if not evidence.google_grounded:
        return SearchWorkerResult(
            state="missing_grounding",
            answer_markdown=answer_markdown,
            google_grounded=False,
            tool_executed=True,
            web_search_queries=evidence.web_search_queries,
            output_summary="missing_grounding",
        )

    return SearchWorkerResult(
        state="grounded",
        answer_markdown=answer_markdown,
        google_grounded=True,
        tool_executed=True,
        sources=evidence.sources,
        citations=evidence.citations,
        suggestions=evidence.suggestions,
        web_search_queries=evidence.web_search_queries,
        output_summary="grounded",
    )

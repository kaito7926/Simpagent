from __future__ import annotations

from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

SEARCH_DENIED_COPY = (
    "Yêu cầu này không được phép dùng Google Search. Không có lượt tìm kiếm nào được thực hiện."
)
SEARCH_UNAVAILABLE_COPY = (
    "Gemini Google Search chưa sẵn sàng cho lượt này. Hãy thử lại tìm kiếm hoặc chuyển sang câu hỏi bình thường."
)
SEARCH_PROVIDER_FAILED_COPY = (
    "Không thể hoàn tất lượt tìm kiếm này từ dịch vụ tìm kiếm. Hãy thử lại tìm kiếm hoặc chuyển sang câu hỏi bình thường."
)
SEARCH_TIMEOUT_COPY = (
    "Không nhận được kết quả từ Google Search trong thời gian cho phép. Hãy thử lại tìm kiếm hoặc chuyển sang câu hỏi bình thường."
)
SEARCH_MISSING_GROUNDING_NOTE = (
    "Kết quả này có thể tham khảo vì chưa có nguồn xác thực rõ ràng."
)


TurnMode = Literal["direct_chat", "google_search"]
SearchResponseState = Literal[
    "grounded",
    "missing_grounding",
    "denied",
    "search_unavailable",
    "provider_failed",
    "timeout",
]


class SearchSource(BaseModel):
    model_config = ConfigDict(extra="forbid")

    index: int = Field(ge=1)
    title: str = Field(min_length=1, max_length=500)
    domain: str = Field(min_length=1, max_length=255)
    uri: str | None = Field(default=None, max_length=2048)


class SearchCitation(BaseModel):
    model_config = ConfigDict(extra="forbid")

    index: int = Field(ge=1)
    source_index: int = Field(ge=1)
    start: int | None = Field(default=None, ge=0)
    end: int | None = Field(default=None, ge=0)


class SearchSuggestions(BaseModel):
    model_config = ConfigDict(extra="forbid")

    trusted: bool = True
    items: list[str] = Field(default_factory=list, max_length=8)


class SearchWorkerResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    state: SearchResponseState
    answer_markdown: str = Field(min_length=1, max_length=4000)
    google_grounded: bool = False
    tool_executed: bool = True
    sources: list[SearchSource] = Field(default_factory=list)
    citations: list[SearchCitation] = Field(default_factory=list)
    suggestions: SearchSuggestions | None = None
    web_search_queries: list[str] = Field(default_factory=list, max_length=8)
    output_summary: str | None = Field(default=None, max_length=4000)


class SearchTurnResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    mode: Literal["google_search"] = "google_search"
    state: SearchResponseState
    google_grounded: bool = False
    tool_executed: bool = False
    correlation_id: str | None = Field(default=None, max_length=64)
    sources: list[SearchSource] = Field(default_factory=list)
    citations: list[SearchCitation] = Field(default_factory=list)
    suggestions: SearchSuggestions | None = None
    retry_of_message_id: UUID | None = None

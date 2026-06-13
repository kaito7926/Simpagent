from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.search import SearchCitation, SearchSource, SearchSuggestions


class SearchWorkerReply(BaseModel):
    model_config = ConfigDict(extra="forbid")

    answer_markdown: str = Field(min_length=1, max_length=4000)
    query_used: str = Field(min_length=1, max_length=2048)


class SearchGroundingEvidence(BaseModel):
    model_config = ConfigDict(extra="forbid")

    google_grounded: bool = False
    sources: list[SearchSource] = Field(default_factory=list)
    citations: list[SearchCitation] = Field(default_factory=list)
    suggestions: SearchSuggestions | None = None
    web_search_queries: list[str] = Field(default_factory=list, max_length=8)

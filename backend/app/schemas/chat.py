from __future__ import annotations

from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator


MessageRole = Literal["system", "user", "assistant", "tool"]
MessageStatus = Literal["pending", "completed", "failed"]


class ChatMessageCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    client_message_id: str = Field(min_length=1, max_length=128)
    content: str = Field(min_length=1, max_length=20_000)


class ConversationCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str | None = Field(default=None, min_length=1, max_length=255)
    initial_message: ChatMessageCreateRequest | None = None

    @model_validator(mode="after")
    def require_title_or_initial_message(self) -> "ConversationCreateRequest":
        if self.title is None and self.initial_message is None:
            raise ValueError("Either title or initial_message is required.")
        return self


class ChatMessageResponse(BaseModel):
    id: UUID
    conversation_id: UUID
    sequence_no: int
    client_message_id: str | None
    role: MessageRole
    status: MessageStatus
    content: str
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime


class ConversationSummary(BaseModel):
    id: UUID
    owner_id: UUID
    title: str | None
    message_count: int
    state_label: str | None = None
    created_at: datetime
    updated_at: datetime


class ConversationDetail(ConversationSummary):
    messages: list[ChatMessageResponse] = Field(default_factory=list)


class ConversationPage(BaseModel):
    items: list[ConversationSummary]
    next_cursor: str | None = None

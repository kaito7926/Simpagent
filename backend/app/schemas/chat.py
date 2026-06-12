from __future__ import annotations

from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


MessageRole = Literal["system", "user", "assistant", "tool"]
MessageStatus = Literal["pending", "completed", "failed"]


class ConversationCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str = Field(min_length=1, max_length=255)


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
    created_at: datetime
    updated_at: datetime


class ConversationDetail(ConversationSummary):
    messages: list[ChatMessageResponse] = Field(default_factory=list)


class ConversationPage(BaseModel):
    items: list[ConversationSummary]
    next_cursor: str | None = None

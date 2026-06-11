from __future__ import annotations

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.search import SearchTurnResult, TurnMode


class SubmitTurnRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    mode: TurnMode
    prompt: str = Field(min_length=1, max_length=4000)
    retry_of_message_id: UUID | None = None


class MessageResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: UUID
    conversation_id: UUID
    sequence_no: int
    role: Literal["user", "assistant", "tool"]
    content: str
    created_at: datetime
    search: SearchTurnResult | None = None


class ToolExecutionResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: UUID
    tool_name: str
    status: str
    correlation_id: str | None = None
    duration_ms: int | None = None


class SubmitTurnResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    conversation_id: UUID
    mode: TurnMode
    user_message: MessageResponse
    assistant_message: MessageResponse
    tool_execution: ToolExecutionResponse | None = None

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal


ChatRole = Literal["user", "assistant"]


@dataclass(frozen=True, slots=True)
class ChatTurn:
    role: ChatRole
    content: str


@dataclass(frozen=True, slots=True)
class ChatCompletionResult:
    content: str
    provider_request_id: str | None
    prompt_tokens: int | None
    completion_tokens: int | None
    finish_reason: str | None

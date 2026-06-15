from __future__ import annotations

from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator


class AdminPage(BaseModel):
    model_config = ConfigDict(extra="forbid")

    limit: int = Field(ge=1, le=100)
    offset: int = Field(ge=0)
    has_more: bool
    next_offset: int | None = Field(default=None, ge=0)


class AdminUserItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: UUID
    email: str
    role: str
    scopes: list[str]
    is_active: bool
    is_demo: bool
    created_at: datetime
    updated_at: datetime


class AdminUserUpdateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    role: Literal["user", "admin"] | None = None
    is_active: bool | None = None

    @model_validator(mode="after")
    def validate_non_empty_change(self) -> "AdminUserUpdateRequest":
        if self.role is None and self.is_active is None:
            raise ValueError("At least one administrative change is required.")
        return self


class AdminUserUpdateResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    user: AdminUserItem
    changed_fields: list[str]


class GuardrailToggleRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    enabled: bool


class OrchestrationSettingsResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    guardrail_safety_enabled: bool
    trusted_supervisor_enabled: bool


class AdminUsersPage(BaseModel):
    model_config = ConfigDict(extra="forbid")

    items: list[AdminUserItem]
    page: AdminPage


class SecurityEventItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: UUID
    event_type: str
    severity: str
    user_id: UUID | None = None
    description: str
    correlation_id: str | None = None
    metadata: dict[str, Any]
    created_at: datetime


class SecurityEventsPage(BaseModel):
    model_config = ConfigDict(extra="forbid")

    items: list[SecurityEventItem]
    page: AdminPage


class ToolExecutionItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: UUID
    user_id: UUID
    conversation_id: UUID | None = None
    tool_name: str
    input_summary: str
    output_summary: str | None = None
    status: str
    duration_ms: int | None = None
    correlation_id: str | None = None
    created_at: datetime


class ToolExecutionsPage(BaseModel):
    model_config = ConfigDict(extra="forbid")

    items: list[ToolExecutionItem]
    page: AdminPage


class AdminMetricsResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    generated_at: datetime
    users_total: int = Field(ge=0)
    users_active: int = Field(ge=0)
    security_events_total: int = Field(ge=0)
    security_events_last_24h: int = Field(ge=0)
    tool_executions_total: int = Field(ge=0)
    tool_executions_last_24h: int = Field(ge=0)

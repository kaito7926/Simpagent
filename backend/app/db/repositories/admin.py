from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.account import User
from app.models.domain import ToolExecution
from app.models.evidence import SecurityEvent


@dataclass(frozen=True, slots=True)
class AdminUserRecord:
    id: UUID
    email: str
    role: str
    scopes: list[str]
    is_active: bool
    is_demo: bool
    created_at: datetime
    updated_at: datetime


@dataclass(frozen=True, slots=True)
class SecurityEventRecord:
    id: UUID
    event_type: str
    severity: str
    user_id: UUID | None
    description: str
    correlation_id: str | None
    metadata: dict
    created_at: datetime


@dataclass(frozen=True, slots=True)
class ToolExecutionRecord:
    id: UUID
    user_id: UUID
    conversation_id: UUID | None
    tool_name: str
    input_summary: str
    output_summary: str | None
    status: str
    duration_ms: int | None
    correlation_id: str | None
    created_at: datetime


@dataclass(frozen=True, slots=True)
class AdminMetricsRecord:
    users_total: int
    users_active: int
    security_events_total: int
    security_events_last_24h: int
    tool_executions_total: int
    tool_executions_last_24h: int
    correlation_references_total: int
    rate_limit_events_total: int


class AdminEvidenceRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def list_users(self, *, limit: int, offset: int) -> tuple[list[AdminUserRecord], bool]:
        stmt = (
            select(User)
            .options(selectinload(User.scopes))
            .order_by(User.created_at.desc(), User.id.desc())
            .offset(offset)
            .limit(limit + 1)
        )
        result = await self.session.execute(stmt)
        users = list(result.scalars().unique())
        has_more = len(users) > limit
        records = [
            AdminUserRecord(
                id=user.id,
                email=user.email,
                role=user.role,
                scopes=sorted(scope.scope for scope in user.scopes),
                is_active=user.is_active,
                is_demo=user.is_demo,
                created_at=user.created_at,
                updated_at=user.updated_at,
            )
            for user in users[:limit]
        ]
        return records, has_more

    async def list_security_events(self, *, limit: int, offset: int) -> tuple[list[SecurityEventRecord], bool]:
        stmt = (
            select(SecurityEvent)
            .order_by(SecurityEvent.created_at.desc(), SecurityEvent.id.desc())
            .offset(offset)
            .limit(limit + 1)
        )
        result = await self.session.execute(stmt)
        events = list(result.scalars())
        has_more = len(events) > limit
        records = [
            SecurityEventRecord(
                id=event.id,
                event_type=event.event_type,
                severity=event.severity,
                user_id=event.user_id,
                description=event.description,
                correlation_id=event.correlation_id,
                metadata=event.event_metadata,
                created_at=event.created_at,
            )
            for event in events[:limit]
        ]
        return records, has_more

    async def list_tool_executions(self, *, limit: int, offset: int) -> tuple[list[ToolExecutionRecord], bool]:
        stmt = (
            select(ToolExecution)
            .order_by(ToolExecution.created_at.desc(), ToolExecution.id.desc())
            .offset(offset)
            .limit(limit + 1)
        )
        result = await self.session.execute(stmt)
        executions = list(result.scalars())
        has_more = len(executions) > limit
        records = [
            ToolExecutionRecord(
                id=execution.id,
                user_id=execution.user_id,
                conversation_id=execution.conversation_id,
                tool_name=execution.tool_name,
                input_summary=execution.input_summary,
                output_summary=execution.output_summary,
                status=execution.status,
                duration_ms=execution.duration_ms,
                correlation_id=execution.correlation_id,
                created_at=execution.created_at,
            )
            for execution in executions[:limit]
        ]
        return records, has_more

    async def get_metrics(self, *, since: datetime) -> AdminMetricsRecord:
        users_total = int((await self.session.execute(select(func.count()).select_from(User))).scalar_one())
        users_active = int(
            (
                await self.session.execute(
                    select(func.count()).select_from(User).where(User.is_active.is_(True))
                )
            ).scalar_one()
        )
        security_events_total = int(
            (await self.session.execute(select(func.count()).select_from(SecurityEvent))).scalar_one()
        )
        security_events_last_24h = int(
            (
                await self.session.execute(
                    select(func.count())
                    .select_from(SecurityEvent)
                    .where(SecurityEvent.created_at >= since)
                )
            ).scalar_one()
        )
        tool_executions_total = int(
            (await self.session.execute(select(func.count()).select_from(ToolExecution))).scalar_one()
        )
        tool_executions_last_24h = int(
            (
                await self.session.execute(
                    select(func.count())
                    .select_from(ToolExecution)
                    .where(ToolExecution.created_at >= since)
                )
            ).scalar_one()
        )
        security_event_correlation_refs = int(
            (
                await self.session.execute(
                    select(func.count(SecurityEvent.correlation_id)).select_from(SecurityEvent)
                )
            ).scalar_one()
        )
        tool_execution_correlation_refs = int(
            (
                await self.session.execute(
                    select(func.count(ToolExecution.correlation_id)).select_from(ToolExecution)
                )
            ).scalar_one()
        )
        rate_limit_events_total = int(
            (
                await self.session.execute(
                    select(func.count())
                    .select_from(SecurityEvent)
                    .where(
                        SecurityEvent.event_type.in_(
                            (
                                "gateway_rate_limited",
                                "rate_limit_exceeded",
                                "admin_rate_limited",
                            )
                        )
                    )
                )
            ).scalar_one()
        )
        return AdminMetricsRecord(
            users_total=users_total,
            users_active=users_active,
            security_events_total=security_events_total,
            security_events_last_24h=security_events_last_24h,
            tool_executions_total=tool_executions_total,
            tool_executions_last_24h=tool_executions_last_24h,
            correlation_references_total=security_event_correlation_refs + tool_execution_correlation_refs,
            rate_limit_events_total=rate_limit_events_total,
        )

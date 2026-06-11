from __future__ import annotations

import logging
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.domain import Conversation, Message, ToolExecution


class ConversationsRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_conversation_for_update(self, *, conversation_id: UUID) -> Conversation | None:
        stmt = select(Conversation).where(Conversation.id == conversation_id).with_for_update()
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_owned_conversation_for_update(self, *, conversation_id: UUID, user_id: UUID) -> Conversation | None:
        stmt = (
            select(Conversation)
            .where(
                Conversation.id == conversation_id,
                Conversation.user_id == user_id,
                Conversation.deleted_at.is_(None),
            )
            .with_for_update()
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def create_conversation(
        self,
        *,
        conversation_id: UUID,
        user_id: UUID,
        title: str | None,
    ) -> Conversation:
        conversation = Conversation(id=conversation_id, user_id=user_id, title=title)
        self.session.add(conversation)
        await self.session.flush()
        return conversation

    async def next_sequence_no(self, *, conversation_id: UUID) -> int:
        stmt = select(func.coalesce(func.max(Message.sequence_no), 0) + 1).where(Message.conversation_id == conversation_id)
        result = await self.session.execute(stmt)
        return int(result.scalar_one())

    async def add_message(
        self,
        *,
        conversation_id: UUID,
        sequence_no: int,
        role: str,
        content: str,
        metadata: dict | None = None,
    ) -> Message:
        message = Message(
            conversation_id=conversation_id,
            sequence_no=sequence_no,
            role=role,
            content=content,
            message_metadata=metadata or {},
        )
        self.session.add(message)
        await self.session.flush()
        return message

    async def get_message_for_update(self, *, conversation_id: UUID, message_id: UUID) -> Message | None:
        stmt = (
            select(Message)
            .where(
                Message.conversation_id == conversation_id,
                Message.id == message_id,
            )
            .with_for_update()
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_message_by_sequence_no(self, *, conversation_id: UUID, sequence_no: int) -> Message | None:
        stmt = select(Message).where(
            Message.conversation_id == conversation_id,
            Message.sequence_no == sequence_no,
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def update_message(
        self,
        message: Message,
        *,
        content: str,
        metadata: dict | None = None,
    ) -> Message:
        message.content = content
        message.message_metadata = metadata or {}
        await self.session.flush()
        return message

    async def add_tool_execution(
        self,
        *,
        user_id: UUID,
        conversation_id: UUID,
        tool_name: str,
        input_summary: str,
        output_summary: str | None,
        status: str,
        duration_ms: int | None,
        correlation_id: str | None,
    ) -> ToolExecution:
        execution = ToolExecution(
            user_id=user_id,
            conversation_id=conversation_id,
            tool_name=tool_name,
            input_summary=input_summary,
            output_summary=output_summary,
            status=status,
            duration_ms=duration_ms,
            correlation_id=correlation_id,
        )
        self.session.add(execution)
        await self.session.flush()
        logging.getLogger("simpagent.tool").info(
            "tool_execution_recorded",
            extra={
                "event": "tool_execution",
                "tool_name": tool_name,
                "status": status,
                "user_id": str(user_id),
                "conversation_id": str(conversation_id),
                "duration_ms": duration_ms,
                "correlation_id": correlation_id,
            },
        )
        return execution

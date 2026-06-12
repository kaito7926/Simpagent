from __future__ import annotations

import base64
import json
from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from sqlalchemy import Select, and_, func, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.domain import Conversation, Message


@dataclass(slots=True)
class ConversationListRow:
    conversation: Conversation
    message_count: int


@dataclass(slots=True)
class ConversationDetailRow:
    conversation: Conversation
    messages: list[Message]
    message_count: int


@dataclass(frozen=True, slots=True)
class ConversationCursor:
    updated_at: datetime
    conversation_id: UUID


class InvalidConversationCursor(ValueError):
    pass


def encode_cursor(row: ConversationListRow) -> str:
    payload = {
        "updated_at": row.conversation.updated_at.isoformat(),
        "id": str(row.conversation.id),
    }
    raw = json.dumps(payload, separators=(",", ":")).encode("utf-8")
    return base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")


def decode_cursor(cursor: str) -> ConversationCursor:
    try:
        padded = cursor + ("=" * (-len(cursor) % 4))
        payload = json.loads(base64.urlsafe_b64decode(padded.encode("ascii")).decode("utf-8"))
        return ConversationCursor(updated_at=datetime.fromisoformat(payload["updated_at"]), conversation_id=UUID(payload["id"]))
    except (KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
        raise InvalidConversationCursor("Invalid conversation cursor") from exc


class ConversationsRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(self, *, user_id: UUID, title: str) -> Conversation:
        conversation = Conversation(user_id=user_id, title=title)
        self.session.add(conversation)
        await self.session.flush()
        await self.session.refresh(conversation)
        return conversation

    async def list_owned(
        self,
        *,
        user_id: UUID,
        limit: int,
        cursor: ConversationCursor | None,
    ) -> tuple[list[ConversationListRow], str | None]:
        message_counts = (
            select(Message.conversation_id, func.count(Message.id).label("message_count"))
            .group_by(Message.conversation_id)
            .subquery()
        )
        stmt: Select[tuple[Conversation, int]] = (
            select(Conversation, func.coalesce(message_counts.c.message_count, 0))
            .outerjoin(message_counts, message_counts.c.conversation_id == Conversation.id)
            .where(Conversation.user_id == user_id, Conversation.deleted_at.is_(None))
            .order_by(Conversation.updated_at.desc(), Conversation.id.desc())
            .limit(limit + 1)
        )
        if cursor is not None:
            stmt = stmt.where(
                or_(
                    Conversation.updated_at < cursor.updated_at,
                    and_(Conversation.updated_at == cursor.updated_at, Conversation.id < cursor.conversation_id),
                )
            )
        result = await self.session.execute(stmt)
        rows = [ConversationListRow(conversation=conversation, message_count=int(message_count)) for conversation, message_count in result.all()]
        page = rows[:limit]
        next_cursor = encode_cursor(page[-1]) if len(rows) > limit and page else None
        return page, next_cursor

    async def get_owned(self, *, user_id: UUID, conversation_id: UUID) -> ConversationDetailRow | None:
        conversation_stmt = select(Conversation).where(
            Conversation.id == conversation_id,
            Conversation.user_id == user_id,
            Conversation.deleted_at.is_(None),
        )
        conversation = await self.session.scalar(conversation_stmt)
        if conversation is None:
            return None
        messages_stmt = (
            select(Message)
            .join(Conversation, Conversation.id == Message.conversation_id)
            .where(
                Conversation.id == conversation_id,
                Conversation.user_id == user_id,
                Conversation.deleted_at.is_(None),
            )
            .order_by(Message.sequence_no.asc())
        )
        messages = list((await self.session.scalars(messages_stmt)).all())
        return ConversationDetailRow(conversation=conversation, messages=messages, message_count=len(messages))

    async def soft_delete_owned(self, *, user_id: UUID, conversation_id: UUID) -> bool:
        stmt = (
            update(Conversation)
            .where(
                Conversation.id == conversation_id,
                Conversation.user_id == user_id,
                Conversation.deleted_at.is_(None),
            )
            .values(deleted_at=func.now())
        )
        result = await self.session.execute(stmt)
        await self.session.flush()
        return bool(result.rowcount)

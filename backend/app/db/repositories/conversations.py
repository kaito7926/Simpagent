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
    state_label: str | None = None


@dataclass(slots=True)
class ConversationDetailRow:
    conversation: Conversation
    messages: list[Message]
    message_count: int


@dataclass(slots=True)
class PreparedTurn:
    conversation: Conversation
    user_message: Message
    assistant_message: Message
    provider_messages: list[Message]


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

    async def lock_owned(self, *, user_id: UUID, conversation_id: UUID) -> Conversation | None:
        stmt = (
            select(Conversation)
            .where(
                Conversation.id == conversation_id,
                Conversation.user_id == user_id,
                Conversation.deleted_at.is_(None),
            )
            .with_for_update()
        )
        return await self.session.scalar(stmt)

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
        rows = [
            ConversationListRow(conversation=conversation, message_count=int(message_count))
            for conversation, message_count in result.all()
        ]
        page = rows[:limit]
        await self._hydrate_state_labels(page)
        next_cursor = encode_cursor(page[-1]) if len(rows) > limit and page else None
        return page, next_cursor

    async def _hydrate_state_labels(self, rows: list[ConversationListRow]) -> None:
        if not rows:
            return
        conversation_ids = [row.conversation.id for row in rows]
        stmt = select(Message.conversation_id, Message.status, Message.message_metadata).where(
            Message.conversation_id.in_(conversation_ids),
            Message.role == "assistant",
            Message.status.in_(("pending", "failed")),
        )
        result = await self.session.execute(stmt)
        labels: dict[UUID, str] = {}
        for conversation_id, status, metadata in result.all():
            if status == "pending":
                labels[conversation_id] = "Pending reply"
            elif status == "failed" and labels.get(conversation_id) != "Pending reply":
                if isinstance(metadata, dict) and metadata.get("retryable") is True:
                    labels[conversation_id] = "Retry available"
        for row in rows:
            row.state_label = labels.get(row.conversation.id)

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

    async def get_existing_user_message(
        self,
        *,
        conversation_id: UUID,
        client_message_id: str,
    ) -> Message | None:
        stmt = select(Message).where(
            Message.conversation_id == conversation_id,
            Message.client_message_id == client_message_id,
            Message.role == "user",
        )
        return await self.session.scalar(stmt)

    async def get_paired_assistant_message(self, *, user_message: Message) -> Message | None:
        stmt = select(Message).where(
            Message.conversation_id == user_message.conversation_id,
            Message.sequence_no == user_message.sequence_no + 1,
            Message.role == "assistant",
        )
        return await self.session.scalar(stmt)

    async def get_pending_assistant(self, *, conversation_id: UUID) -> Message | None:
        stmt = (
            select(Message)
            .where(
                Message.conversation_id == conversation_id,
                Message.role == "assistant",
                Message.status == "pending",
            )
            .order_by(Message.sequence_no.asc())
            .limit(1)
        )
        return await self.session.scalar(stmt)

    async def next_sequence_no(self, *, conversation_id: UUID) -> int:
        current_max = await self.session.scalar(
            select(func.max(Message.sequence_no)).where(Message.conversation_id == conversation_id)
        )
        return int(current_max or 0) + 1

    async def create_user_message(
        self,
        *,
        conversation_id: UUID,
        sequence_no: int,
        client_message_id: str,
        content: str,
    ) -> Message:
        message = Message(
            conversation_id=conversation_id,
            sequence_no=sequence_no,
            client_message_id=client_message_id,
            role="user",
            status="completed",
            content=content,
            message_metadata={},
        )
        self.session.add(message)
        await self.session.flush()
        await self.session.refresh(message)
        return message

    async def create_pending_assistant_message(self, *, conversation_id: UUID, sequence_no: int) -> Message:
        message = Message(
            conversation_id=conversation_id,
            sequence_no=sequence_no,
            role="assistant",
            status="pending",
            content="",
            message_metadata={},
        )
        self.session.add(message)
        await self.session.flush()
        await self.session.refresh(message)
        return message

    async def provider_context(
        self,
        *,
        conversation_id: UUID,
        through_sequence_no: int,
    ) -> list[Message]:
        stmt = (
            select(Message)
            .where(
                Message.conversation_id == conversation_id,
                Message.sequence_no <= through_sequence_no,
                Message.role.in_(("user", "assistant")),
                Message.status == "completed",
            )
            .order_by(Message.sequence_no.asc())
        )
        return list((await self.session.scalars(stmt)).all())

    async def complete_assistant_message(
        self,
        *,
        assistant_message_id: UUID,
        content: str,
        metadata: dict,
    ) -> None:
        stmt = (
            update(Message)
            .where(Message.id == assistant_message_id, Message.role == "assistant")
            .values(status="completed", content=content, message_metadata=metadata)
        )
        await self.session.execute(stmt)
        await self.session.flush()

    async def fail_assistant_message(
        self,
        *,
        assistant_message_id: UUID,
        metadata: dict,
    ) -> None:
        stmt = (
            update(Message)
            .where(Message.id == assistant_message_id, Message.role == "assistant")
            .values(status="failed", content="", message_metadata=metadata)
        )
        await self.session.execute(stmt)
        await self.session.flush()

    async def reset_assistant_message_pending(self, *, assistant_message_id: UUID) -> None:
        stmt = (
            update(Message)
            .where(Message.id == assistant_message_id, Message.role == "assistant")
            .values(status="pending", content="", message_metadata={})
        )
        await self.session.execute(stmt)
        await self.session.flush()

    async def touch_conversation(self, *, conversation_id: UUID) -> None:
        stmt = update(Conversation).where(Conversation.id == conversation_id).values(updated_at=func.now())
        await self.session.execute(stmt)
        await self.session.flush()

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

    async def undo_soft_delete_owned(
        self,
        *,
        user_id: UUID,
        conversation_id: UUID,
        deleted_since: datetime,
    ) -> Conversation | None:
        stmt = (
            update(Conversation)
            .where(
                Conversation.id == conversation_id,
                Conversation.user_id == user_id,
                Conversation.deleted_at.is_not(None),
                Conversation.deleted_at >= deleted_since,
            )
            .values(deleted_at=None, updated_at=func.now())
            .returning(Conversation)
        )
        restored = await self.session.scalar(stmt)
        await self.session.flush()
        return restored

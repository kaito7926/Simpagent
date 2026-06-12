from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.repositories.conversations import (
    ConversationDetailRow,
    ConversationListRow,
    ConversationsRepository,
    InvalidConversationCursor,
    decode_cursor,
)


class ConversationNotFoundError(ValueError):
    pass


@dataclass(slots=True)
class ConversationPageResult:
    rows: list[ConversationListRow]
    next_cursor: str | None


class ChatService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.conversations = ConversationsRepository(session)

    async def create_conversation(self, *, user_id: UUID, title: str):
        conversation = await self.conversations.create(user_id=user_id, title=title)
        await self.session.commit()
        return conversation

    async def list_conversations(self, *, user_id: UUID, limit: int, cursor: str | None) -> ConversationPageResult:
        decoded = decode_cursor(cursor) if cursor else None
        rows, next_cursor = await self.conversations.list_owned(user_id=user_id, limit=limit, cursor=decoded)
        return ConversationPageResult(rows=rows, next_cursor=next_cursor)

    async def get_conversation(self, *, user_id: UUID, conversation_id: UUID) -> ConversationDetailRow:
        row = await self.conversations.get_owned(user_id=user_id, conversation_id=conversation_id)
        if row is None:
            raise ConversationNotFoundError("Conversation not found")
        return row

    async def delete_conversation(self, *, user_id: UUID, conversation_id: UUID) -> None:
        deleted = await self.conversations.soft_delete_owned(user_id=user_id, conversation_id=conversation_id)
        if not deleted:
            await self.session.rollback()
            raise ConversationNotFoundError("Conversation not found")
        await self.session.commit()


__all__ = ["ChatService", "ConversationNotFoundError", "InvalidConversationCursor"]

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.chat_adapter import ChatProviderError
from app.ai.schemas import ChatCompletionResult, ChatTurn
from app.db.repositories.conversations import (
    ConversationDetailRow,
    ConversationListRow,
    ConversationsRepository,
    InvalidConversationCursor,
    decode_cursor,
)


class ConversationNotFoundError(ValueError):
    pass


class TurnInProgressError(RuntimeError):
    pass


class TurnNotRetryableError(RuntimeError):
    pass


class ProviderTurnFailedError(RuntimeError):
    def __init__(self, provider_error: ChatProviderError) -> None:
        super().__init__(provider_error.code)
        self.provider_error = provider_error


@dataclass(slots=True)
class ConversationPageResult:
    rows: list[ConversationListRow]
    next_cursor: str | None


@dataclass(slots=True)
class PreparedProviderTurn:
    conversation_id: UUID
    assistant_message_id: UUID
    messages: list[ChatTurn]


class ChatService:
    UNDO_DELETE_WINDOW_SECONDS = 6

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.conversations = ConversationsRepository(session)

    async def create_conversation(self, *, user_id: UUID, title: str):
        conversation = await self.conversations.create(user_id=user_id, title=title)
        await self.session.commit()
        return conversation

    async def create_conversation_with_initial_message(
        self,
        *,
        user_id: UUID,
        content: str,
        client_message_id: str,
        adapter,
        correlation_id: str | None,
    ) -> ConversationDetailRow:
        title = _title_from_message(content)
        try:
            conversation = await self.conversations.create(user_id=user_id, title=title)
            user_message = await self.conversations.create_user_message(
                conversation_id=conversation.id,
                sequence_no=1,
                client_message_id=client_message_id,
                content=content,
            )
            assistant_message = await self.conversations.create_pending_assistant_message(
                conversation_id=conversation.id,
                sequence_no=2,
            )
            await self.conversations.touch_conversation(conversation_id=conversation.id)
            prepared = PreparedProviderTurn(
                conversation_id=conversation.id,
                assistant_message_id=assistant_message.id,
                messages=[_chat_turn(user_message)],
            )
        except Exception:
            await self.session.rollback()
            raise
        await self.session.commit()

        await self._complete_provider_turn(adapter=adapter, prepared=prepared, correlation_id=correlation_id)
        return await self.get_conversation(user_id=user_id, conversation_id=prepared.conversation_id)

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

    async def undo_delete_conversation(self, *, user_id: UUID, conversation_id: UUID) -> ConversationDetailRow:
        deleted_since = datetime.now(UTC) - timedelta(seconds=self.UNDO_DELETE_WINDOW_SECONDS)
        restored = await self.conversations.undo_soft_delete_owned(
            user_id=user_id,
            conversation_id=conversation_id,
            deleted_since=deleted_since,
        )
        if restored is None:
            await self.session.rollback()
            raise ConversationNotFoundError("Conversation not found")
        await self.session.commit()
        return await self.get_conversation(user_id=user_id, conversation_id=conversation_id)

    async def send_message(
        self,
        *,
        user_id: UUID,
        conversation_id: UUID,
        content: str,
        client_message_id: str,
        adapter,
        correlation_id: str | None,
    ) -> ConversationDetailRow:
        try:
            conversation = await self.conversations.lock_owned(user_id=user_id, conversation_id=conversation_id)
            if conversation is None:
                raise ConversationNotFoundError("Conversation not found")

            existing_user = await self.conversations.get_existing_user_message(
                conversation_id=conversation_id,
                client_message_id=client_message_id,
            )
            if existing_user is not None:
                row = await self._detail_for_locked_conversation(user_id=user_id, conversation_id=conversation_id)
                await self.session.commit()
                return row

            pending = await self.conversations.get_pending_assistant(conversation_id=conversation_id)
            if pending is not None:
                raise TurnInProgressError("A turn is already pending")

            next_sequence = await self.conversations.next_sequence_no(conversation_id=conversation_id)
            user_message = await self.conversations.create_user_message(
                conversation_id=conversation_id,
                sequence_no=next_sequence,
                client_message_id=client_message_id,
                content=content,
            )
            assistant_message = await self.conversations.create_pending_assistant_message(
                conversation_id=conversation_id,
                sequence_no=next_sequence + 1,
            )
            await self.conversations.touch_conversation(conversation_id=conversation_id)
            provider_messages = await self.conversations.provider_context(
                conversation_id=conversation_id,
                through_sequence_no=user_message.sequence_no,
            )
            prepared = PreparedProviderTurn(
                conversation_id=conversation_id,
                assistant_message_id=assistant_message.id,
                messages=[_chat_turn(message) for message in provider_messages],
            )
        except Exception:
            await self.session.rollback()
            raise
        await self.session.commit()

        await self._complete_provider_turn(adapter=adapter, prepared=prepared, correlation_id=correlation_id)
        return await self.get_conversation(user_id=user_id, conversation_id=conversation_id)

    async def retry_message(
        self,
        *,
        user_id: UUID,
        conversation_id: UUID,
        client_message_id: str,
        adapter,
        correlation_id: str | None,
    ) -> ConversationDetailRow:
        try:
            conversation = await self.conversations.lock_owned(user_id=user_id, conversation_id=conversation_id)
            if conversation is None:
                raise ConversationNotFoundError("Conversation not found")

            user_message = await self.conversations.get_existing_user_message(
                conversation_id=conversation_id,
                client_message_id=client_message_id,
            )
            if user_message is None:
                raise ConversationNotFoundError("Conversation not found")

            assistant_message = await self.conversations.get_paired_assistant_message(user_message=user_message)
            if assistant_message is None:
                raise ConversationNotFoundError("Conversation not found")
            if assistant_message.status == "pending":
                raise TurnInProgressError("A turn is already pending")
            if assistant_message.status == "completed":
                row = await self._detail_for_locked_conversation(user_id=user_id, conversation_id=conversation_id)
                await self.session.commit()
                return row
            if assistant_message.status != "failed":
                raise TurnNotRetryableError("The turn cannot be retried")

            await self.conversations.reset_assistant_message_pending(assistant_message_id=assistant_message.id)
            await self.conversations.touch_conversation(conversation_id=conversation_id)
            provider_messages = await self.conversations.provider_context(
                conversation_id=conversation_id,
                through_sequence_no=user_message.sequence_no,
            )
            prepared = PreparedProviderTurn(
                conversation_id=conversation_id,
                assistant_message_id=assistant_message.id,
                messages=[_chat_turn(message) for message in provider_messages],
            )
        except Exception:
            await self.session.rollback()
            raise
        await self.session.commit()

        await self._complete_provider_turn(adapter=adapter, prepared=prepared, correlation_id=correlation_id)
        return await self.get_conversation(user_id=user_id, conversation_id=conversation_id)

    async def _complete_provider_turn(
        self,
        *,
        adapter,
        prepared: PreparedProviderTurn,
        correlation_id: str | None,
    ) -> None:
        try:
            provider = adapter() if callable(adapter) else adapter
            result: ChatCompletionResult = await provider.complete(messages=prepared.messages)
        except ChatProviderError as exc:
            metadata = {
                "error_code": exc.code,
                "provider_request_id": exc.provider_request_id,
                "retryable": exc.retryable,
                "correlation_id": correlation_id,
            }
            await self.conversations.fail_assistant_message(
                assistant_message_id=prepared.assistant_message_id,
                metadata=metadata,
            )
            await self.conversations.touch_conversation(conversation_id=prepared.conversation_id)
            await self.session.commit()
            raise ProviderTurnFailedError(exc) from exc

        metadata = {
            "provider_request_id": result.provider_request_id,
            "prompt_tokens": result.prompt_tokens,
            "completion_tokens": result.completion_tokens,
            "finish_reason": result.finish_reason,
        }
        await self.conversations.complete_assistant_message(
            assistant_message_id=prepared.assistant_message_id,
            content=result.content,
            metadata=metadata,
        )
        await self.conversations.touch_conversation(conversation_id=prepared.conversation_id)
        await self.session.commit()

    async def _detail_for_locked_conversation(self, *, user_id: UUID, conversation_id: UUID) -> ConversationDetailRow:
        row = await self.conversations.get_owned(user_id=user_id, conversation_id=conversation_id)
        if row is None:
            raise ConversationNotFoundError("Conversation not found")
        return row


def _chat_turn(message) -> ChatTurn:
    return ChatTurn(role=message.role, content=message.content)


def _title_from_message(content: str) -> str:
    title = " ".join(content.split())
    if len(title) <= 80:
        return title
    return f"{title[:77].rstrip()}..."


__all__ = [
    "ChatService",
    "ConversationNotFoundError",
    "InvalidConversationCursor",
    "ProviderTurnFailedError",
    "TurnInProgressError",
    "TurnNotRetryableError",
]

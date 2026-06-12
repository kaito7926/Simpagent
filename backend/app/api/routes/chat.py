from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.authorization.policy import PolicyResult, Scope, evaluate_required_scopes
from app.authorization.principal import AuthenticatedPrincipal, resolve_principal
from app.core.errors import ApiError
from app.db.repositories.conversations import ConversationDetailRow, ConversationListRow, InvalidConversationCursor
from app.db.session import get_session
from app.models.domain import Conversation, Message
from app.schemas.chat import (
    ChatMessageResponse,
    ConversationCreateRequest,
    ConversationDetail,
    ConversationPage,
    ConversationSummary,
)
from app.services.chat import ChatService, ConversationNotFoundError

router = APIRouter(prefix="/api/conversations", tags=["chat"])


def _require_scope(principal: AuthenticatedPrincipal, scope: Scope) -> None:
    result = evaluate_required_scopes(principal_scopes=set(principal.scopes), required={scope.value})
    if result is not PolicyResult.allow:
        raise ApiError(status_code=403, code="missing_scope", message="The authenticated principal lacks the required chat scope.")


def _message_response(message: Message) -> ChatMessageResponse:
    return ChatMessageResponse(
        id=message.id,
        conversation_id=message.conversation_id,
        sequence_no=message.sequence_no,
        client_message_id=message.client_message_id,
        role=message.role,
        status=message.status,
        content=message.content,
        metadata=message.message_metadata,
        created_at=message.created_at,
    )


def _summary(conversation: Conversation, *, message_count: int) -> ConversationSummary:
    return ConversationSummary(
        id=conversation.id,
        owner_id=conversation.user_id,
        title=conversation.title,
        message_count=message_count,
        created_at=conversation.created_at,
        updated_at=conversation.updated_at,
    )


def _summary_from_row(row: ConversationListRow) -> ConversationSummary:
    return _summary(row.conversation, message_count=row.message_count)


def _detail_from_row(row: ConversationDetailRow) -> ConversationDetail:
    return ConversationDetail(
        **_summary(row.conversation, message_count=row.message_count).model_dump(),
        messages=[_message_response(message) for message in row.messages],
    )


@router.post("", response_model=ConversationDetail, status_code=status.HTTP_201_CREATED)
async def create_conversation(
    payload: ConversationCreateRequest,
    principal: Annotated[AuthenticatedPrincipal, Depends(resolve_principal)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> ConversationDetail:
    _require_scope(principal, Scope.chat_write)
    service = ChatService(session)
    conversation = await service.create_conversation(user_id=principal.user_id, title=payload.title)
    return ConversationDetail(
        **_summary(conversation, message_count=0).model_dump(),
        messages=[],
    )


@router.get("", response_model=ConversationPage)
async def list_conversations(
    principal: Annotated[AuthenticatedPrincipal, Depends(resolve_principal)],
    session: Annotated[AsyncSession, Depends(get_session)],
    limit: Annotated[int, Query(ge=1, le=50)] = 20,
    cursor: Annotated[str | None, Query(min_length=1, max_length=512)] = None,
) -> ConversationPage:
    _require_scope(principal, Scope.chat_read)
    service = ChatService(session)
    try:
        page = await service.list_conversations(user_id=principal.user_id, limit=limit, cursor=cursor)
    except InvalidConversationCursor as exc:
        raise ApiError(status_code=400, code="invalid_cursor", message="The conversation cursor is invalid.") from exc
    return ConversationPage(items=[_summary_from_row(row) for row in page.rows], next_cursor=page.next_cursor)


@router.get("/{conversation_id}", response_model=ConversationDetail)
async def get_conversation(
    conversation_id: UUID,
    principal: Annotated[AuthenticatedPrincipal, Depends(resolve_principal)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> ConversationDetail:
    _require_scope(principal, Scope.chat_read)
    service = ChatService(session)
    try:
        row = await service.get_conversation(user_id=principal.user_id, conversation_id=conversation_id)
    except ConversationNotFoundError as exc:
        raise ApiError(status_code=404, code="conversation_not_found", message="Conversation not found.") from exc
    return _detail_from_row(row)


@router.delete("/{conversation_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_conversation(
    conversation_id: UUID,
    principal: Annotated[AuthenticatedPrincipal, Depends(resolve_principal)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> Response:
    _require_scope(principal, Scope.chat_write)
    service = ChatService(session)
    try:
        await service.delete_conversation(user_id=principal.user_id, conversation_id=conversation_id)
    except ConversationNotFoundError as exc:
        raise ApiError(status_code=404, code="conversation_not_found", message="Conversation not found.") from exc
    return Response(status_code=status.HTTP_204_NO_CONTENT)

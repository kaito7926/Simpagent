from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.agent.coordinator import ChatCoordinator
from app.ai.chat_adapter import OpenAIChatAdapter
from app.authorization.policy import PolicyResult, Scope, evaluate_required_scopes
from app.authorization.principal import AuthenticatedPrincipal, resolve_principal
from app.core.errors import ApiError
from app.db.repositories.conversations import ConversationDetailRow, ConversationListRow, InvalidConversationCursor
from app.db.session import get_session
from app.models.domain import Conversation, Message
from app.schemas.chat import (
    ChatMessageResponse,
    ChatMessageCreateRequest,
    ConversationCreateRequest,
    ConversationDetail,
    ConversationPage,
    ConversationSummary,
)
from app.services.chat import (
    ChatService,
    ConversationNotFoundError,
    ProviderTurnFailedError,
    TurnInProgressError,
    TurnNotRetryableError,
)

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
    summary = _summary(row.conversation, message_count=row.message_count)
    summary.state_label = row.state_label
    return summary


def _detail_from_row(row: ConversationDetailRow) -> ConversationDetail:
    return ConversationDetail(
        **_summary(row.conversation, message_count=row.message_count).model_dump(),
        messages=[_message_response(message) for message in row.messages],
    )


def _chat_adapter(request: Request):
    adapter = getattr(request.app.state, "chat_adapter", None)
    if adapter is not None:
        return adapter
    return OpenAIChatAdapter(settings=request.app.state.settings)


def _chat_coordinator(
    request: Request,
    *,
    session: AsyncSession,
    principal: AuthenticatedPrincipal,
) -> ChatCoordinator:
    factory = getattr(request.app.state, "chat_coordinator_factory", None)
    if factory is not None:
        return factory(request=request, session=session, principal=principal)
    resolved_search_status = getattr(request.app.state, "search_status", "unconfigured")
    if bool(getattr(request.app.state, "search_ready", False)):
        resolved_search_status = "ready"
    return ChatCoordinator(
        session,
        settings=request.app.state.settings,
        clock=request.app.state.clock,
        principal_scopes=set(principal.scopes),
        chat_adapter_factory=lambda: _chat_adapter(request),
        python_planner=getattr(request.app.state, "python_planner", None),
        python_client=getattr(request.app.state, "python_client", None),
        search_worker=getattr(request.app.state, "search_worker", None),
        search_status=str(resolved_search_status),
    )


def _provider_failed_error(exc: ProviderTurnFailedError) -> ApiError:
    provider_error = exc.provider_error
    return ApiError(
        status_code=502,
        code="provider_failed",
        message="The chat provider could not complete this turn. Retry if the error is retryable.",
        extra={
            "provider_error_code": provider_error.code,
            "retryable": provider_error.retryable,
        },
    )


@router.post("", response_model=ConversationDetail, status_code=status.HTTP_201_CREATED)
async def create_conversation(
    payload: ConversationCreateRequest,
    request: Request,
    principal: Annotated[AuthenticatedPrincipal, Depends(resolve_principal)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> ConversationDetail:
    _require_scope(principal, Scope.chat_write)
    service = ChatService(session)
    if payload.initial_message is not None:
        try:
            return _detail_from_row(
                await service.create_conversation_with_initial_message(
                    user_id=principal.user_id,
                    content=payload.initial_message.content,
                    client_message_id=payload.initial_message.client_message_id,
                    executor=lambda: _chat_coordinator(request, session=session, principal=principal),
                    correlation_id=getattr(request.state, "correlation_id", None),
                )
            )
        except ProviderTurnFailedError as exc:
            raise _provider_failed_error(exc) from exc
    conversation = await service.create_conversation(user_id=principal.user_id, title=payload.title or "New conversation")
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


@router.post("/{conversation_id}/messages", response_model=ConversationDetail)
async def send_message(
    conversation_id: UUID,
    payload: ChatMessageCreateRequest,
    request: Request,
    principal: Annotated[AuthenticatedPrincipal, Depends(resolve_principal)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> ConversationDetail:
    _require_scope(principal, Scope.chat_write)
    service = ChatService(session)
    try:
        row = await service.send_message(
            user_id=principal.user_id,
            conversation_id=conversation_id,
            content=payload.content,
            client_message_id=payload.client_message_id,
            executor=lambda: _chat_coordinator(request, session=session, principal=principal),
            correlation_id=getattr(request.state, "correlation_id", None),
        )
    except ConversationNotFoundError as exc:
        raise ApiError(status_code=404, code="conversation_not_found", message="Conversation not found.") from exc
    except TurnInProgressError as exc:
        raise ApiError(
            status_code=409,
            code="turn_in_progress",
            message="A response is already pending for this conversation.",
        ) from exc
    except ProviderTurnFailedError as exc:
        raise _provider_failed_error(exc) from exc
    return _detail_from_row(row)


@router.post("/{conversation_id}/messages/{client_message_id}/retry", response_model=ConversationDetail)
async def retry_message(
    conversation_id: UUID,
    client_message_id: str,
    request: Request,
    principal: Annotated[AuthenticatedPrincipal, Depends(resolve_principal)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> ConversationDetail:
    _require_scope(principal, Scope.chat_write)
    service = ChatService(session)
    try:
        row = await service.retry_message(
            user_id=principal.user_id,
            conversation_id=conversation_id,
            client_message_id=client_message_id,
            executor=lambda: _chat_coordinator(request, session=session, principal=principal),
            correlation_id=getattr(request.state, "correlation_id", None),
        )
    except ConversationNotFoundError as exc:
        raise ApiError(status_code=404, code="conversation_not_found", message="Conversation not found.") from exc
    except TurnInProgressError as exc:
        raise ApiError(
            status_code=409,
            code="turn_in_progress",
            message="A response is already pending for this conversation.",
        ) from exc
    except TurnNotRetryableError as exc:
        raise ApiError(
            status_code=409,
            code="turn_not_retryable",
            message="This message turn cannot be retried.",
        ) from exc
    except ProviderTurnFailedError as exc:
        raise _provider_failed_error(exc) from exc
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


@router.post("/{conversation_id}/undo-delete", response_model=ConversationSummary)
async def undo_delete_conversation(
    conversation_id: UUID,
    principal: Annotated[AuthenticatedPrincipal, Depends(resolve_principal)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> ConversationSummary:
    _require_scope(principal, Scope.chat_write)
    service = ChatService(session)
    try:
        row = await service.undo_delete_conversation(user_id=principal.user_id, conversation_id=conversation_id)
    except ConversationNotFoundError as exc:
        raise ApiError(status_code=404, code="conversation_not_found", message="Conversation not found.") from exc
    return _summary(row.conversation, message_count=row.message_count)

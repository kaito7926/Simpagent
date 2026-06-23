from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.authorization.principal import AuthenticatedPrincipal, resolve_principal
from app.core.errors import ApiError
from app.db.session import get_session
from app.schemas.chat import SubmitTurnRequest, SubmitTurnResponse
from app.services.chat_turns import ChatTurnsService, ConversationTurnForbidden, ConversationTurnNotFound

router = APIRouter(prefix="/api/conversations", tags=["conversations"])


@router.post("/{conversation_id}/turns", response_model=SubmitTurnResponse)
async def submit_turn(
    conversation_id: UUID,
    payload: SubmitTurnRequest,
    request: Request,
    principal: Annotated[AuthenticatedPrincipal, Depends(resolve_principal)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> SubmitTurnResponse:
    resolved_search_status = getattr(request.app.state, "search_status", "unconfigured")
    if bool(getattr(request.app.state, "search_ready", False)):
        resolved_search_status = "ready"
    service = ChatTurnsService(
        session,
        settings=request.app.state.settings,
        now=request.app.state.clock(),
        correlation_id=getattr(request.state, "correlation_id", None),
        search_provider=str(getattr(request.app.state, "search_provider", "gemini")),
        search_status=str(resolved_search_status),
        search_worker=getattr(request.app.state, "search_worker", None),
    )
    try:
        return await service.submit_turn(
            principal=principal,
            conversation_id=conversation_id,
            payload=payload,
        )
    except ConversationTurnForbidden as exc:
        raise ApiError(status_code=403, code="chat_forbidden", message="The principal cannot submit conversation turns.") from exc
    except ConversationTurnNotFound as exc:
        raise ApiError(status_code=404, code="conversation_not_found", message="Conversation not found.") from exc

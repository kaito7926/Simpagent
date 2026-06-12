from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Request
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.authorization.policy import PolicyResult, Scope, evaluate_required_scopes
from app.authorization.principal import AuthenticatedPrincipal, resolve_principal
from app.core.errors import ApiError
from app.db.session import get_session
from app.services.python_sessions import PythonSessionsService


router = APIRouter(prefix="/api/python", tags=["python"])

ARTIFACT_MEDIA_TYPES = {
    "csv": "text/csv; charset=utf-8",
    "json": "application/json",
    "png": "image/png",
    "txt": "text/plain; charset=utf-8",
}


def _require_chat_read(principal: AuthenticatedPrincipal) -> None:
    result = evaluate_required_scopes(principal_scopes=set(principal.scopes), required={Scope.chat_read.value})
    if result is not PolicyResult.allow:
        raise ApiError(
            status_code=403,
            code="missing_scope",
            message="The authenticated principal lacks the required chat scope.",
        )


@router.get("/artifacts/{artifact_id}")
async def download_python_artifact(
    artifact_id: UUID,
    request: Request,
    principal: Annotated[AuthenticatedPrincipal, Depends(resolve_principal)],
    session: Annotated[AsyncSession, Depends(get_session)],
):
    _require_chat_read(principal)
    service = PythonSessionsService(
        session,
        settings=request.app.state.settings,
        clock=request.app.state.clock,
    )
    candidate = await service.resolve_artifact_download(artifact_id=artifact_id, user_id=principal.user_id)
    if candidate is None:
        raise ApiError(
            status_code=404,
            code="python_artifact_not_found",
            message="Python artifact not found.",
        )
    if candidate.expired:
        raise ApiError(
            status_code=410,
            code="artifact_expired",
            message="This Python artifact has expired and is no longer available.",
        )
    if not candidate.path.exists():
        raise ApiError(
            status_code=404,
            code="python_artifact_not_found",
            message="Python artifact not found.",
        )
    return FileResponse(
        candidate.path,
        filename=candidate.record.name,
        media_type=ARTIFACT_MEDIA_TYPES.get(candidate.record.artifact_type, "application/octet-stream"),
    )

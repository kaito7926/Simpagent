from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.authorization.policy import PolicyResult
from app.authorization.principal import AuthenticatedPrincipal, resolve_principal
from app.core.errors import ApiError
from app.db.session import get_session
from app.schemas.admin import (
    AdminMetricsResponse,
    AdminUserUpdateRequest,
    AdminUserUpdateResponse,
    AdminUsersPage,
    GatewayEvidencePage,
    GuardrailToggleRequest,
    OrchestrationSettingsResponse,
    SecurityEventsPage,
    ToolExecutionsPage,
    WebsearchProviderOverrideRequest,
)
from app.services.admin_evidence import (
    AdminAccessDenied,
    AdminEvidenceService,
    AdminWriteRejected,
)

router = APIRouter(prefix="/api/admin", tags=["admin"])


def _admin_access_error(exc: AdminAccessDenied) -> ApiError:
    if exc.decision is PolicyResult.deny_role:
        return ApiError(
            status_code=403,
            code="admin_role_required",
            message="Administrator role is required for this action.",
        )
    if exc.decision is PolicyResult.deny_scope:
        return ApiError(
            status_code=403,
            code="admin_scope_required",
            message="The principal does not have the required admin scope.",
        )
    return ApiError(
        status_code=403,
        code="admin_access_denied",
        message="The principal cannot access this administrative resource.",
    )


def _service(request: Request, session: AsyncSession) -> AdminEvidenceService:
    return AdminEvidenceService(
        session,
        correlation_id=getattr(request.state, "correlation_id", None),
        now=request.app.state.clock(),
    )


def _admin_write_error(exc: AdminWriteRejected) -> ApiError:
    if exc.reason == "self_mutation_forbidden":
        return ApiError(
            status_code=403,
            code="admin_self_mutation_forbidden",
            message="Administrators cannot change their own administrative access through this endpoint.",
        )
    return ApiError(
        status_code=403,
        code="admin_write_denied",
        message="The administrative write action was denied.",
    )


@router.get("/users", response_model=AdminUsersPage)
async def list_users(
    request: Request,
    principal: Annotated[AuthenticatedPrincipal, Depends(resolve_principal)],
    session: Annotated[AsyncSession, Depends(get_session)],
    limit: Annotated[int, Query(ge=1, le=100)] = 25,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> AdminUsersPage:
    service = _service(request, session)
    try:
        return await service.list_users(principal=principal, limit=limit, offset=offset)
    except AdminAccessDenied as exc:
        raise _admin_access_error(exc) from exc


@router.get("/security-events", response_model=SecurityEventsPage)
async def list_security_events(
    request: Request,
    principal: Annotated[AuthenticatedPrincipal, Depends(resolve_principal)],
    session: Annotated[AsyncSession, Depends(get_session)],
    limit: Annotated[int, Query(ge=1, le=100)] = 25,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> SecurityEventsPage:
    service = _service(request, session)
    try:
        return await service.list_security_events(principal=principal, limit=limit, offset=offset)
    except AdminAccessDenied as exc:
        raise _admin_access_error(exc) from exc


@router.get("/tool-executions", response_model=ToolExecutionsPage)
async def list_tool_executions(
    request: Request,
    principal: Annotated[AuthenticatedPrincipal, Depends(resolve_principal)],
    session: Annotated[AsyncSession, Depends(get_session)],
    limit: Annotated[int, Query(ge=1, le=100)] = 25,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> ToolExecutionsPage:
    service = _service(request, session)
    try:
        return await service.list_tool_executions(principal=principal, limit=limit, offset=offset)
    except AdminAccessDenied as exc:
        raise _admin_access_error(exc) from exc


@router.get("/gateway-evidence", response_model=GatewayEvidencePage)
async def list_gateway_evidence(
    request: Request,
    principal: Annotated[AuthenticatedPrincipal, Depends(resolve_principal)],
    session: Annotated[AsyncSession, Depends(get_session)],
    limit: Annotated[int, Query(ge=1, le=100)] = 25,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> GatewayEvidencePage:
    service = _service(request, session)
    try:
        return await service.list_gateway_evidence(principal=principal, limit=limit, offset=offset)
    except AdminAccessDenied as exc:
        raise _admin_access_error(exc) from exc


@router.get("/metrics", response_model=AdminMetricsResponse)
async def get_metrics(
    request: Request,
    principal: Annotated[AuthenticatedPrincipal, Depends(resolve_principal)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> AdminMetricsResponse:
    service = _service(request, session)
    try:
        return await service.get_metrics(principal=principal)
    except AdminAccessDenied as exc:
        raise _admin_access_error(exc) from exc


@router.get("/orchestration", response_model=OrchestrationSettingsResponse)
async def get_orchestration_settings(
    request: Request,
    principal: Annotated[AuthenticatedPrincipal, Depends(resolve_principal)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> OrchestrationSettingsResponse:
    service = _service(request, session)
    try:
        return await service.get_orchestration_settings(
            principal=principal,
            default_guardrail_enabled=request.app.state.settings.guardrail_safety_enabled_default,
            default_websearch_provider=request.app.state.settings.websearch_provider,
            settings=request.app.state.settings,
        )
    except AdminAccessDenied as exc:
        raise _admin_access_error(exc) from exc


@router.patch("/orchestration/guardrail", response_model=OrchestrationSettingsResponse)
async def update_guardrail_safety(
    payload: GuardrailToggleRequest,
    request: Request,
    principal: Annotated[AuthenticatedPrincipal, Depends(resolve_principal)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> OrchestrationSettingsResponse:
    service = _service(request, session)
    try:
        return await service.set_guardrail_safety_enabled(
            principal=principal,
            enabled=payload.enabled,
            default_websearch_provider=request.app.state.settings.websearch_provider,
            settings=request.app.state.settings,
        )
    except AdminAccessDenied as exc:
        raise _admin_access_error(exc) from exc


@router.patch("/orchestration/websearch-provider", response_model=OrchestrationSettingsResponse)
async def update_websearch_provider_override(
    payload: WebsearchProviderOverrideRequest,
    request: Request,
    principal: Annotated[AuthenticatedPrincipal, Depends(resolve_principal)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> OrchestrationSettingsResponse:
    service = _service(request, session)
    try:
        return await service.set_websearch_provider_override(
            principal=principal,
            provider=payload.provider,
            default_guardrail_enabled=request.app.state.settings.guardrail_safety_enabled_default,
            default_websearch_provider=request.app.state.settings.websearch_provider,
            settings=request.app.state.settings,
        )
    except ValueError as exc:
        raise ApiError(
            status_code=422,
            code="invalid_websearch_provider",
            message=str(exc),
        ) from exc
    except AdminAccessDenied as exc:
        raise _admin_access_error(exc) from exc


@router.patch("/users/{user_id}", response_model=AdminUserUpdateResponse)
async def update_user_access(
    user_id: UUID,
    payload: AdminUserUpdateRequest,
    request: Request,
    principal: Annotated[AuthenticatedPrincipal, Depends(resolve_principal)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> AdminUserUpdateResponse:
    service = _service(request, session)
    try:
        return await service.update_user_access(
            principal=principal,
            target_user_id=user_id,
            role=payload.role,
            is_active=payload.is_active,
        )
    except AdminAccessDenied as exc:
        raise _admin_access_error(exc) from exc
    except AdminWriteRejected as exc:
        raise _admin_write_error(exc) from exc
    except LookupError as exc:
        raise ApiError(
            status_code=404,
            code="admin_user_not_found",
            message="The requested user could not be found.",
        ) from exc

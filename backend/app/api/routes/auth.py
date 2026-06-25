from __future__ import annotations

from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, Request, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.authorization.principal import AuthenticatedPrincipal, resolve_principal
from app.core.config import Settings
from app.core.errors import ApiError
from app.db.session import get_session
from app.schemas.auth import CurrentUserResponse, LoginRequest, RegisterAcceptedResponse, RegisterRequest, TokenResponse
from app.security.csrf import CsrfValidationError
from app.security.dpop import DPoPError, validate_dpop_request
from app.security.refresh_tokens import CSRF_COOKIE_NAME, REFRESH_COOKIE_NAME
from app.services.authentication import AuthenticationFailed, AuthenticationService
from app.services.registration import RegistrationInviteRejected, RegistrationService
from app.services.sessions import RefreshStatus, SessionsService

router = APIRouter(prefix="/api/auth", tags=["auth"])


def get_settings(request: Request) -> Settings:
    return request.app.state.settings


def get_now(request: Request) -> datetime:
    return request.app.state.clock()


def _set_auth_cookies(response: Response, *, settings: Settings, refresh_token: str, csrf_token: str, max_age: int) -> None:
    response.set_cookie(
        key=REFRESH_COOKIE_NAME,
        value=refresh_token,
        max_age=max_age,
        path="/",
        secure=settings.cookie_secure,
        httponly=True,
        samesite=settings.cookie_samesite,
    )
    response.set_cookie(
        key=CSRF_COOKIE_NAME,
        value=csrf_token,
        max_age=max_age,
        path="/",
        secure=settings.cookie_secure,
        httponly=False,
        samesite=settings.cookie_samesite,
    )


def _clear_auth_cookies(response: Response, *, settings: Settings) -> None:
    response.delete_cookie(REFRESH_COOKIE_NAME, path="/", secure=settings.cookie_secure, httponly=True, samesite=settings.cookie_samesite)
    response.delete_cookie(CSRF_COOKIE_NAME, path="/", secure=settings.cookie_secure, httponly=False, samesite=settings.cookie_samesite)


async def _validated_dpop_thumbprint(
    *,
    request: Request,
    session: AsyncSession,
    settings: Settings,
    now: datetime,
    error_code: str,
) -> str | None:
    if not settings.dpop_enabled:
        return None
    try:
        proof = await validate_dpop_request(
            proof_token=request.headers.get("DPoP"),
            method=request.method,
            url=str(request.url),
            settings=settings,
            session=session,
            now=now,
            correlation_id=getattr(request.state, "correlation_id", None),
        )
        await session.commit()
        return proof.key_thumbprint
    except DPoPError as exc:
        await session.commit()
        raise ApiError(status_code=401, code=error_code, message="A valid DPoP proof is required.") from exc


@router.post("/register", response_model=RegisterAcceptedResponse, status_code=status.HTTP_202_ACCEPTED)
async def register(
    payload: RegisterRequest,
    request: Request,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> RegisterAcceptedResponse:
    service = RegistrationService(session)
    try:
        await service.register(
            email=str(payload.email),
            password=payload.password,
            invite_code=payload.invite_code,
            origin=request.headers.get("origin"),
            settings=get_settings(request),
        )
    except CsrfValidationError as exc:
        raise ApiError(status_code=403, code="origin_rejected", message="The request origin is not allowed.") from exc
    except RegistrationInviteRejected as exc:
        raise ApiError(
            status_code=403,
            code="registration_invite_required",
            message="A valid registration invite code is required.",
        ) from exc
    return RegisterAcceptedResponse()


@router.post("/login", response_model=TokenResponse)
async def login(
    payload: LoginRequest,
    request: Request,
    response: Response,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> TokenResponse:
    settings = get_settings(request)
    service = AuthenticationService(session, settings)
    now = get_now(request)
    key_thumbprint = await _validated_dpop_thumbprint(
        request=request,
        session=session,
        settings=settings,
        now=now,
        error_code="invalid_dpop_proof",
    )
    try:
        outcome = await service.login(
            email=str(payload.email),
            password=payload.password,
            origin=request.headers.get("origin"),
            now=now,
            key_thumbprint=key_thumbprint,
        )
    except CsrfValidationError as exc:
        raise ApiError(status_code=403, code="origin_rejected", message="The request origin is not allowed.") from exc
    except AuthenticationFailed as exc:
        raise ApiError(
            status_code=401,
            code="invalid_credentials",
            message="Unable to sign in with the provided credentials. Check your email and password and try again.",
        ) from exc
    _set_auth_cookies(
        response,
        settings=settings,
        refresh_token=outcome.refresh_token,
        csrf_token=outcome.csrf_token,
        max_age=settings.refresh_idle_ttl_seconds,
    )
    return TokenResponse(access_token=outcome.access_token, expires_in=outcome.expires_in)


@router.post("/refresh", response_model=TokenResponse)
async def refresh(
    request: Request,
    response: Response,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> TokenResponse:
    settings = get_settings(request)
    service = SessionsService(session, settings)
    now = get_now(request)
    try:
        key_thumbprint = await _validated_dpop_thumbprint(
            request=request,
            session=session,
            settings=settings,
            now=now,
            error_code="session_invalid",
        )
    except ApiError:
        _clear_auth_cookies(response, settings=settings)
        raise
    try:
        outcome = await service.refresh(
            refresh_token=request.cookies.get(REFRESH_COOKIE_NAME),
            csrf_cookie=request.cookies.get(CSRF_COOKIE_NAME),
            csrf_header=request.headers.get("X-CSRF-Token"),
            origin=request.headers.get("origin"),
            now=now,
            correlation_id=getattr(request.state, "correlation_id", None),
            key_thumbprint=key_thumbprint,
        )
    except CsrfValidationError as exc:
        _clear_auth_cookies(response, settings=settings)
        raise ApiError(status_code=401, code="session_invalid", message="The session is no longer valid.") from exc
    if outcome.status is not RefreshStatus.rotated or not outcome.access_token or not outcome.refresh_token or not outcome.csrf_token or not outcome.expires_in:
        _clear_auth_cookies(response, settings=settings)
        raise ApiError(status_code=401, code="session_invalid", message="The session is no longer valid.")
    _set_auth_cookies(
        response,
        settings=settings,
        refresh_token=outcome.refresh_token,
        csrf_token=outcome.csrf_token,
        max_age=settings.refresh_idle_ttl_seconds,
    )
    return TokenResponse(access_token=outcome.access_token, expires_in=outcome.expires_in)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(
    request: Request,
    response: Response,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> Response:
    settings = get_settings(request)
    service = SessionsService(session, settings)
    now = get_now(request)
    try:
        key_thumbprint = await _validated_dpop_thumbprint(
            request=request,
            session=session,
            settings=settings,
            now=now,
            error_code="session_invalid",
        )
    except ApiError:
        _clear_auth_cookies(response, settings=settings)
        raise
    try:
        await service.logout(
            refresh_token=request.cookies.get(REFRESH_COOKIE_NAME),
            csrf_cookie=request.cookies.get(CSRF_COOKIE_NAME),
            csrf_header=request.headers.get("X-CSRF-Token"),
            origin=request.headers.get("origin"),
            now=now,
            correlation_id=getattr(request.state, "correlation_id", None),
            key_thumbprint=key_thumbprint,
        )
    except CsrfValidationError as exc:
        raise ApiError(status_code=401, code="session_invalid", message="The session is no longer valid.") from exc
    _clear_auth_cookies(response, settings=settings)
    response.status_code = status.HTTP_204_NO_CONTENT
    return response


@router.get("/me", response_model=CurrentUserResponse)
async def me(principal: Annotated[AuthenticatedPrincipal, Depends(resolve_principal)]) -> CurrentUserResponse:
    return principal.to_current_user()

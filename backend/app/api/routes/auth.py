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
from app.security.refresh_tokens import CSRF_COOKIE_NAME, REFRESH_COOKIE_NAME
from app.services.authentication import AuthenticationFailed, AuthenticationService
from app.services.registration import RegistrationService
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
            origin=request.headers.get("origin"),
            settings=get_settings(request),
        )
    except CsrfValidationError as exc:
        raise ApiError(status_code=403, code="origin_rejected", message="The request origin is not allowed.") from exc
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
    try:
        outcome = await service.login(
            email=str(payload.email),
            password=payload.password,
            origin=request.headers.get("origin"),
            now=get_now(request),
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
    try:
        outcome = await service.refresh(
            refresh_token=request.cookies.get(REFRESH_COOKIE_NAME),
            csrf_cookie=request.cookies.get(CSRF_COOKIE_NAME),
            csrf_header=request.headers.get("X-CSRF-Token"),
            origin=request.headers.get("origin"),
            now=get_now(request),
            correlation_id=getattr(request.state, "correlation_id", None),
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
    try:
        await service.logout(
            refresh_token=request.cookies.get(REFRESH_COOKIE_NAME),
            csrf_cookie=request.cookies.get(CSRF_COOKIE_NAME),
            csrf_header=request.headers.get("X-CSRF-Token"),
            origin=request.headers.get("origin"),
            now=get_now(request),
        )
    except CsrfValidationError as exc:
        raise ApiError(status_code=401, code="session_invalid", message="The session is no longer valid.") from exc
    _clear_auth_cookies(response, settings=settings)
    response.status_code = status.HTTP_204_NO_CONTENT
    return response


@router.get("/me", response_model=CurrentUserResponse)
async def me(principal: Annotated[AuthenticatedPrincipal, Depends(resolve_principal)]) -> CurrentUserResponse:
    return principal.to_current_user()

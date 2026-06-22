from __future__ import annotations

import base64
import hashlib
import hmac
import secrets
from typing import Annotated, Literal
from urllib.parse import urlencode

from fastapi import APIRouter, Depends, Request, Response, status
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings
from app.core.errors import ApiError
from app.db.session import get_session
from app.identity.oauth_service import OAuthAuthenticationError, OAuthService
from app.identity.providers.github import GitHubOAuthProvider, GitHubOAuthRequest
from app.identity.providers.google import GoogleOAuthProvider, GoogleOAuthRequest
from app.security.refresh_tokens import CSRF_COOKIE_NAME, REFRESH_COOKIE_NAME


router = APIRouter(prefix="/api/auth/oauth", tags=["auth"])

OAuthRouteProvider = Literal["google", "github"]
OAUTH_STATE_COOKIE_NAMES: dict[OAuthRouteProvider, str] = {
    "google": "simpagent_oauth_google_state",
    "github": "simpagent_oauth_github_state",
}
OAUTH_STATE_MAX_AGE_SECONDS = 5 * 60
OAUTH_STATE_SAMESITE = "lax"


def _b64url(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def _state_signature(state: str, settings: Settings) -> str:
    digest = hmac.digest(settings.csrf_hmac_key_value, state.encode("utf-8"), hashlib.sha256)
    return _b64url(digest)


def _issue_state_cookie(response: Response, *, provider: OAuthRouteProvider, state: str, settings: Settings) -> None:
    response.set_cookie(
        key=OAUTH_STATE_COOKIE_NAMES[provider],
        value=f"{state}.{_state_signature(state, settings)}",
        max_age=OAUTH_STATE_MAX_AGE_SECONDS,
        path=f"/api/auth/oauth/{provider}",
        secure=settings.cookie_secure,
        httponly=True,
        samesite=OAUTH_STATE_SAMESITE,
    )


def _delete_state_cookie(response: Response, *, provider: OAuthRouteProvider, settings: Settings) -> None:
    response.delete_cookie(
        OAUTH_STATE_COOKIE_NAMES[provider],
        path=f"/api/auth/oauth/{provider}",
        secure=settings.cookie_secure,
        httponly=True,
        samesite=OAUTH_STATE_SAMESITE,
    )


def _validate_state_cookie(*, cookie_value: str | None, state: str | None, settings: Settings) -> None:
    if not cookie_value or not state:
        raise ApiError(status_code=400, code="oauth_state_invalid", message="OAuth state is invalid.")
    try:
        cookie_state, signature = cookie_value.rsplit(".", 1)
    except ValueError as exc:
        raise ApiError(status_code=400, code="oauth_state_invalid", message="OAuth state is invalid.") from exc
    expected_signature = _state_signature(cookie_state, settings)
    if not hmac.compare_digest(cookie_state, state) or not hmac.compare_digest(signature, expected_signature):
        raise ApiError(status_code=400, code="oauth_state_invalid", message="OAuth state is invalid.")


def _set_auth_cookies(response: Response, *, settings: Settings, refresh_token: str, csrf_token: str) -> None:
    # Auth cookies are session-only so closing the browser drops refresh ability.
    response.set_cookie(
        key=REFRESH_COOKIE_NAME,
        value=refresh_token,
        path="/",
        secure=settings.cookie_secure,
        httponly=True,
        samesite=settings.cookie_samesite,
    )
    response.set_cookie(
        key=CSRF_COOKIE_NAME,
        value=csrf_token,
        path="/",
        secure=settings.cookie_secure,
        httponly=False,
        samesite=settings.cookie_samesite,
    )


def _frontend_session_url(settings: Settings, *, status_value: str) -> str:
    base = (settings.public_app_origin or settings.allowed_origins[0]).rstrip("/")
    return f"{base}/?{urlencode({'oauth': status_value})}"


def _redirect_to_frontend_session(
    *,
    provider: OAuthRouteProvider,
    settings: Settings,
    refresh_token: str,
    csrf_token: str,
) -> RedirectResponse:
    response = RedirectResponse(
        url=_frontend_session_url(settings, status_value="success"),
        status_code=status.HTTP_303_SEE_OTHER,
    )
    _set_auth_cookies(
        response,
        settings=settings,
        refresh_token=refresh_token,
        csrf_token=csrf_token,
    )
    _delete_state_cookie(response, provider=provider, settings=settings)
    return response


def _google_provider(request: Request, settings: Settings) -> GoogleOAuthProvider:
    provider = getattr(request.app.state, "google_oauth_provider", None)
    if provider is not None:
        return provider
    return GoogleOAuthProvider.from_settings(settings)


def _github_provider(request: Request, settings: Settings) -> GitHubOAuthProvider:
    provider = getattr(request.app.state, "github_oauth_provider", None)
    if provider is not None:
        return provider
    return GitHubOAuthProvider.from_settings(settings)


@router.get("/google/start", name="google_oauth_start")
async def google_oauth_start(request: Request) -> RedirectResponse:
    settings: Settings = request.app.state.settings
    if not settings.google_oauth_configured:
        raise ApiError(
            status_code=503,
            code="oauth_provider_unconfigured",
            message="Google OAuth is not configured.",
        )
    state = secrets.token_urlsafe(32)
    try:
        authorization_url = _google_provider(request, settings).authorization_url(state=state)
    except ValueError as exc:
        raise ApiError(
            status_code=503,
            code="oauth_provider_unconfigured",
            message="Google OAuth is not configured.",
        ) from exc

    response = RedirectResponse(url=authorization_url, status_code=status.HTTP_303_SEE_OTHER)
    _issue_state_cookie(response, provider="google", state=state, settings=settings)
    return response


@router.get("/google/callback", name="google_oauth_callback")
async def google_oauth_callback(
    request: Request,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> RedirectResponse:
    settings: Settings = request.app.state.settings
    if not settings.google_oauth_configured:
        raise ApiError(
            status_code=503,
            code="oauth_provider_unconfigured",
            message="Google OAuth is not configured.",
        )
    if request.query_params.get("error"):
        raise ApiError(status_code=401, code="oauth_login_failed", message="Google OAuth login failed.")

    _validate_state_cookie(
        cookie_value=request.cookies.get(OAUTH_STATE_COOKIE_NAMES["google"]),
        state=request.query_params.get("state"),
        settings=settings,
    )
    code = request.query_params.get("code")
    if not code:
        raise ApiError(status_code=400, code="oauth_code_missing", message="OAuth code is required.")

    provider = _google_provider(request, settings)
    try:
        identity = await provider.authenticate(
            GoogleOAuthRequest(code=code, redirect_uri=settings.google_redirect_uri or "")
        )
        outcome = await OAuthService(session, settings).complete_login(
            provider_name="google",
            identity=identity,
            now=request.app.state.clock(),
        )
    except (OAuthAuthenticationError, ValueError) as exc:
        raise ApiError(status_code=401, code="oauth_login_failed", message="Google OAuth login failed.") from exc

    return _redirect_to_frontend_session(
        provider="google",
        settings=settings,
        refresh_token=outcome.refresh_token,
        csrf_token=outcome.csrf_token,
    )


@router.get("/github/start", name="github_oauth_start")
async def github_oauth_start(request: Request) -> RedirectResponse:
    settings: Settings = request.app.state.settings
    if not settings.github_oauth_configured:
        raise ApiError(
            status_code=503,
            code="oauth_provider_unconfigured",
            message="GitHub OAuth is not configured.",
        )
    state = secrets.token_urlsafe(32)
    try:
        authorization_url = _github_provider(request, settings).authorization_url(state=state)
    except ValueError as exc:
        raise ApiError(
            status_code=503,
            code="oauth_provider_unconfigured",
            message="GitHub OAuth is not configured.",
        ) from exc

    response = RedirectResponse(url=authorization_url, status_code=status.HTTP_303_SEE_OTHER)
    _issue_state_cookie(response, provider="github", state=state, settings=settings)
    return response


@router.get("/github/callback", name="github_oauth_callback")
async def github_oauth_callback(
    request: Request,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> RedirectResponse:
    settings: Settings = request.app.state.settings
    if not settings.github_oauth_configured:
        raise ApiError(
            status_code=503,
            code="oauth_provider_unconfigured",
            message="GitHub OAuth is not configured.",
        )
    if request.query_params.get("error"):
        raise ApiError(status_code=401, code="oauth_login_failed", message="GitHub OAuth login failed.")

    _validate_state_cookie(
        cookie_value=request.cookies.get(OAUTH_STATE_COOKIE_NAMES["github"]),
        state=request.query_params.get("state"),
        settings=settings,
    )
    code = request.query_params.get("code")
    if not code:
        raise ApiError(status_code=400, code="oauth_code_missing", message="OAuth code is required.")

    provider = _github_provider(request, settings)
    try:
        identity = await provider.authenticate(
            GitHubOAuthRequest(code=code, redirect_uri=settings.github_redirect_uri or "")
        )
        outcome = await OAuthService(session, settings).complete_login(
            provider_name="github",
            identity=identity,
            now=request.app.state.clock(),
        )
    except (OAuthAuthenticationError, ValueError) as exc:
        raise ApiError(status_code=401, code="oauth_login_failed", message="GitHub OAuth login failed.") from exc

    return _redirect_to_frontend_session(
        provider="github",
        settings=settings,
        refresh_token=outcome.refresh_token,
        csrf_token=outcome.csrf_token,
    )

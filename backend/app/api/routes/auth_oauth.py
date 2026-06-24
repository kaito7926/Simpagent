from __future__ import annotations

from typing import Annotated, Literal
from urllib.parse import urlencode

from fastapi import APIRouter, Depends, Request, Response, status
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings
from app.core.errors import ApiError
from app.db.repositories.sessions import SessionsRepository
from app.db.session import get_session
from app.identity.oauth_service import OAuthAuthenticationError, OAuthService
from app.identity.providers.github import GitHubOAuthProvider, GitHubOAuthRequest
from app.identity.providers.google import GoogleOAuthProvider, GoogleOAuthRequest
from app.security.oauth_transaction import (
    OAuthTransaction,
    OAuthTransactionError,
    issue_oauth_transaction,
    seal_oauth_transaction,
    unseal_oauth_transaction,
)
from app.security.refresh_tokens import CSRF_COOKIE_NAME, REFRESH_COOKIE_NAME


router = APIRouter(prefix="/api/auth/oauth", tags=["auth"])

OAuthRouteProvider = Literal["google", "github"]
OAUTH_STATE_COOKIE_NAMES: dict[OAuthRouteProvider, str] = {
    "google": "simpagent_oauth_google_state",
    "github": "simpagent_oauth_github_state",
}
OAUTH_STATE_MAX_AGE_SECONDS = 5 * 60
OAUTH_STATE_SAMESITE = "lax"


def _issue_state_cookie(
    response: Response,
    *,
    provider: OAuthRouteProvider,
    transaction: OAuthTransaction,
    settings: Settings,
) -> None:
    response.set_cookie(
        key=OAUTH_STATE_COOKIE_NAMES[provider],
        value=seal_oauth_transaction(transaction=transaction, settings=settings),
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


async def _record_oauth_transaction_event(
    session: AsyncSession,
    *,
    event_type: str,
    severity: str,
    provider: OAuthRouteProvider,
    correlation_id: str | None,
    metadata: dict,
) -> None:
    await SessionsRepository(session).add_security_event(
        event_type=event_type,
        severity=severity,
        user_id=None,
        description=f"OAuth transaction denied for {provider}.",
        correlation_id=correlation_id,
        metadata={"provider": provider, **metadata},
    )
    await session.commit()


def _oauth_state_error() -> ApiError:
    return ApiError(status_code=400, code="oauth_state_invalid", message="OAuth state is invalid.")


async def _consume_oauth_transaction(
    request: Request,
    session: AsyncSession,
    *,
    provider: OAuthRouteProvider,
    settings: Settings,
) -> OAuthTransaction:
    correlation_id = getattr(request.state, "correlation_id", None)
    try:
        transaction = unseal_oauth_transaction(
            cookie_value=request.cookies.get(OAUTH_STATE_COOKIE_NAMES[provider]),
            provider=provider,
            state=request.query_params.get("state"),
            settings=settings,
            now=request.app.state.clock(),
        )
    except OAuthTransactionError as exc:
        await _record_oauth_transaction_event(
            session,
            event_type="oauth_transaction_invalid",
            severity="medium",
            provider=provider,
            correlation_id=correlation_id,
            metadata={"reason": str(exc)},
        )
        raise _oauth_state_error() from exc

    async with session.begin():
        result = await SessionsRepository(session).consume_security_artifact_once(
            artifact_type="oauth_transaction",
            jti=transaction.jti,
            subject=None,
            audience=f"simpagent-oauth-{provider}",
            conversation_id=None,
            binding_key_thumbprint=transaction.code_challenge,
            expires_at=transaction.expires_at,
            now=request.app.state.clock(),
            correlation_id=correlation_id,
            replay_event_type="oauth_transaction_replay",
        )
    if not result.accepted:
        raise _oauth_state_error()
    return transaction


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
        max_age=settings.refresh_idle_ttl_seconds,
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
    transaction = issue_oauth_transaction(provider="google", settings=settings, now=request.app.state.clock())
    try:
        authorization_url = _google_provider(request, settings).authorization_url(
            state=transaction.state,
            code_challenge=transaction.code_challenge,
        )
    except ValueError as exc:
        raise ApiError(
            status_code=503,
            code="oauth_provider_unconfigured",
            message="Google OAuth is not configured.",
        ) from exc

    response = RedirectResponse(url=authorization_url, status_code=status.HTTP_303_SEE_OTHER)
    _issue_state_cookie(response, provider="google", transaction=transaction, settings=settings)
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

    transaction = await _consume_oauth_transaction(request, session, provider="google", settings=settings)
    code = request.query_params.get("code")
    if not code:
        raise ApiError(status_code=400, code="oauth_code_missing", message="OAuth code is required.")

    provider = _google_provider(request, settings)
    try:
        identity = await provider.authenticate(
            GoogleOAuthRequest(
                code=code,
                redirect_uri=settings.google_redirect_uri or "",
                code_verifier=transaction.code_verifier,
            )
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
    transaction = issue_oauth_transaction(provider="github", settings=settings, now=request.app.state.clock())
    try:
        authorization_url = _github_provider(request, settings).authorization_url(
            state=transaction.state,
            code_challenge=transaction.code_challenge,
        )
    except ValueError as exc:
        raise ApiError(
            status_code=503,
            code="oauth_provider_unconfigured",
            message="GitHub OAuth is not configured.",
        ) from exc

    response = RedirectResponse(url=authorization_url, status_code=status.HTTP_303_SEE_OTHER)
    _issue_state_cookie(response, provider="github", transaction=transaction, settings=settings)
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

    transaction = await _consume_oauth_transaction(request, session, provider="github", settings=settings)
    code = request.query_params.get("code")
    if not code:
        raise ApiError(status_code=400, code="oauth_code_missing", message="OAuth code is required.")

    provider = _github_provider(request, settings)
    try:
        identity = await provider.authenticate(
            GitHubOAuthRequest(
                code=code,
                redirect_uri=settings.github_redirect_uri or "",
                code_verifier=transaction.code_verifier,
            )
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

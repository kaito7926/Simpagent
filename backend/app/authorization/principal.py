from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Annotated
from uuid import UUID

from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings
from app.core.errors import ApiError
from app.db.repositories.accounts import AccountsRepository
from app.db.repositories.sessions import SessionsRepository
from app.db.session import get_session
from app.schemas.auth import CurrentUserResponse
from app.security.access_tokens import AccessTokenClaims, AccessTokenError, decode_access_token
from app.security.dpop import DPoPError, validate_dpop_request

from .policy import KNOWN_ROLE_VALUES, KNOWN_SCOPE_VALUES


@dataclass(frozen=True)
class AuthenticatedPrincipal:
    user_id: UUID
    email: str
    role: str
    scopes: tuple[str, ...]
    is_active: bool
    claims: AccessTokenClaims

    def to_current_user(self) -> CurrentUserResponse:
        return CurrentUserResponse(
            id=self.user_id,
            email=self.email,
            role=self.role,
            scopes=list(self.scopes),
            is_active=self.is_active,
        )


bearer_scheme = HTTPBearer(auto_error=False)


def get_settings_from_request(request: Request) -> Settings:
    return request.app.state.settings


def get_now(request: Request) -> datetime:
    return request.app.state.clock()


async def resolve_principal(
    request: Request,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> AuthenticatedPrincipal:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise ApiError(status_code=401, code="missing_principal", message="Authenticated principal is required.")
    settings = get_settings_from_request(request)
    now = get_now(request)
    try:
        claims = decode_access_token(credentials.credentials, settings=settings, now=now)
    except AccessTokenError as exc:
        raise ApiError(status_code=401, code="invalid_token", message="The access token is invalid.") from exc
    if settings.dpop_enabled:
        if not claims.cnf_jkt:
            raise ApiError(status_code=401, code="invalid_dpop_proof", message="A valid DPoP proof is required.")
        try:
            await validate_dpop_request(
                proof_token=request.headers.get("DPoP"),
                method=request.method,
                url=str(request.url),
                settings=settings,
                session=session,
                now=now,
                correlation_id=getattr(request.state, "correlation_id", None),
                expected_key_thumbprint=claims.cnf_jkt,
                subject=str(claims.sub),
            )
            await session.commit()
        except DPoPError as exc:
            await session.commit()
            raise ApiError(status_code=401, code="invalid_dpop_proof", message="A valid DPoP proof is required.") from exc

    accounts = AccountsRepository(session)
    bundle = await accounts.get_user_bundle_by_id(claims.sub)
    if bundle is None or not bundle.user.is_active:
        raise ApiError(status_code=401, code="inactive_principal", message="The authenticated principal is not active.")

    current_role = bundle.user.role
    current_scopes = tuple(sorted(scope.scope for scope in bundle.scopes))
    if current_role not in KNOWN_ROLE_VALUES or set(current_scopes) - KNOWN_SCOPE_VALUES:
        events = SessionsRepository(session)
        await events.add_security_event(
            event_type="unknown_policy_state",
            severity="high",
            user_id=bundle.user.id,
            description="Unknown role or scope state denied.",
            correlation_id=getattr(request.state, "correlation_id", None),
            metadata={"role": "redacted", "scopes_count": len(current_scopes)},
        )
        await session.commit()
        raise ApiError(status_code=401, code="unknown_state", message="The authenticated principal is invalid.")
    if claims.role != current_role or claims.scopes != current_scopes:
        raise ApiError(status_code=401, code="stale_token", message="The access token is no longer valid for the current account state.")
    return AuthenticatedPrincipal(
        user_id=bundle.user.id,
        email=bundle.user.email,
        role=current_role,
        scopes=current_scopes,
        is_active=bundle.user.is_active,
        claims=claims,
    )

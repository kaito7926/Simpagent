from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime
from ipaddress import ip_address, ip_network
import logging
import re
from time import perf_counter
from typing import Any
from uuid import uuid4

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.ai.search_worker.service import build_search_worker_service
from app.api.routes import admin, auth, auth_oauth, chat, conversations, health, python
from app.core.config import Settings, get_settings
from app.core.errors import ApiError, install_error_handlers
from app.core.logging import configure_logging, reset_correlation_id, set_correlation_id
from app.core.provider_status import resolve_search_provider, search_status
from app.db.session import create_session_factory

Clock = Callable[[], datetime]
access_logger = logging.getLogger("simpagent.access")
CORRELATION_ID_PATTERN = re.compile(r"^[A-Za-z0-9._:-]{1,128}$")


def _is_trusted_proxy(client_host: str | None, settings: Settings) -> bool:
    if not client_host:
        return False
    try:
        client_ip = ip_address(client_host)
    except ValueError:
        return False
    for cidr in settings.trusted_proxy_cidrs:
        try:
            if client_ip in ip_network(cidr, strict=False):
                return True
        except ValueError:
            continue
    return False


def _resolved_client_ip(request: Request, settings: Settings) -> str | None:
    peer_host = request.client.host if request.client else None
    if settings.app_env == "test" and request.headers.get("X-Trusted-Proxy-For-Test"):
        peer_host = request.headers["X-Trusted-Proxy-For-Test"]
    if not _is_trusted_proxy(peer_host, settings):
        return peer_host
    forwarded_for = request.headers.get("X-Forwarded-For")
    if not forwarded_for:
        return peer_host
    first_hop = forwarded_for.split(",", 1)[0].strip()
    try:
        return str(ip_address(first_hop))
    except ValueError:
        return peer_host


def utc_now() -> datetime:
    return datetime.now(UTC)


def create_app(
    settings: Settings | None = None,
    *,
    session_factory: Any | None = None,
    clock: Clock | None = None,
) -> FastAPI:
    settings = settings or get_settings()
    configure_logging(settings)
    resolved_session_factory = session_factory or create_session_factory(settings)
    app = FastAPI(title="SimpAgent API", version="0.1.0")
    app.state.settings = settings
    app.state.clock = clock or utc_now
    app.state.session_factory = resolved_session_factory
    app.state.provider_checkers = {}
    app.state.search_status = search_status(settings)
    app.state.search_provider = resolve_search_provider(settings) or "invalid"
    app.state.search_ready = app.state.search_status == "ready"
    app.state.search_worker = build_search_worker_service(settings) if app.state.search_ready else None

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.allowed_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type", "X-CSRF-Token", "X-Correlation-Id"],
        expose_headers=["X-Correlation-Id"],
    )

    @app.middleware("http")
    async def correlation_middleware(request: Request, call_next):
        supplied_correlation_id = request.headers.get("X-Correlation-Id")
        correlation_id = supplied_correlation_id or str(uuid4())
        request.state.correlation_id = correlation_id
        if not CORRELATION_ID_PATTERN.fullmatch(correlation_id):
            return JSONResponse(
                status_code=400,
                content={
                    "error": {
                        "code": "invalid_correlation_id",
                        "message": "X-Correlation-Id must be 1-128 characters of letters, numbers, dot, underscore, colon, or dash.",
                        "correlation_id": str(uuid4()),
                    }
                },
            )
        request.state.client_ip = _resolved_client_ip(request, settings)
        token = set_correlation_id(correlation_id)
        started_at = perf_counter()
        try:
            response = await call_next(request)
        except Exception:
            duration_ms = max(0, int((perf_counter() - started_at) * 1000))
            access_logger.exception(
                "http_request_failed",
                extra={
                    "event": "http_request",
                    "method": request.method,
                    "path": request.url.path,
                    "status_code": 500,
                    "duration_ms": duration_ms,
                    "client_ip": getattr(request.state, "client_ip", None),
                    "user_agent": request.headers.get("user-agent"),
                },
            )
            raise
        else:
            duration_ms = max(0, int((perf_counter() - started_at) * 1000))
            response.headers["X-Correlation-Id"] = correlation_id
            access_logger.info(
                "http_request_completed",
                extra={
                    "event": "http_request",
                    "method": request.method,
                    "path": request.url.path,
                    "status_code": response.status_code,
                    "duration_ms": duration_ms,
                    "client_ip": getattr(request.state, "client_ip", None),
                    "user_agent": request.headers.get("user-agent"),
                },
            )
            return response
        finally:
            reset_correlation_id(token)

    @app.get("/")
    async def root() -> dict[str, str]:
        raise ApiError(
            status_code=503,
            code="frontend_missing",
            message="Frontend route is not yet available.",
        )

    app.include_router(auth.router)
    app.include_router(auth_oauth.router)
    app.include_router(admin.router)
    app.include_router(chat.router)
    app.include_router(conversations.router)
    app.include_router(health.router)
    app.include_router(python.router)
    install_error_handlers(app)
    return app


app = create_app()

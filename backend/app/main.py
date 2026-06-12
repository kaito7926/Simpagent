from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import auth, chat, health, python
from app.core.config import Settings, get_settings
from app.core.errors import ApiError, install_error_handlers
from app.db.session import create_session_factory


Clock = Callable[[], datetime]


def utc_now() -> datetime:
    return datetime.now(UTC)


def create_app(
    settings: Settings | None = None,
    *,
    session_factory: Any | None = None,
    clock: Clock | None = None,
) -> FastAPI:
    settings = settings or get_settings()
    resolved_session_factory = session_factory or create_session_factory(settings)
    app = FastAPI(title="SimpAgent API", version="0.1.0")
    app.state.settings = settings
    app.state.clock = clock or utc_now
    app.state.session_factory = resolved_session_factory
    app.state.provider_checkers = {}

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.allowed_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "DELETE", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type", "X-CSRF-Token", "X-Correlation-Id"],
        expose_headers=["X-Correlation-Id"],
    )

    @app.middleware("http")
    async def correlation_middleware(request: Request, call_next):
        correlation_id = request.headers.get("X-Correlation-Id") or str(uuid4())
        request.state.correlation_id = correlation_id
        response = await call_next(request)
        response.headers["X-Correlation-Id"] = correlation_id
        return response

    @app.get("/")
    async def root() -> dict[str, str]:
        raise ApiError(status_code=503, code="frontend_missing", message="Frontend route is not yet available.")

    app.include_router(auth.router)
    app.include_router(chat.router)
    app.include_router(health.router)
    app.include_router(python.router)
    install_error_handlers(app)
    return app


app = create_app()

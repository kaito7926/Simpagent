from __future__ import annotations

from fastapi import APIRouter, Request, status
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.provider_status import compute_provider_snapshot
from app.schemas.health import ReadinessComponents, ReadinessResponse

router = APIRouter(tags=["health"])


@router.get("/health")
async def health() -> dict[str, str]:
    return {"status": "alive"}


@router.get("/ready", response_model=ReadinessResponse)
async def ready(request: Request) -> JSONResponse:
    session_factory: async_sessionmaker[AsyncSession] = request.app.state.session_factory
    settings = request.app.state.settings
    search_override = getattr(request.app.state, "search_status", None)
    database_status = "ready"
    migrations_status = "unknown"
    try:
        async with session_factory() as session:
            await session.execute(text("SELECT 1"))
            migrations_status = "ready"
    except SQLAlchemyError:
        database_status = "unavailable"
        migrations_status = "unknown"

    providers = compute_provider_snapshot(settings, search_override=search_override)
    components = ReadinessComponents(
        database=database_status,
        migrations=migrations_status,
        llm=providers.llm,
        search=providers.search,
        sandbox=providers.sandbox,
    )
    if database_status != "ready" or migrations_status != "ready":
        payload = ReadinessResponse(status="not_ready", components=components)
        return JSONResponse(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, content=payload.model_dump())
    if providers.llm != "ready" or providers.search != "ready":
        payload = ReadinessResponse(status="degraded", components=components)
        return JSONResponse(status_code=status.HTTP_200_OK, content=payload.model_dump())
    payload = ReadinessResponse(status="ready", components=components)
    return JSONResponse(status_code=status.HTTP_200_OK, content=payload.model_dump())

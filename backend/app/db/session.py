from __future__ import annotations

from collections.abc import AsyncIterator

from fastapi import Request
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import Settings


SessionFactory = async_sessionmaker[AsyncSession]


def create_engine(settings: Settings) -> AsyncEngine:
    return create_async_engine(settings.resolved_database_url, future=True)


def create_session_factory(settings: Settings) -> SessionFactory:
    return async_sessionmaker(bind=create_engine(settings), expire_on_commit=False)


async def get_session(request: Request) -> AsyncIterator[AsyncSession]:
    session_factory: SessionFactory = request.app.state.session_factory
    async with session_factory() as session:
        yield session

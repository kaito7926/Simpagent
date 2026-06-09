from __future__ import annotations

from collections.abc import AsyncIterator
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine

import app.models  # noqa: F401
from app.core.config import Settings
from app.db.base import Base


ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture(scope="session")
def postgres_url(settings: Settings) -> str:
    url = settings.resolved_database_url
    if not url.startswith("postgresql+psycopg://"):
        raise RuntimeError("Only PostgreSQL URLs are allowed for integration tests.")
    return url


@pytest.fixture(scope="session")
def alembic_config(postgres_url: str) -> Config:
    config = Config(str(ROOT / "alembic.ini"))
    config.set_main_option("sqlalchemy.url", postgres_url)
    return config


@pytest.fixture(scope="session", autouse=True)
def migrated_database(alembic_config: Config) -> None:
    command.upgrade(alembic_config, "head")


@pytest.fixture(scope="session")
def postgres_engine(migrated_database: None, postgres_url: str) -> AsyncIterator[AsyncEngine]:
    engine = create_async_engine(postgres_url, future=True)
    try:
        yield engine
    finally:
        import asyncio

        asyncio.run(engine.dispose())


@pytest.fixture(scope="session")
def session_factory(postgres_engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(postgres_engine, expire_on_commit=False)


@pytest.fixture(autouse=True)
async def clean_database(session_factory: async_sessionmaker[AsyncSession]) -> AsyncIterator[None]:
    table_names = [table.name for table in reversed(Base.metadata.sorted_tables)]
    if table_names:
        truncate_sql = f"TRUNCATE TABLE {', '.join(table_names)} RESTART IDENTITY CASCADE"
        async with session_factory() as session:
            await session.execute(text(truncate_sql))
            await session.commit()
    yield
    if table_names:
        truncate_sql = f"TRUNCATE TABLE {', '.join(table_names)} RESTART IDENTITY CASCADE"
        async with session_factory() as session:
            await session.execute(text(truncate_sql))
            await session.commit()


@pytest.fixture
async def db_session(session_factory: async_sessionmaker[AsyncSession]) -> AsyncIterator[AsyncSession]:
    async with session_factory() as session:
        yield session
        await session.rollback()

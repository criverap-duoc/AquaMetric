"""Async SQLAlchemy engine, session wiring and the declarative base.

The engine lives on `app.state` instead of a module global so tests and multiple
app instances never share connections.
"""

from collections.abc import AsyncIterator
from typing import Annotated, Final

from fastapi import Depends, Request
from sqlalchemy import MetaData
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

from app.core.config import Settings

# ADR-008: every AquaMetric table lives here, never in `public` (TerraPlan owns `public`).
SCHEMA: Final = "aquametric"

# Deterministic constraint names, so a migration and the models cannot disagree by accident.
NAMING_CONVENTION: Final[dict[str, str]] = {
    "ix": "ix_%(table_name)s_%(column_0_N_name)s",
    "uq": "uq_%(table_name)s_%(column_0_N_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


class Base(DeclarativeBase):
    """Single declarative base; the schema is part of the metadata, not of each mapper."""

    metadata = MetaData(schema=SCHEMA, naming_convention=NAMING_CONVENTION)


def create_engine(settings: Settings) -> AsyncEngine:
    """Connections open on first query, so startup does not depend on the database being up."""
    return create_async_engine(settings.database_url, pool_pre_ping=True)


def create_session_factory(engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
    """Sessions keep loaded values after commit so responses never trigger a lazy reload."""
    return async_sessionmaker(engine, expire_on_commit=False)


async def get_session(request: Request) -> AsyncIterator[AsyncSession]:
    """One session per request; committing is the service layer's job, not the repository's."""
    session_factory: async_sessionmaker[AsyncSession] = request.app.state.session_factory
    async with session_factory() as session:
        yield session


SessionDep = Annotated[AsyncSession, Depends(get_session)]

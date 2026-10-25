"""Alembic environment: async migrations that only ever touch the `aquametric` schema.

The URL comes from the same `Settings` the API uses (ADR-008): no connection string in
alembic.ini. Because `Settings` requires the API's own variables, migrating needs the same
environment as running the app (`api/.env` locally, the service variables on Render).
"""

import asyncio
from logging.config import fileConfig
from typing import Any

from sqlalchemy import pool, text
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.sql.schema import SchemaItem

import app.models  # noqa: F401  # registers every table on Base.metadata for autogenerate
from alembic import context
from app.core.config import get_settings
from app.core.db import SCHEMA, Base

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def _database_url() -> str:
    """Read DATABASE_URL from Settings; a missing or invalid value fails before any DDL."""
    return get_settings().database_url


def _include_object(
    obj: SchemaItem,
    name: str | None,
    type_: str,
    reflected: bool,
    compare_to: SchemaItem | None,
) -> bool:
    """Autogenerate must never see `public`: TerraPlan owns it and shares the database no more."""
    return getattr(obj, "schema", SCHEMA) == SCHEMA


def _configure(**options: Any) -> None:
    """Shared options for both modes, so online and offline emit the same schema scope.

    `Any` because `context.configure` forwards to Alembic's own typed kwargs; restating its
    signature here would be a copy that silently drifts with each Alembic release.
    """
    context.configure(
        target_metadata=target_metadata,
        include_schemas=True,
        version_table="alembic_version",
        version_table_schema=SCHEMA,
        include_object=_include_object,
        **options,
    )


def run_migrations_offline() -> None:
    """Emit SQL without a DBAPI connection (`alembic upgrade head --sql`)."""
    _configure(
        url=_database_url(),
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.execute(f"CREATE SCHEMA IF NOT EXISTS {SCHEMA}")
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    """Run the migrations on a synchronous connection bridged from the async engine."""
    _configure(connection=connection, compare_type=True)
    with context.begin_transaction():
        # Alembic creates `aquametric.alembic_version` before running any migration, so the
        # schema must exist first; `IF NOT EXISTS` keeps this harmless on every later run.
        connection.execute(text(f"CREATE SCHEMA IF NOT EXISTS {SCHEMA}"))
        context.run_migrations()


async def run_async_migrations() -> None:
    engine = create_async_engine(_database_url(), poolclass=pool.NullPool)
    try:
        async with engine.connect() as connection:
            await connection.run_sync(do_run_migrations)
    finally:
        await engine.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    asyncio.run(run_async_migrations())

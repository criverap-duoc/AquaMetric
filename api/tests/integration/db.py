"""Helpers shared by the integration suite: the throwaway database and the Alembic CLI.

Kept out of `conftest.py` so test modules can import the helpers directly (one definition of
the migration runner) without importing fixtures.
"""

import os
import subprocess
import sys
from pathlib import Path
from typing import Any

import asyncpg

# tests/integration/db.py -> api/
API_DIR = Path(__file__).parents[2]

TEST_INGEST_API_KEY = "test-ingest-api-key-0001"

# Everything ingestion writes. Truncating it gives each test the same starting point.
# `spc_baseline` holds FKs to site/parameter series, so it is listed too (and the whole list is
# truncated in one statement, which is what PostgreSQL requires).
TRUNCATE_SQL = (
    "TRUNCATE aquametric.observation, aquametric.sample, aquametric.site, "
    "aquametric.ingest_idempotency, aquametric.spc_baseline"
)


def dsn(database_url: str) -> str:
    """asyncpg wants the plain scheme; `+asyncpg` is SQLAlchemy's driver marker."""
    return database_url.replace("postgresql+asyncpg://", "postgresql://")


def run_alembic(database_url: str, *args: str) -> None:
    """Run the real CLI, like a deploy does: environment variables are its only input."""
    env = {
        **os.environ,
        "ENV": "ci",
        "DATABASE_URL": database_url,
        "INGEST_API_KEY": TEST_INGEST_API_KEY,
    }
    completed = subprocess.run(  # noqa: S603  # fixed argv, no shell, no user input
        [sys.executable, "-m", "alembic", *args],
        cwd=API_DIR,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    assert completed.returncode == 0, completed.stderr


async def truncate_all(database_url: str) -> None:
    """Empty every application table; the schema and the CI database stay."""
    connection = await asyncpg.connect(dsn(database_url))
    try:
        await connection.execute(TRUNCATE_SQL)
    finally:
        await connection.close()


async def fetchval(database_url: str, query: str, *args: Any) -> Any:
    """One scalar straight from asyncpg, so assertions bypass the API under test."""
    connection = await asyncpg.connect(dsn(database_url))
    try:
        return await connection.fetchval(query, *args)
    finally:
        await connection.close()

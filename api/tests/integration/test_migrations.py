"""Migration tests against a real PostgreSQL 16 (Docker required).

These are the only tests that prove the DDL in `alembic/versions` agrees with `app/models`
and with the SQL conventions of `02 §9`. They are marked `integration` so the fast suite stays
Docker-free (03 §2).
"""

import asyncio
import os
import subprocess
import sys
import uuid
from collections.abc import Iterator
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path

import asyncpg
import pytest
from testcontainers.community.postgres import PostgresContainer

pytestmark = pytest.mark.integration

# tests/integration/test_migrations.py -> api/
API_DIR = Path(__file__).parents[2]

TEST_INGEST_API_KEY = "test-ingest-api-key-0001"
APP_TABLES = {"ingest_idempotency", "observation", "sample", "site", "spc_baseline"}
VERSION_TABLE = "alembic_version"

TABLE_NAMES = "SELECT table_name FROM information_schema.tables WHERE table_schema = 'aquametric'"
INSERT_SITE = """
    INSERT INTO aquametric.site (id, code, name, water_body_type)
    VALUES ($1, $2, $3, $4)
"""
INSERT_SAMPLE = """
    INSERT INTO aquametric.sample (id, site_id, matrix, collected_at, status)
    VALUES ($1, $2, $3, $4, $5)
"""
INSERT_OBSERVATION = """
    INSERT INTO aquametric.observation
        (id, site_id, sample_id, parameter_code, value, unit_code, analyzed_at, source)
    VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
"""
# What IngestService will run: a retried batch collides on the natural key and is skipped.
INSERT_OBSERVATION_ON_CONFLICT = INSERT_OBSERVATION + (
    "ON CONFLICT ON CONSTRAINT uq_obs_natural_key DO NOTHING"
)
INSERT_MEASURED = """
    INSERT INTO aquametric.observation
        (id, site_id, sample_id, parameter_code, value, unit_code, qualifier, loq,
         analyzed_at, source)
    VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
"""
COUNT_OBSERVATIONS = "SELECT count(*) FROM aquametric.observation WHERE site_id = $1"


@pytest.fixture(scope="session")
def database_url() -> Iterator[str]:
    """Migrate one throwaway database for the whole session; the container dies with it."""
    with PostgresContainer("postgres:16-alpine", driver="asyncpg") as container:
        url = container.get_connection_url()
        _run_alembic(url, "upgrade", "head")
        yield url


def _dsn(database_url: str) -> str:
    """asyncpg wants the plain scheme; `+asyncpg` is SQLAlchemy's driver marker."""
    return database_url.replace("postgresql+asyncpg://", "postgresql://")


def _run_alembic(database_url: str, *args: str) -> None:
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


async def _table_names(database_url: str) -> set[str]:
    connection = await asyncpg.connect(_dsn(database_url))
    try:
        rows = await connection.fetch(TABLE_NAMES)
    finally:
        await connection.close()
    return {row["table_name"] for row in rows}


async def _seed_site_and_sample(database_url: str, code: str) -> tuple[uuid.UUID, uuid.UUID]:
    """Create the minimum rows every observation needs; each test uses its own site code."""
    site_id, sample_id = uuid.uuid4(), uuid.uuid4()
    connection = await asyncpg.connect(_dsn(database_url))
    try:
        await connection.execute(INSERT_SITE, site_id, code, f"Sitio {code}", "river")
        await connection.execute(
            INSERT_SAMPLE,
            sample_id,
            site_id,
            "water",
            datetime(2026, 10, 1, 12, tzinfo=UTC),
            "analyzed",
        )
    finally:
        await connection.close()
    return site_id, sample_id


async def test_upgrade_creates_all_tables_in_the_aquametric_schema(database_url: str) -> None:
    """Five application tables plus Alembic's bookkeeping, and nothing in `public`."""
    assert await _table_names(database_url) == APP_TABLES | {VERSION_TABLE}


async def test_downgrade_and_upgrade_are_reversible(database_url: str) -> None:
    """A failed deploy must roll back: the first migration has to be undoable."""
    await asyncio.to_thread(_run_alembic, database_url, "downgrade", "-1")
    assert await _table_names(database_url) - {VERSION_TABLE} == set()

    await asyncio.to_thread(_run_alembic, database_url, "upgrade", "head")
    assert await _table_names(database_url) == APP_TABLES | {VERSION_TABLE}


async def test_models_and_migrations_agree(database_url: str) -> None:
    """`alembic check` fails on any drift between `app/models` and the applied schema."""
    await asyncio.to_thread(_run_alembic, database_url, "check")


async def test_natural_key_skips_a_repeated_observation(database_url: str) -> None:
    """A retried batch collides on the natural key instead of duplicating rows (ADR-009)."""
    site_id, sample_id = await _seed_site_and_sample(database_url, "SIM-TEST-NATURAL")
    analyzed_at = datetime(2026, 10, 1, 12, tzinfo=UTC)
    connection = await asyncpg.connect(_dsn(database_url))
    try:
        await connection.execute(
            INSERT_OBSERVATION,
            uuid.uuid4(),
            site_id,
            sample_id,
            "PH",
            Decimal("7.200000"),
            "UPH",
            analyzed_at,
            "lab",
        )
        # Same measurement, fresh id: the natural key wins and nothing is inserted.
        await connection.execute(
            INSERT_OBSERVATION_ON_CONFLICT,
            uuid.uuid4(),
            site_id,
            sample_id,
            "PH",
            Decimal("7.200000"),
            "UPH",
            analyzed_at,
            "lab",
        )
        count = await connection.fetchval(COUNT_OBSERVATIONS, site_id)
    finally:
        await connection.close()
    assert count == 1


async def test_censored_rows_store_the_loq_and_never_a_value(database_url: str) -> None:
    """`value` and `qualifier` must agree: `< LOQ` rows carry the LOQ and no value (ADR-003)."""
    site_id, sample_id = await _seed_site_and_sample(database_url, "SIM-TEST-CENSORED")
    analyzed_at = datetime(2026, 10, 1, 13, tzinfo=UTC)
    connection = await asyncpg.connect(_dsn(database_url))
    try:
        await connection.execute(
            INSERT_MEASURED,
            uuid.uuid4(),
            site_id,
            sample_id,
            "TURB",
            None,
            "NTU",
            "<",
            Decimal("0.500000"),
            analyzed_at,
            "lab",
        )
        with pytest.raises(asyncpg.exceptions.CheckViolationError):
            await connection.execute(
                INSERT_MEASURED,
                uuid.uuid4(),
                site_id,
                sample_id,
                "TURB",
                Decimal("5.000000"),
                "NTU",
                "<",
                None,
                analyzed_at,
                "lab",
            )
    finally:
        await connection.close()


async def test_observation_requires_an_existing_sample(database_url: str) -> None:
    """The foreign key is the guard: an observation cannot cite a sample that does not exist."""
    site_id, _ = await _seed_site_and_sample(database_url, "SIM-TEST-FK")
    connection = await asyncpg.connect(_dsn(database_url))
    try:
        with pytest.raises(asyncpg.exceptions.ForeignKeyViolationError):
            await connection.execute(
                INSERT_OBSERVATION,
                uuid.uuid4(),
                site_id,
                uuid.uuid4(),
                "PH",
                Decimal("7.000000"),
                "UPH",
                datetime(2026, 10, 1, 14, tzinfo=UTC),
                "lab",
            )
    finally:
        await connection.close()

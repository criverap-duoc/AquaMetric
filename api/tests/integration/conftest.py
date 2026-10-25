"""Fixtures for the integration suite: one PostgreSQL 16 container, one app per test.

Docker is required. The container is migrated once per session; every test that writes starts
from empty tables, so no test depends on the order the suite runs in.
"""

from collections.abc import AsyncIterator, Iterator

import pytest
from httpx import ASGITransport, AsyncClient
from testcontainers.community.postgres import PostgresContainer

from app.core.config import get_settings
from tests.integration.db import TEST_INGEST_API_KEY, run_alembic, truncate_all


@pytest.fixture(scope="session")
def database_url() -> Iterator[str]:
    """Migrate one throwaway database for the whole session; the container dies with it."""
    with PostgresContainer("postgres:16-alpine", driver="asyncpg") as container:
        url = container.get_connection_url()
        run_alembic(url, "upgrade", "head")
        yield url


@pytest.fixture
async def api_client(
    database_url: str, monkeypatch: pytest.MonkeyPatch
) -> AsyncIterator[AsyncClient]:
    """Drive the real ASGI app against the throwaway database, with empty tables.

    Settings are patched before `create_app()` runs, which is why the import is deferred: the
    module-level `app` of `app.main` must not be built with the developer's `.env`.
    """
    await truncate_all(database_url)
    monkeypatch.setenv("ENV", "ci")
    monkeypatch.setenv("DATABASE_URL", database_url)
    monkeypatch.setenv("INGEST_API_KEY", TEST_INGEST_API_KEY)
    get_settings.cache_clear()
    try:
        from app.main import create_app

        app = create_app()
        async with app.router.lifespan_context(app):
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                yield client
    finally:
        get_settings.cache_clear()

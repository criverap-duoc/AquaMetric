"""Shared fixtures: isolated settings, the app under test and an HTTP client."""

from collections.abc import AsyncIterator, Iterator

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from app.core.config import Settings, get_settings

TEST_INGEST_API_KEY = "test-ingest-api-key-0001"
TEST_DATABASE_URL = "postgresql+asyncpg://aquametric:aquametric@localhost:5433/aquametric_test"


@pytest.fixture
def settings(monkeypatch: pytest.MonkeyPatch) -> Iterator[Settings]:
    """Provide deterministic settings and drop the cache afterwards so tests never leak env."""
    monkeypatch.setenv("ENV", "ci")
    monkeypatch.setenv("INGEST_API_KEY", TEST_INGEST_API_KEY)
    monkeypatch.setenv("DATABASE_URL", TEST_DATABASE_URL)
    monkeypatch.setenv("CORS_ORIGINS", "http://localhost:5174")
    monkeypatch.delenv("S3_BUCKET", raising=False)
    get_settings.cache_clear()
    try:
        yield get_settings()
    finally:
        get_settings.cache_clear()


@pytest.fixture
def app(settings: Settings) -> FastAPI:
    """Build a fresh app per test.

    The import is deferred so settings are validated only after the env vars exist.
    """
    from app.main import create_app

    return create_app()


@pytest.fixture
async def client(app: FastAPI) -> AsyncIterator[AsyncClient]:
    """Drive the ASGI app in-process, running lifespan so engine setup and disposal happen."""
    async with app.router.lifespan_context(app):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as http_client:
            yield http_client

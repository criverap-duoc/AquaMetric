"""Application factory: settings, logging, middleware, error handlers and routers."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Final

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app import __version__
from app.core.config import get_settings
from app.core.db import create_engine, create_session_factory
from app.core.errors import register_exception_handlers
from app.core.logging import RequestIdMiddleware, configure_logging
from app.routers import catalog, health, ingest, screening, spc

# Single place that versions the public API; routers declare only their resource segment.
API_PREFIX: Final = "/api/v1"


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Build the engine once per process and release its pool on shutdown."""
    settings = get_settings()
    engine = create_engine(settings)
    app.state.db_engine = engine
    app.state.session_factory = create_session_factory(engine)
    try:
        yield
    finally:
        await engine.dispose()


def create_app() -> FastAPI:
    settings = get_settings()
    configure_logging(settings.log_level)

    app = FastAPI(
        title="AquaMetric API",
        version=__version__,
        summary="Water quality monitoring with statistical process control (SPC).",
        lifespan=lifespan,
    )

    # Registered first so it is the innermost middleware: CORS stays outermost and
    # still decorates the responses produced by the error handlers.
    app.add_middleware(RequestIdMiddleware)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=False,
        allow_methods=["GET", "POST"],
        allow_headers=["Content-Type", "X-API-Key", "Idempotency-Key", "X-Request-ID"],
        expose_headers=["X-Request-ID"],
    )

    register_exception_handlers(app)
    app.include_router(health.router, prefix=API_PREFIX)
    app.include_router(catalog.router, prefix=API_PREFIX)
    app.include_router(screening.router, prefix=API_PREFIX)
    app.include_router(ingest.router, prefix=API_PREFIX)
    app.include_router(spc.router, prefix=API_PREFIX)
    return app


# Uvicorn target: `uvicorn app.main:app`.
app = create_app()

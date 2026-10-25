"""Ingestion endpoint: the single write path for observations (ADR-009)."""

from typing import Annotated

from fastapi import APIRouter, Depends, Header, Request, status

from app.core.db import SessionDep
from app.core.dependencies import CatalogDep, ClockDep
from app.core.security import get_ingest_key
from app.schemas.ingest import MAX_OBSERVATIONS_PER_BATCH, IngestRequest, IngestResponse
from app.services.ingest_service import IngestService

router = APIRouter(prefix="/ingest", tags=["ingest"])


@router.post(
    "/observations",
    response_model=IngestResponse,
    status_code=status.HTTP_200_OK,
    summary="Ingest an atomic batch of observations",
    description=(
        "Stores one batch from TerraPlan (a site, its samples and their observations) in a "
        "single transaction: either every row is stored or nothing is. The `Idempotency-Key` "
        "header is mandatory; replaying the same body returns the stored answer without "
        "reprocessing, and rows that already exist are counted as `duplicates`. "
        f"At most {MAX_OBSERVATIONS_PER_BATCH} observations per batch."
    ),
    responses={
        400: {"description": "VALIDATION_ERROR, UNKNOWN_PARAMETER or UNIT_MISMATCH"},
        401: {"description": "UNAUTHORIZED: missing or invalid X-API-Key"},
        409: {
            "description": (
                "CONFLICT (site code with another id), CATALOG_VERSION_MISMATCH "
                "or IDEMPOTENCY_KEY_REUSE"
            )
        },
        500: {"description": "Unhandled error, returned as application/problem+json"},
    },
)
async def ingest_observations(
    request: Request,
    payload: IngestRequest,
    session: SessionDep,
    catalog: CatalogDep,
    clock: ClockDep,
    idempotency_key: Annotated[str, Header(alias="Idempotency-Key")],
    _api_key: Annotated[str, Depends(get_ingest_key)],
) -> IngestResponse:
    """Authenticate, then delegate: the router holds no rules of its own (02 §5)."""
    raw_body = await request.body()
    service = IngestService(session, catalog, clock)
    return await service.ingest(payload, idempotency_key, raw_body)

"""Pipeline status endpoint: public, read-only and honest about the AWS deployment (ADR-004)."""

from typing import Annotated

from fastapi import APIRouter, Query

from app.core.config import SettingsDep
from app.core.db import SessionDep
from app.schemas.pipeline import PipelineStatusResponse
from app.services.pipeline_service import PipelineService

router = APIRouter(prefix="/pipeline", tags=["pipeline"])


@router.get(
    "/status",
    response_model=PipelineStatusResponse,
    summary="Pipeline and ingestion status",
    description=(
        "Recent ingest batches (from `aquametric.ingest_idempotency`) and the newest observation "
        "of each site. `awsDeployed = false` means the S3 → Lambda path of ADR-002 is not running "
        "and the demo feeds the API directly: an informative state, not an error."
    ),
    responses={500: {"description": "Unhandled error, returned as application/problem+json"}},
)
async def get_pipeline_status(
    session: SessionDep,
    settings: SettingsDep,
    limit: Annotated[
        int, Query(ge=1, le=50, description="Cuántos lotes recientes devolver (1–50).")
    ] = 10,
) -> PipelineStatusResponse:
    """Public read: the log holds no personal data, only batch keys and counters."""
    return await PipelineService(session, settings).get_status(limit)

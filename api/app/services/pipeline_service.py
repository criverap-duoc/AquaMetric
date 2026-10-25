"""Orchestration of the pipeline screen: translate two read-only queries into its contract.

No AWS call happens here. The screen reports what the database knows and one flag says whether
the S3 → Lambda path exists, so «Pipeline AWS no desplegado» is an informative state, not an
error (ADR-004).
"""

from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings
from app.models import IngestIdempotency
from app.repositories.pipeline_repository import PipelineRepository
from app.schemas.pipeline import BatchSummary, PipelineStatusResponse, SiteLastRead


class PipelineService:
    """Build the status payload the `/pipeline` screen renders."""

    def __init__(self, session: AsyncSession, settings: Settings) -> None:
        self._settings = settings
        self._repository = PipelineRepository(session)

    async def get_status(self, limit: int = 10) -> PipelineStatusResponse:
        """Recent batches plus the last reading per site.

        `accepted`/`duplicates` are read from the response stored with the idempotency key: that
        is the only place the numbers a batch actually wrote survive, and replaying the query
        would recount rows that later batches may have added.
        """
        batches = await self._repository.recent_batches(limit)
        readings = await self._repository.last_observation_per_site()
        return PipelineStatusResponse(
            aws_deployed=self._settings.aws_pipeline_deployed,
            recent_batches=[_batch_summary(batch) for batch in batches],
            last_observation_per_site=[
                SiteLastRead(
                    site_id=reading.site_id,
                    site_code=reading.site_code,
                    parameter_code=reading.parameter_code,
                    analyzed_at=reading.analyzed_at,
                    value=None if reading.value is None else float(reading.value),
                    unit_code=reading.unit_code,
                )
                for reading in readings
            ],
            limit=limit,
        )


def _batch_summary(batch: IngestIdempotency) -> BatchSummary:
    """The stored response is untyped JSON (a database boundary), so it is read defensively."""
    stored: dict[str, Any] = batch.response or {}
    return BatchSummary(
        key=batch.key,
        received_at=batch.received_at,
        status=batch.status,
        accepted=int(stored.get("accepted", 0)),
        duplicates=int(stored.get("duplicates", 0)),
    )

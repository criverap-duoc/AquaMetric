"""Read-only queries behind `GET /api/v1/pipeline/status` (ADR-002, ADR-004).

Two questions, two queries: what the `ingest_idempotency` log remembers and what the newest
observation of each site is. Nothing here touches AWS, because the API must answer with the
pipeline undeployed.
"""

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import IngestIdempotency, Observation, Site


@dataclass(frozen=True, slots=True)
class SiteLastObservation:
    """The newest reading of one site, with the parameter it measured."""

    site_id: UUID
    site_code: str
    parameter_code: str
    analyzed_at: datetime
    value: Decimal | None
    unit_code: str


class PipelineRepository:
    """Read-only access to the ingestion log and the observation table."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def recent_batches(self, limit: int) -> list[IngestIdempotency]:
        """Newest batches first; `key` breaks ties so two batches of the same second are stable."""
        rows = await self._session.scalars(
            select(IngestIdempotency)
            .order_by(IngestIdempotency.received_at.desc(), IngestIdempotency.key)
            .limit(limit)
        )
        return list(rows)

    async def last_observation_per_site(self) -> list[SiteLastObservation]:
        """One row per site: a window function ranks each site's readings and keeps the newest.

        `row_number() OVER (PARTITION BY site_id ORDER BY analyzed_at DESC)` avoids the
        `DISTINCT ON` extension (deprecated in the ORM) and behaves the same: the outer query
        keeps `position = 1` and sorts by site code so the screen shows a stable list.
        """
        ranked = (
            select(
                Observation.site_id,
                Site.code.label("site_code"),
                Observation.parameter_code,
                Observation.analyzed_at,
                Observation.value,
                Observation.unit_code,
                func.row_number()
                .over(
                    partition_by=Observation.site_id,
                    order_by=Observation.analyzed_at.desc(),
                )
                .label("position"),
            )
            .join(Site, Site.id == Observation.site_id)
            .subquery()
        )
        result = await self._session.execute(
            select(ranked).where(ranked.c.position == 1).order_by(ranked.c.site_code)
        )
        return [
            SiteLastObservation(
                site_id=row.site_id,
                site_code=row.site_code,
                parameter_code=row.parameter_code,
                analyzed_at=row.analyzed_at,
                value=row.value,
                unit_code=row.unit_code,
            )
            for row in result
        ]

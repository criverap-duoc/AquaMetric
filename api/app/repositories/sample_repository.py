"""Persistence for `aquametric.sample`: upserts plus the existence check ingestion needs."""

from collections.abc import Sequence
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Sample
from app.schemas.ingest import SampleIn


class SampleRepository:
    """TerraPlan republishes samples as the laboratory advances, so this is an upsert."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def upsert_by_id(self, sample_in: SampleIn) -> Sample:
        """Insert or update one sample, without committing."""
        sample = await self._session.get(Sample, sample_in.id)
        if sample is None:
            sample = Sample(
                id=sample_in.id,
                site_id=sample_in.site_id,
                campaign_id=sample_in.campaign_id,
                matrix=sample_in.matrix,
                collected_at=sample_in.collected_at,
                lab_received_at=sample_in.lab_received_at,
                status=sample_in.status,
            )
            self._session.add(sample)
            return sample

        sample.site_id = sample_in.site_id
        sample.campaign_id = sample_in.campaign_id
        sample.matrix = sample_in.matrix
        sample.collected_at = sample_in.collected_at
        sample.lab_received_at = sample_in.lab_received_at
        sample.status = sample_in.status
        return sample

    async def existing_ids(self, sample_ids: Sequence[UUID]) -> set[UUID]:
        """Which of these samples are already stored (an observation may cite a stored one)."""
        if not sample_ids:
            return set()
        result = await self._session.scalars(select(Sample.id).where(Sample.id.in_(sample_ids)))
        return set(result.all())

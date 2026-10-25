"""Persistence for `aquametric.ingest_idempotency`: the stored answer per `Idempotency-Key`."""

from datetime import datetime
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.models import IngestIdempotency


class IngestIdempotencyRepository:
    """One row per key, written in the same transaction as the rows it acknowledges."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_key(self, key: str) -> IngestIdempotency | None:
        """The record for a key, or `None` when the request is new."""
        return await self._session.get(IngestIdempotency, key)

    async def save(
        self,
        *,
        key: str,
        payload_hash: str,
        response: dict[str, Any],
        status: str,
        received_at: datetime,
    ) -> None:
        """Stage the record; the caller's transaction decides whether it survives.

        `received_at` comes from the injected clock, so the stored answer carries the same
        instant the service logged (no `datetime.now()` inside services, per 02 §3).
        """
        self._session.add(
            IngestIdempotency(
                key=key,
                payload_hash=payload_hash,
                response=response,
                status=status,
                received_at=received_at,
            )
        )
        await self._session.flush()

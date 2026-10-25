"""Persistence for `aquametric.observation`: insert-only, conflicts skipped (ADR-009)."""

from collections.abc import Sequence
from typing import Any, cast

from sqlalchemy import Table
from sqlalchemy.dialects import postgresql
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Observation

# Explicit constraint name: the natural key is the contract, not an implementation detail.
NATURAL_KEY_CONSTRAINT = "uq_obs_natural_key"


class ObservationRepository:
    """Observations are evidence: they are inserted, never updated nor replaced."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def bulk_insert_ignore_conflicts(self, observations: Sequence[Observation]) -> int:
        """Insert in bulk, skipping rows whose natural key is already stored.

        Returns:
            How many rows were actually written; the caller derives the duplicates count.

        `ON CONFLICT DO NOTHING` keeps a retried batch from failing: the unique constraint
        `uq_obs_natural_key` (site, parameter, analyzed_at, sample, source) is the guard. Rows
        are batched by SQLAlchemy (`insertmanyvalues`), so a 5000-row batch never approaches
        PostgreSQL's parameter limit.
        """
        if not observations:
            return 0
        table = cast("Table", Observation.__table__)
        written = 0
        for rows in _group_by_columns(observations):
            statement = (
                postgresql.insert(table)
                .on_conflict_do_nothing(constraint=NATURAL_KEY_CONSTRAINT)
                .returning(table.c.id)
            )
            result = await self._session.scalars(statement, rows)
            written += len(result.all())
        return written


def _group_by_columns(observations: Sequence[Observation]) -> list[list[dict[str, Any]]]:
    """Split the batch into groups of rows that set exactly the same columns.

    One INSERT compiles its column list from the first row of the batch, so a batch that mixes a
    censored row (`qualifier`, `loq`, no `value`) with a measured one cannot travel as a single
    `executemany`: PostgreSQL would demand a value for the missing column. Grouping keeps every
    statement homogeneous, and columns nobody set are still left to their server defaults.
    """
    groups: dict[tuple[str, ...], list[dict[str, Any]]] = {}
    for observation in observations:
        row = _row_values(observation)
        groups.setdefault(tuple(sorted(row)), []).append(row)
    return list(groups.values())


def _row_values(observation: Observation) -> dict[str, Any]:
    """Column values explicitly set on the instance, so server defaults still apply."""
    return {
        column.key: value
        for column in Observation.__table__.columns
        if (value := getattr(observation, column.key, None)) is not None
    }

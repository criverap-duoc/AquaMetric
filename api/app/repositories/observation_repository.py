"""Persistence for `aquametric.observation`: insert-only, conflicts skipped (ADR-009).

Writes go through the ingest service; the reads here answer the Series screen and its counters.
Both share `_filters()`, so the rows of a page and the `total` printed next to them can never
describe two different windows.
"""

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Any, cast
from uuid import UUID

from sqlalchemy import ColumnElement, Table, func, select
from sqlalchemy.dialects import postgresql
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Observation, Site

# Explicit constraint name: the natural key is the contract, not an implementation detail.
NATURAL_KEY_CONSTRAINT = "uq_obs_natural_key"


@dataclass(frozen=True, slots=True)
class ObservationAggregate:
    """Counters of one window; the three statistics ignore censored rows (ADR-003)."""

    count: int
    censored_count: int
    min_value: float | None
    max_value: float | None
    mean_value: float | None


class ObservationRepository:
    """Observations are evidence: they are inserted, never updated nor replaced."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def list_paginated(
        self,
        *,
        site_id: UUID | None,
        parameter_code: str | None,
        from_dt: datetime | None,
        to_dt: datetime | None,
        page: int,
        page_size: int,
        order: str = "desc",
    ) -> tuple[list[tuple[Observation, str]], int]:
        """One page of observations with the code of their site, plus the total of the filter.

        The join on `site` is what spares the screen a second request: the table and the charts
        label rows by site code, and `aquametric.site` is small enough for an inner join to cost
        nothing next to reading the observation itself (ADR-006 index).

        `analyzed_at` carries a second sort key on purpose: a paginated list without a total order
        can repeat or skip rows between pages when two observations share a timestamp.
        """
        filters = _filters(site_id, parameter_code, from_dt, to_dt)
        total = await self._session.scalar(
            select(func.count()).select_from(Observation).where(*filters)
        )
        ordering = (
            Observation.analyzed_at.asc() if order == "asc" else Observation.analyzed_at.desc()
        )
        result = await self._session.execute(
            select(Observation, Site.code)
            .join(Site, Site.id == Observation.site_id)
            .where(*filters)
            .order_by(ordering, Observation.id)
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        return [(observation, site_code) for observation, site_code in result.all()], int(
            total or 0
        )

    async def aggregate(
        self,
        *,
        site_id: UUID | None,
        parameter_code: str | None,
        from_dt: datetime | None,
        to_dt: datetime | None,
    ) -> ObservationAggregate:
        """Count, censored count, minimum, maximum and mean of one window in a single query.

        The censored count travels as a `FILTER (WHERE value IS NULL)` aggregate, so the screen
        learns «hay 3 resultados < LOQ» without downloading the rows to count them.
        """
        filters = _filters(site_id, parameter_code, from_dt, to_dt)
        statement = select(
            # `count` would collide with `tuple.count` when the Row is read by attribute.
            func.count().label("rows_total"),
            func.count().filter(Observation.value.is_(None)).label("censored_total"),
            func.min(Observation.value).label("min_value"),
            func.max(Observation.value).label("max_value"),
            func.avg(Observation.value).label("mean_value"),
        ).where(*filters)
        row = (await self._session.execute(statement)).one()
        return ObservationAggregate(
            count=int(row.rows_total),
            censored_count=int(row.censored_total),
            min_value=_as_float(row.min_value),
            max_value=_as_float(row.max_value),
            mean_value=_as_float(row.mean_value),
        )

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


def _filters(
    site_id: UUID | None,
    parameter_code: str | None,
    from_dt: datetime | None,
    to_dt: datetime | None,
) -> list[ColumnElement[bool]]:
    """Conditions of the public filters; an absent filter contributes nothing.

    Building the list once and sharing it between the page and the count is what keeps
    `meta.total` honest: both queries always describe the same subset.
    """
    filters: list[ColumnElement[bool]] = []
    if site_id is not None:
        filters.append(Observation.site_id == site_id)
    if parameter_code is not None:
        filters.append(Observation.parameter_code == parameter_code)
    if from_dt is not None:
        filters.append(Observation.analyzed_at >= from_dt)
    if to_dt is not None:
        filters.append(Observation.analyzed_at <= to_dt)
    return filters


def _as_float(value: Decimal | None) -> float | None:
    """`Numeric` columns arrive as `Decimal`; the contract publishes floats."""
    return None if value is None else float(value)


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

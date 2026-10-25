"""Persistence for `aquametric.spc_baseline` and the observation window each chart needs.

ADR-001: the Phase I limits are estimated once and frozen, so a chart computed months later can
be explained with the same numbers. The unique key `(site, parameter, phase)` makes the write an
upsert — re-posting a baseline recomputes it instead of accumulating stale copies.
"""

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.dialects import postgresql
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Observation, SpcBaseline

PHASE_I = "phase_i"
PHASE_II = "phase_ii"


class SpcBaselineRepository:
    """Reads the series and stores the frozen limits; committing is the service's job."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_baseline(
        self, site_id: uuid.UUID, parameter_code: str, phase: str
    ) -> SpcBaseline | None:
        """The stored baseline of one series and phase, or `None` when it was never frozen."""
        statement = select(SpcBaseline).where(
            SpcBaseline.site_id == site_id,
            SpcBaseline.parameter_code == parameter_code,
            SpcBaseline.phase == phase,
        )
        return await self._session.scalar(statement)

    async def get_observations(
        self,
        site_id: uuid.UUID,
        parameter_code: str,
        *,
        after: datetime | None = None,
        limit: int,
    ) -> list[Observation]:
        """The oldest `limit` observations of a series, in chronological order.

        `after` is exclusive on purpose: the service passes the last Phase I timestamp, and the
        baseline point itself must not be scanned again as Phase II monitoring data. Reading the
        oldest rows (not the newest) is what makes the Phase I window reproducible.
        """
        statement = select(Observation).where(
            Observation.site_id == site_id,
            Observation.parameter_code == parameter_code,
        )
        if after is not None:
            statement = statement.where(Observation.analyzed_at > after)
        statement = statement.order_by(Observation.analyzed_at.asc()).limit(limit)
        return list(await self._session.scalars(statement))

    async def upsert_baseline(
        self,
        *,
        site_id: uuid.UUID,
        parameter_code: str,
        phase: str,
        method: str,
        n_points: int,
        data_range_start: datetime,
        data_range_end: datetime,
        center_line: float,
        ucl: float,
        lcl: float,
        catalog_version: str,
        computed_at: datetime,
    ) -> SpcBaseline:
        """Insert the baseline or replace it in place; one row per `(site, parameter, phase)`.

        The surrogate `id` is regenerated on conflict so a client can tell two recomputations of
        the same baseline apart, while the natural key keeps exactly one stored row. `computedAt`
        comes from the injected clock, never from `now()` in Python (02 §3).
        """
        values: dict[str, Any] = {
            "site_id": site_id,
            "parameter_code": parameter_code,
            "phase": phase,
            "method": method,
            "n_points": n_points,
            "data_range_start": data_range_start,
            "data_range_end": data_range_end,
            "center_line": center_line,
            "ucl": ucl,
            "lcl": lcl,
            "catalog_version": catalog_version,
            "computed_at": computed_at,
        }
        statement = (
            postgresql.insert(SpcBaseline)
            .values(**values)
            .on_conflict_do_update(
                index_elements=[
                    SpcBaseline.site_id,
                    SpcBaseline.parameter_code,
                    SpcBaseline.phase,
                ],
                set_={**values, "id": func.gen_random_uuid()},
            )
            .returning(SpcBaseline)
        )
        return (await self._session.scalars(statement)).one()

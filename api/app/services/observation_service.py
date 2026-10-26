"""Read side of the observations: resolve the filters, then let the repository query.

The validations exist because an empty page would hide a mistake: a `siteId` that is not stored
is a 404 and a `parameterCode` outside the catalog is a 400, never «no data» (01 §5). A window
whose start is later than its end is a 400 as well: it can only mean the dates were swapped.
"""

from datetime import datetime
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.catalog import Catalog
from app.core.errors import NotFoundError, UnknownParameterError, ValidationFailedError
from app.models import Observation
from app.repositories.observation_repository import ObservationRepository
from app.repositories.site_repository import SiteRepository
from app.schemas.observation import (
    ObservationAggregateRead,
    ObservationListMeta,
    ObservationRead,
    ObservationsResponse,
)


class ObservationService:
    """Public read of `aquametric.observation`, the series the screens plot."""

    def __init__(self, session: AsyncSession, catalog: Catalog) -> None:
        self._catalog = catalog
        self._repository = ObservationRepository(session)
        self._sites = SiteRepository(session)

    async def list_observations(
        self,
        *,
        site_id: UUID | None,
        parameter_code: str | None,
        from_dt: datetime | None,
        to_dt: datetime | None,
        page: int,
        page_size: int,
        order: str = "desc",
    ) -> ObservationsResponse:
        """One page of observations, newest first unless `order = asc` is asked for.

        `asc` exists for the SPC screens: the control chart needs the series in chronological
        order to slice the Phase I window, and reversing a page of the future in the client would
        mean reading rows the chart never sees.
        """
        await self._validate(site_id, parameter_code, from_dt, to_dt)
        rows, total = await self._repository.list_paginated(
            site_id=site_id,
            parameter_code=parameter_code,
            from_dt=from_dt,
            to_dt=to_dt,
            page=page,
            page_size=page_size,
            order=order,
        )
        return ObservationsResponse(
            data=[_observation_read(observation, site_code) for observation, site_code in rows],
            meta=ObservationListMeta(
                page=page,
                page_size=page_size,
                total=total,
                from_=from_dt,
                to=to_dt,
            ),
        )

    async def aggregate(
        self,
        *,
        site_id: UUID | None,
        parameter_code: str | None,
        from_dt: datetime | None,
        to_dt: datetime | None,
    ) -> ObservationAggregateRead:
        """Counters of one window, so a screen can print «n» and a mean without the rows."""
        await self._validate(site_id, parameter_code, from_dt, to_dt)
        aggregate = await self._repository.aggregate(
            site_id=site_id,
            parameter_code=parameter_code,
            from_dt=from_dt,
            to_dt=to_dt,
        )
        return ObservationAggregateRead(
            count=aggregate.count,
            censored_count=aggregate.censored_count,
            min_value=aggregate.min_value,
            max_value=aggregate.max_value,
            mean_value=aggregate.mean_value,
        )

    async def _validate(
        self,
        site_id: UUID | None,
        parameter_code: str | None,
        from_dt: datetime | None,
        to_dt: datetime | None,
    ) -> None:
        """Reject the filters that cannot describe a series, before touching the big table."""
        if parameter_code is not None and parameter_code not in self._catalog.parameters:
            raise UnknownParameterError(
                f"El parámetro '{parameter_code}' no existe en el catálogo."
            )
        if site_id is not None and await self._sites.get_by_id(site_id) is None:
            raise NotFoundError(f"El sitio '{site_id}' no existe.")
        if from_dt is not None and to_dt is not None and from_dt > to_dt:
            raise ValidationFailedError(
                "El rango de fechas está invertido: 'from' es posterior a 'to'."
            )


def _observation_read(observation: Observation, site_code: str) -> ObservationRead:
    """ORM row plus the code of its site, which the join already fetched."""
    return ObservationRead(
        id=observation.id,
        site_id=observation.site_id,
        site_code=site_code,
        sample_id=observation.sample_id,
        parameter_code=observation.parameter_code,
        value=None if observation.value is None else float(observation.value),
        unit_code=observation.unit_code,
        qualifier=observation.qualifier,
        loq=None if observation.loq is None else float(observation.loq),
        method=observation.method,
        analyzed_at=observation.analyzed_at,
        qc_flag=observation.qc_flag,
        source=observation.source,
    )

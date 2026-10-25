"""Persistence for `aquametric.site`: the only module that runs SQL against that table."""

from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import ConflictError
from app.models import Site
from app.schemas.ingest import SiteIn


def _as_decimal(value: float | None) -> Decimal | None:
    """Coordinates are `Numeric(9, 6)`: the column expects a `Decimal`, not a float.

    `Decimal(str(x))` keeps the value the client sent (`-33.45`), while `Decimal(float)` would
    drag in the binary-float baggage (…499999999998).
    """
    return None if value is None else Decimal(str(value))


class SiteRepository:
    """Upsert by id; a `code` owned by another id is a client conflict, not a corruption."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def list_paginated(
        self,
        page: int,
        page_size: int,
        is_active: bool | None = None,
    ) -> tuple[list[Site], int]:
        """One page of sites plus the total that matches the filter.

        Ordering is by `code`, not by insertion: a paginated list without a stable sort can
        repeat or skip rows between pages. The count and the page share the same filter, so the
        footer of the table can never disagree with the rows it shows.
        """
        filters = [] if is_active is None else [Site.is_active.is_(is_active)]
        total = await self._session.scalar(select(func.count()).select_from(Site).where(*filters))
        rows = await self._session.scalars(
            select(Site)
            .where(*filters)
            .order_by(Site.code)
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        return list(rows), int(total or 0)

    async def upsert_by_id(self, site_in: SiteIn) -> Site:
        """Insert or update one site, without committing (the service owns the unit of work)."""
        site = await self._session.get(Site, site_in.id)
        if site is None:
            owner_id = await self._session.scalar(select(Site.id).where(Site.code == site_in.code))
            if owner_id is not None:
                raise ConflictError(
                    f"El código de sitio '{site_in.code}' ya existe con otro id ({owner_id}); "
                    f"el lote usa {site_in.id}."
                )
            site = Site(
                id=site_in.id,
                code=site_in.code,
                name=site_in.name,
                water_body_type=site_in.water_body_type,
                latitude=_as_decimal(site_in.latitude),
                longitude=_as_decimal(site_in.longitude),
                is_active=site_in.is_active,
            )
            self._session.add(site)
            return site

        site.name = site_in.name
        site.water_body_type = site_in.water_body_type
        site.latitude = _as_decimal(site_in.latitude)
        site.longitude = _as_decimal(site_in.longitude)
        site.is_active = site_in.is_active
        return site

"""Persistence for `aquametric.site`: the only module that runs SQL against that table."""

from decimal import Decimal

from sqlalchemy import select
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

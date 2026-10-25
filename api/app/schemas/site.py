"""Public contract of `GET /api/v1/sites` (01 §5).

The site is the entity every sample and observation belongs to, so the UI needs its real uuid:
the SPC endpoints key their series by `siteId`, and until this endpoint existed the selectors
guessed the identifier from the demo data.
"""

from typing import Literal
from uuid import UUID

from pydantic import Field

from app.schemas.base import CamelModel

WaterBodyType = Literal["river", "lake", "estuary", "groundwater", "effluent", "drinking"]


class SiteRead(CamelModel):
    """A sampling site. `code` is the stable identifier TerraPlan and the simulator exchange."""

    id: UUID
    code: str
    name: str
    water_body_type: WaterBodyType = Field(
        description="Tipo de cuerpo de agua: river, lake, estuary, groundwater, effluent, drinking."
    )
    latitude: float | None = Field(
        description="Latitud WGS84; nula si el sitio no está georreferenciado."
    )
    longitude: float | None = Field(description="Longitud WGS84; nula por la misma razón.")
    is_active: bool = Field(description="`false` para sitios fuera de operación (se listan igual).")


class SiteListMeta(CamelModel):
    """Standard pagination envelope (02 §4): the same shape every list endpoint returns."""

    page: int = Field(ge=1, description="Página devuelta, desde 1.")
    page_size: int = Field(ge=1, description="Tamaño de página solicitado.")
    total: int = Field(ge=0, description="Sitios que cumplen el filtro, en todas las páginas.")


class SiteListResponse(CamelModel):
    """One page of sites plus the counters the table footer needs."""

    data: list[SiteRead]
    meta: SiteListMeta

"""Public contract of `GET /api/v1/observations` (01 §5).

The Series screen used to plot a replica of the demo data built in the browser; with this endpoint
it plots what `aquametric.observation` stores. Every row carries the site **code** next to its
uuid, so one request is enough: no second call against `/sites` to translate the id.
"""

from typing import Literal
from uuid import UUID

from pydantic import AwareDatetime, Field

from app.schemas.base import CamelModel

QcFlag = Literal["ok", "suspect", "failed"]
ObservationSource = Literal["lab", "field", "sensor"]
Qualifier = Literal["<", ">"]
# Chronological order is what a time series needs; newest first is what a table needs.
ObservationOrder = Literal["asc", "desc"]


class ObservationRead(CamelModel):
    """One stored measurement, with the unit and the qualifier **as reported** (01 §5)."""

    id: UUID
    site_id: UUID
    site_code: str = Field(description="Código estable del sitio (p. ej. `SIM-RIO-MAIPO-01`).")
    sample_id: UUID | None = Field(
        description="Muestra de laboratorio de la que cuelga la lectura; `null` en sensores."
    )
    parameter_code: str = Field(description="Código del parámetro del catálogo, p. ej. `PH`.")
    value: float | None = Field(
        description="Valor medido; `null` cuando el resultado es censurado (`< LOQ`)."
    )
    unit_code: str = Field(
        description="Unidad original de la medición: el API nunca convierte en silencio."
    )
    qualifier: Qualifier | None = Field(
        description="`<` (censurado) o `>`; `null` cuando hay valor medido."
    )
    loq: float | None = Field(description="Límite de cuantificación del resultado censurado.")
    method: str | None = Field(description="Método analítico declarado por el laboratorio.")
    analyzed_at: AwareDatetime = Field(
        description="Instante del análisis, en UTC: las fechas sin zona se rechazan."
    )
    qc_flag: QcFlag = Field(description="Control de calidad: `ok`, `suspect` o `failed`.")
    source: ObservationSource = Field(
        description="Origen de la lectura: `lab`, `field` o `sensor`."
    )


class ObservationListMeta(CamelModel):
    """Pagination envelope plus the window that was actually applied (02 §4)."""

    page: int = Field(ge=1, description="Página devuelta, desde 1.")
    page_size: int = Field(ge=1, description="Tamaño de página solicitado.")
    total: int = Field(
        ge=0, description="Observaciones que cumplen el filtro, en todas las páginas."
    )
    from_: AwareDatetime | None = Field(
        default=None,
        alias="from",
        description="Inicio del rango aplicado (UTC); `null` si no se filtró por fecha.",
    )
    to: AwareDatetime | None = Field(
        default=None,
        description="Fin del rango aplicado (UTC); `null` si no se filtró por fecha.",
    )


class ObservationsResponse(CamelModel):
    """One page of observations plus the counters the table footer needs."""

    data: list[ObservationRead]
    meta: ObservationListMeta


class ObservationAggregateRead(CamelModel):
    """Summary of a window: «cuántas, entre qué valores y con qué media», without the rows.

    Counts include censored results, but the three statistics only use measured values: a
    `< LOQ` row has no number, and substituting `LOQ/2` would publish an invented measurement
    (ADR-003).
    """

    count: int = Field(ge=0, description="Observaciones en la ventana, censuradas incluidas.")
    censored_count: int = Field(
        ge=0, description="Resultados censurados (`< LOQ`) incluidos en `count`."
    )
    min_value: float | None = Field(description="Mínimo de los valores medidos.")
    max_value: float | None = Field(description="Máximo de los valores medidos.")
    mean_value: float | None = Field(description="Media de los valores medidos.")

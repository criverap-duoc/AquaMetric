"""Public contract of the SPC endpoints (ADR-001, 01 §4.1).

Every limit in this module is a **control** limit: estimated from a Phase I baseline, drawn as a
dashed line and named after the chart it belongs to. The words `limits`, `specLimits` and `loq`
stay apart on purpose (01 §4.1): a control limit says what the process usually does, not what a
regulation allows. `warnings[]` always carries the disclaimer, so no client can render a chart
as a compliance statement (ADR-010).
"""

from typing import Literal
from uuid import UUID

from pydantic import AwareDatetime, Field

from app.schemas.base import CamelModel, StrictCamelModel


class ControlLimitsRead(CamelModel):
    """One chart: center line, 3-sigma limits and the sigma they were estimated from."""

    center: float = Field(description="Línea central del gráfico (x̄ para I, MR̄ para MR).")
    ucl: float = Field(
        description="Límite de control superior (3σ). No es un límite normativo ni un LOQ."
    )
    lcl: float = Field(
        description="Límite de control inferior (3σ). No es un límite normativo ni un LOQ."
    )
    sigma: float = Field(
        description="Desviación estándar estimada del estadístico graficado (no la del proceso)."
    )
    method: str = Field(
        description="Gráfico al que pertenecen los límites: `imr_individuals`, `imr_moving_range`, "
        "`xbar_r_xbar` o `xbar_r_range`."
    )
    n_points: int = Field(description="Puntos usados para estimar los límites.")


class RuleViolationRead(CamelModel):
    """One signal of the Nelson/Western Electric scan (01 §4.1)."""

    rule: str = Field(description="Código de la regla: R1, R2, R3, R4 o R5.")
    index: int = Field(description="Posición del punto que completa el patrón (desde 0).")
    description: str = Field(description="Frase en español que la UI muestra junto al punto.")


class BaselineRead(CamelModel):
    """A persisted Phase I baseline, with what makes the limits reproducible (ADR-001)."""

    id: UUID
    site_id: UUID
    parameter_code: str
    phase: str = Field(
        description="Fase del baseline: `phase_i` (límites congelados) o `phase_ii`."
    )
    method: str = Field(description="Método usado para estimar los límites: `imr` o `xbar_r`.")
    n_points: int = Field(description="Puntos válidos que entraron en el cálculo.")
    data_range_start: AwareDatetime = Field(description="Primera observación usada (UTC).")
    data_range_end: AwareDatetime = Field(description="Última observación usada (UTC).")
    center_line: float
    ucl: float
    lcl: float
    catalog_version: str = Field(
        description="Versión del catálogo vigente al calcular los límites."
    )
    computed_at: AwareDatetime = Field(description="Instante del cálculo (UTC).")


class ControlChartResponse(CamelModel):
    """The chart plus everything needed to read it without guessing.

    `baselinePersisted = false` means the limits were computed on the fly from the oldest rows
    available: they are correct for this answer but they are not frozen, so `POST /spc/baseline`
    is what makes them reproducible across calls.
    """

    individuals: ControlLimitsRead
    moving_range: ControlLimitsRead | None = Field(
        default=None, description="Carta MR; se omite si el método es X̄-R."
    )
    xbar: ControlLimitsRead | None = Field(
        default=None, description="Carta X̄; nula mientras no existan subgrupos configurados."
    )
    r: ControlLimitsRead | None = Field(
        default=None, description="Carta R; nula por la misma razón."
    )
    violations: list[RuleViolationRead] = Field(
        default_factory=list, description="Señales detectadas en la fase de monitoreo."
    )
    baseline_persisted: bool = Field(
        description="`true` si los límites vienen de una línea base persistida; `false` si se "
        "calcularon al vuelo."
    )
    baseline_metadata: dict[str, float | int | str] = Field(
        default_factory=dict,
        description="n, censurados y fracción censurada usados, más el método y el mínimo exigido.",
    )
    warnings: list[str] = Field(
        default_factory=list, description="Advertencias obligatorias: no dictamen de cumplimiento."
    )


class BaselineUpsertRequest(StrictCamelModel):
    """Freeze the Phase I limits of one series; the CPU work happens in `POST /spc/baseline`."""

    site_id: UUID = Field(description="Sitio de la serie.")
    parameter_code: str = Field(description="Código del parámetro del catálogo, p. ej. PH.")
    method: Literal["imr", "xbar_r"] = Field(
        default="imr",
        description="Método de la carta. En el MVP solo `imr` se persiste; `xbar_r` se rechaza con "
        "un 400 explicando el motivo.",
    )
    subgroup_size: int | None = Field(
        default=None,
        ge=2,
        le=10,
        description="Tamaño de subgrupo; solo aplica al método `xbar_r`.",
    )
    baseline_points: int = Field(
        default=20,
        ge=20,
        le=200,
        description="Puntos de la Fase I; el mínimo de 20 es el que exige ADR-001.",
    )
    apply_censored_policy: bool = Field(
        default=True,
        description="Sustituir los datos censurados por LOQ/2 en el cálculo (ADR-003). Si es "
        "`false`, una serie con censurados se rechaza en lugar de sustituirlos.",
    )

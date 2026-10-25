"""Public contract of the referential screening endpoints (ADR-010, ADR-012).

`ScreeningFlag` is the only judgement the MVP publishes, and `warnings[]` always carries the
referential disclaimer, so no client can render a flag without the context that qualifies it.
"""

from pydantic import AwareDatetime, Field

from app.schemas.base import CamelModel, StrictCamelModel
from app.screening import ScreeningFlag


class LimitApplied(CamelModel):
    """The catalog limit used for the comparison, with what is needed to audit it.

    `status` travels with the limit on purpose: a `draft-verified` limit is shown as
    «Pendiente de validación», never as an enforceable threshold.
    """

    regulation_code: str = Field(
        description="Código de la regulación del catálogo (p. ej. NCh1333)."
    )
    statistic: str
    min: float | None
    max: float | None
    unit_code: str
    status: str
    context: str | None
    monitoring_area_code: str | None
    quality_level: str | None


class CatalogLimitRead(LimitApplied):
    """Same limit, but identified: the catalog browser lists several parameters at once."""

    parameter_code: str


class ScreeningRequest(StrictCamelModel):
    """One observation plus the scope it must be screened in.

    `regulation` together with `context` (NCh 1.333) or `monitoringArea` + `qualityLevel`
    (D.S. 53/2014) selects a single limit. Anything ambiguous comes back as `not_evaluable`,
    never as a guess.
    """

    parameter_code: str
    value: float
    unit_code: str
    analyzed_at: AwareDatetime
    regulation: str = Field(
        description=(
            "Código de la regulación (p. ej. NCh1333). Se llama `regulation` en las entradas y "
            "`regulationCode` en las respuestas, igual que el campo del catálogo."
        )
    )
    context: str | None = None
    monitoring_area: str | None = None
    quality_level: str | None = None


class ScreeningResponse(CamelModel):
    """The flag, the Spanish reason and the mandatory disclaimers."""

    flag: ScreeningFlag
    reason: str
    limit_applied: LimitApplied | None
    exceedance_ratio: float | None
    warnings: list[str]


class ScreeningLimitsResponse(CamelModel):
    """Limits the caller may screen against.

    `requiresValidated` explains why a listed limit still cannot produce a comparison.
    """

    limits: list[LimitApplied]
    requires_validated: bool

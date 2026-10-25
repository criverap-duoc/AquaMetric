"""Read-only catalog contract: what the UI needs to label values, units and limits."""

from pydantic import AwareDatetime, Field

from app.schemas.base import CamelModel


class CatalogMetaResponse(CamelModel):
    """Provenance of the synchronized catalog, including the chemist's signature state."""

    version: str
    sha256: str
    generated_at: AwareDatetime
    status: str
    validated_by: str | None
    validated_at: AwareDatetime | None


class ParameterRead(CamelModel):
    """A measured quantity. `canonicalUnitCode` fixes the unit every stored value uses."""

    code: str
    name_es: str
    category: str
    canonical_unit_code: str
    decimals: int
    measurement_type: str
    status: str
    mvp_optional: bool


class UnitRead(CamelModel):
    """A unit and its explicit factor to the canonical unit of its dimension."""

    code: str
    name_es: str
    dimension: str
    factor_to_canonical: float


class RegulationRead(CamelModel):
    """A regulation the catalog quotes limits from."""

    code: str
    name: str
    jurisdiction: str
    scope: str


class LimitRead(CamelModel):
    """One catalog limit, identified by parameter and regulation.

    There is no `id`: the synchronized catalog has no surrogate key for a limit, its identity is
    the tuple (parameter, regulation, context, monitoring area, quality level). Inventing one here
    would suggest a stability the source data does not have.
    """

    parameter_code: str
    regulation_code: str = Field(
        description=(
            "Código de la regulación del catálogo (p. ej. NCh1333). Se filtra como "
            "`regulation` y se publica como `regulationCode`, igual que el campo del catálogo."
        )
    )
    statistic: str = Field(
        description="Cómo evalúa la norma el parámetro: `max_absolute`, `P5_P95`, etc."
    )
    min: float | None = Field(description="Cota inferior; nula si la norma no la fija.")
    max: float | None = Field(description="Cota superior; nula si la norma no la fija.")
    max_increase_over_natural: float | None = None
    unit_code: str
    status: str = Field(
        description="`draft-verified` (pendiente de validación por el químico) o `validated`."
    )
    context: str | None = Field(default=None, description="Uso del agua (NCh 1.333).")
    monitoring_area_code: str | None = Field(
        default=None, description="Área de vigilancia (D.S. 53/2014)."
    )
    quality_level: str | None = Field(default=None, description="Nivel de calidad (D.S. 53/2014).")


class LimitsMeta(CamelModel):
    """Counters of the filtered set, so the UI can warn without a second request.

    `validatedCount` is the number of limits that can actually produce a screening flag; the rest
    are shown as «Pendiente de validación» (ADR-010).
    """

    total: int
    validated_count: int
    draft_count: int


class LimitsResponse(CamelModel):
    """One page-less list of limits plus its status counters (the catalog is small and static)."""

    data: list[LimitRead]
    meta: LimitsMeta

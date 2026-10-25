"""Read-only catalog contract: what the UI needs to label values, units and limits."""

from pydantic import AwareDatetime

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

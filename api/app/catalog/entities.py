"""Immutable catalog entities (the shape screening and the API consume).

Pure data: no file access, no validation of the source documents. `loader.py` reads and
validates the synchronized files and builds these values; keeping them apart is what makes
the loader readable and lets tests build an entity without touching the filesystem.
"""

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True, slots=True)
class Parameter:
    """A measured quantity, with the unit every stored value is normalised to."""

    code: str
    name_es: str
    category: str
    canonical_unit_code: str
    decimals: int
    measurement_type: str
    status: str
    mvp_optional: bool


@dataclass(frozen=True, slots=True)
class Unit:
    """A unit of measure; `factor_to_canonical` converts to the canonical unit of its dimension."""

    code: str
    name_es: str
    dimension: str
    factor_to_canonical: float


@dataclass(frozen=True, slots=True)
class Limit:
    """A reference limit published by a regulation.

    `statistic` says how the regulation evaluates the parameter (`max_absolute`, `P95`, ...),
    so a single observation may or may not be comparable against it. `context` is the use of
    water (NCh 1.333) and `monitoring_area_code`/`quality_level` locate D.S. 53/2014 limits;
    `min`/`max` stay `None` when the regulation does not constrain that side.
    """

    parameter_code: str
    regulation_code: str
    statistic: str
    min: float | None
    max: float | None
    max_increase_over_natural: float | None
    unit_code: str
    status: str
    context: str | None
    monitoring_area_code: str | None
    quality_level: str | None


@dataclass(frozen=True, slots=True)
class Regulation:
    """A regulation the catalog quotes limits from."""

    code: str
    name: str
    jurisdiction: str
    scope: str


@dataclass(frozen=True, slots=True)
class Catalog:
    """The whole catalog, indexed by code and with limits in a deterministic order.

    `sha256` is the logical-bundle hash TerraPlan declares in `catalog.meta.json`; it is not
    the hash of that file (a file cannot contain its own hash). `status`, `validated_by` and
    `validated_at` are the chemist's signature state: screening compares nothing until a limit
    itself is `validated`, and the API publishes this state so the UI can say so.
    """

    version: str
    sha256: str
    generated_at: datetime
    status: str
    validated_by: str | None
    validated_at: datetime | None
    parameters: dict[str, Parameter]
    units: dict[str, Unit]
    limits: tuple[Limit, ...]
    regulations: dict[str, Regulation]

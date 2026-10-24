"""Read-only loader for the catalog copy synchronized from TerraPlan.

`catalog/` is a byte-for-byte copy owned by TerraPlan (written only by
`scripts/sync_catalog.py`); this module never writes to it. Everything is parsed and
validated once at startup, so screening and the API look values up by code without
touching the filesystem per request.
"""

import json
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Final

META_FILE: Final = "catalog.meta.json"
PARAMETERS_FILE: Final = "parameters.v1.json"
UNITS_FILE: Final = "units.v1.json"
LIMITS_FILE: Final = "limits.v1.json"
REGULATIONS_FILE: Final = "regulations.v1.json"

# Mirrors the file list of scripts/sync_catalog.py; both must stay in step.
CATALOG_FILES: Final = (META_FILE, PARAMETERS_FILE, UNITS_FILE, LIMITS_FILE, REGULATIONS_FILE)

# Statistics a single observation can be compared against with no multi-year series.
# Everything else (`maxIncreaseOverNatural` needs a natural-value baseline, P5/P95/P5_P95
# need a three-year window) is not evaluable in the MVP: see ADR-012.
ABSOLUTE_STATISTICS: Final = frozenset({"max_absolute", "min_absolute"})


class CatalogLoadError(Exception):
    """Raised when the synchronized catalog is missing or inconsistent.

    Deliberately not a `DomainError`: this surfaces at startup, not inside an HTTP request,
    so no problem+json handler should ever translate it.
    """


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
    the hash of that file (a file cannot contain its own hash).
    """

    version: str
    sha256: str
    generated_at: datetime
    parameters: dict[str, Parameter]
    units: dict[str, Unit]
    limits: tuple[Limit, ...]
    regulations: dict[str, Regulation]


def _read_json(path: Path) -> dict[str, Any]:
    """Read one catalog document.

    JSON is an untyped boundary: every field this module uses is validated by the
    `_require_*` helpers below, which is why `Any` stops here.
    """
    try:
        payload: Any = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise CatalogLoadError(
            f"{path.name}: JSON inválido ({exc.msg}, línea {exc.lineno})"
        ) from exc
    if not isinstance(payload, dict):
        raise CatalogLoadError(f"{path.name}: se esperaba un objeto JSON en la raíz")
    return payload


def _require_str(raw: Mapping[str, Any], field: str, *, path: Path) -> str:
    value = raw.get(field)
    if not isinstance(value, str) or not value:
        raise CatalogLoadError(f"{path.name}: campo '{field}' ausente o no es texto")
    return value


def _optional_str(raw: Mapping[str, Any], field: str, *, path: Path) -> str | None:
    value = raw.get(field)
    if value is None:
        return None
    if not isinstance(value, str):
        raise CatalogLoadError(f"{path.name}: campo '{field}' no es texto")
    return value


def _require_int(raw: Mapping[str, Any], field: str, *, path: Path) -> int:
    value = raw.get(field)
    if isinstance(value, bool) or not isinstance(value, int):
        raise CatalogLoadError(f"{path.name}: campo '{field}' ausente o no es entero")
    return value


def _require_bool(raw: Mapping[str, Any], field: str, *, path: Path) -> bool:
    value = raw.get(field)
    if not isinstance(value, bool):
        raise CatalogLoadError(f"{path.name}: campo '{field}' ausente o no es booleano")
    return value


def _optional_float(raw: Mapping[str, Any], field: str, *, path: Path) -> float | None:
    value = raw.get(field)
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, int | float):
        raise CatalogLoadError(f"{path.name}: campo '{field}' no es numérico")
    return float(value)


def _require_objects(raw: Mapping[str, Any], field: str, *, path: Path) -> list[dict[str, Any]]:
    value = raw.get(field)
    if not isinstance(value, list) or not value:
        raise CatalogLoadError(f"{path.name}: campo '{field}' ausente o vacío")
    items: list[dict[str, Any]] = []
    for index, item in enumerate(value):
        if not isinstance(item, dict):
            raise CatalogLoadError(f"{path.name}: '{field}[{index}]' no es un objeto")
        items.append(item)
    return items


def _parse_timestamp(value: str, *, path: Path) -> datetime:
    """Parse the ISO-8601 timestamp of `updatedAt`; a value without timezone is rejected."""
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise CatalogLoadError(
            f"{path.name}: campo 'updatedAt' no es ISO-8601 ('{value}')"
        ) from exc
    if parsed.tzinfo is None:
        raise CatalogLoadError(f"{path.name}: campo 'updatedAt' sin zona horaria ('{value}')")
    return parsed.astimezone(UTC)


def _build_parameter(raw: Mapping[str, Any], *, path: Path) -> Parameter:
    return Parameter(
        code=_require_str(raw, "code", path=path),
        name_es=_require_str(raw, "nameEs", path=path),
        category=_require_str(raw, "category", path=path),
        canonical_unit_code=_require_str(raw, "canonicalUnitCode", path=path),
        decimals=_require_int(raw, "decimals", path=path),
        measurement_type=_require_str(raw, "measurementType", path=path),
        status=_require_str(raw, "status", path=path),
        mvp_optional=_require_bool(raw, "mvpOptional", path=path),
    )


def _build_unit(raw: Mapping[str, Any], *, path: Path) -> Unit:
    factor = _optional_float(raw, "factorToCanonical", path=path)
    if factor is None:
        raise CatalogLoadError(f"{path.name}: campo 'factorToCanonical' ausente")
    return Unit(
        code=_require_str(raw, "code", path=path),
        name_es=_require_str(raw, "nameEs", path=path),
        dimension=_require_str(raw, "dimension", path=path),
        factor_to_canonical=factor,
    )


def _build_limit(raw: Mapping[str, Any], *, path: Path) -> Limit:
    return Limit(
        parameter_code=_require_str(raw, "parameterCode", path=path),
        regulation_code=_require_str(raw, "regulationCode", path=path),
        statistic=_require_str(raw, "statistic", path=path),
        min=_optional_float(raw, "min", path=path),
        max=_optional_float(raw, "max", path=path),
        max_increase_over_natural=_optional_float(raw, "maxIncreaseOverNatural", path=path),
        unit_code=_require_str(raw, "unitCode", path=path),
        status=_require_str(raw, "status", path=path),
        context=_optional_str(raw, "context", path=path),
        monitoring_area_code=_optional_str(raw, "monitoringAreaCode", path=path),
        quality_level=_optional_str(raw, "qualityLevel", path=path),
    )


def _build_regulation(raw: Mapping[str, Any], *, path: Path) -> Regulation:
    return Regulation(
        code=_require_str(raw, "code", path=path),
        name=_require_str(raw, "name", path=path),
        jurisdiction=_require_str(raw, "jurisdiction", path=path),
        scope=_require_str(raw, "scope", path=path),
    )


def _index_by_code[CodeItem: Parameter | Unit | Regulation](
    items: Iterable[CodeItem], *, path: Path
) -> dict[str, CodeItem]:
    """Index entities by code; a duplicated code would shadow a value silently, so it fails."""
    index: dict[str, CodeItem] = {}
    for item in items:
        if item.code in index:
            raise CatalogLoadError(f"{path.name}: código duplicado '{item.code}'")
        index[item.code] = item
    return index


def _limit_sort_key(limit: Limit) -> tuple[str, str, str]:
    """Order by regulation, parameter and the scope that disambiguates (area or context)."""
    return (
        limit.regulation_code,
        limit.parameter_code,
        limit.monitoring_area_code or limit.context or "",
    )


def _read_versioned(catalog_dir: Path, name: str, *, version: str) -> dict[str, Any]:
    """Read a `.v1.json` file and require the version declared in `catalog.meta.json`."""
    path = catalog_dir / name
    payload = _read_json(path)
    found = _require_str(payload, "version", path=path)
    if found != version:
        raise CatalogLoadError(
            f"{name}: version '{found}' no coincide con '{version}' de {META_FILE}"
        )
    return payload


def _load_parameters(catalog_dir: Path, *, version: str) -> dict[str, Parameter]:
    path = catalog_dir / PARAMETERS_FILE
    raw_parameters = _require_objects(
        _read_versioned(catalog_dir, PARAMETERS_FILE, version=version), "parameters", path=path
    )
    return _index_by_code((_build_parameter(raw, path=path) for raw in raw_parameters), path=path)


def _load_units(catalog_dir: Path, *, version: str) -> dict[str, Unit]:
    path = catalog_dir / UNITS_FILE
    raw_units = _require_objects(
        _read_versioned(catalog_dir, UNITS_FILE, version=version), "units", path=path
    )
    return _index_by_code((_build_unit(raw, path=path) for raw in raw_units), path=path)


def _load_regulations(catalog_dir: Path, *, version: str) -> dict[str, Regulation]:
    path = catalog_dir / REGULATIONS_FILE
    raw_regulations = _require_objects(
        _read_versioned(catalog_dir, REGULATIONS_FILE, version=version), "regulations", path=path
    )
    return _index_by_code((_build_regulation(raw, path=path) for raw in raw_regulations), path=path)


def _load_limits(catalog_dir: Path, *, version: str) -> tuple[Limit, ...]:
    path = catalog_dir / LIMITS_FILE
    raw_limits = _require_objects(
        _read_versioned(catalog_dir, LIMITS_FILE, version=version), "limits", path=path
    )
    limits = sorted((_build_limit(raw, path=path) for raw in raw_limits), key=_limit_sort_key)
    return tuple(limits)


def _validate_references(
    parameters: Mapping[str, Parameter],
    units: Mapping[str, Unit],
    regulations: Mapping[str, Regulation],
    limits: Sequence[Limit],
) -> None:
    """Every cross-file reference must resolve; the API never guesses a missing code."""
    for parameter in parameters.values():
        if parameter.canonical_unit_code not in units:
            raise CatalogLoadError(
                f"{PARAMETERS_FILE}: el parámetro '{parameter.code}' declara la unidad canónica "
                f"'{parameter.canonical_unit_code}', que no existe en {UNITS_FILE}"
            )

    for limit in limits:
        scope = limit.monitoring_area_code or limit.context or "sin contexto"
        if limit.regulation_code not in regulations:
            raise CatalogLoadError(
                f"{LIMITS_FILE}: el límite de '{limit.parameter_code}' ({scope}) referencia la "
                f"regulación '{limit.regulation_code}', que no existe en {REGULATIONS_FILE}"
            )
        if limit.parameter_code not in parameters:
            raise CatalogLoadError(
                f"{LIMITS_FILE}: el límite de '{limit.parameter_code}' ({scope}) referencia un "
                f"parámetro que no existe en {PARAMETERS_FILE}"
            )
        if limit.unit_code not in units:
            raise CatalogLoadError(
                f"{LIMITS_FILE}: el límite de '{limit.parameter_code}' ({scope}) usa la unidad "
                f"'{limit.unit_code}', que no existe en {UNITS_FILE}"
            )


def load_catalog(catalog_dir: Path) -> Catalog:
    """Load and validate the synchronized catalog.

    Reads the five files, requires the same `version` everywhere (a half-synced copy is never
    valid), builds the entities and checks that every reference resolves across files.

    The loader filters **nothing**: every limit is returned whatever its `statistic` or
    `status`. Deciding what a single observation can be compared against is the screening
    service's job, so the day the chemist promotes limits to `validated` nothing here changes.
    See `docs/adr/012-screening-single-observation.md`.

    Raises:
        CatalogLoadError: the catalog is missing, unreadable or internally inconsistent. It is
            raised at startup, never inside a request, so it must not become problem+json.
    """
    missing = [name for name in CATALOG_FILES if not (catalog_dir / name).is_file()]
    if missing:
        raise CatalogLoadError(
            f"{catalog_dir}: faltan archivos del catálogo ({', '.join(missing)}). "
            "Ejecuta `python scripts/sync_catalog.py` para copiarlos desde TerraPlan."
        )

    meta_path = catalog_dir / META_FILE
    meta = _read_json(meta_path)
    version = _require_str(meta, "version", path=meta_path)
    bundle_sha256 = _require_str(meta, "sha256", path=meta_path)
    generated_at = _parse_timestamp(_require_str(meta, "updatedAt", path=meta_path), path=meta_path)

    parameters = _load_parameters(catalog_dir, version=version)
    units = _load_units(catalog_dir, version=version)
    regulations = _load_regulations(catalog_dir, version=version)
    limits = _load_limits(catalog_dir, version=version)
    _validate_references(parameters, units, regulations, limits)

    return Catalog(
        version=version,
        sha256=bundle_sha256,
        generated_at=generated_at,
        parameters=parameters,
        units=units,
        limits=limits,
        regulations=regulations,
    )

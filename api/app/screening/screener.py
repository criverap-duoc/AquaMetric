"""Referential screening of a single observation against the catalog (ADR-012).

Pure module: no I/O, no database, no clock (02 §7). The limit arrives as an argument, so the
same code answers for the API, for the tests and for any future batch report.

It answers one question — «is this value inside the range the regulation publishes?» — and
never whether the site complies: D.S. 53/2014 is evaluated on a three-year P95/P5 series and
NCh 1.333 on the use of the water, and neither is something one sample can provide.
"""

from dataclasses import dataclass
from enum import StrEnum

from app.catalog.entities import Limit, Parameter
from app.catalog.loader import ABSOLUTE_STATISTICS

# Statistic that compares against the natural value of the site, not against a fixed range.
MAX_INCREASE_OVER_NATURAL = "maxIncreaseOverNatural"
# Statistics D.S. 53/2014 evaluates over a three-year window; never per observation.
TRIENNIAL_STATISTICS = frozenset({"P95", "P5", "P5_P95"})
# Only limits the chemist signed may produce a comparison (ADR-012 §2.2).
VALIDATED_STATUS = "validated"


class ScreeningFlag(StrEnum):
    """Outcome of comparing one value with one validated limit.

    Separate from data quality and from regulatory status on purpose: «no se pudo evaluar»,
    «el dato es dudoso» and «cumple/no cumple» are different statements with different owners.
    """

    normal = "normal"
    above_range = "above_range"
    below_range = "below_range"
    not_evaluable = "not_evaluable"


@dataclass(frozen=True, slots=True)
class ScreeningResult:
    """The flag, the Spanish reason shown to the user, the limit used and how far it went.

    `limit_applied` is filled whenever a limit was selected, even if the flag ended up being
    `not_evaluable`: the UI needs to show *which* limit is pending validation or which
    statistic is out of scope. `exceedance_ratio` is `None` unless the flag is out of range.
    """

    flag: ScreeningFlag
    reason: str
    limit_applied: Limit | None
    exceedance_ratio: float | None


def _number(value: float) -> str:
    """Plain decimal text with a comma separator, matching the Spanish copy of the API."""
    return f"{value:.6g}".replace(".", ",")


def _not_evaluable(reason: str, *, limit: Limit | None) -> ScreeningResult:
    """Build the repeated `not_evaluable` shape once, so the policy reads as one block."""
    return ScreeningResult(
        flag=ScreeningFlag.not_evaluable,
        reason=reason,
        limit_applied=limit,
        exceedance_ratio=None,
    )


def select_applicable_limit(
    limits: tuple[Limit, ...],
    parameter_code: str,
    regulation_code: str,
    context: str | None = None,
    monitoring_area_code: str | None = None,
    quality_level: str | None = None,
) -> Limit | None:
    """Pick the single limit that applies to (parameter, regulation, scope).

    Only the scope qualifiers the candidate limits actually use are required: NCh 1.333 limits
    carry `context` (use of the water), D.S. 53/2014 limits carry `monitoring_area_code` plus
    `quality_level`. A missing qualifier, or more than one surviving candidate, returns `None`:
    screening never guesses between two limits (ADR-012 §2.2 point 6).

    Args:
        limits: every limit of the catalog; the loader does not pre-filter.
        parameter_code: catalog code of the parameter, e.g. `PH`.
        regulation_code: catalog code of the regulation, e.g. `NCh1333`.
        context: use of the water (`vida_acuatica`, `riego`), required by NCh 1.333 limits.
        monitoring_area_code: D.S. 53/2014 monitoring area, e.g. `MA-1`.
        quality_level: D.S. 53/2014 quality level, e.g. `conservacion`.

    Returns:
        The only applicable limit, or `None` when there is no unambiguous match.
    """
    candidates = [
        limit
        for limit in limits
        if limit.parameter_code == parameter_code and limit.regulation_code == regulation_code
    ]

    if any(limit.context is not None for limit in candidates):
        if context is None:
            return None
        candidates = [limit for limit in candidates if limit.context == context]

    if any(limit.monitoring_area_code is not None for limit in candidates):
        if monitoring_area_code is None:
            return None
        candidates = [
            limit for limit in candidates if limit.monitoring_area_code == monitoring_area_code
        ]

    if any(limit.quality_level is not None for limit in candidates):
        if quality_level is None:
            return None
        candidates = [limit for limit in candidates if limit.quality_level == quality_level]

    return candidates[0] if len(candidates) == 1 else None


def screen_observation(
    value: float | None,
    qualifier: str | None,
    loq: float | None,
    parameter: Parameter,
    limit: Limit | None,
) -> ScreeningResult:
    """Compare one observation against one limit and explain the answer in Spanish.

    The value must arrive in the parameter's canonical unit (the service converts explicitly
    before calling, `01 §5`); a limit quoted in another unit is never compared silently.

    Args:
        value: measured value; `None` for a censored observation (`< LOQ`).
        qualifier: `"<"` on censored rows, `None` otherwise.
        loq: limit of quantification, present only on censored rows.
        parameter: catalog parameter, used for the unit guard.
        limit: limit chosen by `select_applicable_limit`, or `None` when none applies.

    Returns:
        A `ScreeningResult`; never raises, so any input renders as a state.
    """
    if value is None:
        if qualifier == "<" and loq is not None:
            return _not_evaluable(
                f"Observación censurada (valor < LOQ {_number(loq)}); "
                "no evaluable individualmente.",
                limit=limit,
            )
        return _not_evaluable("Observación sin valor; no evaluable individualmente.", limit=limit)

    if limit is None:
        return _not_evaluable(
            "No hay límite aplicable para la combinación regulación/contexto seleccionada.",
            limit=None,
        )

    if limit.status != VALIDATED_STATUS:
        return _not_evaluable(
            f"Límite en estado '{limit.status}'; pendiente de validación por el químico.",
            limit=limit,
        )

    if limit.statistic == MAX_INCREASE_OVER_NATURAL:
        return _not_evaluable(
            "Requiere baselineReference por sitio (no disponible en MVP).",
            limit=limit,
        )

    if limit.statistic in TRIENNIAL_STATISTICS:
        return _not_evaluable(
            f"Requiere análisis trienal P95/P5 según {limit.regulation_code}; "
            "fuera del alcance del screening individual.",
            limit=limit,
        )

    if limit.statistic not in ABSOLUTE_STATISTICS:
        return _not_evaluable(
            f"Estadístico '{limit.statistic}' no soportado en MVP.",
            limit=limit,
        )

    if limit.unit_code != parameter.canonical_unit_code:
        return _not_evaluable(
            f"El límite está en {limit.unit_code} y el valor en {parameter.canonical_unit_code}; "
            "se requiere conversión explícita.",
            limit=limit,
        )

    if limit.statistic == "max_absolute" and limit.max is not None and value > limit.max:
        return ScreeningResult(
            flag=ScreeningFlag.above_range,
            reason=(
                f"Valor {_number(value)} supera el máximo {_number(limit.max)} {limit.unit_code}."
            ),
            limit_applied=limit,
            exceedance_ratio=value / limit.max if limit.max else None,
        )

    if limit.min is not None and value < limit.min:
        return ScreeningResult(
            flag=ScreeningFlag.below_range,
            reason=(
                f"Valor {_number(value)} está bajo el mínimo {_number(limit.min)} "
                f"{limit.unit_code}."
            ),
            limit_applied=limit,
            exceedance_ratio=limit.min / value if value else None,
        )

    return ScreeningResult(
        flag=ScreeningFlag.normal,
        reason="Dentro del rango de referencia.",
        limit_applied=limit,
        exceedance_ratio=None,
    )

"""Process capability (Cp, Cpk) against **normative** limits — never against control limits.

Pure module (02 §7). Numbers come in, an immutable verdict goes out.

The distinction that the whole project rests on (01 §4.1): control limits describe what the
process *is doing today*, normative limits describe what it *must* do. Cp/Cpk compare the first
with the second, and only make sense when (a) the normative limits were signed by the chemist
(`status = validated`, ADR-012) and (b) the process is in control. This function receives
plain numbers, so it cannot verify (b): the service must refuse to call it for a chart with
violations and say so in the UI.
"""

from collections.abc import Sequence
from math import log10

import numpy as np

from app.spc.constants import (
    CAPABILITY_ORIENTATIVE_BELOW,
    MIN_CAPABILITY_POINTS,
    SKEWNESS_THRESHOLD,
)
from app.spc.errors import InsufficientDataError
from app.spc.types import CapabilityResult
from app.spc.validation import require_finite

LOG10_TRANSFORM = "log10"

WARNING_SMALL_SAMPLE = (
    f"n < {CAPABILITY_ORIENTATIVE_BELOW}; el cálculo de capacidad es orientativo."
)
WARNING_SKEWED = (
    f"Distribución sesgada (skewness > {SKEWNESS_THRESHOLD:g}); considera transform='log10'."
)


def compute_capability(
    observations: Sequence[float],
    spec_limits: tuple[float | None, float | None],
    transform: str | None = None,
) -> CapabilityResult:
    """Compute Cp and Cpk of a series against its normative limits.

    Formulas (Montgomery, 7th ed., ch. 8):

        sigma = std(x, ddof=1)              sample standard deviation (acceptable here: the
                                            capability index describes the spread of all points,
                                            not the short-term variation of the chart)
        Cp  = (USL - LSL) / (6 * sigma)     only with both limits
        Cpk = min((USL - x-bar) / (3 * sigma), (x-bar - LSL) / (3 * sigma))
              (USL - x-bar) / (3 * sigma)   with only USL
              (x-bar - LSL) / (3 * sigma)   with only LSL

    With `transform="log10"` the data **and both limits** are log-transformed, so the index is
    computed on the same scale twice; transforming only the data would divide metres by log10
    of metres and produce a meaningless number.

    Args:
        observations: the series, already in the parameter's canonical unit.
        spec_limits: `(lsl, usl)`; either side may be `None`, not both.
        transform: `None` or `"log10"` for right-skewed parameters (turbidity, coliforms).

    Returns:
        The indices plus the caveats an analyst must read before quoting them.

    Raises:
        InsufficientDataError: fewer than 20 observations, or no normative limit at all.
        ValueError: NaN/infinity, unknown transform, non-positive data or limits under `log10`,
            or zero standard deviation.
    """
    data = require_finite(observations)
    lower_spec, upper_spec = spec_limits
    count = len(data)
    if count < MIN_CAPABILITY_POINTS:
        raise InsufficientDataError(
            f"Se requieren al menos {MIN_CAPABILITY_POINTS} observaciones para estimar la "
            f"capacidad (hay {count})."
        )
    if lower_spec is None and upper_spec is None:
        raise InsufficientDataError(
            "Se requiere al menos un límite normativo (inferior o superior) para calcular la "
            "capacidad."
        )

    values, lower, upper = _on_scale(data, lower_spec, upper_spec, transform)
    array = np.asarray(values, dtype=float)
    sigma = float(np.std(array, ddof=1))
    if sigma == 0:
        raise ValueError(
            "La desviación estándar es cero; sin variación no se puede calcular la capacidad."
        )
    mean = float(np.mean(array))

    cp = (upper - lower) / (6 * sigma) if upper is not None and lower is not None else None
    cpk = _cpk(mean=mean, sigma=sigma, lower=lower, upper=upper)
    return CapabilityResult(
        cp=cp,
        cpk=cpk,
        n=count,
        transform=transform,
        assumption_warning=_assumption_warning(values, mean, sigma, count, transform),
    )


def _on_scale(
    data: list[float],
    lower_spec: float | None,
    upper_spec: float | None,
    transform: str | None,
) -> tuple[list[float], float | None, float | None]:
    """Put the data and the normative limits on the same scale before comparing them."""
    if transform is None:
        return data, lower_spec, upper_spec
    if transform != LOG10_TRANSFORM:
        raise ValueError(
            f"Transformación '{transform}' no soportada; las disponibles son "
            f"transform='{LOG10_TRANSFORM}' o sin transformación."
        )
    if any(value <= 0 for value in data):
        raise ValueError(
            "La transformación log10 requiere valores positivos: hay observaciones en cero o "
            "negativas."
        )
    has_non_positive_limit = (lower_spec is not None and lower_spec <= 0) or (
        upper_spec is not None and upper_spec <= 0
    )
    if has_non_positive_limit:
        raise ValueError(
            "La transformación log10 requiere límites normativos positivos (el inferior es "
            "cero o negativo)."
        )
    return (
        [log10(value) for value in data],
        log10(lower_spec) if lower_spec is not None else None,
        log10(upper_spec) if upper_spec is not None else None,
    )


def _cpk(
    *,
    mean: float,
    sigma: float,
    lower: float | None,
    upper: float | None,
) -> float:
    """Distance from the mean to the nearest normative limit, in 3-sigma units."""
    candidates: list[float] = []
    if upper is not None:
        candidates.append((upper - mean) / (3 * sigma))
    if lower is not None:
        candidates.append((mean - lower) / (3 * sigma))
    return min(candidates)


def _assumption_warning(
    values: list[float],
    mean: float,
    sigma: float,
    count: int,
    transform: str | None,
) -> str | None:
    """Collect the Spanish caveats that must travel with the indices."""
    warnings: list[str] = []
    if count < CAPABILITY_ORIENTATIVE_BELOW:
        warnings.append(WARNING_SMALL_SAMPLE)
    if transform is None and abs(_skewness(values, mean, sigma)) > SKEWNESS_THRESHOLD:
        warnings.append(WARNING_SKEWED)
    return " ".join(warnings) if warnings else None


def _skewness(values: list[float], mean: float, sigma: float) -> float:
    """Fisher's moment coefficient of skewness g1 = mean(((x - mean) / sigma) ** 3).

    `sigma` is the sample standard deviation (ddof=1); the sign matters, and so does its
    magnitude: a strongly left-skewed series breaks the normality assumption exactly as a
    right-skewed one does, hence the `|g1| > 1` test in the caller.
    """
    return sum(((value - mean) / sigma) ** 3 for value in values) / len(values)

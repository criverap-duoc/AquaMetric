"""Control charts computed in Phase I: I-MR (the default) and X-bar/R (ADR-001).

Pure module (02 §7): no I/O, no clock, no global state, no database. Every function receives a
sequence of numbers and returns frozen dataclasses, so the API, the simulator and the golden
tests run exactly the same arithmetic.

Sigma is **always** estimated from the short-term variation (`MR-bar/d2` or `R-bar/d2`), never
from the global standard deviation: `np.std` inflates the limits as soon as the process changes
level, which is precisely the event the chart is supposed to flag.
"""

from collections.abc import Sequence
from math import sqrt
from statistics import fmean

from app.spc.constants import (
    A2_TABLE,
    D2_N2,
    D2_TABLE,
    D3_TABLE,
    D4_N2,
    D4_TABLE,
    K_IMR,
    MIN_BASELINE_POINTS,
    SUBGROUP_MAX,
    SUBGROUP_MIN,
)
from app.spc.errors import InsufficientDataError
from app.spc.types import ControlLimits, IMRResult, XbarRResult
from app.spc.validation import require_finite

METHOD_IMR_INDIVIDUALS = "imr_individuals"
METHOD_IMR_MOVING_RANGE = "imr_moving_range"
METHOD_XBAR_R_XBAR = "xbar_r_xbar"
METHOD_XBAR_R_RANGE = "xbar_r_range"


def compute_imr(observations: Sequence[float]) -> IMRResult:
    """Compute the individuals (I) and moving-range (MR) charts of a Phase I baseline.

    Formulas (Montgomery, *Introduction to Statistical Quality Control*, 7th ed., ch. 6):

        MR_i = |x_i - x_(i-1)|                      i = 2..n
        MR-bar = mean(MR)
        sigma_est = MR-bar / d2,  d2 = 1.128 (n = 2)
        center = x-bar = mean(x)
        UCL = x-bar + 2.66 * MR-bar (2.66 = 3/d2, d2 = 1.128 for n = 2)
        LCL = x-bar - 2.66 * MR-bar
        R chart: center = MR-bar, UCL = 3.267 * MR-bar (D4 for n = 2), LCL = 0

    Args:
        observations: the Phase I series, in chronological order, one value per point.

    Returns:
        The two charts, with `individuals.sigma` holding the process estimate (MR-bar/d2).

    Raises:
        InsufficientDataError: fewer than 20 observations; limits built on fewer points are not
            reproducible.
        ValueError: NaN/infinity in the series, or every moving range equal to zero (a constant
            series has no variation to estimate sigma from, and the limits would collapse onto
            the center line).
    """
    data = require_finite(observations)
    count = len(data)
    if count < MIN_BASELINE_POINTS:
        raise InsufficientDataError(
            f"Se requieren al menos {MIN_BASELINE_POINTS} observaciones válidas para la línea "
            f"base (hay {count})."
        )

    center = fmean(data)
    moving_ranges = [abs(data[index] - data[index - 1]) for index in range(1, count)]
    mr_bar = fmean(moving_ranges)
    sigma = mr_bar / D2_N2
    if sigma == 0:
        raise ValueError(
            "Todos los rangos móviles son cero (serie constante); no hay variación que permita "
            "estimar límites de control."
        )

    spread = K_IMR * mr_bar
    individuals = ControlLimits(
        center=center,
        ucl=center + spread,
        lcl=center - spread,
        sigma=sigma,
        method=METHOD_IMR_INDIVIDUALS,
        n_points=count,
    )
    moving_range = ControlLimits(
        center=mr_bar,
        ucl=D4_N2 * mr_bar,
        lcl=0.0,
        sigma=sigma,
        method=METHOD_IMR_MOVING_RANGE,
        n_points=len(moving_ranges),
    )
    return IMRResult(individuals=individuals, moving_range=moving_range)


def compute_xbar_r(subgroups: Sequence[Sequence[float]]) -> XbarRResult:
    """Compute the X-bar and R charts of a Phase I baseline with rational subgroups.

    Formulas (Montgomery, 7th ed., ch. 6):

        x-bar_j = mean(subgroup_j),  R_j = max(subgroup_j) - min(subgroup_j)
        R-bar = mean(R),  sigma_est = R-bar / d2(n)
        X-bar chart: center = mean(x-bar), UCL/LCL = center +/- A2(n) * R-bar
        R chart: center = R-bar, UCL = D4(n) * R-bar, LCL = D3(n) * R-bar

    `xbar.sigma` is `sigma_est / sqrt(n)` — the standard deviation of the plotted *subgroup
    mean*, which is what makes `center ± k * sigma` reproduce A2(n) * R-bar for k = 3.

    Args:
        subgroups: subgroups in chronological order, each with the same size between 2 and 10.

    Returns:
        Both charts plus the subgroup size.

    Raises:
        InsufficientDataError: no subgroups at all.
        ValueError: subgroup size outside 2..10, subgroups of different sizes, NaN/infinity, or
            every range equal to zero (constant subgroups).
    """
    if not subgroups:
        raise InsufficientDataError("Se requiere al menos un subgrupo para la carta X̄-R.")

    cleaned = [require_finite(subgroup, what="Los subgrupos") for subgroup in subgroups]
    size = len(cleaned[0])
    if not SUBGROUP_MIN <= size <= SUBGROUP_MAX:
        raise ValueError(
            f"El tamaño de subgrupo debe estar entre {SUBGROUP_MIN} y {SUBGROUP_MAX} "
            f"observaciones (recibido {size})."
        )
    for position, subgroup in enumerate(cleaned[1:], start=2):
        if len(subgroup) != size:
            raise ValueError(
                f"El subgrupo {position} tiene {len(subgroup)} observaciones y el primero "
                f"{size}; todos los subgrupos deben tener el mismo tamaño."
            )

    means = [fmean(subgroup) for subgroup in cleaned]
    ranges = [max(subgroup) - min(subgroup) for subgroup in cleaned]
    xbar_center = fmean(means)
    r_bar = fmean(ranges)
    sigma = r_bar / D2_TABLE[size]
    if sigma == 0:
        raise ValueError(
            "Todos los rangos son cero (subgrupos constantes); no hay variación que permita "
            "estimar límites de control."
        )

    xbar_spread = A2_TABLE[size] * r_bar
    xbar = ControlLimits(
        center=xbar_center,
        ucl=xbar_center + xbar_spread,
        lcl=xbar_center - xbar_spread,
        sigma=sigma / sqrt(size),
        method=METHOD_XBAR_R_XBAR,
        n_points=len(means),
    )
    r_chart = ControlLimits(
        center=r_bar,
        ucl=D4_TABLE[size] * r_bar,
        lcl=D3_TABLE[size] * r_bar,
        sigma=sigma,
        method=METHOD_XBAR_R_RANGE,
        n_points=len(ranges),
    )
    return XbarRResult(xbar=xbar, r=r_chart, subgroup_size=size)

"""Immutable results of the SPC core.

`frozen=True, slots=True` on purpose (02 §7): a computed limit cannot be mutated afterwards, so
a chart, a rule scan and a persisted baseline can share the same object without copying or
defensive re-checks.
"""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ControlLimits:
    """Center line, control limits and the estimated sigma of one chart.

    `sigma` is the standard deviation **of the plotted statistic**, not of the raw process, so
    that `center ± k * sigma` always reproduces the zones the Nelson rules talk about: for the
    individuals chart it is the process sigma (MR-bar/d2), for the X-bar chart it is
    sigma/sqrt(n). `method` names the chart the limits belong to, because a control limit, a
    normative limit and a LOQ are three different things and must never be mixed up (01 §4.1).
    """

    center: float
    ucl: float
    lcl: float
    sigma: float
    method: str
    n_points: int


@dataclass(frozen=True, slots=True)
class IMRResult:
    """Both charts of an individuals / moving-range pair."""

    individuals: ControlLimits
    moving_range: ControlLimits


@dataclass(frozen=True, slots=True)
class XbarRResult:
    """Both charts of an X-bar / R pair, plus the subgroup size they were built with."""

    xbar: ControlLimits
    r: ControlLimits
    subgroup_size: int


@dataclass(frozen=True, slots=True)
class RuleViolation:
    """One detected signal, with the Spanish sentence the UI shows.

    `index` is the zero-based position in the series of the point that completes the pattern
    (the out-of-limit point, the ninth point of a run, the last point of the growing window);
    `description` counts points from 1, the way the chart labels them.
    """

    rule: str
    index: int
    description: str


@dataclass(frozen=True, slots=True)
class CapabilityResult:
    """Cp/Cpk of a process against its **normative** limits (never against control limits).

    `cp` is `None` when the parameter has only one normative limit; `cpk` is always reported.
    `transform` records the scale actually used (`"log10"` or `None`) so the number can be
    reproduced; `assumption_warning` carries the caveats in Spanish for the analyst.
    """

    cp: float | None
    cpk: float | None
    n: int
    transform: str | None
    assumption_warning: str | None

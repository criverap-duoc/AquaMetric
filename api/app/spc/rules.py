"""Nelson / Western Electric rules R1–R5 over a series and its control limits (01 §4.1).

Pure module (02 §7). The limits arrive as an argument: a rule scan never computes limits, so it
can be applied to a Phase I baseline, to a frozen Phase II baseline or to a chart read from the
database with the same code and the same outcome.

The UI codes are the project's own: R1 = Nelson 1, R2 = Nelson 2, R3 = Nelson 3, R4 = Nelson 5,
R5 = Nelson 6. Each rule fires **once per pattern** (once per run, once per excursion), which is
what an analyst wants to see on the chart instead of one marker per overlapping window.
"""

from collections.abc import Sequence

from app.spc.types import ControlLimits, RuleViolation
from app.spc.validation import require_finite

RULE_3SIGMA = "R1"
RULE_SAME_SIDE = "R2"
RULE_TREND = "R3"
RULE_TWO_OF_THREE = "R4"
RULE_FOUR_OF_FIVE = "R5"

# Consecutive points required by each pattern (Nelson 2 and 3).
SAME_SIDE_LENGTH = 9
TREND_LENGTH = 6
# Window and minimum count "on the same side" for the zone rules (Nelson 5 and 6).
TWO_OF_THREE_WINDOW = 3
TWO_OF_THREE_NEEDED = 2
FOUR_OF_FIVE_WINDOW = 5
FOUR_OF_FIVE_NEEDED = 4
SIGMA_ZONE_TWO = 2.0
SIGMA_ZONE_ONE = 1.0

_RULE_WORDS = {
    RULE_TWO_OF_THREE: "dos de tres puntos consecutivos",
    RULE_FOUR_OF_FIVE: "cuatro de cinco puntos consecutivos",
}


def detect_rules(observations: Sequence[float], limits: ControlLimits) -> list[RuleViolation]:
    """Scan a series against one chart's limits and list every signal found.

    Rules (01 §4.1):

        R1  one point beyond 3 sigma (outside [LCL, UCL])
        R2  nine consecutive points on the same side of the center line
        R3  six consecutive points increasing (or six decreasing)
        R4  two of three consecutive points beyond 2 sigma, same side
        R5  four of five consecutive points beyond 1 sigma, same side

    `limits.sigma` must be the standard deviation of the plotted statistic (see
    `ControlLimits`), so the 1/2 sigma zones line up with the drawn limits.

    Args:
        observations: the series in chronological order.
        limits: the chart limits the points are compared against.

    Returns:
        Violations sorted by point index and then by rule code; empty when the process is in
        control. The index is zero-based; descriptions count points from 1.

    Raises:
        ValueError: NaN/infinity in the series, or `limits.sigma <= 0` (without variation the
            1/2 sigma zones have no width and every point would look like an excursion).
    """
    data = require_finite(observations)
    if limits.sigma <= 0:
        raise ValueError(
            "La desviación estimada es cero: sin variación no se pueden evaluar las zonas de "
            "1σ y 2σ."
        )
    if not data:
        return []

    violations: list[RuleViolation] = [
        *_rule_beyond_limits(data, limits),
        *_rule_same_side(data, limits),
        *_rule_trend(data),
        *_rule_zone(
            data,
            limits,
            multiple=SIGMA_ZONE_TWO,
            window=TWO_OF_THREE_WINDOW,
            needed=TWO_OF_THREE_NEEDED,
            rule=RULE_TWO_OF_THREE,
        ),
        *_rule_zone(
            data,
            limits,
            multiple=SIGMA_ZONE_ONE,
            window=FOUR_OF_FIVE_WINDOW,
            needed=FOUR_OF_FIVE_NEEDED,
            rule=RULE_FOUR_OF_FIVE,
        ),
    ]
    violations.sort(key=lambda violation: (violation.index, violation.rule))
    return violations


def _rule_beyond_limits(data: list[float], limits: ControlLimits) -> list[RuleViolation]:
    """R1: at least one point strictly outside the control limits (Nelson 1)."""
    return [
        RuleViolation(
            rule=RULE_3SIGMA,
            index=index,
            description=f"Punto {index + 1} fuera de los límites de control (±3σ).",
        )
        for index, value in enumerate(data)
        if value > limits.ucl or value < limits.lcl
    ]


def _rule_same_side(data: list[float], limits: ControlLimits) -> list[RuleViolation]:
    """R2: nine consecutive points on the same side of the center line (Nelson 2).

    A point exactly on the center line breaks the run: it belongs to neither side, and counting
    it as «above» would fire the rule on a flat series.
    """
    violations: list[RuleViolation] = []
    run_side = 0
    run_length = 0
    for index, value in enumerate(data):
        side = 0 if value == limits.center else (1 if value > limits.center else -1)
        if side == 0:
            run_side, run_length = 0, 0
            continue
        if side == run_side:
            run_length += 1
        else:
            run_side, run_length = side, 1
        if run_length == SAME_SIDE_LENGTH:
            where = "encima" if side > 0 else "debajo"
            violations.append(
                RuleViolation(
                    rule=RULE_SAME_SIDE,
                    index=index,
                    description=(
                        f"Punto {index + 1}: nueve puntos consecutivos por {where} de la línea "
                        "central."
                    ),
                )
            )
    return violations


def _rule_trend(data: list[float]) -> list[RuleViolation]:
    """R3: six consecutive increasing (or decreasing) points (Nelson 3).

    Repeated values break both runs: a plateau is not a trend.
    """
    violations: list[RuleViolation] = []
    increasing = 1
    decreasing = 1
    for index in range(1, len(data)):
        if data[index] > data[index - 1]:
            increasing += 1
            decreasing = 1
        elif data[index] < data[index - 1]:
            decreasing += 1
            increasing = 1
        else:
            increasing = 1
            decreasing = 1
        if increasing == TREND_LENGTH:
            violations.append(
                RuleViolation(
                    rule=RULE_TREND,
                    index=index,
                    description=f"Punto {index + 1}: seis puntos consecutivos en aumento.",
                )
            )
        elif decreasing == TREND_LENGTH:
            violations.append(
                RuleViolation(
                    rule=RULE_TREND,
                    index=index,
                    description=f"Punto {index + 1}: seis puntos consecutivos en descenso.",
                )
            )
    return violations


def _rule_zone(
    data: list[float],
    limits: ControlLimits,
    *,
    multiple: float,
    window: int,
    needed: int,
    rule: str,
) -> list[RuleViolation]:
    """R4/R5: `needed` points of `window` beyond `multiple` sigma, all on the same side.

    Overlapping windows that belong to the same excursion are reported once, at the first window
    that completes the pattern; the following windows of that excursion are skipped.
    """
    upper_zone = limits.center + multiple * limits.sigma
    lower_zone = limits.center - multiple * limits.sigma
    violations: list[RuleViolation] = []
    last_reported: int | None = None
    for index in range(window - 1, len(data)):
        chunk = data[index - window + 1 : index + 1]
        above = sum(1 for value in chunk if value > upper_zone)
        below = sum(1 for value in chunk if value < lower_zone)
        if above < needed and below < needed:
            continue
        if last_reported is not None and index - last_reported < window:
            continue
        last_reported = index
        where = "por encima" if above >= needed else "por debajo"
        violations.append(
            RuleViolation(
                rule=rule,
                index=index,
                description=(
                    f"Punto {index + 1}: {_RULE_WORDS[rule]} más allá de {multiple:g}σ del "
                    f"mismo lado ({where})."
                ),
            )
        )
    return violations

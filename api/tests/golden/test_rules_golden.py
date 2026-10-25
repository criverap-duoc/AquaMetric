"""Golden cases for rules R1–R5, each with a positive and a negative example.

The limits are stated by hand (center 10, sigma 1, UCL 13, LCL 7) so the expected index of every
signal can be counted on paper; see `tests/golden/README.md` §4. The mapping between the project
codes and the published rules is in `01 §4.1`: R1 = Nelson 1, R2 = Nelson 2, R3 = Nelson 3,
R4 = Nelson 5, R5 = Nelson 6.
"""

from collections.abc import Sequence

import pytest

from app.spc import ControlLimits, RuleViolation, detect_rules
from app.spc.rules import (
    FOUR_OF_FIVE_WINDOW,
    RULE_3SIGMA,
    RULE_FOUR_OF_FIVE,
    RULE_SAME_SIDE,
    RULE_TREND,
    RULE_TWO_OF_THREE,
    SAME_SIDE_LENGTH,
    TREND_LENGTH,
    TWO_OF_THREE_WINDOW,
)

LIMITS = ControlLimits(center=10.0, ucl=13.0, lcl=7.0, sigma=1.0, method="test", n_points=0)


def _scan(series: Sequence[float]) -> list[RuleViolation]:
    """Run the scan against the hand-written limits."""
    return detect_rules(series, LIMITS)


def _found(series: Sequence[float]) -> list[tuple[str, int]]:
    """Reduce each violation to (rule, index), the compact form used in the README table."""
    return [(violation.rule, violation.index) for violation in _scan(series)]


def test_r1_fires_on_a_point_beyond_the_upper_limit() -> None:
    """13.5 > UCL 13: one signal, at the third point (index 2)."""
    violations = _scan([10.0, 10.0, 13.5, 10.0, 10.0])

    assert [(violation.rule, violation.index) for violation in violations] == [(RULE_3SIGMA, 2)]
    assert violations[0].description == "Punto 3 fuera de los límites de control (±3σ)."


def test_r1_fires_on_a_point_beyond_the_lower_limit() -> None:
    """6.5 < LCL 7: the same rule covers both tails."""
    assert _found([10.0, 6.5, 10.0, 10.0]) == [(RULE_3SIGMA, 1)]


def test_r1_does_not_fire_on_a_point_exactly_on_the_limit() -> None:
    """A point at exactly 13.0 is on the limit, not beyond it (Nelson 1 is strict)."""
    assert _found([10.0, 13.0, 7.0, 10.0]) == []


def test_a_clean_alternating_series_triggers_no_rule() -> None:
    """No false positives: 9/10 alternating around 9.5 stays quiet for all five rules."""
    clean = ControlLimits(
        center=9.5, ucl=12.16, lcl=6.84, sigma=1 / 1.128, method="test", n_points=20
    )

    assert detect_rules([9.0, 10.0] * 10, clean) == []


def test_r2_fires_on_nine_consecutive_points_on_the_same_side() -> None:
    """Nine points above the center line: reported once, at the ninth one (index 8)."""
    assert _found([10.5] * SAME_SIDE_LENGTH) == [(RULE_SAME_SIDE, 8)]


def test_r2_reports_one_signal_per_run_not_one_per_extra_point() -> None:
    """Twelve points above the center line are one run, so one signal."""
    assert _found([10.5] * 12) == [(RULE_SAME_SIDE, 8)]


def test_r2_does_not_fire_on_eight_points_on_the_same_side() -> None:
    """Eight is below the threshold; a point on the center line also breaks the run."""
    assert _found([10.5] * 8 + [10.0] + [10.5, 10.5]) == []


def test_r3_fires_on_six_consecutive_increasing_points() -> None:
    """6 increasing points: one signal, at the sixth one (index 5)."""
    assert _found([9.0, 9.5, 10.0, 10.5, 11.0, 11.5]) == [(RULE_TREND, 5)]


def test_r3_fires_on_six_consecutive_decreasing_points() -> None:
    """The mirror image: 11.5 down to 9.0."""
    assert _found([11.5, 11.0, 10.5, 10.0, 9.5, 9.0]) == [(RULE_TREND, 5)]


def test_r3_does_not_fire_when_a_repeated_value_breaks_the_run() -> None:
    """Five increases then a plateau: the run restarts, so no signal."""
    assert _found([9.0, 9.5, 10.0, 10.5, 11.0, 11.0]) == []
    assert TREND_LENGTH == 6


def test_r4_fires_on_two_of_three_points_beyond_two_sigma() -> None:
    """2 sigma = 12; two of the three points exceed it (same side) at index 3."""
    assert _found([10.0, 12.5, 10.2, 12.5]) == [(RULE_TWO_OF_THREE, 3)]


def test_r4_does_not_fire_when_the_two_points_are_on_opposite_sides() -> None:
    """One above 12 and one below 8 is not a shift: the rule requires the same side."""
    assert _found([10.0, 12.5, 10.2, 7.9]) == []
    assert TWO_OF_THREE_WINDOW == 3


def test_r4_reports_one_signal_per_excursion() -> None:
    """Six points beyond 2 sigma: two signals (windows 1-3 and 4-6), not four."""
    indices = [
        violation.index for violation in _scan([12.5] * 6) if violation.rule == RULE_TWO_OF_THREE
    ]

    assert indices == [2, 5]


def test_r5_fires_on_four_of_five_points_beyond_one_sigma() -> None:
    """1 sigma = 11; four of the last five points exceed it at index 4."""
    assert _found([11.5, 11.5, 10.0, 11.5, 11.5]) == [(RULE_FOUR_OF_FIVE, 4)]


def test_r5_does_not_fire_on_three_of_five_points_beyond_one_sigma() -> None:
    """Three of five is a common fluctuation, below the rule's threshold."""
    assert _found([11.5, 11.5, 10.0, 11.5, 10.6]) == []
    assert FOUR_OF_FIVE_WINDOW == 5


def test_violations_are_sorted_by_point_then_by_rule() -> None:
    """The UI draws the markers in series order, so the core already returns them ordered."""
    series = [13.5] + [10.5] * 11
    violations = _scan(series)
    keys = [(violation.index, violation.rule) for violation in violations]

    assert keys == sorted(keys)
    assert len(violations) >= 2


@pytest.mark.parametrize(
    "rule", [RULE_3SIGMA, RULE_SAME_SIDE, RULE_TREND, RULE_TWO_OF_THREE, RULE_FOUR_OF_FIVE]
)
def test_every_rule_code_is_reachable(rule: str) -> None:
    """Guard against a rule that exists in the docs but never fires in the code."""
    series_by_rule: dict[str, list[float]] = {
        RULE_3SIGMA: [10.0, 13.5],
        RULE_SAME_SIDE: [10.5] * 9,
        RULE_TREND: [9.0, 9.5, 10.0, 10.5, 11.0, 11.5],
        RULE_TWO_OF_THREE: [10.0, 12.5, 10.2, 12.5],
        RULE_FOUR_OF_FIVE: [11.5, 11.5, 10.0, 11.5, 11.5],
    }

    assert rule in {violation.rule for violation in _scan(series_by_rule[rule])}

"""Golden case for the I-MR chart: limits computed by hand, matched to 1e-9.

Dataset A (`[9, 10] * 10`) is chosen so every step of the arithmetic can be redone on paper:
19 moving ranges, all equal to 1, so MR-bar = 1 and sigma = 1/1.128. See
`tests/golden/README.md` §2 for the derivation and the book reference (ADR-001).
"""

from statistics import stdev

import pytest

from app.spc import compute_imr
from app.spc.errors import InsufficientDataError

TOLERANCE = 1e-9
ALTERNATING = [9.0, 10.0] * 10
# Ten points at 10/11 and ten at 14/15: a level shift the global sd would smear into wider
# limits, which is exactly what ADR-001 forbids.
SHIFTED = [10.0, 11.0] * 5 + [14.0, 15.0] * 5


def test_individuals_chart_matches_hand_computed_limits() -> None:
    """x-bar = 9.5, MR-bar = 1 => UCL = 9.5 + 2.66 * 1 = 12.16, LCL = 6.84."""
    result = compute_imr(ALTERNATING)

    assert result.individuals.center == pytest.approx(9.5, abs=TOLERANCE)
    assert result.individuals.ucl == pytest.approx(12.16, abs=TOLERANCE)
    assert result.individuals.lcl == pytest.approx(6.84, abs=TOLERANCE)
    assert result.individuals.sigma == pytest.approx(1 / 1.128, abs=TOLERANCE)
    assert result.individuals.n_points == 20
    assert result.individuals.method == "imr_individuals"


def test_moving_range_chart_matches_hand_computed_limits() -> None:
    """MR-bar = 1 => center 1, UCL = 3.267 * 1 = 3.267 (D4 for n = 2), LCL = 0."""
    result = compute_imr(ALTERNATING)

    assert result.moving_range.center == pytest.approx(1.0, abs=TOLERANCE)
    assert result.moving_range.ucl == pytest.approx(3.267, abs=TOLERANCE)
    assert result.moving_range.lcl == pytest.approx(0.0, abs=TOLERANCE)
    assert result.moving_range.n_points == 19
    assert result.moving_range.method == "imr_moving_range"


def test_limits_use_moving_range_sigma_not_global_standard_deviation() -> None:
    """The documented shift case: 19 moving ranges summing 21 => MR-bar = 21/19.

    center = 12.5, UCL/LCL = 12.5 +/- 2.66 * (21/19) = 12.5 +/- 2.94, so 15.44 / 9.56.
    A chart built on the global sd would be far wider and would hide the shift (ADR-001).
    """
    result = compute_imr(SHIFTED)

    assert result.individuals.center == pytest.approx(12.5, abs=TOLERANCE)
    assert result.individuals.ucl == pytest.approx(15.44, abs=TOLERANCE)
    assert result.individuals.lcl == pytest.approx(9.56, abs=TOLERANCE)
    assert result.individuals.sigma == pytest.approx(21 / 19 / 1.128, abs=TOLERANCE)
    assert result.moving_range.center == pytest.approx(21 / 19, abs=TOLERANCE)
    assert result.moving_range.ucl == pytest.approx(3.267 * 21 / 19, abs=TOLERANCE)

    global_sd = stdev(SHIFTED)
    assert global_sd > 1.5
    assert result.individuals.ucl < 12.5 + 3 * global_sd


def test_exactly_twenty_points_is_enough_and_nineteen_is_not() -> None:
    """The 20-point floor is the contract, not an off-by-one: 19 raises, 20 computes."""
    with pytest.raises(InsufficientDataError):
        compute_imr(ALTERNATING[:19])

    result = compute_imr(ALTERNATING[:20])
    assert result.individuals.n_points == 20

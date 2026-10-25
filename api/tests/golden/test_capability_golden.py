"""Golden case for process capability: a series whose Cp and Cpk are exactly 1.33.

The 20 values are symmetric around 10 with a sample standard deviation of exactly 1 (sum of
squared deviations = 19, ddof = 1), so `(13.99 - 6.01) / (6 * 1) = 1.33` can be recomputed by
hand. See `tests/golden/README.md` §5.
"""

import pytest

from app.spc import compute_capability
from app.spc.capability import WARNING_SKEWED, WARNING_SMALL_SAMPLE
from app.spc.errors import InsufficientDataError

TOLERANCE = 1e-9
# Deviations from 10: -1.5 (x4), -0.5 (x2), 0 (x8), +0.5 (x2), +1.5 (x4).
# Sum of squares = 4*2.25 + 2*0.25 + 0 + 2*0.25 + 4*2.25 = 19 => variance = 19/19 = 1.
SYMMETRIC = [8.5] * 4 + [9.5] * 2 + [10.0] * 8 + [10.5] * 2 + [11.5] * 4
TWO_SIDED_SPEC = (6.01, 13.99)


def test_two_sided_cp_and_cpk_are_the_documented_values() -> None:
    """Cp = (USL - LSL) / 6 sigma = 7.98 / 6 = 1.33; Cpk = 3.99 / 3 = 1.33."""
    result = compute_capability(SYMMETRIC, TWO_SIDED_SPEC)

    assert result.cp == pytest.approx(1.33, abs=TOLERANCE)
    assert result.cpk == pytest.approx(1.33, abs=TOLERANCE)
    assert result.n == 20
    assert result.transform is None


def test_small_sample_carries_its_warning() -> None:
    """20 points is enough to compute, not enough to quote: the caveat travels with the number."""
    result = compute_capability(SYMMETRIC, TWO_SIDED_SPEC)

    assert result.assumption_warning is not None
    assert result.assumption_warning.startswith(WARNING_SMALL_SAMPLE)


def test_upper_limit_only_reports_cpk_and_no_cp() -> None:
    """Cp needs both limits; Cpk = (12 - 10) / (3 * 1) = 0.666..."""
    result = compute_capability(SYMMETRIC, (None, 12.0))

    assert result.cp is None
    assert result.cpk == pytest.approx(2 / 3, abs=TOLERANCE)


def test_lower_limit_only_reports_the_distance_to_that_limit() -> None:
    """Cpk = (10 - 8) / 3 = 0.666...: the side that exists is the side that limits the process."""
    result = compute_capability(SYMMETRIC, (8.0, None))

    assert result.cp is None
    assert result.cpk == pytest.approx(2 / 3, abs=TOLERANCE)


def test_asymmetric_mean_lowers_cpk_below_cp() -> None:
    """Shifting every value by +0.5 keeps the spread and halves the margin on the upper side.

    sigma stays 1 (a shift does not change deviations), so Cp = 1.33 and
    Cpk = (13.99 - 10.5) / 3 = 1.1633... — the classic demonstration that capability is not
    only about spread.
    """
    shifted = [value + 0.5 for value in SYMMETRIC]
    result = compute_capability(shifted, TWO_SIDED_SPEC)

    assert result.cp == pytest.approx(1.33, abs=TOLERANCE)
    assert result.cpk == pytest.approx(3.49 / 3, abs=TOLERANCE)
    assert result.cpk is not None
    assert result.cp is not None
    assert result.cpk < result.cp


def test_log10_transform_applies_to_data_and_limits() -> None:
    """Both the data and the normative limits move to the log scale.

    Values documented in `tests/golden/README.md` §5: sigma_log = 0.047..., mean_log = 0.998...,
    Cp = (log10(13.99) - log10(6.01)) / (6 * sigma_log) = 1.39596..., Cpk = 1.12533...
    """
    result = compute_capability(SYMMETRIC, TWO_SIDED_SPEC, "log10")

    assert result.transform == "log10"
    assert result.cp == pytest.approx(1.3959620330800055, abs=1e-9)
    assert result.cpk == pytest.approx(1.1253351884687073, abs=1e-9)
    # Without the transform the same data gives 1.33: the scale matters.
    assert compute_capability(SYMMETRIC, TWO_SIDED_SPEC).cp == pytest.approx(1.33, abs=TOLERANCE)


def test_skewed_series_gets_the_transform_suggestion() -> None:
    """Nineteen values at 10 and one at 30: g1 > 1, so the normal-theory index is flagged."""
    skewed = [10.0] * 19 + [30.0]
    result = compute_capability(skewed, (0.0, 40.0))

    assert result.assumption_warning is not None
    assert WARNING_SKEWED in result.assumption_warning


def test_both_limits_absent_is_insufficient_data() -> None:
    """Capability against nothing is not a number: the chemist has not signed any limit."""
    with pytest.raises(InsufficientDataError):
        compute_capability(SYMMETRIC, (None, None))


def test_nineteen_points_is_insufficient_data() -> None:
    """Same 20-point floor as the charts, checked explicitly (no off-by-one)."""
    with pytest.raises(InsufficientDataError):
        compute_capability(SYMMETRIC[:19], TWO_SIDED_SPEC)

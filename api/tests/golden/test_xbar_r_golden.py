"""Golden case for the X-bar/R chart with subgroups of n = 3.

Every subgroup is `(m - 1, m, m + 1)`, so the subgroup mean is exactly `m` and the range is
exactly 2; twenty subgroups with means 11..22 alternate as in the derivation of
`tests/golden/README.md` §3. R-bar = 2, mean of means = 16.5, A2(3) = 1.023.
"""

import pytest

from app.spc import compute_xbar_r
from app.spc.charts import METHOD_XBAR_R_RANGE, METHOD_XBAR_R_XBAR
from app.spc.errors import InsufficientDataError

TOLERANCE = 1e-9
SUBGROUP_MEANS = [11, 13, 12, 14, 13, 15, 14, 16, 15, 17, 16, 18, 17, 19, 18, 20, 19, 21, 20, 22]
SUBGROUPS = [[mean - 1, mean, mean + 1] for mean in SUBGROUP_MEANS]


def test_xbar_chart_matches_hand_computed_limits() -> None:
    """center = 16.5, A2(3) * R-bar = 1.023 * 2 = 2.046 => UCL 18.546, LCL 14.454."""
    result = compute_xbar_r(SUBGROUPS)

    assert result.subgroup_size == 3
    assert result.xbar.center == pytest.approx(16.5, abs=TOLERANCE)
    assert result.xbar.ucl == pytest.approx(18.546, abs=TOLERANCE)
    assert result.xbar.lcl == pytest.approx(14.454, abs=TOLERANCE)
    assert result.xbar.n_points == 20
    assert result.xbar.method == METHOD_XBAR_R_XBAR


def test_range_chart_matches_hand_computed_limits() -> None:
    """R-bar = 2 => center 2, UCL = D4(3) * 2 = 2.574 * 2 = 5.148, LCL = D3(3) * 2 = 0."""
    result = compute_xbar_r(SUBGROUPS)

    assert result.r.center == pytest.approx(2.0, abs=TOLERANCE)
    assert result.r.ucl == pytest.approx(5.148, abs=TOLERANCE)
    assert result.r.lcl == pytest.approx(0.0, abs=TOLERANCE)
    assert result.r.method == METHOD_XBAR_R_RANGE


def test_sigma_is_the_process_estimate_and_xbar_sigma_is_its_root_n_scaling() -> None:
    """sigma = R-bar/d2(3) = 2/1.693; the plotted means scatter sigma/sqrt(3) around the center."""
    result = compute_xbar_r(SUBGROUPS)

    process_sigma = 2 / 1.693
    assert result.r.sigma == pytest.approx(process_sigma, abs=TOLERANCE)
    assert result.xbar.sigma == pytest.approx(process_sigma / 3**0.5, abs=TOLERANCE)
    # 3 * sigma of the plotted statistic must reproduce A2(3) * R-bar: that is why the Nelson
    # zones in `detect_rules` line up with the drawn limits. The residual 1.3e-4 gap is the
    # published A2 rounded to three decimals (3/(d2*sqrt(3)) = 1.02315).
    assert 3 * result.xbar.sigma == pytest.approx(2.046, abs=5e-4)


def test_subgroups_of_four_use_their_own_constants() -> None:
    """A2(4) = 0.729 and D4(4) = 2.282: using the n = 3 row would give different limits."""
    subgroups_of_four = [[mean - 1, mean, mean, mean + 1] for mean in SUBGROUP_MEANS]
    result = compute_xbar_r(subgroups_of_four)

    assert result.subgroup_size == 4
    assert result.xbar.ucl == pytest.approx(16.5 + 0.729 * 2, abs=TOLERANCE)
    assert result.xbar.lcl == pytest.approx(16.5 - 0.729 * 2, abs=TOLERANCE)
    assert result.r.ucl == pytest.approx(2.282 * 2, abs=TOLERANCE)
    assert result.r.lcl == pytest.approx(0.0, abs=TOLERANCE)


def test_no_subgroups_is_reported_as_insufficient_data() -> None:
    """An empty series is a data problem, not a programming error."""
    with pytest.raises(InsufficientDataError):
        compute_xbar_r([])

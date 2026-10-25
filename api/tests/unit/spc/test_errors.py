"""Guards of the pure SPC core: every refusal says why, in Spanish, before any number exists.

These tests cover the contracts that protect the analyst from a plausible-looking result:
20 points minimum, subgroup sizes tabulated in the book, NaN never silently averaged away, and
a constant series never producing a control chart.
"""

import pytest

from app.spc import (
    ControlLimits,
    InsufficientDataError,
    SPCError,
    compute_imr,
    compute_xbar_r,
    detect_rules,
)

VALID_SERIES = [10.0, 11.0] * 10
LIMITS = ControlLimits(center=10.0, ucl=13.0, lcl=7.0, sigma=1.0, method="test", n_points=20)


def test_insufficient_data_error_is_part_of_the_spc_error_family() -> None:
    """The service catches `SPCError`; a new subclass must not escape that net."""
    assert issubclass(InsufficientDataError, SPCError)


def test_imr_with_twelve_points_names_the_shortfall_in_spanish() -> None:
    """The message the analyst reads says how many points are needed and how many exist."""
    with pytest.raises(InsufficientDataError) as error:
        compute_imr(VALID_SERIES[:12])

    assert str(error.value) == (
        "Se requieren al menos 20 observaciones válidas para la línea base (hay 12)."
    )


def test_imr_rejects_nan_before_averaging_it() -> None:
    """NaN poisons the center line silently; the core refuses the series instead."""
    series = [*VALID_SERIES[:19], float("nan")]

    with pytest.raises(ValueError, match="NaN"):
        compute_imr(series)


def test_imr_rejects_infinity() -> None:
    """Infinity breaks the mean in the same way and gets the same answer."""
    with pytest.raises(ValueError, match="infinito"):
        compute_imr([*VALID_SERIES[:19], float("inf")])


def test_imr_rejects_a_constant_series() -> None:
    """Zero variation means zero sigma: the limits would collapse onto the center line."""
    with pytest.raises(ValueError, match="rangos móviles son cero"):
        compute_imr([7.0] * 20)


def test_xbar_r_rejects_a_subgroup_of_one() -> None:
    """Subgroups must have 2 to 10 observations; one value has no range."""
    with pytest.raises(ValueError, match="tamaño de subgrupo"):
        compute_xbar_r([[10.0], [11.0]])


def test_xbar_r_rejects_a_subgroup_of_eleven() -> None:
    """Beyond 10 the tables do not apply: the constants are simply not tabulated for it."""
    with pytest.raises(ValueError, match="tamaño de subgrupo"):
        compute_xbar_r([list(range(10, 21))] * 3)


def test_xbar_r_rejects_mixed_subgroup_sizes() -> None:
    """A chart needs one rational subgroup size; mixing them makes R-bar meaningless."""
    with pytest.raises(ValueError, match="mismo tamaño"):
        compute_xbar_r([[10.0, 11.0, 12.0], [10.0, 11.0]])


def test_xbar_r_rejects_nan_inside_a_subgroup() -> None:
    """One bad value invalidates the whole subgroup, not just one point."""
    with pytest.raises(ValueError, match="NaN"):
        compute_xbar_r([[10.0, float("nan"), 12.0], [10.0, 11.0, 12.0]])


def test_xbar_r_rejects_constant_subgroups() -> None:
    """All ranges zero: no sigma, no chart."""
    with pytest.raises(ValueError, match="rangos son cero"):
        compute_xbar_r([[10.0, 10.0, 10.0], [10.0, 10.0, 10.0]])


def test_detect_rules_rejects_zero_sigma() -> None:
    """Without sigma the 1/2 sigma zones have no width and everything looks like an excursion."""
    flat = ControlLimits(center=10.0, ucl=10.0, lcl=10.0, sigma=0.0, method="test", n_points=20)

    with pytest.raises(ValueError, match="desviación estimada es cero"):
        detect_rules([10.0, 10.0], flat)


def test_detect_rules_on_an_empty_series_returns_no_violations() -> None:
    """An empty window is a normal state while a series loads, not an error."""
    assert detect_rules([], LIMITS) == []

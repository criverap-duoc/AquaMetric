"""Golden check of every control-chart constant against its book value.

The expected numbers are **re-typed from the table** on purpose: if a digit in
`app/spc/constants.py` is wrong, this test is the only thing that notices.
Source: Montgomery, *Introduction to Statistical Quality Control*, 7th ed., Appendix VI;
ISO 7870-2:2023. See `tests/golden/README.md` §1.
"""

from math import sqrt
from typing import Final

import pytest

from app.spc.constants import (
    A2_N2,
    A2_N3,
    A2_N4,
    A2_N5,
    A2_N6,
    A2_N7,
    A2_N8,
    A2_N9,
    A2_N10,
    A2_TABLE,
    D2_N2,
    D2_N3,
    D2_N4,
    D2_N5,
    D2_N6,
    D2_N7,
    D2_N8,
    D2_N9,
    D2_N10,
    D2_TABLE,
    D3_N2,
    D3_N3,
    D3_N4,
    D3_N5,
    D3_N6,
    D3_N7,
    D3_N8,
    D3_N9,
    D3_N10,
    D3_TABLE,
    D4_N2,
    D4_N3,
    D4_N4,
    D4_N5,
    D4_N6,
    D4_N7,
    D4_N8,
    D4_N9,
    D4_N10,
    D4_TABLE,
    K_IMR,
)

BOOK_D2: Final[dict[int, float]] = {
    2: 1.128,
    3: 1.693,
    4: 2.059,
    5: 2.326,
    6: 2.534,
    7: 2.704,
    8: 2.847,
    9: 2.970,
    10: 3.078,
}
BOOK_D3: Final[dict[int, float]] = {
    2: 0.000,
    3: 0.000,
    4: 0.000,
    5: 0.000,
    6: 0.000,
    7: 0.076,
    8: 0.136,
    9: 0.184,
    10: 0.223,
}
BOOK_D4: Final[dict[int, float]] = {
    2: 3.267,
    3: 2.574,
    4: 2.282,
    5: 2.114,
    6: 2.004,
    7: 1.924,
    8: 1.864,
    9: 1.816,
    10: 1.777,
}
BOOK_A2: Final[dict[int, float]] = {
    2: 1.880,
    3: 1.023,
    4: 0.729,
    5: 0.577,
    6: 0.483,
    7: 0.419,
    8: 0.373,
    9: 0.337,
    10: 0.308,
}

NAMED_D2: Final[dict[int, float]] = {
    2: D2_N2,
    3: D2_N3,
    4: D2_N4,
    5: D2_N5,
    6: D2_N6,
    7: D2_N7,
    8: D2_N8,
    9: D2_N9,
    10: D2_N10,
}
NAMED_D3: Final[dict[int, float]] = {
    2: D3_N2,
    3: D3_N3,
    4: D3_N4,
    5: D3_N5,
    6: D3_N6,
    7: D3_N7,
    8: D3_N8,
    9: D3_N9,
    10: D3_N10,
}
NAMED_D4: Final[dict[int, float]] = {
    2: D4_N2,
    3: D4_N3,
    4: D4_N4,
    5: D4_N5,
    6: D4_N6,
    7: D4_N7,
    8: D4_N8,
    9: D4_N9,
    10: D4_N10,
}
NAMED_A2: Final[dict[int, float]] = {
    2: A2_N2,
    3: A2_N3,
    4: A2_N4,
    5: A2_N5,
    6: A2_N6,
    7: A2_N7,
    8: A2_N8,
    9: A2_N9,
    10: A2_N10,
}
SIZES: Final[tuple[int, ...]] = (2, 3, 4, 5, 6, 7, 8, 9, 10)


@pytest.mark.parametrize("size", SIZES)
def test_named_d2_constant_matches_book_table(size: int) -> None:
    """d2(n) = E[W] = E[R/sigma]; the divisor that turns R-bar into sigma."""
    assert NAMED_D2[size] == BOOK_D2[size]
    assert D2_TABLE[size] == BOOK_D2[size]


@pytest.mark.parametrize("size", SIZES)
def test_named_d3_constant_matches_book_table(size: int) -> None:
    """D3(n) is the R chart's lower factor; zero while the 3-sigma band would go below zero."""
    assert NAMED_D3[size] == BOOK_D3[size]
    assert D3_TABLE[size] == BOOK_D3[size]


@pytest.mark.parametrize("size", SIZES)
def test_named_d4_constant_matches_book_table(size: int) -> None:
    """D4(n) is the R chart's upper factor: UCL_R = D4(n) * R-bar."""
    assert NAMED_D4[size] == BOOK_D4[size]
    assert D4_TABLE[size] == BOOK_D4[size]


@pytest.mark.parametrize("size", SIZES)
def test_named_a2_constant_matches_book_table(size: int) -> None:
    """A2(n) is the X-bar chart's factor: UCL/LCL = x-bar-bar +/- A2(n) * R-bar."""
    assert NAMED_A2[size] == BOOK_A2[size]
    assert A2_TABLE[size] == BOOK_A2[size]


def test_k_imr_equals_three_over_d2_for_two_points() -> None:
    """2.66 is the published rounding of 3/d2 with d2 = 1.128 (3/1.128 = 2.6596)."""
    assert K_IMR == 2.66
    assert abs(K_IMR - 3 / D2_N2) < 1e-3


@pytest.mark.parametrize("size", SIZES)
def test_a2_agrees_with_three_over_d2_sqrt_n(size: int) -> None:
    """A2(n) = 3 / (d2(n) * sqrt(n)); the published tables round it to three decimals.

    This cross-check ties the X-bar limits to the sigma estimate, so a table typo cannot hide:
    it would have to be wrong in both columns by the same amount.
    """
    assert abs(BOOK_A2[size] - 3 / (BOOK_D2[size] * sqrt(size))) < 1e-3

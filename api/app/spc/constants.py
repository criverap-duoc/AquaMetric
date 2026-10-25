"""Control-chart constants, taken from the published tables (ADR-001).

Every table is built from a single named constant, so a mistyped digit can only live in one
place; `tests/golden/test_constants.py` re-states the book values independently and compares.

Source for every constant below: Montgomery, *Introduction to Statistical Quality Control*,
7th ed., Appendix VI (Table VI); ISO 7870-2:2023, tables of control-chart constants.
"""

from typing import Final

# Source: Montgomery, Introduction to Statistical Quality Control, 7th ed., Table VI;
# ISO 7870-2:2023. Mean of the relative range W = R/sigma.
D2_N2: Final = 1.128
D2_N3: Final = 1.693
D2_N4: Final = 2.059
D2_N5: Final = 2.326
D2_N6: Final = 2.534
D2_N7: Final = 2.704
D2_N8: Final = 2.847
D2_N9: Final = 2.970
D2_N10: Final = 3.078

# Source: Montgomery, 7th ed., Table VI; ISO 7870-2:2023. Lower limit factor for the R chart
# (D3 = 0 for n <= 6: the range cannot go below zero within the 3-sigma band).
D3_N2: Final = 0.000
D3_N3: Final = 0.000
D3_N4: Final = 0.000
D3_N5: Final = 0.000
D3_N6: Final = 0.000
D3_N7: Final = 0.076
D3_N8: Final = 0.136
D3_N9: Final = 0.184
D3_N10: Final = 0.223

# Source: Montgomery, 7th ed., Table VI; ISO 7870-2:2023. Upper limit factor for the R chart.
D4_N2: Final = 3.267
D4_N3: Final = 2.574
D4_N4: Final = 2.282
D4_N5: Final = 2.114
D4_N6: Final = 2.004
D4_N7: Final = 1.924
D4_N8: Final = 1.864
D4_N9: Final = 1.816
D4_N10: Final = 1.777

# Source: Montgomery, 7th ed., Table VI; ISO 7870-2:2023. Factor that turns R-bar into the
# 3-sigma half-width of the X-bar chart: UCL/LCL = x-bar-bar +/- A2 * R-bar.
A2_N2: Final = 1.880
A2_N3: Final = 1.023
A2_N4: Final = 0.729
A2_N5: Final = 0.577
A2_N6: Final = 0.483
A2_N7: Final = 0.419
A2_N8: Final = 0.373
A2_N9: Final = 0.337
A2_N10: Final = 0.308

# 3/d2 for n = 2 (3/1.128 = 2.6596), published rounded to two decimals. Using the rounded value
# keeps the limits identical to the ones printed in every SPC reference.
# Source: Montgomery, 7th ed., ch. 6 (individuals and moving-range chart).
K_IMR: Final = 2.66

D2_TABLE: Final[dict[int, float]] = {
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
D3_TABLE: Final[dict[int, float]] = {
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
D4_TABLE: Final[dict[int, float]] = {
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
A2_TABLE: Final[dict[int, float]] = {
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

# Phase I baseline: fewer than 20 points cannot separate routine noise from a real shift
# (01 §4.1, ADR-001), so the core refuses to publish limits instead of publishing weak ones.
MIN_BASELINE_POINTS: Final = 20
# Capability needs a stable estimate of sigma too; same floor, different message.
MIN_CAPABILITY_POINTS: Final = 20
# Below this size the normality assumption dominates the estimate, so the result is orientative.
CAPABILITY_ORIENTATIVE_BELOW: Final = 30
# |skewness| above this means the normal-theory Cp/Cpk is not trustworthy as printed.
SKEWNESS_THRESHOLD: Final = 1.0
# X-bar/R charts are tabulated for subgroups of 2 to 10 observations only.
SUBGROUP_MIN: Final = 2
SUBGROUP_MAX: Final = 10
# A series with more than 20 % censored values cannot support a reliable estimate (ADR-003).
DEFAULT_CENSORED_MAX_FRACTION: Final = 0.2

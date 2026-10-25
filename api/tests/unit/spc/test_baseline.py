"""The censored-data policy and the Phase I baseline selection (ADR-003, 01 §4.1).

Three censoring regimes are exercised — 0 %, 10 % and 30 % — because the rule is a share, not
a count: the same six censored values are acceptable in a series of 100 and refused in one of
20. The substitution is `LOQ / 2` and it lives only in the calculation.
"""

import pytest

from app.spc import InsufficientDataError, apply_censored_policy, select_baseline

MAX_FRACTION = 0.2


def _row(
    value: float | None,
    loq: float | None = None,
    qualifier: str | None = None,
    qc_flag: str = "ok",
) -> tuple[float | None, float | None, str | None, str]:
    """Build one stored observation row: (value, loq, qualifier, qc_flag)."""
    return (value, loq, qualifier, qc_flag)


def test_policy_returns_the_series_untouched_when_nothing_is_censored() -> None:
    """0 % censored: the values pass through and the metadata records the zero."""
    values = [float(value) for value in range(10, 20)]
    substituted, metadata = apply_censored_policy(
        values, [None] * 10, [None] * 10, max_fraction=MAX_FRACTION
    )

    assert substituted == values
    assert metadata["n"] == 10
    assert metadata["censored_count"] == 0
    assert metadata["censored_fraction"] == 0.0


def test_policy_substitutes_half_the_loq_for_censored_rows_only() -> None:
    """10 % censored (2 of 20): those two become LOQ/2, the rest keep their measured value."""
    values: list[float | None] = [1.0] * 18 + [None, None]
    loqs = [None] * 18 + [0.5, 4.0]
    qualifiers = [None] * 18 + ["<", "<"]
    substituted, metadata = apply_censored_policy(
        values, loqs, qualifiers, max_fraction=MAX_FRACTION
    )

    assert substituted == [1.0] * 18 + [0.25, 2.0]
    assert metadata["censored_count"] == 2
    assert metadata["censored_fraction"] == pytest.approx(0.1)


def test_policy_accepts_exactly_the_configured_share() -> None:
    """The threshold is strict: 20 % censored with a 20 % ceiling is allowed."""
    values: list[float | None] = [1.0] * 16 + [None] * 4
    substituted, metadata = apply_censored_policy(
        values, [None] * 16 + [2.0] * 4, [None] * 16 + ["<"] * 4, max_fraction=MAX_FRACTION
    )

    assert metadata["censored_fraction"] == pytest.approx(0.2)
    assert substituted[16:] == [1.0, 1.0, 1.0, 1.0]


def test_policy_refuses_a_series_with_thirty_percent_censored() -> None:
    """30 % censored (6 of 20) cannot support limits, and the message says so with numbers."""
    values: list[float | None] = [1.0] * 14 + [None] * 6

    with pytest.raises(InsufficientDataError) as error:
        apply_censored_policy(
            values, [None] * 14 + [2.0] * 6, [None] * 14 + ["<"] * 6, max_fraction=MAX_FRACTION
        )

    assert "30% de los datos están censurados" in str(error.value)
    assert "máximo aceptable es 20%" in str(error.value)


def test_policy_refuses_a_censored_row_without_loq() -> None:
    """Without the LOQ there is nothing to halve: refusing beats inventing a number."""
    values: list[float | None] = [1.0] * 9 + [None]
    loqs = [None] * 10
    qualifiers = [None] * 9 + ["<"]

    with pytest.raises(ValueError, match="no tiene LOQ"):
        apply_censored_policy(values, loqs, qualifiers, max_fraction=MAX_FRACTION)


def test_policy_refuses_a_row_with_neither_value_nor_qualifier() -> None:
    """A null value is only legitimate when the row says `< LOQ`."""
    with pytest.raises(ValueError, match="no tiene valor ni qualifier"):
        apply_censored_policy([None], [None], [None], max_fraction=MAX_FRACTION)


def test_policy_refuses_sequences_of_different_lengths() -> None:
    """Aligned inputs are a precondition, not an assumption to be discovered by an index error."""
    with pytest.raises(ValueError, match="mismo largo"):
        apply_censored_policy([1.0, 2.0], [None], [None, None], max_fraction=MAX_FRACTION)


def test_policy_on_an_empty_series_is_insufficient_data() -> None:
    """Zero observations cannot give a fraction; it is reported as missing data, not as 0 %."""
    with pytest.raises(InsufficientDataError, match="0 valores"):
        apply_censored_policy([], [], [], max_fraction=MAX_FRACTION)


def test_select_baseline_keeps_only_the_ok_rows() -> None:
    """Suspect and failed data never anchor the limits; they do not even count towards `n`."""
    rows = [_row(10.0 + index) for index in range(20)] + [
        _row(99.0, qc_flag="suspect"),
        _row(120.0, qc_flag="failed"),
    ]
    values, metadata = select_baseline(rows)

    assert len(values) == 20
    assert metadata["n"] == 20
    assert 99.0 not in values
    assert 120.0 not in values
    assert metadata["method"] == "imr"
    assert metadata["min_points"] == 20


def test_select_baseline_counts_only_usable_rows_before_complaining() -> None:
    """19 usable rows plus 5 suspect ones is «hay 19», not «hay 24»."""
    rows = [_row(10.0 + index) for index in range(19)] + [
        _row(50.0, qc_flag="suspect") for _ in range(5)
    ]

    with pytest.raises(InsufficientDataError) as error:
        select_baseline(rows)

    assert str(error.value) == (
        "Se requieren al menos 20 observaciones válidas para la línea base (hay 19)."
    )


def test_select_baseline_applies_the_censored_policy_it_documents() -> None:
    """Two of twenty censored rows enter the calculation as LOQ/2 and the metadata says so."""
    rows = [_row(10.0 + index) for index in range(18)] + [
        _row(None, loq=0.4, qualifier="<"),
        _row(None, loq=0.8, qualifier="<"),
    ]
    values, metadata = select_baseline(rows)

    assert values[18:] == [pytest.approx(0.2), pytest.approx(0.4)]
    assert metadata["censored_count"] == 2
    assert metadata["censored_fraction"] == pytest.approx(0.1)


def test_select_baseline_honours_a_custom_minimum() -> None:
    """Ten points are enough when the caller asks for ten: the floor is a parameter, not a law."""
    rows = [_row(float(10 + index)) for index in range(10)]
    values, metadata = select_baseline(rows, min_points=10)

    assert len(values) == 10
    assert metadata["min_points"] == 10


def test_select_baseline_honours_a_custom_censoring_ceiling() -> None:
    """With a 50 % ceiling the same six censored rows that were refused above are accepted."""
    rows = [_row(1.0) for _ in range(14)] + [_row(None, loq=2.0, qualifier="<") for _ in range(6)]
    values, metadata = select_baseline(rows, censored_max_fraction=0.5)

    assert metadata["censored_count"] == 6
    assert values[14:] == [pytest.approx(1.0)] * 6


def test_select_baseline_on_an_empty_series_is_insufficient_data() -> None:
    """No rows at all is the ordinary «todavía no hay datos» state of a brand-new site."""
    with pytest.raises(InsufficientDataError, match="hay 0"):
        select_baseline([])

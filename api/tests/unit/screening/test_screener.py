"""Contract tests for `app/screening/screener.py`, built on hand-made catalog entities.

The fixtures mirror the real catalog rows (`PH` / NCh 1.333 / `vida_acuatica`: 6,0–9,0 UPH) so a
reader can compare them with `catalog/limits.v1.json`. Only `status`, `statistic` and the unit
change between tests: the policy under test is exactly those three.
"""

from dataclasses import replace

import pytest

from app.catalog import Limit, Parameter
from app.screening import (
    ScreeningFlag,
    ScreeningResult,
    screen_observation,
    select_applicable_limit,
)

PH_PARAMETER = Parameter(
    code="PH",
    name_es="pH",
    category="fisicoquimico",
    canonical_unit_code="UPH",
    decimals=2,
    measurement_type="laboratorio",
    status="draft-verified",
    mvp_optional=False,
)

# PH / NCh 1.333 / vida acuática, as published in catalog/limits.v1.json.
PH_LIMIT = Limit(
    parameter_code="PH",
    regulation_code="NCh1333",
    statistic="max_absolute",
    min=6.0,
    max=9.0,
    max_increase_over_natural=None,
    unit_code="UPH",
    status="validated",
    context="vida_acuatica",
    monitoring_area_code=None,
    quality_level=None,
)

# PH / D.S. 53/2014 / MA-1 / conservación, historical percentile over a three-year window.
DS53_PH_LIMIT = Limit(
    parameter_code="PH",
    regulation_code="DS53-2014-MMA",
    statistic="P5_P95",
    min=6.5,
    max=8.7,
    max_increase_over_natural=None,
    unit_code="UPH",
    status="validated",
    context=None,
    monitoring_area_code="MA-1",
    quality_level="conservacion",
)


def screen(value: float | None, limit: Limit | None) -> ScreeningResult:
    """Screen `value` against `limit` with the PH parameter and no censoring."""
    return screen_observation(value, None, None, PH_PARAMETER, limit)


def test_screen_censored_observation_is_not_evaluable() -> None:
    result = screen_observation(None, "<", 0.5, PH_PARAMETER, PH_LIMIT)

    assert result.flag is ScreeningFlag.not_evaluable
    assert "censurada" in result.reason
    assert result.limit_applied == PH_LIMIT
    assert result.exceedance_ratio is None


def test_screen_without_applicable_limit_is_not_evaluable() -> None:
    result = screen(7.5, None)

    assert result.flag is ScreeningFlag.not_evaluable
    assert "No hay límite aplicable" in result.reason
    assert result.limit_applied is None


def test_screen_draft_limit_is_not_evaluable() -> None:
    result = screen(9.5, replace(PH_LIMIT, status="draft-verified"))

    assert result.flag is ScreeningFlag.not_evaluable
    assert "pendiente de validación" in result.reason
    assert result.limit_applied is not None
    assert result.limit_applied.status == "draft-verified"


def test_screen_max_absolute_above_max_is_above_range() -> None:
    result = screen(9.5, PH_LIMIT)

    assert result.flag is ScreeningFlag.above_range
    assert "supera el máximo" in result.reason
    assert result.exceedance_ratio == pytest.approx(9.5 / 9.0)


def test_screen_max_absolute_below_min_is_below_range() -> None:
    result = screen(5.5, PH_LIMIT)

    assert result.flag is ScreeningFlag.below_range
    assert "bajo el mínimo" in result.reason
    assert result.exceedance_ratio == pytest.approx(6.0 / 5.5)


def test_screen_min_absolute_below_min_is_below_range() -> None:
    oxygen = Limit(
        parameter_code="DO",
        regulation_code="NCh1333",
        statistic="min_absolute",
        min=5.0,
        max=None,
        max_increase_over_natural=None,
        unit_code="MG_L",
        status="validated",
        context="vida_acuatica",
        monitoring_area_code=None,
        quality_level=None,
    )
    dissolved_oxygen = Parameter(
        code="DO",
        name_es="Oxígeno disuelto",
        category="fisicoquimico",
        canonical_unit_code="MG_L",
        decimals=2,
        measurement_type="laboratorio",
        status="draft-verified",
        mvp_optional=False,
    )

    result = screen_observation(3.0, None, None, dissolved_oxygen, oxygen)

    assert result.flag is ScreeningFlag.below_range
    assert result.exceedance_ratio == pytest.approx(5.0 / 3.0)


def test_screen_inside_range_is_normal() -> None:
    result = screen(7.4, PH_LIMIT)

    assert result.flag is ScreeningFlag.normal
    assert result.reason == "Dentro del rango de referencia."
    assert result.exceedance_ratio is None


def test_screen_max_increase_over_natural_is_not_evaluable() -> None:
    turbidity_limit = replace(
        PH_LIMIT,
        parameter_code="TURB",
        statistic="maxIncreaseOverNatural",
        min=None,
        max=None,
        max_increase_over_natural=4.0,
        unit_code="NTU",
    )
    turbidity = replace(PH_PARAMETER, code="TURB", canonical_unit_code="NTU", name_es="Turbiedad")

    result = screen_observation(6.0, None, None, turbidity, turbidity_limit)

    assert result.flag is ScreeningFlag.not_evaluable
    assert "baselineReference" in result.reason


def test_screen_triennial_statistic_is_not_evaluable() -> None:
    result = screen(7.4, DS53_PH_LIMIT)

    assert result.flag is ScreeningFlag.not_evaluable
    assert "trienal" in result.reason
    assert result.limit_applied == DS53_PH_LIMIT


def test_screen_unknown_statistic_is_not_evaluable() -> None:
    result = screen(7.4, replace(PH_LIMIT, statistic="mean_max"))

    assert result.flag is ScreeningFlag.not_evaluable
    assert "no soportado" in result.reason


def test_screen_limit_in_another_unit_is_not_evaluable() -> None:
    """MG/L and MG-N/L share a dimension but are not the same quantity: never compare."""
    result = screen(7.4, replace(PH_LIMIT, unit_code="MG_L"))

    assert result.flag is ScreeningFlag.not_evaluable
    assert "conversión explícita" in result.reason


def test_select_limit_requires_context_for_nch1333() -> None:
    limits = (PH_LIMIT,)

    assert select_applicable_limit(limits, "PH", "NCh1333") is None


def test_select_limit_returns_the_exact_context() -> None:
    irrigation = replace(PH_LIMIT, context="riego", min=5.5)
    limits = (PH_LIMIT, irrigation)

    assert select_applicable_limit(limits, "PH", "NCh1333", "riego") == irrigation
    assert select_applicable_limit(limits, "PH", "NCh1333", "vida_acuatica") == PH_LIMIT


def test_select_limit_requires_area_and_level_for_ds53() -> None:
    limits = (DS53_PH_LIMIT,)

    assert select_applicable_limit(limits, "PH", "DS53-2014-MMA") is None
    assert (
        select_applicable_limit(limits, "PH", "DS53-2014-MMA", monitoring_area_code="MA-1") is None
    )
    assert (
        select_applicable_limit(
            limits,
            "PH",
            "DS53-2014-MMA",
            monitoring_area_code="MA-1",
            quality_level="conservacion",
        )
        == DS53_PH_LIMIT
    )


def test_select_limit_with_two_candidates_is_ambiguous() -> None:
    limits = (PH_LIMIT, replace(PH_LIMIT))

    assert select_applicable_limit(limits, "PH", "NCh1333", "vida_acuatica") is None


def test_select_limit_ignores_other_parameter_or_regulation() -> None:
    limits = (PH_LIMIT, DS53_PH_LIMIT)

    assert select_applicable_limit(limits, "DO", "NCh1333", "vida_acuatica") is None
    assert select_applicable_limit(limits, "PH", "NCh999", "vida_acuatica") is None

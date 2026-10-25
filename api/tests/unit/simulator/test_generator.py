"""Deterministic tests for the pure simulator (02 §7, 03 §2 N2).

The determinism assertions are deliberate: the demo data behind the README screenshots must be
reproducible from `--seed`, so a change in the RNG call order has to break a test here and not
the screenshots.

The event tests pin `ar1_phi = 0`: with the default 0.7 the 20-point windows they compare
overlap heavily and the assertions would become statistical instead of deterministic.
"""

from datetime import UTC, datetime
from statistics import fmean

import numpy as np
import pytest

from app.catalog.loader import load_catalog
from app.core.config import REPO_ROOT
from app.simulator import Event, EventType, ScenarioConfig, generate_batch, generate_series
from app.simulator.generator import SeriesPoint

START_AT = datetime(2026, 10, 1, tzinfo=UTC)
BASE_MEAN = 7.5
BASE_STD = 0.3


def scenario(
    *,
    days: int = 3,
    interval_minutes: int = 30,
    seed: int = 42,
    ar1_phi: float = 0.0,
    events: tuple[Event, ...] = (),
) -> ScenarioConfig:
    """A pH scenario at a fixed baseline; the defaults give 144 hourly-equivalent points."""
    return ScenarioConfig(
        site_code="SIM-TEST-01",
        parameter_code="PH",
        days=days,
        seed=seed,
        base_mean=BASE_MEAN,
        base_std=BASE_STD,
        ar1_phi=ar1_phi,
        events=events,
        interval_minutes=interval_minutes,
    )


def value_at(series: list[SeriesPoint], index: int) -> float:
    """The measured value at `index`, failing loudly on a dropout or a censored point."""
    value = series[index][1]
    assert value is not None, f"el punto {index} no tiene valor medido"
    return value


def test_determinism_same_seed_same_series() -> None:
    """Same scenario and same seed reproduce value by value, timestamps included."""
    events = (
        Event(at_index=5, type=EventType.censored, magnitude=0.1, duration=2),
        Event(at_index=40, type=EventType.shift, magnitude=0.6, duration=10),
        Event(at_index=60, type=EventType.dropout, magnitude=0.0, duration=3),
    )
    first = generate_series(scenario(events=events), START_AT)
    second = generate_series(scenario(events=events), START_AT)

    assert len(first) == len(second) == 144
    for left, right in zip(first, second, strict=True):
        assert left[0] == right[0]
        assert left[2:] == right[2:]
        assert _same_value(left[1], right[1])


def test_determinism_different_seed_different_series() -> None:
    """A different seed is a different realisation, not a rescaled copy."""
    first = generate_series(scenario(seed=42, ar1_phi=0.7), START_AT)
    second = generate_series(scenario(seed=43, ar1_phi=0.7), START_AT)

    assert [point[1] for point in first[:10]] != [point[1] for point in second[:10]]


def test_no_events_mean_and_std() -> None:
    """Without events the series looks like the configured process: mean and spread hold.

    iid sampling (`ar1_phi = 0`) over 2880 points, in place of the 2000 the rule of thumb
    suggests, because points = days * 1440 // interval.
    """
    series = generate_series(scenario(days=2, interval_minutes=1), START_AT)
    values = [value_at(series, index) for index in range(len(series))]

    assert len(values) == 2880
    assert abs(fmean(values) - BASE_MEAN) < 0.05 * BASE_STD
    assert 0.9 * BASE_STD < float(np.std(values, ddof=1)) < 1.1 * BASE_STD


def _same_value(left: float | None, right: float | None) -> bool:
    """Compare two readings, treating two missing values as equal (no NaN in the contract)."""
    if left is None or right is None:
        return left is right
    return abs(left - right) <= 1e-12


def test_shift_event_increases_mean() -> None:
    """A `shift` moves the level by its magnitude and holds it for the whole block."""
    series = generate_series(
        scenario(events=(Event(at_index=100, type=EventType.shift, magnitude=0.6, duration=20),)),
        START_AT,
    )
    before = [value_at(series, index) for index in range(100)]
    during = [value_at(series, index) for index in range(100, 120)]

    assert fmean(during) > fmean(before) + 0.4
    assert value_at(series, 120) < fmean(during)


def test_spike_event_single_point() -> None:
    """A `spike` breaks exactly one point; the next readings are back to the process level."""
    series = generate_series(
        scenario(events=(Event(at_index=50, type=EventType.spike, magnitude=3.0),)),
        START_AT,
    )

    assert value_at(series, 50) > value_at(series, 49) + 2.0
    assert abs(value_at(series, 51) - BASE_MEAN) < 4 * BASE_STD
    assert abs(value_at(series, 52) - BASE_MEAN) < 4 * BASE_STD


def test_drift_event_linear() -> None:
    """A `drift` ramps from one increment to `magnitude` across the block: a positive trend."""
    series = generate_series(
        scenario(events=(Event(at_index=10, type=EventType.drift, magnitude=2.0, duration=10),)),
        START_AT,
    )
    block = [value_at(series, index) for index in range(10, 20)]

    assert block[-1] > block[0] + 1.5
    # A least-squares slope is robust to the noise each point of the ramp rides on.
    slope = float(np.polyfit(np.arange(len(block)), block, 1)[0])
    assert slope > 0.05


def test_dropout_produces_none_values() -> None:
    """A `dropout` is a lost reading: no value, no qualifier, no LOQ."""
    series = generate_series(
        scenario(events=(Event(at_index=30, type=EventType.dropout, magnitude=0.0, duration=5),)),
        START_AT,
    )

    dropped = series[30:35]
    assert len(dropped) == 5
    assert all(
        value is None and qualifier is None and loq is None for _, value, qualifier, loq in dropped
    )
    assert value_at(series, 35) is not None


def test_censored_produces_loq() -> None:
    """A censored point reports `< LOQ` and never a value (ADR-003)."""
    series = generate_series(
        scenario(events=(Event(at_index=20, type=EventType.censored, magnitude=0.1, duration=3),)),
        START_AT,
    )

    censored = series[20:23]
    assert all(value is None for _, value, _, _ in censored)
    assert all(qualifier == "<" for _, _, qualifier, _ in censored)
    assert all(loq == 0.1 for _, _, _, loq in censored)


def test_ar1_phi_validation() -> None:
    """`ar1_phi = 1` is a random walk and `-0.1` has no stationary variance: both are rejected."""
    with pytest.raises(ValueError, match="ar1_phi"):
        scenario(ar1_phi=1.5)
    with pytest.raises(ValueError, match="ar1_phi"):
        scenario(ar1_phi=-0.1)


def test_generate_batch_uses_catalog_units() -> None:
    """The batch speaks the ingest contract: catalog unit, catalog version, no phantom sample.

    A `dropout` cannot be expressed in the contract (there is no «no value and no LOQ»), so it is
    not sent: the batch carries 47 of the 48 hourly points of one day.
    """
    catalog = load_catalog(REPO_ROOT / "catalog")
    batch = generate_batch(
        scenario(days=1, events=(Event(at_index=10, type=EventType.dropout, magnitude=0.0),)),
        START_AT,
        catalog,
    )

    assert batch.catalog_version == "1.0.0"
    assert batch.site.code == "SIM-TEST-01"
    assert {observation.unit_code for observation in batch.observations} == {"UPH"}
    assert {observation.parameter_code for observation in batch.observations} == {"PH"}
    assert len(batch.observations) == 47
    # 01 §5: una lectura de sensor no cuelga de una muestra de laboratorio.
    assert batch.samples == []
    assert all(observation.sample_id is None for observation in batch.observations)

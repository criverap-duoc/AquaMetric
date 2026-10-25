"""Deterministic generation of sensor-like series (02 §7).

The module is pure: the start instant arrives as an argument, the catalog as a value, and the
randomness comes from `numpy.random.PCG64(seed)`. Same scenario and same seed therefore produce
the same batch on any machine, in any timezone and on any day — which is what makes the demo in
the README reproducible.

Model: an AR(1) process around `base_mean` with innovations scaled so the stationary standard
deviation stays `base_std` (`sigma_e = sigma * sqrt(1 - phi^2)`), plus the anomalies declared in
`ScenarioConfig.events`.
"""

from datetime import UTC, datetime, timedelta
from math import sqrt
from typing import Literal
from uuid import NAMESPACE_DNS, uuid5

import numpy as np

from app.catalog import Catalog
from app.schemas.ingest import IngestRequest, ObservationIn, SampleIn, SiteIn
from app.simulator.scenario import Event, EventType, ScenarioConfig

# Only `<` is generated: the simulator reports detection limits, never saturation (ADR-003).
type SeriesQualifier = Literal["<"] | None
# One row of the series: timestamp, value, qualifier and quantification limit.
type SeriesPoint = tuple[datetime, float | None, SeriesQualifier, float | None]

# The demo is always Chilean central-southern river water; one coordinate would be a lie anyway.
_SITE_LATITUDE = -33.45
_SITE_LONGITUDE = -70.66
_SAMPLE_MATRIX = "water"


def to_utc(value: datetime) -> datetime:
    """Normalise a timestamp to UTC, rejecting naive datetimes (01 §5).

    Raises:
        ValueError: `value` has no timezone, so it cannot be placed on the timeline.
    """
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("La fecha debe incluir zona horaria (por ejemplo 2026-10-01T00:00:00Z).")
    return value.astimezone(UTC)


def generate_series(config: ScenarioConfig, start_at: datetime) -> list[SeriesPoint]:
    """Build the whole series, anomalies included.

    `x[0] = base_mean + base_std * z[0]` and, for `t >= 1`,
    `x[t] = phi * x[t-1] + (1 - phi) * base_mean + base_std * sqrt(1 - phi²) * z[t]`,
    with `z` a single standard-normal stream drawn from `PCG64(seed)`.

    Args:
        config: the scenario. Its events are applied in declaration order.
        start_at: UTC instant of the first observation; the series advances by
            `config.interval_minutes` from there.

    Returns:
        One tuple per point: `(timestamp, value, qualifier, loq)`. A `dropout` yields
        `(t, None, None, None)`; a censored point yields `(t, None, "<", loq)`.

    Raises:
        ValueError: `start_at` has no timezone.
    """
    origin = to_utc(start_at)
    points = config.points
    phi = config.ar1_phi
    innovation_scale = config.base_std * sqrt(1.0 - phi * phi)

    rng = np.random.Generator(np.random.PCG64(config.seed))
    shocks = rng.standard_normal(points)
    values = np.empty(points, dtype=float)
    values[0] = config.base_mean + config.base_std * shocks[0]
    for index in range(1, points):
        values[index] = (
            phi * values[index - 1]
            + (1.0 - phi) * config.base_mean
            + innovation_scale * shocks[index]
        )

    # Missing readings travel as NaN until the end, so one marker covers dropout and censored.
    qualifiers: list[SeriesQualifier] = [None] * points
    loqs: list[float | None] = [None] * points
    for event in config.events:
        _apply_event(values, qualifiers, loqs, event)

    return [
        (
            origin + timedelta(minutes=config.interval_minutes * index),
            None if np.isnan(values[index]) else float(values[index]),
            qualifiers[index],
            loqs[index],
        )
        for index in range(points)
    ]


def _apply_event(
    values: np.ndarray,
    qualifiers: list[SeriesQualifier],
    loqs: list[float | None],
    event: Event,
) -> None:
    """Write one anomaly into the arrays, clipped to the end of the series.

    The arrays are the ones `generate_series` just built, so mutating them keeps the function
    pure from the caller's point of view while avoiding three copies per event.
    """
    start = event.at_index
    stop = min(start + event.duration, values.size)
    if event.type is EventType.shift:
        values[start:stop] += event.magnitude
    elif event.type is EventType.spike:
        values[start] += event.magnitude
    elif event.type is EventType.drift:
        # Linear ramp: the k-th point of the block moves by `magnitude * k / duration`.
        ramp = np.arange(1, stop - start + 1, dtype=float) / event.duration
        values[start:stop] += event.magnitude * ramp
    elif event.type is EventType.dropout:
        values[start:stop] = np.nan
    else:  # EventType.censored
        values[start:stop] = np.nan
        for index in range(start, stop):
            qualifiers[index] = "<"
            loqs[index] = event.magnitude


def generate_batch(config: ScenarioConfig, start_at: datetime, catalog: Catalog) -> IngestRequest:
    """Wrap a generated series in the ingest contract (`POST /api/v1/ingest/observations`).

    Units come from the catalog (the parameter's canonical unit), never from the simulator, and
    ids are `uuid5` of the scenario, so re-running a seed rewrites the same rows.

    Two consequences of the contract shape what the batch contains:
      * a `dropout` is a missing reading, and the contract has no way to say «no value and no
        LOQ», so those points are left out instead of being sent as censored rows;
      * a `sensor` reading does not hang from a laboratory sample (01 §5), so the batch carries
        no sample and `sampleId` stays null.

    Args:
        config: the scenario.
        start_at: UTC instant of the first observation.
        catalog: the synchronized catalog, injected so this module stays free of I/O.

    Raises:
        ValueError: the parameter is not in the catalog, or the scenario produced no ingestable
            observation.
    """
    origin = to_utc(start_at)
    parameter = catalog.parameters.get(config.parameter_code)
    if parameter is None:
        raise ValueError(f"El parámetro '{config.parameter_code}' no existe en el catálogo.")

    site = SiteIn(
        id=uuid5(NAMESPACE_DNS, config.site_code),
        code=config.site_code,
        name=f"Sitio simulado {config.site_code}",
        water_body_type="river",
        latitude=_SITE_LATITUDE,
        longitude=_SITE_LONGITUDE,
        is_active=True,
    )
    sample = SampleIn(
        id=uuid5(NAMESPACE_DNS, f"{config.site_code}-{config.seed}"),
        site_id=site.id,
        campaign_id=None,
        matrix=_SAMPLE_MATRIX,
        collected_at=origin,
        lab_received_at=None,
        status="analyzed",
    )
    uses_sample = config.source != "sensor"

    observations = [
        ObservationIn(
            id=uuid5(NAMESPACE_DNS, f"{config.site_code}-{index}-{config.seed}"),
            site_id=site.id,
            sample_id=sample.id if uses_sample else None,
            parameter_code=config.parameter_code,
            value=value,
            unit_code=parameter.canonical_unit_code,
            qualifier=qualifier,
            loq=loq,
            method=None,
            analyzed_at=timestamp,
            qc_flag="ok",
            source=config.source,
        )
        for index, (timestamp, value, qualifier, loq) in enumerate(generate_series(config, origin))
        if value is not None or qualifier is not None
    ]
    if not observations:
        raise ValueError("El escenario no produjo observaciones ingeribles (todo fue dropout).")

    return IngestRequest(
        catalog_version=catalog.version,
        site=site,
        samples=[sample] if uses_sample else [],
        observations=observations,
    )

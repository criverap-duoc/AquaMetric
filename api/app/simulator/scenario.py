"""What the simulator must produce, expressed as data and nothing else (02 §7).

A scenario is fully described here — site, parameter, length, seed, baseline and the anomalies
to inject — so the generator needs neither a clock nor a database, and the same description
always yields the same series. The `SIM-` prefix that keeps these sites apart from TerraPlan is
enforced by the CLI (`run.py`), the only component that knows about operational conventions.
"""

from dataclasses import dataclass
from enum import StrEnum

from app.schemas.ingest import ObservationSource

# Length of the day in minutes; the number of points follows from the sampling interval.
MINUTES_PER_DAY = 1440
MIN_INTERVAL_MINUTES = 1
MAX_INTERVAL_MINUTES = 1440


class EventType(StrEnum):
    """Anomalies the demo needs: one code per signature an SPC chart can show.

    `shift` moves the level, `spike` breaks it for one point, `drift` rises slowly, `dropout`
    loses the reading and `censored` reports a value below the quantification limit (ADR-003).
    """

    shift = "shift"
    spike = "spike"
    drift = "drift"
    dropout = "dropout"
    censored = "censored"


@dataclass(frozen=True, slots=True)
class Event:
    """An injected anomaly, positioned by index so nothing depends on the wall clock.

    `magnitude` is expressed in the parameter's canonical unit, except for `censored`, where it
    is the quantification limit reported as `< LOQ`. `spike` always hits a single point and
    ignores `duration`; the other events cover `[at_index, at_index + duration)`.
    """

    at_index: int
    type: EventType
    magnitude: float
    duration: int = 1


@dataclass(frozen=True, slots=True)
class ScenarioConfig:
    """Everything the generator needs, validated once at construction.

    The baseline comes from the caller because it is a property of the water body, not of the
    simulator: `base_std` is the spread of a healthy series and `ar1_phi` its autocorrelation
    (sensor readings are never independent, which is exactly what I-MR charts assume away).

    Raises:
        ValueError: a parameter is out of range or an event falls outside the series.
    """

    site_code: str
    parameter_code: str
    days: int
    seed: int
    base_mean: float
    base_std: float
    ar1_phi: float = 0.7
    events: tuple[Event, ...] = ()
    source: ObservationSource = "sensor"
    interval_minutes: int = 60

    def __post_init__(self) -> None:
        if not 0.0 <= self.ar1_phi < 1.0:
            raise ValueError(f"ar1_phi debe cumplir 0 <= phi < 1 (recibido {self.ar1_phi}).")
        if self.days <= 0:
            raise ValueError(f"days debe ser mayor que 0 (recibido {self.days}).")
        if self.base_std <= 0.0:
            raise ValueError(f"base_std debe ser mayor que 0 (recibido {self.base_std}).")
        if not MIN_INTERVAL_MINUTES <= self.interval_minutes <= MAX_INTERVAL_MINUTES:
            raise ValueError(
                f"interval_minutes debe estar entre {MIN_INTERVAL_MINUTES} y "
                f"{MAX_INTERVAL_MINUTES} (recibido {self.interval_minutes})."
            )
        for index, event in enumerate(self.events):
            if event.at_index < 0:
                raise ValueError(
                    f"events[{index}].at_index debe ser >= 0 (recibido {event.at_index})."
                )
            if event.duration < 1:
                raise ValueError(
                    f"events[{index}].duration debe ser >= 1 (recibido {event.duration})."
                )
            # An event beyond the end of the series would be silently ignored by the generator.
            if event.at_index >= self.points:
                raise ValueError(
                    f"events[{index}].at_index ({event.at_index}) cae fuera de la serie "
                    f"({self.points} puntos)."
                )

    @property
    def points(self) -> int:
        """Number of observations: `days * 24 * 60 // interval_minutes`."""
        return self.days * MINUTES_PER_DAY // self.interval_minutes

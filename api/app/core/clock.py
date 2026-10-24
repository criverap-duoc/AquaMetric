"""Injected time source, so tests and the simulator never depend on the wall clock."""

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Annotated, Protocol

from fastapi import Depends


class Clock(Protocol):
    """Anything able to report the current instant in UTC."""

    def now(self) -> datetime: ...


@dataclass(frozen=True, slots=True)
class SystemClock:
    """Production clock; always timezone-aware to avoid naive datetimes in the database."""

    def now(self) -> datetime:
        return datetime.now(UTC)


@dataclass(frozen=True, slots=True)
class FrozenClock:
    """Fixed clock for tests: same input, same output, no sleeping."""

    instant: datetime

    def __post_init__(self) -> None:
        if self.instant.tzinfo is None:
            raise ValueError("FrozenClock requires a timezone-aware instant (UTC)")

    def now(self) -> datetime:
        return self.instant


def get_clock() -> Clock:
    return SystemClock()


ClockDep = Annotated[Clock, Depends(get_clock)]

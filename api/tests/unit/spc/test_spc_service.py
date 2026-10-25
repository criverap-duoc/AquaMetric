"""The service layer of the SPC slice: which rows are Phase I, which are Phase II, and how a
refusal of the pure core reaches the client as a 422 (ADR-001, ADR-003, ADR-010).

The repository is replaced at the module seam (`spc_service.SpcBaselineRepository`), so these
tests need no Docker and no database while still running the real statistical core and the real
catalog. The series are synthetic but their limits are not asserted by hand: the point here is
the orchestration (which exception becomes which status, which warning is always present), while
the formulas are pinned by `tests/golden/`.
"""

from collections.abc import Sequence
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from types import TracebackType
from typing import Any, cast
from uuid import UUID, uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.catalog import Catalog
from app.catalog.loader import load_catalog
from app.core.clock import FrozenClock
from app.core.config import REPO_ROOT
from app.core.errors import InsufficientDataError, NotFoundError, UnknownParameterError
from app.models import Observation, SpcBaseline
from app.schemas.spc import BaselineUpsertRequest
from app.services import spc_service
from app.services.spc_service import SpcService

SITE_ID = UUID("5c1f0b0a-0000-4000-8000-0000000000b1")
PARAMETER = "PH"
START = datetime(2026, 10, 1, 6, 0, tzinfo=UTC)
CLOCK = FrozenClock(datetime(2026, 10, 24, 12, 0, tzinfo=UTC))

# 20 Phase I points cycling between 7.1 and 7.9 UPH (a constant series has no sigma at all).
BASELINE_VALUES = [7.5 + 0.2 * ((index % 5) - 2) for index in range(20)]
# 10 Phase II points alternating around the center line, the last one a spike well beyond 3 sigma.
MONITORING_VALUES = [7.6, 7.4] * 4 + [7.6, 9.5]


@pytest.fixture(scope="module")
def catalog() -> Catalog:
    """The synchronized catalog, loaded once: the codes exercised are the real ones."""
    return load_catalog(REPO_ROOT / "catalog")


def rows(
    values: Sequence[float | None],
    *,
    start: datetime = START,
    loq: float = 1.0,
) -> list[Observation]:
    """Stored observations, one per value; `None` becomes a censored row (`<` + LOQ)."""
    built: list[Observation] = []
    for index, value in enumerate(values):
        censored = value is None
        built.append(
            Observation(
                id=uuid4(),
                site_id=SITE_ID,
                parameter_code=PARAMETER,
                value=None if censored else Decimal(str(value)),
                unit_code="UPH",
                qualifier="<" if censored else None,
                loq=Decimal(str(loq)) if censored else None,
                analyzed_at=start + timedelta(hours=6 * index),
                qc_flag="ok",
                source="sensor",
            )
        )
    return built


class FakeBaselineRepository:
    """In-memory stand-in for `SpcBaselineRepository` that records the upsert calls."""

    def __init__(
        self,
        baseline_rows: list[Observation],
        monitoring_rows: list[Observation] | None = None,
    ) -> None:
        self._baseline_rows = baseline_rows
        self._monitoring_rows = monitoring_rows or []
        self.upsert_calls: list[dict[str, Any]] = []
        self.stored: dict[tuple[UUID, str, str], SpcBaseline] = {}

    async def get_observations(
        self,
        site_id: UUID,
        parameter_code: str,
        *,
        after: datetime | None = None,
        limit: int,
    ) -> list[Observation]:
        """The Phase II window is requested with `after`; the Phase I one without."""
        source = self._monitoring_rows if after is not None else self._baseline_rows
        return source[:limit]

    async def get_baseline(
        self, site_id: UUID, parameter_code: str, phase: str
    ) -> SpcBaseline | None:
        return self.stored.get((site_id, parameter_code, phase))

    async def upsert_baseline(self, **kwargs: Any) -> SpcBaseline:
        self.upsert_calls.append(kwargs)
        baseline = SpcBaseline(id=uuid4(), **kwargs)
        key = (kwargs["site_id"], kwargs["parameter_code"], kwargs["phase"])
        self.stored[key] = baseline
        return baseline


class FakeSession:
    """The only part of `AsyncSession` the service uses: the async context manager of a txn."""

    def begin(self) -> "FakeSession":
        """`AsyncSession.begin()` returns a context manager, not a coroutine."""
        return self

    async def __aenter__(self) -> "FakeSession":
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        return None


def service(
    catalog: Catalog,
    monkeypatch: pytest.MonkeyPatch,
    baseline_rows: list[Observation],
    monitoring_rows: list[Observation] | None = None,
) -> tuple[SpcService, FakeBaselineRepository]:
    """Wire a service onto the fake repository; the real session is never touched."""
    fake = FakeBaselineRepository(baseline_rows, monitoring_rows)
    monkeypatch.setattr(spc_service, "SpcBaselineRepository", lambda session: fake)
    built = SpcService(cast(AsyncSession, FakeSession()), catalog, CLOCK)
    return built, fake


async def test_compute_chart_insufficient_baseline(
    catalog: Catalog, monkeypatch: pytest.MonkeyPatch
) -> None:
    """19 rows are one short: the answer is a 422 with the real count, not limits built on 19."""
    spc, _ = service(catalog, monkeypatch, rows([7.5, 7.6] * 9 + [7.4]))

    with pytest.raises(InsufficientDataError) as error:
        await spc.compute_chart(SITE_ID, PARAMETER)

    assert error.value.status == 422
    assert error.value.code == "INSUFFICIENT_DATA"
    assert "hay 19" in error.value.detail


async def test_compute_chart_censored_too_many(
    catalog: Catalog, monkeypatch: pytest.MonkeyPatch
) -> None:
    """5 censored of 20 is 25 %: above the 20 % of ADR-003, so the series is refused."""
    values: list[float | None] = [7.5, 7.6, 7.4, 7.7, 7.3] * 3 + [None] * 5
    spc, _ = service(catalog, monkeypatch, rows(values))

    with pytest.raises(InsufficientDataError) as error:
        await spc.compute_chart(SITE_ID, PARAMETER)

    assert error.value.status == 422
    assert "censurados" in error.value.detail


async def test_compute_chart_normal(catalog: Catalog, monkeypatch: pytest.MonkeyPatch) -> None:
    """20 Phase I points plus a spike in Phase II: one R1 violation, both warnings present."""
    spc, _ = service(
        catalog,
        monkeypatch,
        rows(BASELINE_VALUES),
        rows(MONITORING_VALUES, start=START + timedelta(hours=6 * len(BASELINE_VALUES))),
    )

    chart = await spc.compute_chart(SITE_ID, PARAMETER)

    assert chart.individuals.ucl > chart.individuals.center > chart.individuals.lcl
    assert chart.individuals.n_points == 20
    assert chart.moving_range is not None
    assert len(chart.violations) == 1
    assert chart.violations[0].rule == "R1"
    assert chart.violations[0].index == 9
    assert chart.baseline_persisted is False
    assert any("no dictamen de cumplimiento legal" in warning for warning in chart.warnings)
    assert any("computados al vuelo" in warning for warning in chart.warnings)
    assert chart.baseline_metadata["n"] == 20


async def test_compute_chart_counts_excluded_censored_in_monitoring(
    catalog: Catalog, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A censored Phase II reading is not plotted, and the warning says how many were left out."""
    monitoring: list[float | None] = [7.6, None, 7.4, 7.6]
    spc, _ = service(
        catalog,
        monkeypatch,
        rows(BASELINE_VALUES),
        rows(monitoring, start=START + timedelta(hours=6 * len(BASELINE_VALUES))),
    )

    chart = await spc.compute_chart(SITE_ID, PARAMETER)

    assert any("1 observaciones censuradas" in warning for warning in chart.warnings)
    assert chart.violations == []


async def test_persist_baseline_upsert(catalog: Catalog, monkeypatch: pytest.MonkeyPatch) -> None:
    """Two posts of the same series recompute twice but keep a single stored baseline."""
    spc, fake = service(catalog, monkeypatch, rows(BASELINE_VALUES))
    request = BaselineUpsertRequest(site_id=SITE_ID, parameter_code=PARAMETER)

    first = await spc.persist_baseline(request)
    second = await spc.persist_baseline(request)

    assert len(fake.upsert_calls) == 2
    assert len(fake.stored) == 1
    assert first.n_points == second.n_points == 20
    assert first.catalog_version == catalog.version
    assert first.computed_at == CLOCK.now()
    assert first.center_line > first.lcl
    assert first.ucl > first.center_line


async def test_compute_chart_rejects_unknown_parameter(
    catalog: Catalog, monkeypatch: pytest.MonkeyPatch
) -> None:
    """An unknown code is a 400 raised before the database is touched at all."""
    spc, fake = service(catalog, monkeypatch, rows(BASELINE_VALUES))

    with pytest.raises(UnknownParameterError) as error:
        await spc.compute_chart(SITE_ID, "XXX")

    assert error.value.status == 400
    assert fake.upsert_calls == []


async def test_get_persisted_baseline_without_baseline_is_not_found(
    catalog: Catalog, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A series that was never frozen answers 404 and names the endpoint that would freeze it."""
    spc, _ = service(catalog, monkeypatch, rows(BASELINE_VALUES))

    with pytest.raises(NotFoundError) as error:
        await spc.get_persisted_baseline(SITE_ID, PARAMETER)

    assert error.value.status == 404
    assert "POST /api/v1/spc/baseline" in error.value.detail

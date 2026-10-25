"""The normative band a control chart may publish (H1-E1c, ADR-010).

`specLimits` is not another control limit: it is the regulation range, drawn with its own style.
Two rules are tested here — only `validated` limits travel, and an ambiguous set of signed limits
is not resolved by picking the first one.
"""

import math
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from uuid import UUID

import pytest
from httpx import ASGITransport, AsyncClient

from app.catalog import Catalog, load_catalog
from app.core.config import Settings, get_settings
from app.core.dependencies import get_catalog
from tests.integration.db import TEST_INGEST_API_KEY, truncate_all
from tests.integration.seeding import ingest_batch, observation_body, site_body

pytestmark = pytest.mark.integration

CHARTS_URL = "/api/v1/spc/control-charts"
SITE_ID = UUID("6d0b5c1e-0000-4000-8000-0000000000d1")
SITE_CODE = "SIM-TEST-SPEC"
PARAMETER = "PH"
UNIT = "UPH"
POINTS = 30
START = datetime(2026, 10, 1, 6, 0, tzinfo=UTC)

# Real catalog rows: PH / NCh 1.333 has one limit per water use (vida_acuatica 6,0–9,0; riego
# 5,5–9,0). Promoting one is the only way to test the day the chemist signs a value.
VIDA_ACUATICA = ("PH", "NCh1333", "vida_acuatica")
RIEGO = ("PH", "NCh1333", "riego")


def catalog_with(promoted: set[tuple[str, str, str]], settings: Settings) -> Catalog:
    """The real catalog with exactly the listed limits signed."""
    catalog = load_catalog(settings.catalog_dir)
    limits = tuple(
        replace(limit, status="validated")
        if (limit.parameter_code, limit.regulation_code, limit.context) in promoted
        else limit
        for limit in catalog.limits
    )
    return replace(catalog, limits=limits)


@asynccontextmanager
async def chart_client(
    database_url: str, catalog: Catalog, monkeypatch: pytest.MonkeyPatch
) -> AsyncIterator[AsyncClient]:
    """App whose catalog returns the promoted copy, on the throwaway database."""
    await truncate_all(database_url)
    monkeypatch.setenv("ENV", "ci")
    monkeypatch.setenv("DATABASE_URL", database_url)
    monkeypatch.setenv("INGEST_API_KEY", TEST_INGEST_API_KEY)
    get_settings.cache_clear()
    try:
        from app.main import create_app

        app = create_app()
        app.dependency_overrides[get_catalog] = lambda: catalog
        async with app.router.lifespan_context(app):
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                yield client
        app.dependency_overrides.clear()
    finally:
        get_settings.cache_clear()
        get_catalog.cache_clear()


@pytest.fixture
def validated_catalog(settings: Settings) -> Catalog:
    return catalog_with({VIDA_ACUATICA}, settings)


@pytest.fixture
def ambiguous_catalog(settings: Settings) -> Catalog:
    return catalog_with({VIDA_ACUATICA, RIEGO}, settings)


@pytest.fixture
async def validated_client(
    database_url: str, validated_catalog: Catalog, monkeypatch: pytest.MonkeyPatch
) -> AsyncIterator[AsyncClient]:
    async with chart_client(database_url, validated_catalog, monkeypatch) as client:
        yield client


@pytest.fixture
async def ambiguous_client(
    database_url: str, ambiguous_catalog: Catalog, monkeypatch: pytest.MonkeyPatch
) -> AsyncIterator[AsyncClient]:
    async with chart_client(database_url, ambiguous_catalog, monkeypatch) as client:
        yield client


async def seed_series(client: AsyncClient) -> None:
    """A 30-point PH series: enough for the 20-point Phase I baseline of ADR-001."""
    values = [round(7.5 + 0.3 * math.sin(index * 1.7), 3) for index in range(POINTS)]
    await ingest_batch(
        client,
        site=site_body(SITE_ID, SITE_CODE, name="Sitio de prueba del rango normativo"),
        observations=[
            observation_body(SITE_ID, START + timedelta(hours=6 * index), value=value)
            for index, value in enumerate(values)
        ],
    )


async def test_validated_limit_is_published_as_spec_limits(validated_client: AsyncClient) -> None:
    await seed_series(validated_client)

    response = await validated_client.get(
        CHARTS_URL, params={"siteId": str(SITE_ID), "parameterCode": PARAMETER}
    )

    payload = response.json()

    assert response.status_code == 200, response.text
    assert payload["specLimits"] == {
        "min": 6.0,
        "max": 9.0,
        "unitCode": UNIT,
        "regulationCode": "NCh1333",
        "status": "validated",
    }
    # The control limits are a different object with its own values; the band is only a reference.
    assert payload["individuals"]["method"] == "imr_individuals"
    assert payload["individuals"]["ucl"] != payload["specLimits"]["max"]


async def test_draft_limits_are_not_published(api_client: AsyncClient) -> None:
    """Every limit of the synchronized catalog is `draft-verified`, so there is nothing to draw."""
    await seed_series(api_client)

    response = await api_client.get(
        CHARTS_URL, params={"siteId": str(SITE_ID), "parameterCode": PARAMETER}
    )

    assert response.status_code == 200, response.text
    assert response.json()["specLimits"] is None


async def test_two_validated_limits_leave_the_range_empty(ambiguous_client: AsyncClient) -> None:
    """Two signed water uses mean two different bands: the chart does not choose one."""
    await seed_series(ambiguous_client)

    response = await ambiguous_client.get(
        CHARTS_URL, params={"siteId": str(SITE_ID), "parameterCode": PARAMETER}
    )

    assert response.status_code == 200, response.text
    assert response.json()["specLimits"] is None

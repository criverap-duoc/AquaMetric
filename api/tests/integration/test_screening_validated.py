"""One limit promoted to `validated`, everything else untouched (ADR-012 §7).

The catalog is immutable and `get_catalog` is cached, so the only way to test the day the chemist
signs a limit is to replace the value in memory and override the dependency. What this proves:

1. A validated limit really produces `above_range` / `normal` for a single observation.
2. Promoting one limit does not promote its neighbours: `DO` stays `not_evaluable`.
3. The same catalog feeds the selector, so `/screening/limits` reports the new status.
"""

from collections.abc import AsyncIterator
from dataclasses import replace

import pytest
from httpx import ASGITransport, AsyncClient

from app.catalog import Catalog, load_catalog
from app.core.config import Settings
from app.core.dependencies import get_catalog
from app.screening import ScreeningFlag

pytestmark = pytest.mark.integration

SCREENING_URL = "/api/v1/screening/evaluate"
LIMITS_URL = "/api/v1/screening/limits"
ANALYZED_AT = "2026-10-01T12:00:00Z"

# The single row this module promotes: PH / NCh 1.333 / vida acuática (6,0–9,0 UPH).
PROMOTED = ("PH", "NCh1333", "vida_acuatica")


@pytest.fixture
def validated_catalog(settings: Settings) -> Catalog:
    """The real catalog with exactly one limit signed by the chemist."""
    catalog = load_catalog(settings.catalog_dir)
    limits = tuple(
        replace(limit, status="validated")
        if (
            limit.parameter_code,
            limit.regulation_code,
            limit.context,
        )
        == PROMOTED
        else limit
        for limit in catalog.limits
    )
    return replace(catalog, limits=limits)


@pytest.fixture
async def screening_client(
    validated_catalog: Catalog, settings: Settings
) -> AsyncIterator[AsyncClient]:
    """App whose catalog dependency returns the promoted copy instead of the loaded one."""
    from app.main import create_app

    get_catalog.cache_clear()
    app = create_app()
    app.dependency_overrides[get_catalog] = lambda: validated_catalog
    try:
        async with app.router.lifespan_context(app):
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as http_client:
                yield http_client
    finally:
        app.dependency_overrides.clear()
        get_catalog.cache_clear()


def ph_body(value: float) -> dict[str, object]:
    return {
        "parameterCode": "PH",
        "value": value,
        "unitCode": "UPH",
        "analyzedAt": ANALYZED_AT,
        "regulation": "NCh1333",
        "context": "vida_acuatica",
    }


async def test_validated_limit_above_max_is_above_range(screening_client: AsyncClient) -> None:
    response = await screening_client.post(SCREENING_URL, json=ph_body(9.5))

    payload = response.json()

    assert response.status_code == 200
    assert payload["flag"] == ScreeningFlag.above_range
    assert payload["limitApplied"]["status"] == "validated"
    assert "supera el máximo" in payload["reason"]
    assert payload["exceedanceRatio"] == pytest.approx(1.0556, abs=1e-4)
    assert payload["warnings"]


async def test_validated_limit_inside_range_is_normal(screening_client: AsyncClient) -> None:
    response = await screening_client.post(SCREENING_URL, json=ph_body(6.5))

    payload = response.json()

    assert payload["flag"] == ScreeningFlag.normal
    assert payload["reason"] == "Dentro del rango de referencia."
    assert payload["exceedanceRatio"] is None


async def test_promoting_one_limit_leaves_the_others_pending(screening_client: AsyncClient) -> None:
    """DO is still `draft-verified`, so the same body shape keeps answering `not_evaluable`."""
    response = await screening_client.post(
        SCREENING_URL,
        json={
            "parameterCode": "DO",
            "value": 3.0,
            "unitCode": "MG_L",
            "analyzedAt": ANALYZED_AT,
            "regulation": "NCh1333",
            "context": "vida_acuatica",
        },
    )

    payload = response.json()

    assert payload["flag"] == ScreeningFlag.not_evaluable
    assert "pendiente de validación" in payload["reason"]
    assert payload["limitApplied"]["status"] == "draft-verified"


async def test_selector_reports_the_promoted_limit(screening_client: AsyncClient) -> None:
    response = await screening_client.get(
        LIMITS_URL,
        params={
            "parameterCode": "PH",
            "regulation": "NCh1333",
            "context": "vida_acuatica",
        },
    )

    limits = response.json()["limits"]

    assert response.status_code == 200
    assert len(limits) == 1
    assert limits[0]["status"] == "validated"
    assert limits[0]["max"] == 9.0

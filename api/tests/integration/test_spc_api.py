"""Contract tests for the public SPC endpoints and the authenticated baseline write (D-2).

Docker required: the point is the real PostgreSQL path — the Phase I limits, the persisted
baseline, the upsert and the 401/404/422 answers are produced by the same tables, handlers and
dependencies the app uses. Every chart must also repeat that control limits are not a compliance
verdict (ADR-010): seeing a chart without that sentence would mean the policy is broken.
"""

import math
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID, uuid4

import pytest
from httpx import AsyncClient

from tests.integration.db import TEST_INGEST_API_KEY, fetchval

pytestmark = pytest.mark.integration

CHARTS_URL = "/api/v1/spc/control-charts"
BASELINE_URL = "/api/v1/spc/baseline"
RULES_URL = "/api/v1/spc/rules"
INGEST_URL = "/api/v1/ingest/observations"

CATALOG_VERSION = "1.0.0"
SITE_ID = UUID("5c1f0b0a-0000-4000-8000-0000000000c1")
SITE_CODE = "SIM-TEST-SPC"
PARAMETER = "PH"
UNIT = "UPH"
BASELINE_POINTS = 20
START = datetime(2026, 10, 1, 6, 0, tzinfo=UTC)
RULE_CODES = {"R1", "R2", "R3", "R4", "R5"}


def analyzed_at(index: int) -> str:
    """ISO-8601 UTC with `Z`, one reading every six hours (naive timestamps are a 400)."""
    return (START + timedelta(hours=6 * index)).isoformat().replace("+00:00", "Z")


def baseline_values() -> list[float]:
    """20 readings around 7.5 UPH with real variation: a constant series has no sigma."""
    return [round(7.5 + 0.3 * math.sin(index * 1.7), 3) for index in range(BASELINE_POINTS)]


def monitoring_values() -> list[float]:
    """10 further readings, the last one a spike well beyond the 3-sigma band (rule R1)."""
    return [round(7.5 + 0.3 * math.cos(index * 1.3), 3) for index in range(9)] + [9.8]


def payload(values: list[float]) -> dict[str, Any]:
    """A sensor batch: no samples, one site, one observation per value."""
    return {
        "catalogVersion": CATALOG_VERSION,
        "site": {
            "id": str(SITE_ID),
            "code": SITE_CODE,
            "name": "Sitio de prueba SPC",
            "waterBodyType": "river",
            "latitude": -33.45,
            "longitude": -70.66,
        },
        "samples": [],
        "observations": [
            {
                "id": str(uuid4()),
                "siteId": str(SITE_ID),
                "parameterCode": PARAMETER,
                "value": value,
                "unitCode": UNIT,
                "analyzedAt": analyzed_at(index),
                "source": "sensor",
            }
            for index, value in enumerate(values)
        ],
    }


def ingest_headers() -> dict[str, str]:
    """Ingest needs the API key and a fresh `Idempotency-Key` for every batch."""
    return {"X-API-Key": TEST_INGEST_API_KEY, "Idempotency-Key": uuid4().hex}


def baseline_request() -> dict[str, Any]:
    return {
        "siteId": str(SITE_ID),
        "parameterCode": PARAMETER,
        "method": "imr",
        "baselinePoints": BASELINE_POINTS,
    }


def write_headers() -> dict[str, str]:
    return {"X-API-Key": TEST_INGEST_API_KEY}


async def seed(client: AsyncClient, values: list[float]) -> None:
    """Load the series through the real ingest endpoint: no test-only write path."""
    response = await client.post(INGEST_URL, json=payload(values), headers=ingest_headers())
    assert response.status_code == 200, response.text


async def seed_series(client: AsyncClient) -> None:
    """30 readings: the 20 of Phase I plus 10 of Phase II, the last one out of control."""
    await seed(client, baseline_values() + monitoring_values())


def assert_problem(response: Any, status_code: int, code: str) -> dict[str, Any]:
    """Assert the RFC 9457 shape the UI already parses."""
    assert response.status_code == status_code, response.text
    assert response.headers["content-type"] == "application/problem+json"
    body: dict[str, Any] = response.json()
    assert body["code"] == code
    assert body["status"] == status_code
    assert body["detail"]
    return body


async def baseline_rows(database_url: str) -> int:
    """Rows in `spc_baseline`, read straight from PostgreSQL."""
    return int(await fetchval(database_url, "SELECT count(*) FROM aquametric.spc_baseline"))


async def test_get_control_charts_public(api_client: AsyncClient) -> None:
    """No credentials, no persisted baseline: limits computed on the fly, with the disclaimer."""
    await seed_series(api_client)

    response = await api_client.get(
        CHARTS_URL,
        params={"siteId": str(SITE_ID), "parameterCode": PARAMETER},
    )

    assert response.status_code == 200, response.text
    body = response.json()
    individuals = body["individuals"]
    assert individuals["ucl"] > individuals["center"] > individuals["lcl"]
    assert individuals["nPoints"] == BASELINE_POINTS
    assert body["movingRange"]["lcl"] == 0
    assert body["baselinePersisted"] is False
    assert body["baselineMetadata"]["n"] == BASELINE_POINTS
    assert any("no dictamen de cumplimiento legal" in item for item in body["warnings"])
    assert any("computados al vuelo" in item for item in body["warnings"])


async def test_get_control_charts_insufficient(api_client: AsyncClient) -> None:
    """A series with no rows answers 422 INSUFFICIENT_DATA, not an invented chart."""
    response = await api_client.get(
        CHARTS_URL,
        params={"siteId": str(SITE_ID), "parameterCode": PARAMETER},
    )

    body = assert_problem(response, 422, "INSUFFICIENT_DATA")
    assert "20" in body["detail"]


async def test_unknown_parameter_is_a_400(api_client: AsyncClient) -> None:
    """An unknown code is rejected before the series is even read."""
    response = await api_client.get(
        CHARTS_URL,
        params={"siteId": str(SITE_ID), "parameterCode": "XXX"},
    )

    assert_problem(response, 400, "UNKNOWN_PARAMETER")


async def test_post_baseline_requires_api_key(api_client: AsyncClient) -> None:
    """The only write of the slice: without `X-API-Key` there is no baseline."""
    await seed_series(api_client)

    response = await api_client.post(BASELINE_URL, json=baseline_request())

    assert_problem(response, 401, "UNAUTHORIZED")


async def test_post_baseline_with_key(api_client: AsyncClient, database_url: str) -> None:
    """With the key the Phase I limits are frozen and published."""
    await seed_series(api_client)

    response = await api_client.post(BASELINE_URL, json=baseline_request(), headers=write_headers())

    assert response.status_code == 201, response.text
    body = response.json()
    UUID(body["id"])
    assert body["nPoints"] == BASELINE_POINTS
    assert body["phase"] == "phase_i"
    assert body["method"] == "imr"
    assert body["catalogVersion"] == CATALOG_VERSION
    assert body["ucl"] > body["centerLine"] > body["lcl"]
    assert await baseline_rows(database_url) == 1


async def test_post_baseline_is_an_upsert(api_client: AsyncClient, database_url: str) -> None:
    """Re-posting the same series recomputes it: a new id, still a single stored row."""
    await seed_series(api_client)

    first = await api_client.post(BASELINE_URL, json=baseline_request(), headers=write_headers())
    second = await api_client.post(BASELINE_URL, json=baseline_request(), headers=write_headers())

    assert first.status_code == 201 and second.status_code == 201, second.text
    assert first.json()["id"] != second.json()["id"]
    assert first.json()["centerLine"] == second.json()["centerLine"]
    assert await baseline_rows(database_url) == 1


async def test_get_baseline_after_persist(api_client: AsyncClient) -> None:
    """The persisted baseline is readable publicly and matches what the POST answered."""
    await seed_series(api_client)
    posted = await api_client.post(BASELINE_URL, json=baseline_request(), headers=write_headers())

    response = await api_client.get(
        BASELINE_URL,
        params={"siteId": str(SITE_ID), "parameterCode": PARAMETER},
    )

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["id"] == posted.json()["id"]
    assert body["centerLine"] == posted.json()["centerLine"]
    assert body["ucl"] == posted.json()["ucl"]


async def test_get_baseline_without_persisting_is_404(api_client: AsyncClient) -> None:
    """Limits computed on the fly are not a baseline: the contract says so with a 404."""
    await seed_series(api_client)

    response = await api_client.get(
        BASELINE_URL,
        params={"siteId": str(SITE_ID), "parameterCode": PARAMETER},
    )

    assert_problem(response, 404, "NOT_FOUND")


async def test_get_rules_public(api_client: AsyncClient) -> None:
    """The rules endpoint lists the signals of the same chart, publicly."""
    await seed_series(api_client)

    response = await api_client.get(
        RULES_URL,
        params={"siteId": str(SITE_ID), "parameterCode": PARAMETER},
    )

    assert response.status_code == 200, response.text
    violations = response.json()
    assert isinstance(violations, list)
    for violation in violations:
        assert violation["rule"] in RULE_CODES
        assert violation["description"]
    # The spike of the seeded series must be reported: a chart without signals would be wrong.
    assert any(violation["rule"] == "R1" for violation in violations)

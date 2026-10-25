"""Batch builders for the integration suite: the ingest endpoint is the only write path.

`POST /api/v1/ingest/observations` is the single door into the database (ADR-009), so the tests
that need sites or observations load them through it instead of running their own INSERT.
"""

from datetime import UTC, datetime
from typing import Any
from uuid import UUID, uuid4

from httpx import AsyncClient, Response

from tests.integration.db import TEST_INGEST_API_KEY

CATALOG_VERSION = "1.0.0"
INGEST_URL = "/api/v1/ingest/observations"
DEFAULT_PARAMETER = "PH"
DEFAULT_UNIT = "UPH"
DEFAULT_VALUE = 7.5


def ingest_headers(idempotency_key: str | None = None) -> dict[str, str]:
    """API key plus a fresh `Idempotency-Key`, unless the test wants to replay one."""
    return {"X-API-Key": TEST_INGEST_API_KEY, "Idempotency-Key": idempotency_key or uuid4().hex}


def utc_iso(value: datetime) -> str:
    """ISO-8601 UTC with `Z`: the contract rejects a timestamp without a zone."""
    return value.astimezone(UTC).isoformat().replace("+00:00", "Z")


def site_body(
    site_id: UUID,
    code: str,
    *,
    name: str,
    is_active: bool = True,
) -> dict[str, Any]:
    return {
        "id": str(site_id),
        "code": code,
        "name": name,
        "waterBodyType": "river",
        "latitude": -33.45,
        "longitude": -70.66,
        "isActive": is_active,
    }


def observation_body(
    site_id: UUID,
    analyzed_at: datetime,
    *,
    value: float = DEFAULT_VALUE,
    parameter_code: str = DEFAULT_PARAMETER,
    unit_code: str = DEFAULT_UNIT,
) -> dict[str, Any]:
    return {
        "id": str(uuid4()),
        "siteId": str(site_id),
        "parameterCode": parameter_code,
        "value": value,
        "unitCode": unit_code,
        "analyzedAt": utc_iso(analyzed_at),
        "source": "sensor",
    }


async def ingest_batch(
    client: AsyncClient,
    *,
    site: dict[str, Any],
    observations: list[dict[str, Any]],
    idempotency_key: str | None = None,
) -> Response:
    """Post one batch and fail loudly: a rejected batch makes the test meaningless."""
    response = await client.post(
        INGEST_URL,
        json={
            "catalogVersion": CATALOG_VERSION,
            "site": site,
            "samples": [],
            "observations": observations,
        },
        headers=ingest_headers(idempotency_key),
    )
    assert response.status_code == 200, response.text
    return response

"""Contract tests for `GET /api/v1/pipeline/status` (ADR-002, ADR-004).

The point of the endpoint is that the demo can show a pipeline screen with the S3 → Lambda path
undeployed: `awsDeployed = false` is a fact, not a failure. The batches come from the real
`ingest_idempotency` log, so replaying an idempotency key cannot invent a second row.
"""

from datetime import UTC, datetime, timedelta
from uuid import NAMESPACE_DNS, UUID, uuid5

import pytest
from httpx import AsyncClient

from tests.integration.seeding import ingest_batch, observation_body, site_body, utc_iso

pytestmark = pytest.mark.integration

STATUS_URL = "/api/v1/pipeline/status"
START = datetime(2026, 10, 1, 6, 0, tzinfo=UTC)


def site_id(index: int) -> UUID:
    return uuid5(NAMESPACE_DNS, f"PIPE-SITE-{index}")


def site_code(index: int) -> str:
    return f"PIPE-SITE-{index}"


async def ingest_site(client: AsyncClient, index: int, offsets_hours: list[int]) -> None:
    """One batch per site, with the readings that tell which one is the newest."""
    await ingest_batch(
        client,
        site=site_body(site_id(index), site_code(index), name=f"Sitio de prueba {index}"),
        observations=[
            observation_body(site_id(index), START + timedelta(hours=offset))
            for offset in offsets_hours
        ],
    )


async def test_status_without_data_is_not_an_error(api_client: AsyncClient) -> None:
    response = await api_client.get(STATUS_URL)

    payload = response.json()

    assert response.status_code == 200
    assert payload["awsDeployed"] is False
    assert payload["recentBatches"] == []
    assert payload["lastObservationPerSite"] == []
    assert payload["limit"] == 10


async def test_status_lists_batches_and_the_newest_reading_per_site(
    api_client: AsyncClient,
) -> None:
    await ingest_site(api_client, 1, [0, 2])
    await ingest_site(api_client, 2, [1])
    await ingest_site(api_client, 3, [3, 4])

    response = await api_client.get(STATUS_URL)

    payload = response.json()
    batches = payload["recentBatches"]
    readings = payload["lastObservationPerSite"]

    assert response.status_code == 200
    assert len(batches) == 3
    received = [batch["receivedAt"] for batch in batches]
    assert received == sorted(received, reverse=True)
    assert all(batch["status"] == "success" for batch in batches)
    assert sum(batch["accepted"] for batch in batches) == 5
    assert sum(batch["duplicates"] for batch in batches) == 0
    assert all(len(batch["key"]) == 32 for batch in batches)

    assert [reading["siteCode"] for reading in readings] == [
        "PIPE-SITE-1",
        "PIPE-SITE-2",
        "PIPE-SITE-3",
    ]
    newest = {reading["siteCode"]: reading["analyzedAt"] for reading in readings}
    assert newest["PIPE-SITE-1"] == utc_iso(START + timedelta(hours=2))
    assert newest["PIPE-SITE-2"] == utc_iso(START + timedelta(hours=1))
    assert newest["PIPE-SITE-3"] == utc_iso(START + timedelta(hours=4))
    assert all(reading["parameterCode"] == "PH" for reading in readings)
    assert all(reading["unitCode"] == "UPH" for reading in readings)


async def test_status_honours_the_limit(api_client: AsyncClient) -> None:
    await ingest_site(api_client, 1, [0])
    await ingest_site(api_client, 2, [1])
    await ingest_site(api_client, 3, [2])

    response = await api_client.get(STATUS_URL, params={"limit": 2})

    payload = response.json()

    assert response.status_code == 200
    assert len(payload["recentBatches"]) == 2
    assert payload["limit"] == 2
    # The cap only narrows the log; the per-site summary is not paginated.
    assert len(payload["lastObservationPerSite"]) == 3

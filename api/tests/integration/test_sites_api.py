"""Contract tests for `GET /api/v1/sites` (H3-E1c).

The endpoint exists so the Series and Control selectors stop guessing the site uuid: what these
tests fix is the envelope (`data` + `meta`), the stable ordering by `code` and the two filters
the screen uses (active flag and pagination).
"""

from datetime import UTC, datetime
from uuid import NAMESPACE_DNS, UUID, uuid5

import pytest
from httpx import AsyncClient

from tests.integration.seeding import ingest_batch, observation_body, site_body

pytestmark = pytest.mark.integration

SITES_URL = "/api/v1/sites"
CODES = ("ALPHA-RIVER", "BRAVO-RIVER", "CHARLIE-RIVER")
ANALYZED_AT = datetime(2026, 10, 1, 6, 0, tzinfo=UTC)


def site_id(code: str) -> UUID:
    """Deterministic uuid per code, the same convention the simulator uses."""
    return uuid5(NAMESPACE_DNS, code)


async def add_site(client: AsyncClient, code: str, *, is_active: bool = True) -> None:
    await ingest_batch(
        client,
        site=site_body(site_id(code), code, name=f"Sitio {code}", is_active=is_active),
        observations=[observation_body(site_id(code), analyzed_at=ANALYZED_AT)],
    )


async def test_sites_without_rows_is_an_empty_page(api_client: AsyncClient) -> None:
    response = await api_client.get(SITES_URL)

    payload = response.json()

    assert response.status_code == 200
    assert payload["data"] == []
    assert payload["meta"] == {"page": 1, "pageSize": 50, "total": 0}


async def test_sites_lists_three_sites_ordered_by_code(api_client: AsyncClient) -> None:
    for code in CODES:
        await add_site(api_client, code)

    response = await api_client.get(SITES_URL)

    payload = response.json()
    codes = [site["code"] for site in payload["data"]]

    assert response.status_code == 200
    assert codes == list(CODES)
    assert payload["meta"]["total"] == 3
    first = payload["data"][0]
    assert first["id"] == str(site_id("ALPHA-RIVER"))
    assert first["waterBodyType"] == "river"
    assert first["isActive"] is True
    assert first["latitude"] == pytest.approx(-33.45)


async def test_sites_filters_inactive(api_client: AsyncClient) -> None:
    await add_site(api_client, "ALPHA-RIVER")
    await add_site(api_client, "BRAVO-RIVER", is_active=False)

    response = await api_client.get(SITES_URL, params={"isActive": "false"})

    payload = response.json()

    assert response.status_code == 200
    assert [site["code"] for site in payload["data"]] == ["BRAVO-RIVER"]
    assert payload["data"][0]["isActive"] is False
    assert payload["meta"]["total"] == 1


async def test_sites_paginates_without_repeating_rows(api_client: AsyncClient) -> None:
    for code in CODES:
        await add_site(api_client, code)

    first = await api_client.get(SITES_URL, params={"page": 1, "pageSize": 2})
    second = await api_client.get(SITES_URL, params={"page": 2, "pageSize": 2})

    first_codes = [site["code"] for site in first.json()["data"]]
    second_payload = second.json()

    assert first_codes == ["ALPHA-RIVER", "BRAVO-RIVER"]
    assert [site["code"] for site in second_payload["data"]] == ["CHARLIE-RIVER"]
    assert second_payload["meta"] == {"page": 2, "pageSize": 2, "total": 3}

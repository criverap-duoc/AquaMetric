"""Contract tests for `GET /api/v1/observations` (slice F-1a).

The Series screen used to plot a replica of the demo data built in the browser. What these tests
fix is what replaces it: the paginated envelope, the three filters, the site code embedded in each
row (one request instead of two), the censored shape and the two client errors an empty page
would hide — an unknown site (404) and a parameter outside the catalog (400).

The aggregate endpoint gets one test of its own: it is the single query the screens use for «n»,
the mean and the range of a window.
"""

from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import NAMESPACE_DNS, UUID, uuid4, uuid5

import pytest
from httpx import AsyncClient

from tests.integration.seeding import ingest_batch, observation_body, site_body, utc_iso

pytestmark = pytest.mark.integration

OBSERVATIONS_URL = "/api/v1/observations"
AGGREGATE_URL = "/api/v1/observations/aggregate"
ALPHA = "ALPHA-RIVER"
BRAVO = "BRAVO-RIVER"
BASE_AT = datetime(2026, 10, 1, 6, 0, tzinfo=UTC)
STEP = timedelta(hours=6)
PH_UNIT = "UPH"
DO_UNIT = "MG_L"
LOQ = 0.05


def site_uuid(code: str) -> UUID:
    """Deterministic uuid per code, the same convention the simulator uses."""
    return uuid5(NAMESPACE_DNS, code)


def parse(value: str) -> datetime:
    """ISO-8601 with `Z` or `+00:00`, both accepted by the contract."""
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def censored_body(site_id: UUID, analyzed_at: datetime) -> dict[str, Any]:
    """A `< LOQ` result: no value, a qualifier and the detection limit (ADR-003)."""
    return {
        "id": str(uuid4()),
        "siteId": str(site_id),
        "parameterCode": "PH",
        "value": None,
        "unitCode": PH_UNIT,
        "qualifier": "<",
        "loq": LOQ,
        "analyzedAt": utc_iso(analyzed_at),
        "source": "lab",
    }


async def add_site(client: AsyncClient, code: str, observations: list[dict[str, Any]]) -> None:
    """Load one batch: the ingest endpoint is the only write path (ADR-009)."""
    await ingest_batch(
        client,
        site=site_body(site_uuid(code), code, name=f"Sitio {code}"),
        observations=observations,
    )


async def test_observations_without_rows_is_an_empty_page(api_client: AsyncClient) -> None:
    response = await api_client.get(OBSERVATIONS_URL)

    payload = response.json()

    assert response.status_code == 200
    assert payload["data"] == []
    assert payload["meta"] == {"page": 1, "pageSize": 100, "total": 0, "from": None, "to": None}


async def test_observations_returns_newest_first_with_site_code(api_client: AsyncClient) -> None:
    site_id = site_uuid(ALPHA)
    await add_site(
        api_client,
        ALPHA,
        [
            observation_body(site_id, analyzed_at=BASE_AT),
            censored_body(site_id, BASE_AT + STEP),
        ],
    )

    response = await api_client.get(OBSERVATIONS_URL)

    payload = response.json()
    newest, oldest = payload["data"]

    assert response.status_code == 200
    assert payload["meta"]["total"] == 2
    assert [row["siteCode"] for row in payload["data"]] == [ALPHA, ALPHA]
    # El resultado censurado viaja sin valor inventado: operador y LOQ.
    assert newest["value"] is None
    assert newest["qualifier"] == "<"
    assert newest["loq"] == pytest.approx(LOQ)
    assert parse(newest["analyzedAt"]) == BASE_AT + STEP
    assert oldest["value"] == pytest.approx(7.5)
    assert oldest["qualifier"] is None
    assert oldest["loq"] is None


async def test_observations_filter_by_site(api_client: AsyncClient) -> None:
    for code in (ALPHA, BRAVO):
        await add_site(api_client, code, [observation_body(site_uuid(code), analyzed_at=BASE_AT)])

    response = await api_client.get(OBSERVATIONS_URL, params={"siteId": str(site_uuid(BRAVO))})

    payload = response.json()

    assert response.status_code == 200
    assert payload["meta"]["total"] == 1
    assert [row["siteCode"] for row in payload["data"]] == [BRAVO]


async def test_observations_filter_by_parameter_keeps_the_original_unit(
    api_client: AsyncClient,
) -> None:
    site_id = site_uuid(ALPHA)
    await add_site(
        api_client,
        ALPHA,
        [
            observation_body(site_id, analyzed_at=BASE_AT),
            observation_body(
                site_id,
                analyzed_at=BASE_AT + STEP,
                parameter_code="DO",
                unit_code=DO_UNIT,
                value=8.1,
            ),
        ],
    )

    response = await api_client.get(OBSERVATIONS_URL, params={"parameterCode": "DO"})

    payload = response.json()

    assert response.status_code == 200
    assert payload["meta"]["total"] == 1
    assert payload["data"][0]["parameterCode"] == "DO"
    assert payload["data"][0]["unitCode"] == DO_UNIT


async def test_observations_filter_by_window(api_client: AsyncClient) -> None:
    site_id = site_uuid(ALPHA)
    await add_site(
        api_client,
        ALPHA,
        [observation_body(site_id, analyzed_at=BASE_AT + index * STEP) for index in range(3)],
    )
    window_start = BASE_AT + STEP

    response = await api_client.get(
        OBSERVATIONS_URL,
        params={"from": utc_iso(window_start), "to": utc_iso(window_start + STEP)},
    )

    payload = response.json()

    assert response.status_code == 200
    assert payload["meta"]["total"] == 2
    assert {parse(row["analyzedAt"]) for row in payload["data"]} == {
        window_start,
        window_start + STEP,
    }
    # El envelope devuelve la ventana aplicada, para que el pie del gráfico pueda citarla.
    assert parse(payload["meta"]["from"]) == window_start
    assert parse(payload["meta"]["to"]) == window_start + STEP


async def test_observations_paginate_without_repeating_rows(api_client: AsyncClient) -> None:
    site_id = site_uuid(ALPHA)
    await add_site(
        api_client,
        ALPHA,
        [observation_body(site_id, analyzed_at=BASE_AT + index * STEP) for index in range(5)],
    )

    first = await api_client.get(OBSERVATIONS_URL, params={"page": 1, "pageSize": 2})
    second = await api_client.get(OBSERVATIONS_URL, params={"page": 2, "pageSize": 2})

    first_payload = first.json()
    second_payload = second.json()
    first_ids = {row["id"] for row in first_payload["data"]}
    second_ids = {row["id"] for row in second_payload["data"]}

    assert len(first_ids) == len(second_ids) == 2
    assert first_ids.isdisjoint(second_ids)
    # Un `total` por página: la tabla no puede mostrar otro número que el del filtro.
    assert first_payload["meta"]["total"] == second_payload["meta"]["total"] == 5
    # Orden descendente: la página 2 empieza en la tercera observación más reciente.
    assert parse(second_payload["data"][0]["analyzedAt"]) == BASE_AT + 2 * STEP


async def test_observations_ascending_order_serves_the_control_chart(
    api_client: AsyncClient,
) -> None:
    site_id = site_uuid(ALPHA)
    await add_site(
        api_client,
        ALPHA,
        [observation_body(site_id, analyzed_at=BASE_AT + index * STEP) for index in range(3)],
    )

    response = await api_client.get(OBSERVATIONS_URL, params={"order": "asc"})

    payload = response.json()
    timestamps = [parse(row["analyzedAt"]) for row in payload["data"]]

    assert response.status_code == 200
    assert timestamps == sorted(timestamps)
    assert timestamps[0] == BASE_AT


async def test_observations_unknown_site_returns_not_found(api_client: AsyncClient) -> None:
    response = await api_client.get(OBSERVATIONS_URL, params={"siteId": str(uuid4())})

    payload = response.json()

    assert response.status_code == 404
    assert payload["code"] == "NOT_FOUND"


async def test_observations_unknown_parameter_returns_unknown_parameter(
    api_client: AsyncClient,
) -> None:
    response = await api_client.get(OBSERVATIONS_URL, params={"parameterCode": "NOPE"})

    payload = response.json()

    assert response.status_code == 400
    assert payload["code"] == "UNKNOWN_PARAMETER"


async def test_observations_aggregate_counts_and_statistics(api_client: AsyncClient) -> None:
    site_id = site_uuid(ALPHA)
    await add_site(
        api_client,
        ALPHA,
        [
            observation_body(site_id, analyzed_at=BASE_AT, value=7.5),
            observation_body(site_id, analyzed_at=BASE_AT + STEP, value=8.5),
            censored_body(site_id, BASE_AT + 2 * STEP),
        ],
    )

    response = await api_client.get(AGGREGATE_URL, params={"parameterCode": "PH"})

    payload = response.json()

    assert response.status_code == 200
    assert payload["count"] == 3
    assert payload["censoredCount"] == 1
    # Las censuradas cuentan, pero no entran en min/max/media (ADR-003).
    assert payload["minValue"] == pytest.approx(7.5)
    assert payload["maxValue"] == pytest.approx(8.5)
    assert payload["meanValue"] == pytest.approx(8.0)

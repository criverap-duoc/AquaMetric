"""Contract tests for `POST /api/v1/ingest/observations` (01 §5, ADR-009).

Docker required. The point of these tests is the real PostgreSQL transaction: the natural-key
conflict, the atomic rollback and the stored idempotency answer are not provable with a fake.
"""

from decimal import Decimal
from typing import Any
from uuid import UUID, uuid4

import pytest
from httpx import AsyncClient

from tests.integration.db import TEST_INGEST_API_KEY, fetchval

pytestmark = pytest.mark.integration

INGEST_URL = "/api/v1/ingest/observations"
# The synchronized catalog is v1.0.0; the local copy is what the app loads.
CATALOG_VERSION = "1.0.0"
COLLECTED_AT = "2026-10-01T11:30:00Z"
ANALYZED_AT = "2026-10-01T12:00:00Z"

SITE_ID = UUID("5c1f0b0a-0000-4000-8000-000000000001")
SAMPLE_ID = UUID("5c1f0b0a-0000-4000-8000-000000000002")
SITE_CODE = "SIM-TEST-INGEST"


def observation(**overrides: Any) -> dict[str, Any]:
    """A measured observation with real catalog codes (`PH` measured in `UPH`)."""
    payload: dict[str, Any] = {
        "id": str(uuid4()),
        "siteId": str(SITE_ID),
        "sampleId": str(SAMPLE_ID),
        "parameterCode": "PH",
        "value": 7.2,
        "unitCode": "UPH",
        "analyzedAt": ANALYZED_AT,
        "source": "lab",
    }
    payload.update(overrides)
    return payload


def batch(
    *observations: dict[str, Any],
    catalog_version: str = CATALOG_VERSION,
    site_id: UUID = SITE_ID,
    site_code: str = SITE_CODE,
) -> dict[str, Any]:
    """A valid one-site batch; with no arguments it carries a single `PH` observation."""
    return {
        "catalogVersion": catalog_version,
        "site": {
            "id": str(site_id),
            "code": site_code,
            "name": "Sitio de prueba de ingesta",
            "waterBodyType": "river",
            "latitude": -33.45,
            "longitude": -70.66,
        },
        "samples": [
            {
                "id": str(SAMPLE_ID),
                "siteId": str(site_id),
                "campaignId": None,
                "matrix": "water",
                "collectedAt": COLLECTED_AT,
                "labReceivedAt": None,
                "status": "analyzed",
            }
        ],
        "observations": list(observations) or [observation(siteId=str(site_id))],
    }


def headers(key: str = "ingest-key-1") -> dict[str, str]:
    """The two mandatory headers of the ingest contract."""
    return {"X-API-Key": TEST_INGEST_API_KEY, "Idempotency-Key": key}


def assert_problem(response: Any, status_code: int, code: str) -> dict[str, Any]:
    """Assert the RFC 9457 shape TerraPlan and the UI already parse."""
    assert response.status_code == status_code, response.text
    assert response.headers["content-type"] == "application/problem+json"
    body: dict[str, Any] = response.json()
    assert body["code"] == code
    assert body["status"] == status_code
    assert body["type"] == "about:blank"
    assert body["detail"]
    return body


COUNT_SQL = {
    table: f"SELECT count(*) FROM aquametric.{table}"  # noqa: S608 - identifiers, not user input
    for table in ("site", "sample", "observation", "ingest_idempotency")
}


async def count(database_url: str, table: str) -> int:
    """Rows in one application table, read straight from PostgreSQL."""
    return int(await fetchval(database_url, COUNT_SQL[table]))


async def test_ingest_stores_the_batch(api_client: AsyncClient, database_url: str) -> None:
    """A valid batch answers `{accepted, duplicates}` and writes site, sample and rows."""
    payload = batch(
        observation(parameterCode="PH"),
        observation(parameterCode="TURB", unitCode="NTU"),
    )

    response = await api_client.post(INGEST_URL, json=payload, headers=headers())

    assert response.status_code == 200, response.text
    assert response.json() == {"accepted": 2, "duplicates": 0}
    assert await count(database_url, "site") == 1
    assert await count(database_url, "sample") == 1
    assert await count(database_url, "observation") == 2
    assert await count(database_url, "ingest_idempotency") == 1
    latitude = await fetchval(database_url, "SELECT latitude FROM aquametric.site")
    assert latitude == Decimal("-33.450000")


async def test_idempotency_replays_the_stored_answer(
    api_client: AsyncClient, database_url: str
) -> None:
    """The same key with the same body is answered from storage and reprocessed nowhere."""
    payload = batch()

    first = await api_client.post(INGEST_URL, json=payload, headers=headers("k-replay"))
    second = await api_client.post(INGEST_URL, json=payload, headers=headers("k-replay"))

    assert first.status_code == 200, first.text
    assert second.status_code == 200, second.text
    assert second.json() == first.json() == {"accepted": 1, "duplicates": 0}
    assert await count(database_url, "observation") == 1
    assert await count(database_url, "ingest_idempotency") == 1


async def test_idempotency_key_reuse_with_another_body_conflicts(
    api_client: AsyncClient, database_url: str
) -> None:
    """Reusing a key for different data is a client bug, not a retry."""
    await api_client.post(INGEST_URL, json=batch(), headers=headers("k-reuse"))

    response = await api_client.post(
        INGEST_URL,
        json=batch(observation(parameterCode="TURB", unitCode="NTU")),
        headers=headers("k-reuse"),
    )

    assert_problem(response, 409, "IDEMPOTENCY_KEY_REUSE")
    assert await count(database_url, "observation") == 1


async def test_new_key_over_the_same_rows_counts_duplicates(
    api_client: AsyncClient, database_url: str
) -> None:
    """The natural key turns a resend into `duplicates`, so TerraPlan can retry safely."""
    payload = batch(
        observation(parameterCode="PH"), observation(parameterCode="TURB", unitCode="NTU")
    )
    await api_client.post(INGEST_URL, json=payload, headers=headers("k-first"))

    response = await api_client.post(INGEST_URL, json=payload, headers=headers("k-second"))

    assert response.status_code == 200, response.text
    assert response.json() == {"accepted": 0, "duplicates": 2}
    assert await count(database_url, "observation") == 2


async def test_catalog_major_mismatch_is_rejected(
    api_client: AsyncClient, database_url: str
) -> None:
    """A different major may rename or drop codes, so it is refused instead of guessed."""
    response = await api_client.post(
        INGEST_URL, json=batch(catalog_version="2.0.0"), headers=headers()
    )

    assert_problem(response, 409, "CATALOG_VERSION_MISMATCH")
    assert await count(database_url, "site") == 0
    assert await count(database_url, "observation") == 0


async def test_catalog_minor_difference_is_accepted(
    api_client: AsyncClient, database_url: str
) -> None:
    """Only the major matters: a newer minor still speaks the same codes."""
    response = await api_client.post(
        INGEST_URL, json=batch(catalog_version="1.7.3"), headers=headers()
    )

    assert response.status_code == 200, response.text
    assert response.json() == {"accepted": 1, "duplicates": 0}


async def test_unknown_parameter_rejects_the_whole_batch(
    api_client: AsyncClient, database_url: str
) -> None:
    """Atomicity: one unknown code and nothing is stored, not even the valid rows beside it."""
    payload = batch(observation(parameterCode="PH"), observation(parameterCode="XX_DESCONOCIDO"))

    response = await api_client.post(INGEST_URL, json=payload, headers=headers())

    body = assert_problem(response, 400, "UNKNOWN_PARAMETER")
    assert "XX_DESCONOCIDO" in body["detail"]
    assert await count(database_url, "site") == 0
    assert await count(database_url, "sample") == 0
    assert await count(database_url, "observation") == 0
    assert await count(database_url, "ingest_idempotency") == 0


async def test_unit_from_another_dimension_is_rejected(
    api_client: AsyncClient, database_url: str
) -> None:
    """`PH` is measured in `UPH`; `DEG_C` measures temperature."""
    payload = batch(observation(parameterCode="PH", unitCode="DEG_C"))

    response = await api_client.post(INGEST_URL, json=payload, headers=headers())

    assert_problem(response, 400, "UNIT_MISMATCH")
    assert await count(database_url, "observation") == 0


async def test_unknown_unit_is_rejected(api_client: AsyncClient, database_url: str) -> None:
    """Units come from the catalog; free text is never accepted."""
    response = await api_client.post(
        INGEST_URL, json=batch(observation(unitCode="BANANA")), headers=headers()
    )

    assert_problem(response, 400, "UNIT_MISMATCH")
    assert await count(database_url, "observation") == 0


async def test_unit_in_the_same_dimension_is_accepted(
    api_client: AsyncClient, database_url: str
) -> None:
    """`DO` may arrive as `MG_L` or `MG_N_L`: same dimension, so nothing is converted."""
    response = await api_client.post(
        INGEST_URL,
        json=batch(observation(parameterCode="DO", unitCode="MG_N_L", value=8.1)),
        headers=headers(),
    )

    assert response.status_code == 200, response.text
    assert await count(database_url, "observation") == 1


async def test_unknown_sample_reference_rejects_the_batch(
    api_client: AsyncClient, database_url: str
) -> None:
    """An observation may cite a batch sample or a stored one; anything else is a 400."""
    response = await api_client.post(
        INGEST_URL,
        json=batch(observation(sampleId=str(uuid4()))),
        headers=headers(),
    )

    assert_problem(response, 400, "VALIDATION_ERROR")
    assert await count(database_url, "observation") == 0


async def test_stored_sample_can_be_referenced(api_client: AsyncClient, database_url: str) -> None:
    """TerraPlan may send observations for a sample published in an earlier batch."""
    await api_client.post(INGEST_URL, json=batch(), headers=headers("k-sample"))
    later = batch(observation(parameterCode="TURB", unitCode="NTU"))
    later["samples"] = []

    response = await api_client.post(INGEST_URL, json=later, headers=headers("k-sample-2"))

    assert response.status_code == 200, response.text
    assert response.json() == {"accepted": 1, "duplicates": 0}


async def test_censored_observation_is_stored_without_a_value(
    api_client: AsyncClient, database_url: str
) -> None:
    """`< LOQ` rows keep the LOQ and the qualifier, never a value (ADR-003)."""
    payload = batch(
        observation(parameterCode="TURB", unitCode="NTU", value=None, qualifier="<", loq=0.5)
    )

    response = await api_client.post(INGEST_URL, json=payload, headers=headers())

    assert response.status_code == 200, response.text
    stored = "SELECT {column} FROM aquametric.observation WHERE parameter_code = 'TURB'"
    assert await fetchval(database_url, stored.format(column="value")) is None
    assert await fetchval(database_url, stored.format(column="qualifier")) == "<"
    assert await fetchval(database_url, stored.format(column="loq")) == Decimal("0.500000")


async def test_mixed_batch_stores_censored_and_valued_rows(
    api_client: AsyncClient, database_url: str
) -> None:
    """One batch, one INSERT: rows with and without `loq` must not split the statement."""
    payload = batch(
        observation(parameterCode="PH", value=7.4),
        observation(parameterCode="TURB", unitCode="NTU", value=None, qualifier="<", loq=0.5),
    )

    response = await api_client.post(INGEST_URL, json=payload, headers=headers("k-mixed"))

    assert response.status_code == 200, response.text
    assert response.json() == {"accepted": 2, "duplicates": 0}
    assert await count(database_url, "observation") == 2


async def test_value_with_a_qualifier_is_rejected(
    api_client: AsyncClient, database_url: str
) -> None:
    """A qualifier without a null value is incoherent, so the schema refuses the batch."""
    response = await api_client.post(
        INGEST_URL, json=batch(observation(qualifier="<", loq=0.5)), headers=headers()
    )

    assert_problem(response, 400, "VALIDATION_ERROR")
    assert await count(database_url, "observation") == 0


async def test_site_code_owned_by_another_id_conflicts(
    api_client: AsyncClient, database_url: str
) -> None:
    """Two ids cannot share a `code`: the second batch is refused and changes nothing."""
    await api_client.post(INGEST_URL, json=batch(), headers=headers("k-site"))

    response = await api_client.post(
        INGEST_URL,
        json=batch(site_id=uuid4(), site_code=SITE_CODE),
        headers=headers("k-site-2"),
    )

    assert_problem(response, 409, "CONFLICT")
    assert await count(database_url, "site") == 1
    assert await count(database_url, "observation") == 1


async def test_missing_api_key_is_rejected(api_client: AsyncClient, database_url: str) -> None:
    """Writing without `X-API-Key` is a 401, whatever the payload says (ADR-011)."""
    response = await api_client.post(
        INGEST_URL, json=batch(), headers={"Idempotency-Key": "k-no-auth"}
    )

    assert_problem(response, 401, "UNAUTHORIZED")
    assert await count(database_url, "observation") == 0


async def test_wrong_api_key_is_rejected(api_client: AsyncClient, database_url: str) -> None:
    """A wrong key is never echoed back in the problem document."""
    response = await api_client.post(
        INGEST_URL,
        json=batch(),
        headers={"X-API-Key": "definitely-not-the-key", "Idempotency-Key": "k-bad-auth"},
    )

    body = assert_problem(response, 401, "UNAUTHORIZED")
    assert "definitely-not-the-key" not in str(body)
    assert await count(database_url, "observation") == 0


async def test_missing_idempotency_key_is_rejected(
    api_client: AsyncClient, database_url: str
) -> None:
    """`Idempotency-Key` is mandatory: without it a retry could duplicate data silently."""
    response = await api_client.post(
        INGEST_URL, json=batch(), headers={"X-API-Key": TEST_INGEST_API_KEY}
    )

    assert_problem(response, 400, "VALIDATION_ERROR")
    assert await count(database_url, "observation") == 0


async def test_batch_over_the_observation_cap_is_rejected(
    api_client: AsyncClient, database_url: str
) -> None:
    """The 5000-observation cap is part of the contract, not a runtime surprise."""
    payload = batch(*[observation() for _ in range(5001)])

    response = await api_client.post(INGEST_URL, json=payload, headers=headers())

    assert_problem(response, 400, "VALIDATION_ERROR")
    assert await count(database_url, "observation") == 0

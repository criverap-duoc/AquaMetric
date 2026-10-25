"""Contract tests for the public screening and catalog endpoints (01 §5, ADR-012).

They drive the real app — routers, dependencies and problem+json handlers — against the
synchronized catalog. Every limit in it is `draft-verified`, so the expected answer is
`not_evaluable` **with a reason**: seeing a comparison here would mean the policy is broken.
"""

import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.integration

SCREENING_URL = "/api/v1/screening/evaluate"
LIMITS_URL = "/api/v1/screening/limits"
ANALYZED_AT = "2026-10-01T12:00:00Z"


def screening_body(**overrides: object) -> dict[str, object]:
    """A PH screening in `vida_acuatica`, the only parameter with a NCh 1.333 absolute limit."""
    body: dict[str, object] = {
        "parameterCode": "PH",
        "value": 7.4,
        "unitCode": "UPH",
        "analyzedAt": ANALYZED_AT,
        "regulation": "NCh1333",
        "context": "vida_acuatica",
    }
    body.update(overrides)
    return body


async def test_screen_draft_limit_is_not_evaluable(api_client: AsyncClient) -> None:
    response = await api_client.post(SCREENING_URL, json=screening_body(value=9.5))

    assert response.status_code == 200
    body = response.json()
    assert body["flag"] == "not_evaluable"
    assert "pendiente de validación" in body["reason"]
    assert body["limitApplied"]["status"] == "draft-verified"
    assert body["exceedanceRatio"] is None
    # Two always-present disclaimers plus the NCh 1.333 sentence.
    assert len(body["warnings"]) == 3
    assert "no dictamen de cumplimiento" in body["warnings"][0]


async def test_screen_without_context_reports_no_applicable_limit(api_client: AsyncClient) -> None:
    body = screening_body()
    del body["context"]

    response = await api_client.post(SCREENING_URL, json=body)

    assert response.status_code == 200
    payload = response.json()
    assert payload["flag"] == "not_evaluable"
    assert "No hay límite aplicable" in payload["reason"]
    assert payload["limitApplied"] is None


async def test_screen_ds53_without_area_reports_no_applicable_limit(
    api_client: AsyncClient,
) -> None:
    response = await api_client.post(
        SCREENING_URL, json=screening_body(regulation="DS53-2014-MMA", context=None)
    )

    payload = response.json()

    assert response.status_code == 200
    assert payload["flag"] == "not_evaluable"
    assert payload["limitApplied"] is None
    assert any("serie trienal" in warning for warning in payload["warnings"])


async def test_screen_unknown_parameter_returns_problem_json(api_client: AsyncClient) -> None:
    response = await api_client.post(SCREENING_URL, json=screening_body(parameterCode="XYZ"))

    assert response.status_code == 400
    assert response.headers["content-type"] == "application/problem+json"
    assert response.json()["code"] == "UNKNOWN_PARAMETER"


async def test_screen_unit_mismatch_returns_problem_json(api_client: AsyncClient) -> None:
    response = await api_client.post(SCREENING_URL, json=screening_body(unitCode="MG_L"))

    assert response.status_code == 400
    assert response.json()["code"] == "UNIT_MISMATCH"
    assert "UPH" in response.json()["detail"]


async def test_screening_limits_lists_both_uses_of_water(api_client: AsyncClient) -> None:
    response = await api_client.get(
        LIMITS_URL, params={"parameterCode": "PH", "regulation": "NCh1333"}
    )

    payload = response.json()

    assert response.status_code == 200
    assert payload["requiresValidated"] is True
    assert {limit["context"] for limit in payload["limits"]} == {"vida_acuatica", "riego"}
    assert all(limit["status"] == "draft-verified" for limit in payload["limits"])


async def test_catalog_meta_exposes_the_signature_state(api_client: AsyncClient) -> None:
    response = await api_client.get("/api/v1/catalog/meta")

    payload = response.json()

    assert response.status_code == 200
    assert payload["version"] == "1.0.0"
    assert len(payload["sha256"]) == 64
    assert payload["status"] == "draft-verified"
    assert payload["validatedBy"] is None
    assert payload["validatedAt"] is None


async def test_catalog_parameters_keep_the_canonical_unit(api_client: AsyncClient) -> None:
    response = await api_client.get("/api/v1/catalog/parameters")

    parameters = {item["code"]: item for item in response.json()}

    assert response.status_code == 200
    assert len(parameters) == 9
    assert parameters["PH"]["canonicalUnitCode"] == "UPH"
    assert parameters["PH"]["decimals"] == 2


async def test_catalog_limits_filter_by_parameter_and_regulation(api_client: AsyncClient) -> None:
    response = await api_client.get(
        "/api/v1/catalog/limits", params={"parameterCode": "PH", "regulation": "DS53-2014-MMA"}
    )

    limits = response.json()

    assert response.status_code == 200
    assert limits
    assert all(limit["parameterCode"] == "PH" for limit in limits)
    assert all(limit["statistic"] == "P5_P95" for limit in limits)
    assert all(limit["monitoringAreaCode"] for limit in limits)

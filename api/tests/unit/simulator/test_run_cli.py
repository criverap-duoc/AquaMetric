"""The CLI is the only I/O of the simulator: it must speak the ingest contract verbatim.

`httpx.post` is replaced, so these tests never need a running API: what is asserted is the shape
of the request (URL, headers, body) and the determinism of the idempotency key, not FastAPI.
"""

from pathlib import Path
from typing import Any

import httpx
import pytest

from app.simulator import run

# api/tests/unit/simulator/test_run_cli.py -> repository root.
CATALOG_DIR = Path(__file__).resolve().parents[4] / "catalog"
API_KEY = "test_key_at_least_16_chars"
START = "2026-10-01T00:00:00Z"
BASE_ARGS = [
    "--site",
    "SIM-TEST-01",
    "--parameter",
    "PH",
    "--seed",
    "42",
    "--days",
    "1",
    "--start",
    START,
    "--api-url",
    "http://test",
    "--api-key",
    API_KEY,
    "--catalog-dir",
    str(CATALOG_DIR),
]


class FakeResponse:
    """Stand-in for `httpx.Response`: the CLI only reads the status code and the body."""

    def __init__(self, status_code: int = 200, body: dict[str, int] | None = None) -> None:
        self.status_code = status_code
        self.text = ""
        self._body = body if body is not None else {"accepted": 23, "duplicates": 0}

    def json(self) -> dict[str, int]:
        return self._body


def install_post(monkeypatch: pytest.MonkeyPatch) -> list[dict[str, Any]]:
    """Capture the single POST the CLI sends instead of reaching a real API."""
    calls: list[dict[str, Any]] = []

    def fake_post(url: str, **kwargs: Any) -> FakeResponse:
        calls.append({"url": url, **kwargs})
        return FakeResponse()

    monkeypatch.setattr(httpx, "post", fake_post)
    return calls


def test_cli_posts_the_batch_with_the_ingest_contract(monkeypatch: pytest.MonkeyPatch) -> None:
    """One POST, both headers, the catalog version and the catalog unit: no guessing anywhere."""
    calls = install_post(monkeypatch)

    exit_code = run.main(BASE_ARGS)

    assert exit_code == 0
    assert len(calls) == 1
    call = calls[0]
    assert call["url"] == "http://test/api/v1/ingest/observations"
    assert call["headers"]["X-API-Key"] == API_KEY
    assert len(call["headers"]["Idempotency-Key"]) == 64
    body = call["json"]
    assert body["catalogVersion"] == "1.0.0"
    assert body["site"]["code"] == "SIM-TEST-01"
    assert {observation["parameterCode"] for observation in body["observations"]} == {"PH"}
    assert {observation["unitCode"] for observation in body["observations"]} == {"UPH"}
    # 24 horas de lecturas, una perdida por el dropout que el CLI inyecta por defecto.
    assert len(body["observations"]) == 23


def test_cli_idempotency_key_is_deterministic(monkeypatch: pytest.MonkeyPatch) -> None:
    """Running the same command twice replays the same key and the same payload (ADR-009)."""
    calls = install_post(monkeypatch)

    assert run.main(BASE_ARGS) == 0
    assert run.main(BASE_ARGS) == 0

    assert len(calls) == 2
    assert calls[0]["headers"]["Idempotency-Key"] == calls[1]["headers"]["Idempotency-Key"]
    assert calls[0]["json"] == calls[1]["json"]


def test_cli_rejects_a_site_without_the_sim_prefix(monkeypatch: pytest.MonkeyPatch) -> None:
    """A real TerraPlan code must never reach the simulator: it fails before any HTTP."""
    calls = install_post(monkeypatch)
    args = [*BASE_ARGS]
    args[args.index("SIM-TEST-01")] = "RIO-MAIPO-01"

    assert run.main(args) == 1
    assert calls == []

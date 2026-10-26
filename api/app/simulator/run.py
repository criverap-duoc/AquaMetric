"""CLI entry point: generate a scenario and push it through the ingest API.

This module is the only place in `app/simulator/` with I/O (02 §7): it reads the synchronized
catalog from disk and posts the batch over HTTP. It never touches PostgreSQL or SQLAlchemy, so
the simulator is just another client of `POST /api/v1/ingest/observations` and every write still
goes through validation, normalisation and idempotency (ADR-009).

Usage:
    uv run python -m app.simulator.run --site SIM-RIO-MAIPO-01 --parameter PH --seed 42
"""

import argparse
import hashlib
import json
import os
import sys
from collections.abc import Sequence
from dataclasses import replace
from datetime import UTC, datetime
from pathlib import Path
from typing import Final

import httpx

from app.catalog import Catalog
from app.catalog.loader import load_catalog
from app.catalog.validation import CatalogLoadError
from app.core.config import REPO_ROOT
from app.schemas.ingest import MAX_OBSERVATIONS_PER_BATCH, IngestResponse
from app.simulator.generator import generate_batch, to_utc
from app.simulator.scenario import Event, EventType, ScenarioConfig

# Sites from the simulator must stay apart from TerraPlan's real campaigns (01 §5).
SITE_PREFIX: Final = "SIM-"
INGEST_PATH: Final = "/api/v1/ingest/observations"
DEFAULT_API_URL: Final = "http://localhost:8000"
DEFAULT_EVENTS: Final = "shift,spike,drift,dropout,censored"
DEFAULT_INTERVAL_MINUTES: Final = 60
MAX_DAYS: Final = 365
MIN_API_KEY_LENGTH: Final = 16
REQUEST_TIMEOUT_SECONDS: Final = 60.0

# A healthy baseline per catalog parameter, used only to make demo data believable:
# (mean, standard deviation) in the parameter's canonical unit.
PARAMETER_BASELINES: Final[dict[str, tuple[float, float]]] = {
    "PH": (7.5, 0.3),
    "TEMP": (15.0, 2.0),
    "DO": (8.0, 1.5),
    "COND": (500.0, 100.0),
    "TURB": (5.0, 2.0),
    "N_NO3": (0.5, 0.2),
    "N_NO2": (0.05, 0.02),
    "P_PO4": (0.05, 0.02),
    "CL": (20.0, 5.0),
}


class CliError(Exception):
    """A problem the user can fix: missing configuration, bad arguments or a failed ingest."""


def build_parser() -> argparse.ArgumentParser:
    """Declare the flags once, so `--help` and the README cannot drift apart."""
    parser = argparse.ArgumentParser(
        prog="python -m app.simulator.run",
        description=(
            "Genera una serie determinista y la envía a POST /api/v1/ingest/observations. "
            "La API debe estar corriendo en --api-url."
        ),
    )
    parser.add_argument("--site", required=True, help="Sitio simulado; debe empezar con 'SIM-'.")
    parser.add_argument(
        "--parameter", required=True, help="Código del parámetro del catálogo, por ejemplo PH."
    )
    parser.add_argument(
        "--days",
        type=int,
        default=30,
        help=f"Días simulados, 1 a {MAX_DAYS} (por defecto 30).",
    )
    parser.add_argument(
        "--seed", type=int, required=True, help="Semilla; la misma semilla genera los mismos datos."
    )
    parser.add_argument(
        "--events",
        default=DEFAULT_EVENTS,
        help=f"Anomalías separadas por coma (por defecto {DEFAULT_EVENTS}).",
    )
    parser.add_argument("--api-url", default=DEFAULT_API_URL, help="URL base de la API.")
    parser.add_argument(
        "--api-key",
        default=None,
        help="API key de escritura; por defecto se lee de INGEST_API_KEY.",
    )
    parser.add_argument(
        "--start",
        default=None,
        help="Inicio ISO-8601 UTC de la serie (por defecto, ahora). Fijarlo hace la demo idéntica.",
    )
    parser.add_argument(
        "--catalog-dir",
        default=None,
        help="Carpeta del catálogo; por defecto CATALOG_DIR o catalog/ del repositorio.",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Run the CLI and return the process exit code: 0 on a 200, 1 on any other outcome."""
    args = build_parser().parse_args(argv)
    try:
        summary = _run(args)
    except CliError as exc:
        sys.stderr.write(f"Error: {exc}\n")
        return 1
    sys.stdout.write(f"{summary}\n")
    return 0


def _run(args: argparse.Namespace) -> str:
    """Validate the flags, build the batch and post it; returns the success line to print."""
    site_code = str(args.site)
    if not site_code.startswith(SITE_PREFIX):
        raise CliError(
            f"El sitio debe empezar con '{SITE_PREFIX}' para no chocar con los sitios reales de "
            f"TerraPlan (recibido '{site_code}')."
        )
    days = int(args.days)
    if not 1 <= days <= MAX_DAYS:
        raise CliError(f"--days debe estar entre 1 y {MAX_DAYS} (recibido {days}).")
    parameter_code = str(args.parameter)
    api_key = _api_key(args.api_key)
    start_at = _parse_start(args.start)
    event_types = _parse_events(str(args.events))

    catalog = _load_catalog(args.catalog_dir)
    parameter = catalog.parameters.get(parameter_code)
    if parameter is None:
        known = ", ".join(sorted(catalog.parameters))
        raise CliError(f"El parámetro '{parameter_code}' no existe. Disponibles: {known}.")
    baseline = PARAMETER_BASELINES.get(parameter.code)
    if baseline is None:
        raise CliError(
            f"No hay línea base de demo para '{parameter.code}'; agrégala en PARAMETER_BASELINES."
        )

    try:
        base_config = ScenarioConfig(
            site_code=site_code,
            parameter_code=parameter.code,
            days=days,
            seed=int(args.seed),
            base_mean=baseline[0],
            base_std=baseline[1],
        )
        config = replace(base_config, events=_build_events(event_types, config=base_config))
        batch = generate_batch(config, start_at, catalog)
    except ValueError as exc:
        raise CliError(str(exc)) from exc

    if len(batch.observations) > MAX_OBSERVATIONS_PER_BATCH:
        raise CliError(
            f"El lote tiene {len(batch.observations)} observaciones y el máximo por lote es "
            f"{MAX_OBSERVATIONS_PER_BATCH}: reduce --days."
        )

    url = f"{str(args.api_url).rstrip('/')}{INGEST_PATH}"
    try:
        response = httpx.post(
            url,
            json=batch.model_dump(mode="json", by_alias=True),
            headers={"X-API-Key": api_key, "Idempotency-Key": idempotency_key(config, start_at)},
            timeout=REQUEST_TIMEOUT_SECONDS,
        )
    except httpx.HTTPError as exc:
        raise CliError(
            f"No se pudo contactar la API en {url} ({exc}). ¿Está corriendo uvicorn?"
        ) from exc
    if response.status_code != 200:
        raise CliError(
            f"La ingesta falló con HTTP {response.status_code}: {_problem_detail(response)}"
        )

    ingested = IngestResponse.model_validate(response.json())
    return (
        f"Sitio {config.site_code} · {config.parameter_code} · {len(batch.observations)} lecturas "
        f"· aceptadas {ingested.accepted} · duplicadas {ingested.duplicates} · HTTP 200"
    )


def _api_key(value: str | None) -> str:
    """The write key, from the flag or from the environment; it is never stored anywhere."""
    key = value or os.environ.get("INGEST_API_KEY")
    if not key:
        raise CliError("Falta la API key: pasa --api-key o define INGEST_API_KEY.")
    if len(key) < MIN_API_KEY_LENGTH:
        raise CliError(f"La API key debe tener al menos {MIN_API_KEY_LENGTH} caracteres.")
    return key


def _parse_start(value: str | None) -> datetime:
    """The UTC instant of the first observation; `None` means «now» and only the CLI says so."""
    if value is None:
        return datetime.now(UTC)
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise CliError(f"--start no es ISO-8601 ('{value}').") from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise CliError(f"--start debe incluir zona horaria UTC ('{value}').")
    return parsed.astimezone(UTC)


def _parse_events(value: str) -> tuple[EventType, ...]:
    """Turn `shift,spike` into event types, rejecting any name the generator does not know."""
    parsed: list[EventType] = []
    for name in value.split(","):
        name = name.strip()
        if not name:
            continue
        try:
            parsed.append(EventType(name))
        except ValueError as exc:
            valid = ", ".join(item.value for item in EventType)
            raise CliError(f"Anomalía desconocida '{name}'. Válidas: {valid}.") from exc
    return tuple(parsed)


def _load_catalog(value: str | None) -> Catalog:
    """Read the synchronized catalog from `--catalog-dir`, CATALOG_DIR or the repository copy."""
    directory = (
        Path(value) if value else Path(os.environ.get("CATALOG_DIR") or REPO_ROOT / "catalog")
    )
    try:
        return load_catalog(directory)
    except CatalogLoadError as exc:
        raise CliError(f"No se pudo cargar el catálogo: {exc}") from exc


def _build_events(types: Sequence[EventType], *, config: ScenarioConfig) -> tuple[Event, ...]:
    """Place the requested anomalies where the demo can actually show them.

    Positions are fractions of the series and magnitudes multiples of `base_std`, so the same
    layout works for pH (±0,3 UPH) and for conductivity (±100 µS/cm).

    Every anchor stays inside the window the control chart draws *and* scans: `GET
    /spc/control-charts` covers a Phase I baseline (40 points by default) plus 100 monitored
    points, i.e. the first ~140 readings, so an anomaly planted at 40 % of a 30-day hourly series
    (index ~288) would never reach the chart. The anchors also stay after index 50, so a longer
    Phase I (the chart accepts 20, 30, 40 or 50 baseline points) still never sees an anomaly. Each
    anomaly gets its own slot, which keeps a parameter's `shift`+`spike` readable as two separate
    events.

    Magnitudes are sized for a Phase I of 40 points, whose sigma is still an estimate: a 2,5-sigma
    shift leaves about half its points under the limit and reads as scattered noise, whereas
    3,5 sigma produces the contiguous run a shift is supposed to look like. The censored block
    reports half a standard deviation as its LOQ — a plausible detection limit, and low enough
    that `LOQ/2` stays inside the control limits instead of faking an out-of-limit reading.
    """
    points = config.points
    events: list[Event] = []
    for event_type in types:
        if event_type is EventType.shift:
            events.append(
                Event(
                    at_index=int(points * 0.120),
                    type=event_type,
                    magnitude=3.5 * config.base_std,
                    duration=max(1, int(points * 0.042)),
                )
            )
        elif event_type is EventType.spike:
            events.append(
                Event(
                    at_index=int(points * 0.105),
                    type=event_type,
                    magnitude=6.0 * config.base_std,
                )
            )
        elif event_type is EventType.drift:
            events.append(
                Event(
                    at_index=int(points * 0.080),
                    type=event_type,
                    magnitude=3.5 * config.base_std,
                    duration=max(1, int(points * 0.036)),
                )
            )
        elif event_type is EventType.dropout:
            events.append(
                Event(
                    at_index=int(points * 0.155),
                    type=event_type,
                    magnitude=0.0,
                    duration=max(1, int(points * 0.008)),
                )
            )
        else:  # EventType.censored
            events.append(
                Event(
                    at_index=int(points * 0.070),
                    type=event_type,
                    magnitude=0.5 * config.base_std,
                    duration=max(1, int(points * 0.006)),
                )
            )
    return tuple(events)


def idempotency_key(config: ScenarioConfig, start_at: datetime) -> str:
    """sha256 of the canonical scenario, so replaying a command replays the batch (ADR-009).

    `start_at` is part of the material because it moves every timestamp: the same seed over a new
    window is a different payload, and reusing the key for it would be a legitimate
    `IDEMPOTENCY_KEY_REUSE`.
    """
    material = {
        "site": config.site_code,
        "parameter": config.parameter_code,
        "seed": config.seed,
        "days": config.days,
        "intervalMinutes": config.interval_minutes,
        "source": config.source,
        "startAt": to_utc(start_at).isoformat(),
        "events": [
            {
                "atIndex": event.at_index,
                "type": event.type.value,
                "magnitude": event.magnitude,
                "duration": event.duration,
            }
            for event in config.events
        ],
    }
    canonical = json.dumps(material, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _problem_detail(response: httpx.Response) -> str:
    """The `detail` of an RFC 9457 problem, or whatever the server sent instead."""
    try:
        body = response.json()
    except ValueError:
        return response.text[:200] or "sin detalle"
    detail = body.get("detail") if isinstance(body, dict) else None
    return str(detail) if detail else response.text[:200]


if __name__ == "__main__":  # `python -m app.simulator.run`
    sys.exit(main())

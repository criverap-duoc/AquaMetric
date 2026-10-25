#!/usr/bin/env bash
# seed_demo.sh — Carga los datos demo del portafolio con el simulador determinista (C-1, 03 §7).
#
# Qué hace:
#   * Genera 4 sitios simulados × 5 parámetros × 30 días (720 lecturas horarias por serie).
#   * Reparte las anomalías para que el dashboard y las cartas SPC tengan algo que mostrar:
#     un salto de nivel, un pico, una deriva lenta, un corte de señal y valores censurados.
#   * Inserta todo por `POST /api/v1/ingest/observations` (X-API-Key + Idempotency-Key), es
#     decir, por el mismo camino de escritura que TerraPlan: nada de SQL directo (ADR-009).
#
# Determinista: con la misma semilla (SEED) y el mismo inicio (DEMO_START) se obtienen los
# mismos valores, así que las capturas y el GIF del README se pueden repetir.
#
# Uso (desde cualquier carpeta, con la API corriendo en localhost:8000):
#   ./scripts/seed_demo.sh
#   API_URL=http://localhost:8000 SEED=42 DEMO_START=2026-09-24T00:00:00Z ./scripts/seed_demo.sh
#
# Requisitos: `uv`, `curl`, `catalog/` sincronizado y `INGEST_API_KEY` en el entorno (o en
# `api/.env`, que `app.core.config` lee al arrancar). Por defecto el inicio de la serie es
# «hace 30 días», para que el dashboard muestre datos recientes; fijar DEMO_START lo congela.
# `date -d` es de GNU date: en macOS hay que pasar DEMO_START explícito.

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
API_URL="${API_URL:-http://localhost:8000}"
SEED="${SEED:-42}"
DAYS="${DAYS:-30}"
START="${DEMO_START:-$(date -u -d '-30 days' +%Y-%m-%dT%H:00:00Z)}"

SITES=(SIM-RIO-MAIPO-01 SIM-RIO-MAPOCHO-01 SIM-ESTERO-LAMPA-01 SIM-ESTERO-PUANGUE-01)
PARAMETERS=(PH DO COND TURB N_NO3)

# Qué anomalía lleva cada parámetro, para que no todas las series se vean iguales.
events_for() {
  case "$1" in
    PH) echo "shift,spike" ;;
    DO) echo "drift" ;;
    COND) echo "dropout,censored" ;;
    TURB) echo "shift,drift" ;;
    N_NO3) echo "spike,censored" ;;
    *) echo "shift,spike" ;;
  esac
}

if ! curl -fsS -o /dev/null "$API_URL/api/v1/health"; then
  echo "La API no responde en $API_URL/api/v1/health. Arráncala con:" >&2
  echo "  cd api && uv run uvicorn app.main:app --reload --port 8000" >&2
  exit 1
fi

cd "$ROOT_DIR/api"

for site in "${SITES[@]}"; do
  for parameter in "${PARAMETERS[@]}"; do
    echo "→ $site · $parameter · ${DAYS}d · seed $SEED · $(events_for "$parameter")"
    uv run python -m app.simulator.run \
      --site "$site" \
      --parameter "$parameter" \
      --days "$DAYS" \
      --seed "$SEED" \
      --start "$START" \
      --events "$(events_for "$parameter")" \
      --api-url "$API_URL"
  done
done

echo "Listo: ${#SITES[@]} sitios × ${#PARAMETERS[@]} parámetros desde $START (seed $SEED)."

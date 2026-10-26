#!/usr/bin/env bash
# seed_demo.sh — carga la demo del portafolio con el simulador determinista (C-1, 03 §7).
#
# Qué hace:
#   * 4 sitios × 5 parámetros × 30 días ≈ 14 400 lecturas horarias (720 por serie).
#   * Un juego de anomalías **distinto por parámetro** (`events_for`): `shift`+`spike` en PH,
#     `drift` en DO, `spike` en COND, `dropout`+`censored` en TURB y `drift`+`spike` en N_NO3.
#   * Una semilla distinta por combinación sitio+parámetro (`SEED_BASE + índice`), así que las
#     veinte series son distintas y las cartas de control no se ven todas iguales.
#   * Escribe por `POST /api/v1/ingest/observations` (X-API-Key + Idempotency-Key), es decir, por
#     el mismo camino que TerraPlan: nada de SQL directo (ADR-009).
#
# Determinista e idempotente: fija una ventana estable (medianoche UTC de hace 29 días) y una
# semilla por serie, así que re-ejecutarlo el mismo día devuelve la *respuesta guardada* de la
# ingesta (misma Idempotency-Key) sin escribir filas nuevas ni fallar. Fijar `DEMO_START` congela
# la ventana para las capturas del README.
#
# Uso (con la API corriendo y el catálogo sincronizado):
#   ./scripts/seed_demo.sh
#   API_URL=http://localhost:8000 SEED_BASE=42 DAYS=30 ./scripts/seed_demo.sh
#
# Requisitos: `uv`, `curl`, `catalog/` sincronizado y `INGEST_API_KEY` en `api/.env` o en el
# entorno. `date -d` es de GNU date: en macOS hay que pasar DEMO_START explícito.

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
API_URL="${API_URL:-http://localhost:8000}"
SEED_BASE="${SEED_BASE:-42}"
DAYS="${DAYS:-30}"
# Vacío = un juego de anomalías distinto por parámetro (`events_for`, más abajo). Definir EVENTS
# fuerza el mismo juego en las veinte series y solo sirve para probar una anomalía concreta.
EVENTS="${EVENTS:-}"
# Ventana alineada a la medianoche UTC: la serie termina hoy (el dashboard se ve fresco) y dos
# corridas del mismo día son idénticas, que es lo que hace la semilla útil.
START="${DEMO_START:-$(date -u -d '-29 days' +%Y-%m-%dT00:00:00Z)}"

SITES=(SIM-RIO-MAIPO-01 SIM-RIO-MAPOCHO-01 SIM-ESTERO-LAMPA-01 SIM-ESTERO-PUANGUE-01)
PARAMETERS=(PH DO COND TURB N_NO3)
CATALOG_FILES=(catalog.meta.json limits.v1.json parameters.v1.json regulations.v1.json units.v1.json)

fail() {
  printf 'Error: %s\n' "$*" >&2
  exit 1
}

# Un juego de anomalías distinto por parámetro (03 §7). Con las mismas cinco en las veinte series,
# el Resumen mostraba veinte veces la misma alerta («Punto 79») y las cinco cartas de un sitio se
# veían idénticas; cada juego deja una firma SPC distinta (ver «Datos demo» en el README).
events_for() {
  if [[ -n "$EVENTS" ]]; then
    printf '%s' "$EVENTS"
    return
  fi

  case "$1" in
    PH) printf 'shift,spike' ;;
    DO) printf 'drift' ;;
    COND) printf 'spike' ;;
    TURB) printf 'dropout,censored' ;;
    N_NO3) printf 'drift,spike' ;;
    *) printf 'shift,spike,drift,dropout,censored' ;;
  esac
}

# ---------------------------------------------------------------- precondiciones ---
command -v curl >/dev/null 2>&1 || fail "falta curl en el PATH."
command -v uv >/dev/null 2>&1 || fail "falta uv en el PATH (instalar: https://docs.astral.sh/uv/)."

if ! curl -fsS --max-time 5 -o /dev/null "$API_URL/api/v1/health"; then
  printf 'Error: la API no responde en %s/api/v1/health.\n' "$API_URL" >&2
  printf 'Arráncala con: cd api && uv run uvicorn app.main:app --reload --port 8000\n' >&2
  exit 1
fi

for file in "${CATALOG_FILES[@]}"; do
  [[ -f "$ROOT_DIR/catalog/$file" ]] || fail "falta catalog/$file; sincroniza con scripts/sync_catalog.py."
done

cd "$ROOT_DIR/api"
[[ -f .env ]] || fail "falta api/.env; cópialo de api/.env.example y ajusta INGEST_API_KEY."

# El CLI lee la key del entorno: si no está exportada, se toma de api/.env (nunca se imprime).
if [[ -z "${INGEST_API_KEY:-}" ]]; then
  INGEST_API_KEY="$(sed -n 's/^INGEST_API_KEY=//p' .env | tr -d '\r' | head -n 1)"
  export INGEST_API_KEY
fi
[[ -n "${INGEST_API_KEY:-}" ]] || fail "INGEST_API_KEY vacía: defínela en api/.env o en el entorno."

# ------------------------------------------------------------------------ lotes ---
TOTAL_BATCHES=$(( ${#SITES[@]} * ${#PARAMETERS[@]} ))
printf 'Demo: %d sitios × %d parámetros = %d lotes · %sd desde %s · anomalías %s\n' \
  "${#SITES[@]}" "${#PARAMETERS[@]}" "$TOTAL_BATCHES" "$DAYS" "$START" \
  "${EVENTS:-distintas por parámetro (ver README)}"

batch=0
accepted_total=0
duplicates_total=0

for site in "${SITES[@]}"; do
  for parameter in "${PARAMETERS[@]}"; do
    seed=$(( SEED_BASE + batch ))
    batch=$(( batch + 1 ))
    events="$(events_for "$parameter")"
    printf '→ [%02d/%02d] %s · %s · seed %d · %s\n' \
      "$batch" "$TOTAL_BATCHES" "$site" "$parameter" "$seed" "$events"

    line="$(uv run python -m app.simulator.run \
      --site "$site" \
      --parameter "$parameter" \
      --days "$DAYS" \
      --seed "$seed" \
      --events "$events" \
      --start "$START" \
      --api-url "$API_URL")"
    printf '  %s\n' "$line"

    # El CLI imprime "... · aceptadas N · duplicadas M · HTTP 200"; se leen con expansión de
    # parámetros para no depender de sed/grep en cada lote.
    accepted="${line##*aceptadas }"
    accepted="${accepted%%[!0-9]*}"
    duplicates="${line##*duplicadas }"
    duplicates="${duplicates%%[!0-9]*}"
    [[ -n "$accepted" && -n "$duplicates" ]] || fail "no se pudo leer el conteo de la ingesta: $line"

    accepted_total=$(( accepted_total + accepted ))
    duplicates_total=$(( duplicates_total + duplicates ))
  done
done

# ------------------------------------------------------------------- verificación ---
sites_total="$(curl -fsS "$API_URL/api/v1/sites?page=1&pageSize=1" \
  | sed -n 's/.*"total":[[:space:]]*\([0-9][0-9]*\).*/\1/p')"
sites_total="${sites_total:-0}"
[[ "$sites_total" -ge "${#SITES[@]}" ]] \
  || fail "se esperaban al menos ${#SITES[@]} sitios y /api/v1/sites informa $sites_total."

readings=$(( accepted_total + duplicates_total ))
echo
printf 'OK: %d sitios, %d parámetros, %d observaciones (aceptadas %d · duplicadas %d · %d lotes).\n' \
  "$sites_total" "${#PARAMETERS[@]}" "$readings" "$accepted_total" "$duplicates_total" "$batch"


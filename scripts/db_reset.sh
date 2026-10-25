#!/usr/bin/env bash
# db_reset.sh — Recrea el esquema `aquametric` de DESARROLLO y vuelve a aplicar migraciones.
#
# Qué hace:
#   1. Lee DATABASE_URL y ENV desde `api/.env` (sin ejecutar el archivo).
#   2. Borra el esquema `aquametric` completo (CASCADE): tablas, datos y la fila de
#      `aquametric.alembic_version` que usa Alembic.
#   3. Lo vuelve a crear vacío y corre `uv run alembic upgrade head`.
#
# Por qué existe: `uv run alembic downgrade -1` sobre la migración inicial **también** borra el
# esquema completo, pero su nombre no lo dice. Ver docs/adr/013-alembic-downgrade-note.md.
#
# ⚠ SOLO DESARROLLO. NUNCA en producción, staging, Neon ni Render: destruye todos los datos.
#    Si ENV es `staging` o `production`, el script se detiene antes de tocar nada.
#
# Uso (desde la raíz del repo, con PostgreSQL arriba: `docker compose up -d postgres`):
#   ./scripts/db_reset.sh
#
# Requisitos: `uv` y `psql` (cliente de PostgreSQL 16) en el PATH, `api/.env` con DATABASE_URL.

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ENV_FILE="$ROOT_DIR/api/.env"

if [[ ! -f "$ENV_FILE" ]]; then
  echo "No existe $ENV_FILE: copia api/.env.example y ajusta DATABASE_URL." >&2
  exit 1
fi

# Lectura literal del .env: nada de `source`, que ejecutaría el contenido.
DB_URL="$(grep -E '^DATABASE_URL=' "$ENV_FILE" | tail -n 1 | cut -d '=' -f 2- || true)"
APP_ENV="$(grep -E '^ENV=' "$ENV_FILE" | tail -n 1 | cut -d '=' -f 2- || true)"
APP_ENV="${APP_ENV:-local}"

if [[ "$APP_ENV" == "production" || "$APP_ENV" == "staging" ]]; then
  echo "ENV=$APP_ENV: este script borra datos y solo se usa en desarrollo. Abortando." >&2
  exit 1
fi

if [[ -z "${DB_URL:-}" ]]; then
  echo "DATABASE_URL está vacía en $ENV_FILE." >&2
  exit 1
fi

# psql no entiende el prefijo de driver de SQLAlchemy.
PSQL_URL="${DB_URL/postgresql+asyncpg:/postgresql:}"

echo "Recreando el esquema aquametric en ${PSQL_URL##*@} ..."
psql "$PSQL_URL" -v ON_ERROR_STOP=1 \
  -c "DROP SCHEMA IF EXISTS aquametric CASCADE; CREATE SCHEMA aquametric;"

echo "Aplicando migraciones ..."
cd "$ROOT_DIR/api"
uv run alembic upgrade head

echo "Listo: esquema aquametric vacío y migraciones al día."

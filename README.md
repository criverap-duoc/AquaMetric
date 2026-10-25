# AquaMetric

Plataforma de monitoreo de calidad de agua con **control estadístico de procesos (SPC)**.
Recibe observaciones de laboratorio (TerraPlan) y de un simulador de sensores, las normaliza
contra un catálogo compartido y las analiza con cartas de control (I-MR / X̄-R), reglas de
Nelson y capacidad de proceso. La UI es pública y de solo lectura.

> **Estado: Fase A cerrada.** API con `create_app()`, `/api/v1/health`, errores en
> `application/problem+json`, logging JSON con `requestId`, esquema `aquametric` con Alembic y
> **ingesta atómica e idempotente** (`POST /api/v1/ingest/observations`). Simulador, SPC y
> frontend llegan en las fases siguientes.

## Stack

| Capa | Tecnología |
|---|---|
| Lenguaje | Python ≥ 3.13 (gestionado con `uv`) |
| API | FastAPI + Uvicorn |
| Validación | Pydantic v2 + `pydantic-settings` (JSON en camelCase) |
| BD | PostgreSQL 16, esquema `aquametric` (SQLAlchemy 2.0 async + asyncpg + Alembic) |
| Calidad | `ruff`, `mypy`, `pytest` |

## Estructura

```
aquametric-fastapi/
├─ api/
│  ├─ pyproject.toml
│  ├─ alembic/              # migraciones (version_table_schema = aquametric)
│  ├─ app/
│  │  ├─ main.py            # create_app(): settings, middleware, handlers, routers
│  │  ├─ catalog/           # loader + validación del catálogo sincronizado
│  │  ├─ core/              # config · clock · db · security · dependencies · errors · logging
│  │  ├─ models/            # SQLAlchemy 2.0 (esquema aquametric)
│  │  ├─ repositories/      # único acceso a la BD
│  │  ├─ routers/           # health · ingest
│  │  ├─ schemas/           # CamelModel y contratos
│  │  └─ services/          # IngestService: transacción única e idempotencia
│  └─ tests/                # unit/ · integration/ (Testcontainers)
├─ catalog/                 # copia de solo lectura, sincronizada con scripts/sync_catalog.py
├─ docs/                    # ADRs, métodos SPC, glosario, design system
├─ scripts/                 # sync_catalog.py · db_reset.sh (solo desarrollo)
└─ docker-compose.yml       # PostgreSQL local en el puerto 5433
```

## Quickstart

```bash
# 1. PostgreSQL local (contenedor aquametric-pg en localhost:5433)
docker compose up -d postgres

# 2. Dependencias de la API
cd api
uv sync

# 3. Variables de entorno
cp .env.example .env        # ajustar INGEST_API_KEY

# 4. Esquema de la base (migraciones Alembic)
uv run alembic upgrade head

# 5. Servidor
uv run uvicorn app.main:app --reload --port 8000
```

OpenAPI: <http://localhost:8000/docs> · Health: <http://localhost:8000/api/v1/health>

## Endpoints

| Método | Ruta | Acceso | Descripción |
|---|---|---|---|
| GET | `/api/v1/health` | Público | Liveness: `status`, `service`, `version`, `env`, `timestamp`, `requestId` |
| POST | `/api/v1/ingest/observations` | `X-API-Key` + `Idempotency-Key` | Lote atómico e idempotente: `{catalogVersion, site, samples[], observations[]}` → `{accepted, duplicates}` |

El endpoint de ingesta exige `X-API-Key` **y** `Idempotency-Key`; toda la lectura es pública. Un
lote se valida completo antes de escribir: cualquier fila inválida (`UNKNOWN_PARAMETER`,
`UNIT_MISMATCH`, `VALIDATION_ERROR`) deja la base intacta, y repetir la misma key con el mismo
cuerpo devuelve la respuesta guardada sin reprocesar. Ningún error sale de la API con otra forma
que `application/problem+json`.

## Reset de la base de datos (solo desarrollo)

`alembic downgrade -1` sobre la migración inicial **borra el esquema completo**, con datos y todo
(ver `docs/adr/013-alembic-downgrade-note.md`). Para empezar de cero en local:

```bash
./scripts/db_reset.sh    # lee DATABASE_URL de api/.env, recrea aquametric y migra
```

## Variables de entorno

Definidas en `api/.env.example` (nunca commitear `.env`): `ENV`, `DATABASE_URL`,
`INGEST_API_KEY` (obligatoria, sin valor por defecto), `CORS_ORIGINS` (allowlist separada por
comas), `CATALOG_DIR`, `AWS_REGION`, `S3_BUCKET`, `BASELINE_MIN_POINTS`,
`CENSORED_MAX_FRACTION`, `LOG_LEVEL`.

## Calidad

```bash
cd api
uv run ruff check .
uv run ruff format --check .
uv run mypy app
uv run pytest -q -m "not integration"
```

Convenciones del proyecto: JSON en camelCase, fechas ISO-8601 en UTC, tablas en el esquema
`aquametric`, límites de control ≠ límites normativos ≠ LOQ, y screening **referencial** (nunca
un dictamen de cumplimiento legal).

## Documentación

- `docs/` — decisiones de arquitectura (ADR), `spc-methods.md`, `glossary.md`, design system.
- Proyecto hermano: **TerraPlan** (NestJS), dueño del catálogo de parámetros, unidades y límites.

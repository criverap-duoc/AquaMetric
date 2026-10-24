# AquaMetric

Plataforma de monitoreo de calidad de agua con **control estadístico de procesos (SPC)**.
Recibe observaciones de laboratorio (TerraPlan) y de un simulador de sensores, las normaliza
contra un catálogo compartido y las analiza con cartas de control (I-MR / X̄-R), reglas de
Nelson y capacidad de proceso. La UI es pública y de solo lectura.

> **Estado: Fase A-1 (scaffold).** API creada con `create_app()`, `/api/v1/health` operativo,
> errores en `application/problem+json` y logging JSON con `requestId`. Todavía **no** hay
> base de datos, ingesta, SPC ni frontend: llegan en las fases A-2 en adelante.

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
│  ├─ app/
│  │  ├─ main.py            # create_app(): settings, middleware, handlers, routers
│  │  ├─ core/              # config · clock · errors · logging · db
│  │  ├─ routers/           # health
│  │  └─ schemas/           # CamelModel y contratos
│  └─ tests/                # unit/
├─ catalog/                 # copia de solo lectura del catálogo de TerraPlan (pendiente)
├─ docs/                    # ADRs, métodos SPC, glosario, design system
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

# 4. Servidor
uv run uvicorn app.main:app --reload --port 8000
```

OpenAPI: <http://localhost:8000/docs> · Health: <http://localhost:8000/api/v1/health>

## Endpoints

| Método | Ruta | Acceso | Descripción |
|---|---|---|---|
| GET | `/api/v1/health` | Público | Liveness: `status`, `service`, `version`, `env`, `timestamp`, `requestId` |

Los endpoints de escritura (ingesta, línea base SPC) exigirán `X-API-Key`; toda la lectura es
pública. Ningún error sale de la API con otra forma que `application/problem+json`.

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

# AquaMetric

[![CI](https://img.shields.io/badge/CI-GitHub%20Actions%20(Fase%20F)-lightgrey?logo=githubactions&logoColor=white)](#estado-del-proyecto)
[![Python](https://img.shields.io/badge/Python-3.13%2B-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-async-009688?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![License](https://img.shields.io/badge/License-MIT-green)](./README.md#licencia)

Plataforma de monitoreo de calidad de agua con **control estadístico de procesos (SPC)**.
Recibe observaciones de laboratorio (TerraPlan) y de un simulador de sensores, las normaliza
contra un catálogo compartido y las analiza con cartas de control (I-MR / X̄-R), reglas de
Nelson y capacidad de proceso. La UI es pública y de solo lectura.

> ⚠️ **Screening referencial, no dictamen de cumplimiento.** AquaMetric compara un valor con el
> rango que publica el catálogo; **no** declara si un sitio cumple la norma. El D.S. 53/2014 se
> evalúa con percentiles en ventanas de tres años y la NCh 1.333 según el uso del agua, y ninguna
> de las dos se puede resolver con una observación aislada. Ver
> [`docs/adr/010-screening-not-compliance.md`](docs/adr/010-screening-not-compliance.md).

## Qué hace

| Pieza | Estado | Qué resuelve |
|---|---|---|
| **Ingesta idempotente** | ✅ Fase A | Un solo camino de escritura (`POST /api/v1/ingest/observations`): lote atómico, validado contra el catálogo, con doble idempotencia |
| **Screening referencial** | ✅ Fase B | Compara una observación con un límite `validated` del catálogo y responde `normal` / `above_range` / `below_range` / `not_evaluable` |
| **Simulador determinista** | ✅ Fase C | Genera series AR(1) con eventos (`shift`, `spike`, `drift`, `dropout`, `censored`); misma semilla ⇒ mismos datos |
| **Núcleo SPC** | ✅ Fase D | Cartas I-MR y X̄-R, reglas de Nelson R1–R5, capacidad Cp/Cpk, línea base con tests golden |
| **UI pública** | ⏳ Fase E | Dashboard científico de solo lectura (React 19 + Vite + Tailwind 4 + shadcn/ui) |
| **Despliegue** | ⏳ Fase F | Render (API) + Neon (PostgreSQL) + Vercel (web), README con demo viva |
| **Pipeline AWS** | ⏳ Fase G | EventBridge → Lambda → S3 → Lambda → API, con SAM (se recorta primero si hay atraso) |

## Estado del proyecto

| Fase | Alcance | Estado |
|---|---|---|
| **A** | Scaffold, config, catálogo sincronizado, esquema `aquametric`, ingesta atómica e idempotente | **cerrada** |
| **B** | Screening referencial puro + endpoints públicos de lectura (`catalog`, `screening`) | **cerrada** |
| **C** | Simulador CLI determinista (sitios `SIM-…`) | **cerrada** (C-1) |
| **D** | Núcleo SPC puro con tests golden; endpoints `spc/baseline` y `spc/control-chart` | **cerrada** la D-1 (núcleo); endpoints en D-2 |
| **E** | Frontend público de solo lectura (7 pantallas) | pendiente |
| **F** | Despliegue (Render + Neon + Vercel), CI, ADRs, demo viva | pendiente |
| **G** | Pipeline AWS con SAM | pendiente (opcional) |


## Stack

| Capa | Tecnología |
|---|---|
| Lenguaje | Python ≥ 3.13 (gestionado con `uv`) |
| API | FastAPI + Uvicorn (async de punta a punta) |
| Validación | Pydantic v2 + `pydantic-settings` (JSON en camelCase) |
| BD | PostgreSQL 16, esquema `aquametric` (SQLAlchemy 2.0 async + asyncpg + Alembic) |
| Estadística | `numpy` (núcleo SPC puro) · `pandas` solo en el simulador |
| Simulador | Generador determinista `numpy.random.Generator(PCG64(seed))` + CLI |
| Calidad | `ruff` (lint + format), `mypy`, `pytest` (+ `moto` para S3) |
| Contenedores | Docker multi-stage (usuario no root) + Docker Compose |
| Frontend (Fase E) | React 19 + Vite + TypeScript + Tailwind 4 + shadcn/ui + TanStack Query, `pnpm` |
| AWS (Fase G) | S3 + Lambda + EventBridge Scheduler, IaC con SAM, región `us-east-1` |


## Estructura

```
aquametric-fastapi/
├─ api/
│  ├─ pyproject.toml        # uv · ruff · mypy · pytest
│  ├─ alembic/              # migraciones (version_table_schema = aquametric)
│  ├─ app/
│  │  ├─ main.py            # create_app(): settings, middleware, handlers, routers
│  │  ├─ catalog/           # loader + validación del catálogo sincronizado
│  │  ├─ core/              # config · clock · db · security · dependencies · errors · logging
│  │  ├─ models/            # SQLAlchemy 2.0: site · sample · observation · ingest_idempotency · spc_baseline
│  │  ├─ repositories/      # único acceso a la BD
│  │  ├─ routers/           # health · ingest · catalog · screening
│  │  ├─ schemas/           # CamelModel y contratos públicos
│  │  ├─ screening/         # screening referencial puro (sin I/O)
│  │  ├─ services/          # IngestService: transacción única e idempotencia
│  │  ├─ simulator/         # generador determinista + CLI (escribe por la API)
│  │  └─ spc/               # ★ núcleo puro: charts · rules · capability · baseline · constants
│  └─ tests/                # unit/ · integration/ (Testcontainers) · golden/ (SPC)
├─ catalog/                 # copia de solo lectura, sincronizada con scripts/sync_catalog.py
├─ docs/                    # adr/ · architecture.md · spc-methods.md · glossary.md · design-system.md
├─ scripts/                 # sync_catalog.py · db_reset.sh · seed_demo.sh · contrast-check.py
├─ .clinerules/             # reglas del proyecto (contexto, estándares, flujos, UI)
└─ docker-compose.yml       # PostgreSQL local en el puerto 5433
```

## Quickstart (local)

```bash
# 0. Código y catálogo
git clone <url-del-repo> aquametric-fastapi
cd aquametric-fastapi
python ../scripts/sync_catalog.py --from-path <ruta-a-terraplan>/catalog   # copia verificada por sha256

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

El catálogo ya está commiteado, así que el paso 0 es opcional si solo quieres levantar la API: el
script existe para re-sincronizar cuando cambie en TerraPlan (y verificar el `sha256`).


OpenAPI: <http://localhost:8000/docs> · Health: <http://localhost:8000/api/v1/health>

## Endpoints

| Método | Ruta | Acceso | Descripción |
|---|---|---|---|
| GET | `/api/v1/health` | Público | Liveness: `status`, `service`, `version`, `env`, `timestamp`, `requestId` |
| GET | `/api/v1/catalog/meta` | Público | Versión, `sha256` del bundle y estado de firma (`status`, `validatedBy`, `validatedAt`) |
| GET | `/api/v1/catalog/parameters` | Público | Parámetros con unidad canónica y decimales de presentación |
| GET | `/api/v1/catalog/units` | Público | Unidades con su factor explícito a la unidad canónica |
| GET | `/api/v1/catalog/limits` | Público | Límites del catálogo (filtros `parameterCode`, `regulation`), `draft` incluidos |
| GET | `/api/v1/catalog/regulations` | Público | Regulaciones citadas por el catálogo |
| POST | `/api/v1/screening/evaluate` | Público | Screening **referencial** de una observación contra un límite: `flag`, `reason`, `limitApplied`, `warnings[]` |
| GET | `/api/v1/screening/limits` | Público | Límites que el selector puede citar (`parameterCode` + `regulation` + contexto/área) |
| POST | `/api/v1/ingest/observations` | `X-API-Key` + `Idempotency-Key` | Lote atómico e idempotente: `{catalogVersion, site, samples[], observations[]}` → `{accepted, duplicates}` |

El único endpoint de escritura es la ingesta: exige `X-API-Key` **y** `Idempotency-Key`; toda la
lectura y el screening son públicos porque analizan datos ya publicados. Un lote se valida
completo antes de escribir: cualquier fila inválida (`UNKNOWN_PARAMETER`, `UNIT_MISMATCH`,
`VALIDATION_ERROR`) deja la base intacta, y repetir la misma key con el mismo cuerpo devuelve la
respuesta guardada sin reprocesar. Ningún error sale de la API con otra forma que
`application/problem+json`.

El screening responde `not_evaluable` (con motivo en español) mientras ningún límite tenga
`status = validated`: hoy los 60 límites del catálogo están `draft-verified`, así que **no
compara nada todavía**. Eso es el comportamiento correcto, no una falla (ADR-012).


## Reset de la base de datos (solo desarrollo)

`alembic downgrade -1` sobre la migración inicial **borra el esquema completo**, con datos y todo
(ver `docs/adr/013-alembic-downgrade-note.md`). Para empezar de cero en local:

```bash
./scripts/db_reset.sh    # lee DATABASE_URL de api/.env, recrea aquametric y migra
```

## Datos demo (simulador determinista)

Los lotes de TerraPlan son pocos (una campaña no llega a la línea base de 20 puntos), así que la
demo se alimenta de un simulador propio: sitios `SIM-…`, series horarias con un proceso AR(1) y
anomalías inyectadas (`shift`, `spike`, `drift`, `dropout`, `censored`). El generador es **puro**
(recibe la fecha de inicio y el catálogo; nada de reloj ni de base de datos) y la CLI escribe por
`POST /api/v1/ingest/observations`, igual que TerraPlan:

```bash
# con la API corriendo en localhost:8000
./scripts/seed_demo.sh     # 4 sitios x 5 parámetros x 30 días, seed 42

# o una serie concreta
cd api
uv run python -m app.simulator.run --site SIM-RIO-MAIPO-01 --parameter PH --seed 42 --days 30 \
  --events shift,spike --start 2026-09-24T00:00:00Z
```

Misma semilla + mismo `--start` ⇒ mismos valores: las capturas y el GIF del README se repiten.
Fijar `--start` (o `DEMO_START`) es también lo que hace reproducible la `Idempotency-Key`.

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
uv run pytest -q -m "not integration"     # unit + golden, sin Docker
uv run pytest -q -m integration           # Testcontainers (requiere Docker)
```

El núcleo SPC (`app/spc/`) es la pieza con más red: `api/tests/golden/` fija valores esperados
calculados de forma independiente (constantes `d₂/D₄/A₂`, cartas I-MR y X̄-R, reglas R1–R5,
capacidad y regímenes de censurados). `api/tests/golden/README.md` documenta cómo se obtuvo cada
número; un cambio de fórmula que mueva un decimal rompe un test, no una demo.


Convenciones del proyecto: JSON en camelCase, fechas ISO-8601 en UTC, tablas en el esquema
`aquametric`, límites de control ≠ límites normativos ≠ LOQ, y screening **referencial** (nunca
un dictamen de cumplimiento legal).

## Despliegue

La imagen se construye con el **contexto en la raíz del repositorio**, no en `api/`: necesita la
copia sincronizada de `catalog/` o toda lectura del catálogo falla en runtime (hallazgo H1-A4,
ADR-016).

```bash
docker build -f api/Dockerfile -t aquametric-api:test .
docker run --rm aquametric-api:test ls /app/catalog   # debe listar los 5 archivos del catálogo
```

En Render, `render.yaml` ya declara `dockerfilePath: ./api/Dockerfile`, `dockerContext: .` y las
variables: `CATALOG_DIR=/app/catalog` viene fija, `DATABASE_URL` y `CORS_ORIGINS` se cargan en el
panel (ningún secreto en el repo) e `INGEST_API_KEY` se genera. Antes de dar la URL por buena:
`GET /api/v1/health` responde 200 y `POST /api/v1/screening/evaluate` devuelve `not_evaluable` con
motivo (nunca 500, que sería la señal de que el catálogo no entró en la imagen).

## Documentación

| Documento | Para qué |
|---|---|
| [`docs/architecture.md`](docs/architecture.md) | Vista de conjunto: diagramas Mermaid, camino único de escritura, capas, tablas, pipeline AWS y despliegue |
| [`docs/spc-methods.md`](docs/spc-methods.md) | Fórmulas de I-MR y X̄-R, reglas R1–R5, capacidad y política de censurados, en lenguaje claro |
| [`docs/glossary.md`](docs/glossary.md) | Glosario (dominio químico, SPC, screening, infraestructura) para el químico y el analista |
| [`docs/design-system.md`](docs/design-system.md) | Tokens, tipografía, componentes y reglas de gráficos de la UI |
| [`docs/adr/`](docs/adr/) | 17 decisiones de arquitectura, de la estimación 3σ en Fase I (ADR-001) al contexto de build en Docker (ADR-016) |
| [`.clinerules/`](.clinerules/) | Reglas del proyecto: contexto, estándares de código, flujos de trabajo, directivas de UI y limpieza |

Números clave del núcleo SPC: `docs/spc-methods.md` §2–§6; los valores esperados de cada test
golden y cómo se obtuvieron, en `api/tests/golden/README.md`.

## Proyecto hermano

**TerraPlan** (NestJS) es la fuente de verdad del catálogo de parámetros, unidades y límites, y el
origen de los lotes de laboratorio. AquaMetric guarda una copia de solo lectura en `catalog/`
sincronizada con `scripts/sync_catalog.py` (ADR-005); un cambio de catálogo se hace en TerraPlan y
se sincroniza aquí, nunca al revés.

## Licencia

MIT.


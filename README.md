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
| **UI pública** | ✅ Fase E | 7 pantallas de solo lectura (React 19 + Vite + Tailwind 4 + shadcn/ui): resumen, sitios, series, control SPC, screening, pipeline y ajustes, alimentadas por el API |
| **Despliegue** | ⏳ Fase F | Render (API) + Neon (PostgreSQL) + Vercel (web), README con demo viva |
| **Pipeline AWS** | ⏳ Fase G | EventBridge → Lambda → S3 → Lambda → API, con SAM (se recorta primero si hay atraso) |

## Estado del proyecto

| Fase | Alcance | Estado |
|---|---|---|
| **A** | Scaffold, config, catálogo sincronizado, esquema `aquametric`, ingesta atómica e idempotente | **cerrada** |
| **B** | Screening referencial puro + endpoints públicos de lectura (`catalog`, `screening`) | **cerrada** |
| **C** | Simulador CLI determinista (sitios `SIM-…`) | **cerrada** (C-1) |
| **D** | Núcleo SPC puro con tests golden; endpoints `spc/control-charts`, `spc/baseline` y `spc/rules` | **cerrada** (D-1 núcleo, D-2 endpoints) |
| **E** | Frontend público de solo lectura (7 pantallas) sobre los endpoints reales | **cerrada** (E-1a…E-1f) |
| **F** | Despliegue (Render + Neon + Vercel), CI, capturas y demo viva | **en curso** (F-1a: `GET /observations` y las pantallas de Series y Control sobre datos reales) |
| **G** | Pipeline AWS con SAM | pendiente (opcional, se recorta primero) |

## Demo en vivo

- **App**: https://aquametric-rho.vercel.app
- **API**: https://aquametric-api.onrender.com/api/v1/docs
- **Repo**: https://github.com/criverap-duoc/AquaMetric

> Datos demo del simulador (4 sitios × 5 parámetros × 30 días = 14.380 lecturas). El screening está en modo referencial porque el químico aún no firmó los límites del catálogo (ADR-012).

## Capturas

Las capturas se graban con la demo cargada (`./scripts/seed_demo.sh`, semilla fija) para que el GIF
se pueda repetir. Carpeta: [`docs/captures/`](docs/captures/).

| Pantalla | Archivo |
|---|---|
| Resumen (KPIs y alertas) - Sitios de Monitoreo | `docs/captures/AquaMetric1.gif` |
| Series (tendencia + tabla de observaciones) - Control SPC (carta I-MR con reglas R1/R2) | `docs/captures/AquaMetric2.gif` |
| Screening: Comparación con Límites Normativos - Pipeline con últimas ingestas y lecturas - Ajustes: Parámetros, dimensiones y rangos (sólo lectura) | `docs/captures/AquaMetric3.gif` |

![Resumen - Sitios](docs/captures/01-resumen.gif)
![Series - Control SPC](docs/captures/02-control.gif)
![Screening - Pipeline - Ajustes](docs/captures/03-series.gif)


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
│  │  ├─ routers/           # health · catalog · screening · ingest · spc · sites · pipeline
│  │  ├─ schemas/           # CamelModel y contratos públicos
│  │  ├─ screening/         # screening referencial puro (sin I/O)
│  │  ├─ services/          # IngestService: transacción única e idempotencia
│  │  ├─ simulator/         # generador determinista + CLI (escribe por la API)
│  │  └─ spc/               # ★ núcleo puro: charts · rules · capability · baseline · constants
│  └─ tests/                # unit/ · integration/ (Testcontainers) · golden/ (SPC)
├─ catalog/                 # copia de solo lectura, sincronizada con scripts/sync_catalog.py
├─ web/                     # UI pública: React 19 + Vite + TypeScript + Tailwind 4 + shadcn/ui
│  └─ src/
│     ├─ api/               # clientes TanStack Query (sites · catalog · pipeline · spc)
│     ├─ components/        # ui/ (shadcn) · domain/ (ControlChart, ScreeningBadge, StatTile…)
│     ├─ features/          # resumen · sitios · series · control · screening · pipeline · ajustes
│     └─ lib/               # api-client (problem+json) · format (es-CL)
├─ docs/                    # adr/ · captures/ · architecture.md · spc-methods.md · glossary.md · design-system.md
├─ scripts/                 # sync_catalog.py · db_reset.sh · seed_demo.sh · contrast-check.py
├─ .clinerules/             # reglas del proyecto (contexto, estándares, flujos, UI)
└─ docker-compose.yml       # PostgreSQL local en el puerto 5433
```

## Demo local en 5 pasos

Requisitos: Docker, `uv` (Python ≥ 3.13), Node ≥ 20 y `pnpm`.

```bash
# 1. PostgreSQL local (contenedor aquametric-pg, puerto 5433)
docker compose up -d postgres

# 2. Dependencias de la API (desde api/)
cd api
uv sync

# 3. Variables de entorno (no se commitea: api/.env está en .gitignore)
cp .env.example .env        # ajustar INGEST_API_KEY

# 4. Esquema de la base (migraciones Alembic, esquema aquametric)
uv run alembic upgrade head

# 5. API en el puerto 8000
uv run uvicorn app.main:app --reload --port 8000
```

En otra terminal, la UI (puerto 5174):

```bash
cd web && pnpm install && pnpm dev
```

La web apunta al API por `VITE_API_URL` (`web/.env.example` lo fija en `http://localhost:8000`, que
es también el valor por defecto cuando no hay archivo). El origen de la UI tiene que estar en
`CORS_ORIGINS` del API: `http://localhost:5174` ya viene así en `api/.env.example`.

Y con la API ya corriendo, los datos de demostración:

```bash
./scripts/seed_demo.sh     # 4 sitios × 5 parámetros × 30 días; idempotente
```

| URL | Qué es |
|---|---|
| <http://localhost:5174> | UI pública (7 pantallas, solo lectura) |
| <http://localhost:8000/api/v1/docs> | API interactiva (Swagger UI) |
| <http://localhost:8000/api/v1/health> | Health check |

**Nota sobre `api/.env`:** las credenciales de `DATABASE_URL` deben coincidir con
`docker-compose.yml` (`aquametric:aquametric@localhost:5433/aquametric`). El puerto **5433** es a
propósito: TerraPlan usa 5432 y así ambos proyectos corren a la vez. `INGEST_API_KEY` es
obligatoria (la API no arranca sin ella) y debe tener al menos 16 caracteres; el simulador la lee
de `api/.env` o del entorno, nunca de la línea de comandos de este script.

El catálogo ya está commiteado en `catalog/`, así que solo hay que re-sincronizarlo cuando cambie
en TerraPlan:

```bash
python ../scripts/sync_catalog.py --from-path <ruta-a-terraplan>/catalog   # verifica el sha256
```

## Endpoints


| Método | Ruta | Acceso | Descripción |
|---|---|---|---|
| GET | `/api/v1/health` | Público | Liveness: `status`, `service`, `version`, `env`, `timestamp`, `requestId` |
| GET | `/api/v1/catalog/meta` | Público | Versión, `sha256` del bundle y estado de firma (`status`, `validatedBy`, `validatedAt`) |
| GET | `/api/v1/catalog/parameters` | Público | Parámetros con unidad canónica y decimales de presentación |
| GET | `/api/v1/catalog/units` | Público | Unidades con su factor explícito a la unidad canónica |
| GET | `/api/v1/catalog/limits` | Público | Límites del catálogo (`parameterCode`, `regulation`, `context`, `monitoringArea`, `qualityLevel`, `status`); `meta` cuenta validados y pendientes |
| GET | `/api/v1/catalog/regulations` | Público | Regulaciones citadas por el catálogo |
| POST | `/api/v1/screening/evaluate` | Público | Screening **referencial** de una observación contra un límite: `flag`, `reason`, `limitApplied`, `warnings[]` |
| GET | `/api/v1/screening/limits` | Público | Límites que el selector puede citar (`parameterCode` + `regulation` + contexto/área) |
| GET | `/api/v1/sites` | Público | Sitios paginados por `code` (`page`, `pageSize`, `isActive`): entregan el `siteId` que esperan los endpoints SPC |
| GET | `/api/v1/observations` | Público | Observaciones paginadas (`siteId`, `parameterCode`, `from`, `to`, `order`), con `siteCode` en cada fila; censuradas como `value=null` + `qualifier="<"` + `loq` |
| GET | `/api/v1/observations/aggregate` | Público | Conteo, censuradas, mínimo, máximo y media de una ventana en una sola consulta |
| GET | `/api/v1/pipeline/status` | Público | Últimos lotes de `ingest_idempotency` y última lectura por sitio; `awsDeployed=false` cuando el pipeline AWS no existe (ADR-004) |
| GET | `/api/v1/spc/control-charts` | Público | Carta I-MR de una serie (`siteId`, `parameterCode`, ventana): límites de control, puntos y violaciones `R1`–`R5` |
| GET | `/api/v1/spc/baseline` | Público | Línea base Fase I persistida de una serie (los mismos números para cualquier cliente) |
| POST | `/api/v1/spc/baseline` | `X-API-Key` | Congela la línea base Fase I de una serie; recomputarla deja una sola fila por fase |
| GET | `/api/v1/spc/rules` | Público | Señales del tramo de monitoreo de una serie; lista vacía = en control |
| POST | `/api/v1/ingest/observations` | `X-API-Key` + `Idempotency-Key` | Lote atómico e idempotente: `{catalogVersion, site, samples[], observations[]}` → `{accepted, duplicates}` |

Hay dos endpoints de escritura y ambos exigen `X-API-Key`: `POST /api/v1/ingest/observations`
(además con `Idempotency-Key`) y `POST /api/v1/spc/baseline` (congelar la línea base). Toda la
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
# con la API corriendo en localhost:8000 (y con api/.env ya copiado)
./scripts/seed_demo.sh

# o una serie concreta
cd api
uv run python -m app.simulator.run --site SIM-RIO-MAIPO-01 --parameter PH --seed 42 --days 30 \
  --events shift,spike --start 2026-09-27T00:00:00Z
```

Cada parámetro lleva **su propio juego de anomalías** en lugar de las cinco en todas las series: con
el mismo juego, las veinte cartas de control se veían idénticas y el Resumen repetía la misma alerta
veinte veces.

| Parámetro | Anomalías inyectadas | Firma en la carta de control |
|---|---|---|
| `PH` | `shift` de 3,5 σ durante 30 puntos + `spike` de 6 σ | Un bloque de ~30 puntos sobre el UCL (R1) con una R2 dentro; el `spike` es un R1 aislado |
| `DO` | `drift` en rampa hasta 3,5 σ en 26 puntos | Los R1 se amontonan al final de la rampa, con R4/R5 acompañando |
| `COND` | `spike` de 6 σ | Un R1 exactamente en el `spike` (índice 75), sin bloque alrededor |
| `TURB` | `dropout` de 5 lecturas + 4 lecturas censuradas (`< LOQ`) | Ningún R1 en el hueco: la señal es el hueco de 5 lecturas y los círculos huecos de los censurados |
| `N_NO3` | `drift` + `spike` | Bloque de R1 en el tramo final de la rampa y una R3 durante ella |

Las anomalías se plantan entre los índices 50 y 116 de la serie, dentro de la ventana que la carta
dibuja **y** evalúa (40 puntos de línea base + 100 de monitoreo): un evento fuera de esa ventana
existe en la base pero nadie lo ve, que es exactamente lo que pasaba antes de este ajuste.

La firma es la **forma** —bloque, rampa, punto aislado, hueco—, no el conteo: los límites salen de
40 puntos de línea base, así que una serie en control todavía arrastra unos pocos R1 sueltos por
ventana (medido: 0 a 7 en las veinte series de la demo; la misma variabilidad que motiva usar 40 y
no 20, más arriba). Los cuatro sitios usan semillas distintas, de modo que el número exacto de
señales cambia y la forma no.

Dos decisiones del generador explican cómo se ven las cartas:

- **`ar1_phi = 0,25` por defecto.** Con `ar1_phi = 0,7` el rango móvil de la serie es mucho menor
  que su dispersión real, así que los límites quedaban a ±1,6 σ verdaderas y **una de cada ocho
  lecturas normales rompía R1** (medido con 200 series simuladas: 13 % de la ventana de monitoreo
  con 0,7; con 0,25 baja a ~1,7 %): las anomalías plantadas se ahogaban entre falsas alarmas y las
  cartas volvían a parecerse entre sí.
- **Fase I de 40 puntos en la carta.** El mínimo de ADR-001 son 20, pero con 20 puntos el ancho de
  los límites tiene 21,5 % de dispersión relativa (14,4 % con 40) y la tasa de R1 espurios sube de
  1,7 % a 2,6 % de los puntos monitorizados; el filtro de la pantalla Control permite volver a
  20, 30 o 50.

El script exige la API arriba (`/api/v1/health`) y el catálogo sincronizado, y después envía **20
lotes** (4 sitios × 5 parámetros, 14 380 lecturas) con una semilla propia por combinación
(`SEED_BASE + índice`, por defecto 42…61), el juego de anomalías de su parámetro y una ventana fija:
el inicio es la medianoche UTC de hace 29 días (`DEMO_START` la congela). Al terminar verifica
`/api/v1/sites` e imprime `OK: 4 sitios, 5 parámetros, 14380 observaciones`.

Es **idempotente**: re-ejecutarlo el mismo día repite la misma `Idempotency-Key`, así que la API
devuelve la respuesta guardada y no escribe filas nuevas (verificado contando
`aquametric.observation` antes y después). Misma semilla + mismo `--start` ⇒ mismos valores, que es
lo que hace repetibles las capturas y el GIF del README.


## Variables de entorno

Definidas en `api/.env.example` (nunca commitear `.env`): `ENV`, `DATABASE_URL`,
`INGEST_API_KEY` (obligatoria, sin valor por defecto), `CORS_ORIGINS` (allowlist separada por
comas), `CATALOG_DIR`, `AWS_REGION`, `S3_BUCKET`, `AWS_PIPELINE_DEPLOYED` (`false` mientras la
demo escriba directo a la API y la pantalla Pipeline lo diga), `BASELINE_MIN_POINTS`,
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

El paso a paso completo (Neon, Render, migraciones, Vercel, CORS, datos demo y UptimeRobot) está en
[`docs/deploy.md`](docs/deploy.md).

## Documentación

| Documento | Para qué |
|---|---|
| [`docs/architecture.md`](docs/architecture.md) | Vista de conjunto: diagramas Mermaid, camino único de escritura, capas, tablas, pipeline AWS y despliegue |
| [`docs/deploy.md`](docs/deploy.md) | Despliegue paso a paso: Neon, Render, migraciones, Vercel, CORS, datos demo y UptimeRobot |
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


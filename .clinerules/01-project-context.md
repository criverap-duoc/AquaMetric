# 01 · Contexto del proyecto — AquaMetric (FastAPI)

> Proyecto **greenfield**. Regla madre: *construir consistente desde cero y entregar un MVP desplegado en 2–3 semanas*. Rigor donde importa (estadística y contrato de datos), simplicidad en el resto.
> Idioma: ver `02-coding-standards.md` (respuestas en español · código en inglés · commits en inglés).

## 1. Qué es

**AquaMetric**: plataforma de monitoreo de calidad de agua con **control estadístico de procesos (SPC)**.

1. **Recibe** observaciones desde **TerraPlan** (NestJS; resultados de laboratorio de campañas de muestreo) y desde un **simulador de sensores** (lecturas continuas).
2. **Normaliza** unidades y valida contra el **catálogo compartido** (parámetros, unidades, límites).
3. **Analiza**: cartas de control (I-MR / X̄-R), reglas de Nelson/Western Electric, capacidad de proceso y **screening referencial** contra los límites del catálogo (**no** es un dictamen de cumplimiento legal; ver §5).
4. **Visualiza** con una UI React propia, **pública y de solo lectura**, con un dashboard científico claro y creíble (datos demo del simulador + lotes de TerraPlan).
5. Un **pipeline en AWS** (S3 + Lambda + EventBridge) ingiere y procesa lecturas del simulador.

Público de la UI: analistas de datos, científicos, reguladores. Sensación: rigor, claridad, credibilidad.

### Alcance MVP (2–3 semanas)

| Dentro | Fuera (no hacer sin aprobación) |
|---|---|
| Ingesta idempotente de lotes (Site, Sample, Observation) | Streaming real (Kafka/Kinesis), MQTT |
| SPC: I-MR (defecto) y X̄-R, 5 reglas, línea base (Fase I) | ML predictivo, forecasting avanzado |
| **Screening** referencial (`screeningFlag`) contra el catálogo | **Dictamen de cumplimiento legal**, percentiles P95/P5 y ventanas de 3 años (D.S. 53/2014), editor de normas en UI |
| Simulador determinista (CLI primero; Lambda programada después) | Sensores físicos reales |
| Pipeline AWS mínimo (S3 → Lambda → API) con IaC (SAM) — **lo primero que se recorta** | VPC, ECS/EKS, Step Functions, RDS |
| Auth: `X-API-Key` en escritura; lectura pública | **Usuarios, login, JWT, roles**, SSO/OAuth |
| Frontend mínimo profesional (7 pantallas, público, solo lectura) | Mapas interactivos pesados |
| EWMA/CUSUM | *Stretch*: solo si sobra tiempo |

### Plan de 3 semanas

| Semana | Entregable |
|---|---|
| 1 | Scaffold (uv, Docker), config, **catálogo real sincronizado**, esquema `aquametric` + migraciones, **ingesta atómica e idempotente**, screening puro + endpoints de lectura |
| 2 | **Simulador CLI** (genera las series que SPC necesita), **núcleo SPC puro con tests golden**, endpoints SPC, frontend (resumen, series, carta de control) |
| 3 | Frontend restante, deploy (Render + Neon + Vercel), datos demo con anomalías, README con badges + GIF + diagrama, ADRs · **pipeline AWS (SAM) al final: se recorta primero si hay atraso** |

> Orden de fases y criterio de recorte: ver `03-automation-workflows.md` §4–§5. Los lotes de TerraPlan son escasos (pocas campañas): **no alcanzan** la línea base de 20 puntos, por eso las series SPC de la demo salen del simulador (sitios `SIM-…`), no de datos reales.

## 2. Stack

| Capa | Tecnología | Nota |
|---|---|---|
| Lenguaje | **Python ≥ 3.13** (gestionado por `uv`) | Verificar con `uv run python --version` |
| Framework | **FastAPI** + Uvicorn | Async de punta a punta |
| Validación | **Pydantic v2** + `pydantic-settings` | Modelos camelCase en el borde (ver §5) |
| BD | **PostgreSQL 16+** (Neon free), **esquema `aquametric`** (nunca `public`) | `numeric`, `timestamptz`. TerraPlan vive en `public`: así no hay colisión si algún día se fusionan las BD |
| ORM | **SQLAlchemy 2.0 (async, tipado `Mapped[]`)** + `asyncpg` + **Alembic** | Sin `create_all` fuera de tests |
| Estadística | `numpy` (núcleo SPC), `scipy` (cuando haga falta), `pandas` solo en simulador/análisis exploratorio | El núcleo SPC es **puro** (sin I/O) |
| Auth | **Solo API key** (`X-API-Key`, `hmac.compare_digest`) en endpoints de escritura. Lectura pública. **Sin JWT, sin usuarios, sin roles** | AquaMetric no tiene login; la UI es pública y de solo lectura con datos demo |
| AWS | **S3** (aterrizaje), **Lambda** (procesador + tick de simulador), **EventBridge Scheduler**, **SAM** (IaC), `boto3` | Región `us-east-1` (ADR). Tests con `moto` (no LocalStack) |
| Tests | `pytest`, `pytest-asyncio`, `httpx.AsyncClient`, `testcontainers[postgres]`, `moto`, `hypothesis` (opcional) | |
| Calidad | `ruff` (lint+format), `mypy` | |
| Contenedores | Docker (multi-stage, usuario no root) + Docker Compose | |
| CI | GitHub Actions: ruff, mypy, pytest unit + integration, verificación de `sha256` del catálogo | |
| Frontend | React 19 + Vite + TypeScript + Tailwind 4 + shadcn/ui + shadcn `chart` (Recharts) + TanStack Query/Table + React Router | Ver `04-ui-ux-directives.md` |
| Hosting | API: **Render** (Docker, free) · Postgres: **Neon** · Web: **Vercel** · Pipeline: **AWS** | Free tiers cambian: verificar vigencia antes de desplegar |

### Package managers — REGLAS ESTRICTAS

- **Python: solo `uv`.** Nunca `pip install`, `poetry`, `pipenv` ni `python -m venv` manual. Dependencias: `uv add <pkg>` / `uv add --dev <pkg>`; ejecutar: `uv run <cmd>`. Lockfile: `uv.lock` (commitear).
  Única excepción: `lambdas/*/requirements.txt` **generado** con `uv export` para SAM (no editar a mano; mantener mínimo: stdlib + `boto3`).
- **Frontend: solo `pnpm`.** Nunca `npm`/`yarn`/`npx` (usar `pnpm dlx`, `pnpm exec`).
- Si aparece `requirements.txt` (fuera de `lambdas/`), `poetry.lock`, `Pipfile`, `package-lock.json` o `yarn.lock` ⇒ **reportar y proponer borrarlo**.

### AWS Free Tier — realidad vigente (verificada oct-2026, revalidar al desplegar)

Las cuentas nuevas (desde jul-2025) eligen entre plan **Free** y **Paid**: créditos iniciales (~US$100, hasta ~US$200 con actividades de onboarding). El plan Free **termina a los 6 meses o al agotar créditos** y entonces la cuenta se cierra; **Lambda** mantiene 1 M de requests/mes siempre gratis; **S3 no tiene cuota gratuita permanente** (consume créditos). Consecuencias para este proyecto:

1. **La demo viva NO puede depender del pipeline AWS.** La API (Render + Neon) debe funcionar sola; `POST /api/v1/ingest/observations` es el camino principal y el simulador puede cargar datos directo por CLI.
2. El pipeline AWS se documenta con **IaC reproducible (SAM)**, diagrama, GIF/capturas y un **ADR** que explique el límite de 6 meses.
3. Crear **alarma de presupuesto** el día 1; no habilitar AWS Organizations / Control Tower / IAM Identity Center en el plan Free.
4. Lifecycle de S3: expirar `raw/` y `processed/` a 30 días; `quarantine/` a 90.
5. **Cline nunca ejecuta** `aws ...` ni `sam deploy` que **cree o borre recursos** sin aprobación explícita de Cristóbal en ese mismo turno. `sam validate` y `sam build` son seguros.

## 3. Arquitectura

Monorepo:

```
aquametric/
├─ api/                         # proyecto Python (pyproject.toml, uv.lock)
│  ├─ app/
│  │  ├─ main.py                # create_app(), routers, handlers, middleware
│  │  ├─ core/                  # config.py · db.py · security.py · errors.py · logging.py · clock.py
│  │  ├─ routers/               # sites.py · catalog.py · observations.py · ingest.py
│  │  │                         #   screening.py · spc.py · pipeline.py · health.py
│  │  ├─ services/              # lógica de negocio y orquestación
│  │  ├─ repositories/          # único acceso a BD (SQLAlchemy)
│  │  ├─ models/                # SQLAlchemy, esquema `aquametric` (site · sample · observation · ingest_idempotency · spc_baseline)
│  │  ├─ schemas/               # Pydantic (entrada/salida; base CamelModel)
│  │  ├─ spc/                   # ★ núcleo puro: constants · charts · rules · capability · baseline
│  │  ├─ simulator/             # generador determinista (puro) + CLI
│  │  ├─ catalog/               # loader del catálogo sincronizado
│  │  └─ aws/                   # wrappers finos de boto3 (S3)
│  ├─ alembic/ · alembic.ini
│  └─ tests/                    # unit/ · integration/ · golden/
├─ lambdas/
│  ├─ simulator_tick/handler.py     # EventBridge → genera lote → S3 raw/
│  └─ ingest_processor/handler.py   # S3 ObjectCreated → valida → API de ingesta
├─ infra/template.yaml          # SAM: bucket + lambdas + scheduler + permisos mínimos
├─ web/                         # React (ver 04)
├─ catalog/                     # ★ COPIA de solo lectura desde TerraPlan (NO EDITAR)
├─ docs/                        # design-system.md · architecture.md · glossary.md · adr/ · spc-methods.md
├─ scripts/                     # sync_catalog.py · contrast-check.py
├─ docker-compose.yml · .editorconfig
└─ .clinerules/
```

### Capas (dependencia unidireccional)

`Router → Service → Repository → Model/DB` · `spc/` y `simulator/` son **puros** (los llaman los services).

| Capa | Responsabilidad | Prohibido |
|---|---|---|
| Router | HTTP, validación Pydantic, `Depends`, códigos de estado, OpenAPI | Lógica de negocio, SQL, estadística |
| Service | Reglas de negocio, orquestación, unidad de trabajo (commit) | Leer `Request`, SQL suelto |
| Repository | Consultas SQLAlchemy; recibe `AsyncSession` | `commit()`, reglas de negocio, `HTTPException` |
| `spc/` (puro) | Cálculo de límites, reglas, capacidad | I/O, BD, red, `datetime.now()`, estado global |

### Flujo del pipeline AWS

```
EventBridge Scheduler ──► Lambda simulator_tick ──► S3 raw/sensor/{site}/{yyyy}/{mm}/{dd}/{ts}.json
                                                      │ ObjectCreated
                                                      ▼
                                          Lambda ingest_processor ──► POST /api/v1/ingest/observations (X-API-Key)
                                                      │ error de validación
                                                      ▼
                                              S3 quarantine/…   (éxito ⇒ mover a processed/)
TerraPlan ──────────────────────────────────────────────────────► POST /api/v1/ingest/observations   (directo, sin S3)
```

Decisión: **un solo camino de escritura** (la API) para que validación, normalización e idempotencia vivan en un único lugar.

## 4. Decisiones clave (resumen; detalle en `docs/adr/`)

| ADR | Decisión | Por qué |
|---|---|---|
| 001 | **SPC con límites 3σ estimados en Fase I** (sigma por `MR̄/d2`, no desviación estándar muestral) | Es el método estándar para observaciones individuales; la desviación estándar global infla los límites ante cambios de nivel |
| 002 | Pipeline S3 → Lambda → API | Muestra AWS serverless real con un único camino de escritura |
| 003 | **Datos censurados (`< LOQ`)**: sustitución `LOQ/2` *solo para cálculo*, nunca almacenada; si > 20 % de la serie está censurada ⇒ "no aplicable" | Práctica común, simple y trazable. **Política a validar con el químico** |
| 004 | API en Render y no en Lambda | Demo viva independiente del plan Free de AWS (6 meses) |
| 005 | Catálogo sincronizado desde TerraPlan con `sha256` | Una sola fuente de verdad entre ambos proyectos |
| 006 | PostgreSQL simple (sin TimescaleDB) con índice `(site_id, parameter_code, analyzed_at)` | Volumen de portafolio; Neon free no requiere extensiones extra |
| 007 | Región AWS `us-east-1` | Mayor disponibilidad de servicios en el plan Free; latencia irrelevante para batch |
| 008 | **Esquema PostgreSQL `aquametric`** + Alembic con `version_table_schema="aquametric"` | Evita colisiones con TerraPlan (`public`) y deja abierta una fusión futura de BD |
| 009 | **Ingesta atómica** (lote válido completo o nada) + idempotencia en dos niveles | TerraPlan reintenta con backoff; un 4xx claro es más fácil de operar que una aceptación parcial |
| 010 | **Screening referencial, no dictamen de cumplimiento** | El D.S. 53/2014 evalúa percentiles sobre ventanas de 3 años (según el catálogo de TerraPlan; **validar con el químico**): una observación aislada no puede declararse "cumple" |
| 011 | **Sin JWT ni usuarios**; API key para escribir, lectura pública | Servicio de portafolio con datos demo; menos superficie y menos código |

### 4.1 Núcleo SPC (la pieza que más pesa en el portafolio)

- **Fase I (línea base):** primeras `n ≥ 20` observaciones válidas (`qcFlag = ok`, no censuradas o dentro de la política) por `(site, parameter)`. Se calculan y **persisten** los límites de control; son reproducibles (guardar rango de datos, método, versión).
- **Fase II (monitoreo):** observaciones nuevas se evalúan contra límites congelados.
- **Carta I-MR (individuales):** `CL = x̄`; `UCL/LCL = x̄ ± 2.66·MR̄` (2.66 = 3/d2, d2 = 1.128 para n = 2). Carta MR: `CL = MR̄`, `UCL = 3.267·MR̄` (D4 para n = 2), `LCL = 0`.
- **Carta X̄-R (subgrupos n = 2…10)** con constantes `A2`, `D3`, `D4` de tabla estándar en `spc/constants.py`, **cada una verificada por test contra valores de libro**.
- **Reglas** (códigos de UI ↔ estándar): `R1` = 1 punto más allá de 3σ (Nelson 1) · `R2` = 9 consecutivos del mismo lado de CL (Nelson 2) · `R3` = 6 consecutivos crecientes/decrecientes (Nelson 3) · `R4` = 2 de 3 más allá de 2σ, mismo lado (Nelson 5) · `R5` = 4 de 5 más allá de 1σ, mismo lado (Nelson 6).
- **Capacidad** (`Cp`, `Cpk`): solo con límite(s) normativo(s) **validados** y proceso en control; informar `n` y advertir supuesto de normalidad. Opción `transform = log10` para parámetros sesgados (turbidez, coliformes…).
- **Límites de control ≠ límites normativos ≠ LOQ.** En código y UI llevan nombres y estilos distintos (`control_limits`, `spec_limits`, `loq`). Nunca un `limits` ambiguo.

## 5. Catálogo y esquemas compartidos con TerraPlan (CONTRATO)

**Fuente de verdad:** `/catalog` en el repo de **TerraPlan**. Aquí existe una **copia de solo lectura** sincronizada con `scripts/sync_catalog.py` (`--from-path ../terraplan/catalog` o `--from-url …`) y verificada por `sha256` en CI. **No editar `catalog/` a mano.** Para cambiar algo: modificarlo en TerraPlan, versionar (`catalog.meta.json`), sincronizar aquí.

**Convenciones de contrato (idénticas en ambos proyectos):**

- JSON en la API: **camelCase** (Pydantic `CamelModel`). Columnas de BD: **snake_case**; tablas en singular y **dentro del esquema `aquametric`**: `aquametric.site`, `aquametric.sample`, `aquametric.observation`, `aquametric.ingest_idempotency`.
- **Si los campos o códigos del catálogo real difieren de las tablas de esta sección, manda el catálogo real** (`catalog/*.v1.json`, incluye `regulations.v1.json`): reportar la diferencia, no "corregir" el catálogo. Los códigos reales (`PH`, `TURB`, `N_NO3`, `UPH`, `NTU`, `MG_N_L`…) mandan sobre los ejemplos de estas reglas.
- IDs `uuid`. Fechas ISO-8601 **UTC** (con `Z`); rechazar fechas sin zona. Mostrar en `America/Santiago` solo en la UI.
- Unidad canónica por parámetro; **nunca convertir en silencio**: guardar valor + `unitCode` originales y convertir explícitamente con el catálogo.
- Códigos de parámetro/unidad: del catálogo (ej. `PH`, `TURB`, `COND`, `DO`, `TEMP`), nunca escritos a mano.

| Entidad | Campos |
|---|---|
| `Site` | `id`, `code` (único, ej. `RIO-MAIPO-01`), `name`, `waterBodyType` (`river\|lake\|estuary\|groundwater\|effluent\|drinking`), `latitude`, `longitude` (WGS84), `isActive` |
| `Sample` | `id`, `siteId`, `campaignId?`, `matrix`, `collectedAt` (UTC), `labReceivedAt?`, `status` (`collected\|in_transit\|received\|analyzed\|rejected`) |
| `Observation` | `id`, `siteId`, `sampleId?` (null si viene de sensor), `parameterCode`, `value` (number\|null), `unitCode`, `qualifier` (`"<"\|">"\|null`), `loq?`, `method?`, `analyzedAt` (UTC), `qcFlag` (`ok\|suspect\|failed`), `source` (`lab\|field\|sensor`) |
| `Parameter` | `code`, `nameEs`, `category`, `canonicalUnitCode`, `decimals`, `holdingTimeHours?`, `preservation?`, `container?` |
| `Unit` | `code`, `nameEs`, `dimension` (+ factor de conversión a la canónica de su dimensión) |
| `Limit` | `id`, `parameterCode`, `regulationCode` (ej. norma chilena), `context`, `min?`, `max?`, `unitCode`, `status` (`draft\|validated`), `sourceNote` |

- **Censurados:** `value = null` + `qualifier = "<"` + `loq`. Nunca guardar 0 ni LOQ/2.
### Screening (no cumplimiento legal)

- `screen_observation()` es **pura** y devuelve `screeningFlag`: `normal | above_range | below_range | not_evaluable`.
- Se **calcula al leer**, nunca se persiste (así no queda obsoleta al cambiar la versión del catálogo).
- Resolución del límite: por `regulationCode` + `context` explícitos (parámetros de consulta). Es `not_evaluable` si: hay ambigüedad, el límite está en `draft`, o la observación es censurada / sin valor.
- **Prohibido** en el MVP: dictamen de cumplimiento, percentiles P95/P5, ventanas de 3 años, y cualquier texto de UI que diga "Cumple" o "Excede". La política la valida el químico colaborador.
- Los límites `draft` se muestran como "Pendiente de validación". Capacidad (Cp/Cpk) solo con límites `validated`. No inventar valores normativos.
- **Antes de implementar el screening:** leer el catálogo real y documentar en un ADR el mapeo por defecto sitio → regulación/contexto.

### Contrato de ingesta — `POST /api/v1/ingest/observations`

- Auth: `X-API-Key` (`hmac.compare_digest`); falta o inválida ⇒ `401 UNAUTHORIZED`. Header `Idempotency-Key` **obligatorio** (TerraPlan envía el sha256 del lote).
- Cuerpo: `{ catalogVersion, site, samples[], observations[] }`. Tope: 5 000 observaciones por lote.
- **Lote atómico:** se valida **todo** antes de escribir; cualquier fila inválida ⇒ `4xx problem+json` y **no se guarda nada** (una sola transacción). No hay aceptación parcial ni `rejected[]`.
- Validaciones:
  - `catalogVersion` con major distinto del local ⇒ `409 CATALOG_VERSION_MISMATCH`.
  - `parameterCode` inexistente ⇒ `400 UNKNOWN_PARAMETER`.
  - `unitCode` inexistente o incompatible con la dimensión del parámetro ⇒ `400 UNIT_MISMATCH`.
  - `sampleId` de una observación debe existir en `samples[]` del mismo lote o ya estar almacenada ⇒ si no, `400 VALIDATION_ERROR`.
  - Fechas sin zona, `qualifier`/`value` incoherentes (`value` null sin `qualifier`) ⇒ `400 VALIDATION_ERROR`.
- **Idempotencia en dos niveles:**
  1. `aquametric.ingest_idempotency(key, payload_hash, response, received_at, status)`: misma key + mismo hash ⇒ `200` con **la respuesta guardada**, sin reprocesar; misma key + hash distinto ⇒ `409 IDEMPOTENCY_KEY_REUSE`. La key se registra **en la misma transacción** que los datos (si el lote falla, la key no queda registrada).
  2. Clave natural en `observation` (`siteId+parameterCode+analyzedAt+sampleId+source`) con `ON CONFLICT DO NOTHING`.
- Upserts: `site` por `id` (si el `code` ya existe con otro `id` ⇒ `409 CONFLICT`); `samples` por `id` actualizando `status` y `labReceivedAt` (TerraPlan puede republicar); `observations` solo inserción.
- Respuesta `200`: `{ accepted, duplicates }`.

## 6. Rutas locales, puertos y variables

| Elemento | Valor |
|---|---|
| Ruta del repo | `{{RUTA_LOCAL_AQUAMETRIC}}` ← **completar** |
| Ruta del proyecto hermano | `{{RUTA_LOCAL_TERRAPLAN}}` ← **completar** |
| API | `http://localhost:8000` (OpenAPI `/docs`, prefijo `/api/v1`) |
| Web | `http://localhost:5174` |
| PostgreSQL | `localhost:5433` (contenedor `aquametric-pg`) |

(TerraPlan usa 3000 / 5173 / 5432 / 27017 para correr ambos a la vez.)

Variables (`api/.env`, **nunca** commitear; mantener `api/.env.example` al día): `ENV`, `DATABASE_URL` (`postgresql+asyncpg://…`), `INGEST_API_KEY`, `CORS_ORIGINS`, `CATALOG_DIR`, `AWS_REGION`, `S3_BUCKET`, `BASELINE_MIN_POINTS` (def. 20), `CENSORED_MAX_FRACTION` (def. 0.2).

## 7. Comandos

```bash
# Instalación y desarrollo (desde api/)
uv sync
docker compose up -d postgres
uv run alembic upgrade head
uv run uvicorn app.main:app --reload --port 8000
pnpm --filter web dev                 # (desde la raíz; web usa pnpm)

# Calidad
uv run ruff check .
uv run ruff format --check .
uv run mypy app
uv run pytest -q -m "not integration"          # unit (rápido, sin Docker)
uv run pytest -q -m integration                # Testcontainers (requiere Docker)
uv run pytest -q --tb=short -x                 # todo, corta en la primera falla
uv run python -m py_compile <archivo.py>       # chequeo de sintaxis barato

# Migraciones
uv run alembic revision --autogenerate -m "<message>"   # SIEMPRE revisar el archivo generado
uv run alembic upgrade head
uv run alembic downgrade -1

# Datos
uv run python -m app.simulator.run --site SIM-RIO-MAIPO-01 --days 30 --seed 42   # sitios SIM-*; inserta vía IngestService
uv run python ../scripts/sync_catalog.py --from-path ../../terraplan/catalog

# Frontend
pnpm --filter web typecheck && pnpm --filter web lint && pnpm --filter web build

# AWS (infra/) — validate/build son seguros; deploy requiere aprobación explícita
sam validate --template infra/template.yaml
sam build --template infra/template.yaml
```

Si la shell falla con `&&`, ejecutar los comandos por separado.

## 8. Documentación obligatoria (portafolio)

- `README.md` profesional: badges (CI, cobertura, licencia, deploy), GIF/capturas (dashboard y carta de control), demo en vivo, **diagrama de arquitectura (Mermaid)** incluyendo el pipeline AWS, quickstart, decisiones, enlace a TerraPlan.
- `docs/adr/NNN-titulo.md` por cada decisión de §4 (Contexto · Decisión · Consecuencias).
- `docs/spc-methods.md`: fórmulas, constantes, reglas y supuestos **en lenguaje claro** (para el químico y para reclutadores).
- `docs/glossary.md`: glosario simple (SPC, UCL/LCL, LOQ, Fase I/II, etc.).
- Recordatorios de cuándo actualizarlos: ver `03-automation-workflows.md`.

## 9. Diseño visual

El design system está en **`docs/design-system.md`** (tokens, tipografía, componentes, gráficos, a11y). Reglas de aplicación en `04-ui-ux-directives.md`. **Leer el documento solo al crear o modificar UI**, y solo la sección necesaria.

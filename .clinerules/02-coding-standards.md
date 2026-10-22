# 02 · Estándares de código — AquaMetric (FastAPI + React)

## 1. Idioma

| Qué | Idioma |
|---|---|
| Respuestas a Cristóbal (chat) | **Español** |
| Identificadores (variables, funciones, clases, módulos, rutas API, columnas) | **Inglés** |
| Comentarios y docstrings | Inglés, solo el *porqué* (y fórmulas en docstrings de `spc/`) |
| Mensajes de commit | **Inglés**, Conventional Commits |
| Textos visibles al usuario (UI, `detail` de errores) | **Español claro (es-CL)** |
| README, ADRs, `docs/spc-methods.md` | Español; términos técnicos en inglés |
| OpenAPI (`summary`/`description`) | Inglés |

## 2. Naming

| Elemento | Convención | Ejemplo |
|---|---|---|
| Módulos y paquetes Python (`.py`, carpetas) | `snake_case` | `ingest_service.py` |
| Funciones, variables, métodos | `snake_case` | `compute_control_limits` |
| Clases, excepciones, Pydantic, modelos ORM, `StrEnum` | `PascalCase` | `ObservationCreate`, `ResourceConflictError` |
| Constantes | `UPPER_SNAKE_CASE` | `D2_N2 = 1.128` |
| Valores de enum string | `snake_case` | `in_transit` |
| Tablas y columnas SQL | `snake_case`, tabla **singular** | `observation.analyzed_at` |
| Propiedades JSON (API) | `camelCase` (vía alias) | `analyzedAt` |
| Rutas HTTP | `kebab-case`, plural, prefijo `/api/v1` | `/api/v1/spc/control-charts` |
| Archivos **no Python** (docs, config, web) | `kebab-case` | `design-system.md`, `control-chart.tsx` |
| Componentes React (símbolo) / hooks | `PascalCase` / `useXxx` | `ControlChart` · `use-control-chart.ts` |
| Booleanos | prefijo `is_/has_/can_` (py) · `is/has/can` (ts) | `is_active` |

> **Nota (desviación consciente del brief):** los `.py` van en `snake_case` y **no** en `kebab-case`, porque un guion en el nombre de módulo rompe `import` (PEP 8). El kebab-case aplica solo a archivos no-Python.

Nombres de módulo por rol: `routers/<resource_plural>.py` · `services/<thing>_service.py` · `repositories/<thing>_repository.py` · `models/<thing>.py` · `schemas/<thing>.py` · tests `tests/{unit,integration}/test_<unit>.py`.

## 3. Python: reglas generales

- **Type hints obligatorios** en toda firma pública; `mypy` limpio. Prohibido `Any` salvo en bordes con terceros (con comentario). `X | None` (no `Optional`). `from __future__ import annotations` no necesario en 3.13.
- `ruff` es la autoridad de estilo: `line-length = 100`, reglas `E,F,I,UP,B,SIM,ASYNC,S` (bandit básico), `ruff format`.
- Imports absolutos desde `app.` (ordenados por `ruff`); sin `import *`.
- Funciones ≤ 50 líneas, preferir funciones pequeñas y puras. Dataclasses `frozen=True, slots=True` para resultados de dominio.
- `async def` solo con I/O real. **Nunca** bloquear el event loop: trabajo CPU > ~50 ms (cálculos SPC grandes) ⇒ `await anyio.to_thread.run_sync(...)`.
- Sin estado global mutable. Dependencias por `Depends` o parámetros.
- Tiempo: siempre `datetime` **aware en UTC**; inyectar `Clock` (`core/clock.py`), prohibido `datetime.now()` en servicios/`spc/`. `zoneinfo.ZoneInfo("America/Santiago")` solo para mostrar.

## 4. Pydantic (v2) y contratos

- Base común `CamelModel` en `schemas/base.py`:

```python
class CamelModel(BaseModel):
    model_config = ConfigDict(
        alias_generator=to_camel, populate_by_name=True, from_attributes=True,
    )
```

- Modelos de **entrada**: `ConfigDict(extra="forbid")`; sufijos `Create`, `Update`, `Query`. De **salida**: sufijo `Read`/`Response`. Un esquema por contrato; nunca devolver modelos ORM.
- `StrEnum` para dominios cerrados (`QcFlag`, `WaterBodyType`, `SampleStatus`, `ObsSource`).
- Fechas: tipo `AwareDatetime` (rechaza fechas sin zona); normalizar a UTC en el validador.
- Validar contra el catálogo con validadores/`field_validator` que consultan `CatalogService` (código de parámetro y unidad existentes; `unitCode` compatible con la dimensión del parámetro). Nada de strings libres.
- Paginación estándar: `page` (≥1), `page_size` (1–100, def. 50) → `{ data, meta: { page, pageSize, total } }`. Series largas: `max_points` (downsampling en servidor).
- Números: `float` en API/estadística; `Numeric(18, 6)` en BD; decimales de **presentación** por parámetro, desde el catálogo.

## 5. Routers

- Delgados (≤ 15 líneas por endpoint): validar → llamar al service → devolver esquema.
- Cada `APIRouter(prefix=..., tags=[...])`; cada endpoint con `response_model`, `status_code`, `summary` y `responses={...}` para errores documentados.
- Dependencias con alias `Annotated`: `SessionDep`, `IngestKeyDep` (valida `X-API-Key`).
- **Sin usuarios ni JWT.** Regla de acceso: todo endpoint que **escribe** (`POST /ingest/*`, `POST /spc/baseline`, carga del simulador) exige `IngestKeyDep`; los `GET` son públicos y de solo lectura. Un endpoint nuevo que escriba sin `IngestKeyDep` es un bug.
- Versionado por prefijo (`/api/v1`). Cambios incompatibles ⇒ nueva versión + ADR.
- OpenAPI es parte del producto: cuidar nombres, ejemplos (`json_schema_extra`) y descripciones.

## 6. Services y repositories

- **Service:** reglas de negocio, orquestación, **unidad de trabajo** (`async with session.begin():` o commit en el service). Lanza errores de dominio.
- **Repository:** consultas con `select()` de SQLAlchemy 2.0; recibe `AsyncSession`; **nunca** hace `commit()`. Sin SQL por f-string (solo parámetros ligados). Evitar N+1 (`selectinload`/`joinedload`).
- Idempotencia de ingesta en dos niveles (ver `01` §5): tabla `ingest_idempotency` (misma transacción que los datos) + `INSERT … ON CONFLICT DO NOTHING` (`postgresql.insert(...).on_conflict_do_nothing(...)`) con conteo por `RETURNING`.
- **Validar todo el lote antes de escribir** (catálogo, unidades, referencias) y escribir en **una sola transacción**: o entra todo o no entra nada.
- Una sola ruta de escritura de observaciones: `IngestService`. El simulador, TerraPlan y la Lambda pasan por ahí.
- `screen_observation()` se invoca **al leer** (service de lectura), nunca al escribir.

## 7. SPC y simulador (código puro)

- `app/spc/` y `app/simulator/` **sin I/O**, sin `datetime.now()`, sin acceso a BD/red. Entradas: arrays `numpy` / tipos simples. Salidas: dataclasses inmutables.
- Cada constante estadística (`d2`, `D3`, `D4`, `A2`) con comentario de fuente y **test contra valor de libro**. Cero números mágicos.
- Docstring con **fórmula** y supuestos en cada función pública (p. ej. `UCL = x̄ + 2.66·MR̄`).
- Estimar sigma con `MR̄/d2` (individuales) o `R̄/d2` (subgrupos); **no** `np.std` global para límites de control.
- Manejo explícito de `NaN`/censurados/`n` insuficiente ⇒ lanzar `InsufficientDataError` (no devolver resultados engañosos). `ddof` siempre explícito.
- Nombres inequívocos: `control_limits`, `spec_limits`, `loq`. Prohibido un `limits` genérico.
- Simulador determinista: `numpy.random.Generator(PCG64(seed))`; mismo `seed` ⇒ mismos datos. Modelo base: AR(1) + ruido de sensor + eventos inyectables (`shift`, `spike`, `drift`, `dropout`, `censored`) declarados en un `ScenarioConfig`.

## 8. Errores

- Excepciones de dominio propias (`class DomainError(Exception)` con `code`, `status`, `detail_es`). Un **único** conjunto de handlers (`core/errors.py`) los traduce a **RFC 9457 `application/problem+json`**, con **la misma forma que TerraPlan**:

```json
{ "type": "about:blank", "title": "Insufficient data", "status": 422,
  "code": "INSUFFICIENT_DATA", "detail": "Se requieren al menos 20 observaciones para la línea base (hay 12).",
  "requestId": "…", "errors": [] }
```

- Códigos estables (mantener tabla): `VALIDATION_ERROR` 400 · `UNKNOWN_PARAMETER` 400 · `UNIT_MISMATCH` 400 · `UNAUTHORIZED` 401 · `NOT_FOUND` 404 · `CONFLICT` 409 · `CATALOG_VERSION_MISMATCH` 409 · `IDEMPOTENCY_KEY_REUSE` 409 · `INSUFFICIENT_DATA` 422 · `UPSTREAM_UNAVAILABLE` 502 · `INTERNAL` 500. (`FORBIDDEN` no se usa: no hay roles.)
- `RequestValidationError` de FastAPI → `VALIDATION_ERROR` con lista `errors[]` (campo, mensaje) y status **400** (se sobreescribe el 422 por defecto de FastAPI para ser consistente con TerraPlan). El 422 queda reservado para errores semánticos de análisis (`INSUFFICIENT_DATA`: línea base con n < 20, etc.).
- `detail` en español claro; **nunca** stack traces, SQL ni secretos. 500 ⇒ log completo + `requestId`, respuesta genérica.
- Prohibido `except Exception: pass` y `except:` desnudo. Capturar lo específico y registrar.

## 9. Base de datos

- Modelos SQLAlchemy 2.0 tipados (`Mapped[...] = mapped_column(...)`). PK `uuid` (`server_default=gen_random_uuid()`). `DateTime(timezone=True)` siempre.
- Alembic: `revision --autogenerate` + **revisión manual obligatoria** del archivo. No editar migraciones aplicadas. Nunca `Base.metadata.create_all()` fuera de tests.
- Constraints en la BD: `UNIQUE` (idempotencia), `CHECK` (enums, `qualifier`), FKs, índice compuesto `(site_id, parameter_code, analyzed_at)`.
- **Esquema `aquametric`** para todas las tablas: `MetaData(schema="aquametric")` en la `Base`; Alembic con `version_table_schema="aquametric"` e `include_schemas=True`; la migración inicial hace `CREATE SCHEMA IF NOT EXISTS aquametric`. Nada en `public`. Mismos nombres de tabla/columna que TerraPlan para `site`, `sample`, `observation` (convención compartida), pero en su propio esquema.
- `ingest_idempotency(key PK, payload_hash, response jsonb, received_at, status)`.
- Seeds idempotentes (`scripts/` o comando de CLI).

## 10. Seguridad, config y logging

- `pydantic-settings` (`core/config.py`); la app **falla al arrancar** si falta una variable crítica. Secretos solo por env.
- **Sin JWT ni hash de contraseñas.** Escritura: `X-API-Key` con `hmac.compare_digest`. Lectura pública: devolver solo datos demo/de laboratorio ya publicados, nunca secretos ni configuración interna. CORS por allowlist, sin `*`. Limitar tamaño de cuerpo en ingesta (tope 5 000 observaciones).
- Logging JSON a stdout (módulo `logging`), `requestId` por request (middleware) propagado a logs y a errores. No loguear secretos ni payloads completos.
- Dependencias: no agregar ninguna sin justificarla en una línea; fijar versión con `uv add`.

## 11. Lambdas (`lambdas/`)

- Handler delgado: parsear evento → validar → llamar → mover objeto (`processed/` o `quarantine/`). Idempotente (mismo objeto dos veces ⇒ mismo resultado).
- Sin secretos en código; configuración por variables de entorno de la función (`API_URL`, `API_KEY`). Para el secreto usar **SSM Parameter Store (parámetro estándar, sin costo)** o variable de entorno cifrada; **no** AWS Secrets Manager (tiene costo).
- Dependencias mínimas: stdlib + `boto3`. Logs estructurados con `request_id` de Lambda. Timeout explícito (≤ 30 s) y memoria mínima suficiente.
- Permisos IAM de **mínimo privilegio** en `infra/template.yaml` (solo el bucket y prefijos necesarios).

## 12. Tests (priorizar MVP sobre cobertura)

Prioridad (en este orden; parar cuando se cumpla el plazo):

1. **`spc/` con tests golden:** datasets con resultados conocidos (ejemplo de libro / calculado de forma independiente y documentado en `tests/golden/README.md`); constantes `d2/D3/D4/A2`; cada regla R1–R5 con casos positivo y negativo.
2. **Ingesta** (integración): lote OK ⇒ 200; mismo lote 2× ⇒ `accepted=0, duplicates=N` (respuesta guardada); misma key con payload distinto ⇒ 409 `IDEMPOTENCY_KEY_REUSE`; `catalogVersion` incompatible ⇒ 409; `parameterCode`/`unitCode` desconocido ⇒ 400 **y nada guardado** (atomicidad); `sampleId` inexistente ⇒ 400; API key inválida ⇒ 401; censurados bien guardados.
3. **Simulador:** determinismo por `seed` + eventos inyectados detectados por SPC.
4. **Screening** (unit, con límites del catálogo real) y **acceso** (e2e rápido): escritura sin API key ⇒ 401; `GET` sin credenciales ⇒ 200.
5. Lambdas con `moto` (S3) y API falsa.

Reglas: `pytest` + `pytest-asyncio` (`asyncio_mode = "auto"`); integración marcada `@pytest.mark.integration` (Testcontainers Postgres); nombres `test_<unidad>_<comportamiento>`; Arrange-Act-Assert; sin `sleep`; sin `skip/xfail` commiteados sin motivo; proveedores AWS siempre falsos (`moto`). Metas orientativas: `spc/` ≥ 90 %, global ≥ 65 %.

## 13. Frontend (TypeScript/React) — reglas de código

- `strict: true`; **prohibido `any`**. Alias `@/`. Estructura por *feature*: `web/src/features/<feature>/{components,hooks,api,types}`; compartido: `components/ui` (shadcn), `components/domain`, `lib`.
- Datos remotos con **TanStack Query**; tablas con **TanStack Table**; formularios con react-hook-form + zod (esquemas reflejan los de Pydantic).
- Un único `lib/api-client.ts` (maneja `problem+json` y refresh). Tipos del API en `types/` (idealmente generados desde OpenAPI con `openapi-typescript`).
- Gráficos solo con shadcn `chart`/Recharts, colores por tokens CSS; datos pesados ya **downsampleados** por el API.
- Estilos: solo clases Tailwind con tokens (ver `04-ui-ux-directives.md`).
- Formato de fechas/números únicamente vía `lib/format.ts` (es-CL, `America/Santiago`, decimales del catálogo).

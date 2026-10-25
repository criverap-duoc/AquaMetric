# ADR-009: Ingesta atómica e idempotencia en dos niveles

- **Estado**: aceptado
- **Fecha**: 2026-10-24
- **Contexto**: ver `.clinerules/01-project-context.md` §5 (contrato de ingesta) y §4 (ADR-009)
- **Decisores**: Cristóbal Vera (químico + dev)

## Contexto

TerraPlan publica lotes de laboratorio y reintenta con backoff ante cualquier fallo de red. Eso
implica dos problemas distintos que se suelen confundir:

1. **Atomicidad**: un lote de 500 observaciones donde falla una fila. ¿Se guardan las 499? Si sí,
   el emisor no sabe qué quedó y no puede reintentar sin duplicar; el analista ve una serie con
   un hueco que nadie declaró. La aceptación parcial obliga a inventar un `rejected[]` y a
   explicar al usuario un estado intermedio que nadie quiere mantener.
2. **Duplicación**: el mismo lote llega dos veces (reintento, doble clic del operador, Lambda que
   se ejecuta dos veces). Sin idempotencia, la serie se duplica y la carta de control se
   distorsiona —el peor resultado posible para una herramienta estadística.

Además existe un caso del mundo real: TerraPlan **republica** un lote para corregir el estado de
una muestra (`received` → `analyzed`), sin que las observaciones cambien.

## Decisión

**Validar todo antes de escribir, y escribir en una sola transacción.** Cualquier fila inválida
(código de parámetro desconocido, unidad incompatible, `sampleId` inexistente, fecha sin zona,
`qualifier` incoherente) produce un `4xx` `application/problem+json` y **no se guarda nada**. No
hay aceptación parcial ni `rejected[]`.

**Idempotencia en dos niveles, complementarios:**

1. **Por petición** — `aquametric.ingest_idempotency(key PK, payload_hash, response jsonb,
   received_at, status)`:
   - misma `Idempotency-Key` + mismo `payload_hash` ⇒ `200` con **la respuesta guardada**, sin
     reprocesar (misma `accepted`/`duplicates` que la primera vez);
   - misma key + hash distinto ⇒ `409 IDEMPOTENCY_KEY_REUSE`;
   - la fila de idempotencia se escribe **en la misma transacción** que los datos: si el lote
     falla, la key no queda registrada y el reintento es legítimo.
2. **Por fila** — `UNIQUE (site_id, parameter_code, analyzed_at, sample_id, source)`
   (`uq_obs_natural_key`) + `INSERT ... ON CONFLICT DO NOTHING`, contando lo insertado por
   `RETURNING`. Protege incluso si el emisor olvida la key o cambia el orden del lote.

**Upserts acotados:** `site` por `id` (si el `code` ya existe con otro `id` ⇒ `409 CONFLICT`),
`samples` por `id` actualizando `status` y `lab_received_at`; `observations` **solo inserción**
(una observación corregida se publica como nueva fila con otro `analyzed_at`, no se reescribe la
historia).

**Respuesta `200`**: `{ accepted, duplicates }`, suficiente para que el emisor sepa qué pasó sin
leer la base.

## Consecuencias

**Positivas**
- El emisor razona con dos estados: entró completo o no entró. Reintentar siempre es seguro.
- La serie nunca queda con huecos silenciosos ni duplicada; el SPC confía en sus datos.
- La ventana de la transacción es corta y la comprobación de catálogo ocurre antes de abrirla.

**Negativas / riesgos**
- Un lote atómico exige tener *todo* el catálogo y las referencias coherentes; es más estricto
  que aceptar lo bueno y descartar lo malo. Deliberado: un 4xx claro es mejor que un estado
  parcial que nadie audita.
- La tabla `ingest_idempotency` crece sin límite; requiere una política de purga (p. ej. 90 días)
  que hoy no está implementada. **Deuda conocida.**
- El `UNIQUE` natural incluye `sample_id` y `source`: dos lecturas del mismo instante con distinto
  origen son filas distintas a propósito.

## Referencias

- `.clinerules/01-project-context.md` §5 (contrato), `.clinerules/02-coding-standards.md` §6
- `api/app/services/ingest_service.py`, `api/app/repositories/`
- `api/app/models/ingest_idempotency.py`, `api/app/models/observation.py` (`uq_obs_natural_key`)
- `docs/adr/005-catalog-sync-sha256.md`, `docs/adr/002-aws-pipeline-s3-lambda-api.md`

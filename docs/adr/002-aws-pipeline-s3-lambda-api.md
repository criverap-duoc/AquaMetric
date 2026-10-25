# ADR-002: Pipeline AWS S3 → Lambda → API como camino único de escritura

- **Estado**: aceptado
- **Fecha**: 2026-10-24
- **Contexto**: ver `.clinerules/01-project-context.md` §3 y §4
- **Decisores**: Cristóbal Vera (químico + dev)

## Contexto

AquaMetric recibe observaciones de dos orígenes distintos: TerraPlan (lotes de laboratorio de
campañas de muestreo) y un simulador de sensores (lecturas continuas). El segundo justifica un
pipeline serverless en AWS: hay que generar un lote periódico, dejarlo en un lugar durable y
procesarlo sin tener un servidor encendido esperando. El portafolio además necesita mostrar AWS
real, no solo una caja de PostgreSQL.

Lo que **no** puede pasar es que la escritura tenga dos caminos. Si la Lambda insertara en
PostgreSQL además de la API, la validación contra el catálogo, la normalización de unidades y la
idempotencia existirían dos veces y con el tiempo divergirían. Un lote mal formado debe
descubrirse en el borde, no en el consumidor.

## Decisión

Un **solo camino de escritura**: `POST /api/v1/ingest/observations`. TerraPlan, el simulador CLI
y la Lambda de ingesta terminan todos en ese endpoint, con `X-API-Key` e `Idempotency-Key`.

```
EventBridge Scheduler (cron)
  └─► Lambda simulator_tick ──► S3 raw/sensor/{site}/{yyyy}/{mm}/{dd}/{ts}.json
                                    │ s3:ObjectCreated
                                    ▼
                        Lambda ingest_processor ──► POST /api/v1/ingest/observations
                                    │                (X-API-Key, Idempotency-Key = sha256)
                                    ├─ 2xx ► copiar a processed/
                                    └─ 4xx ► copiar a quarantine/ (+ motivo en el log)

TerraPlan ──────────────────────────────────► POST /api/v1/ingest/observations
Simulador CLI ──────────────────────────────► POST /api/v1/ingest/observations
```

Reglas asociadas:

1. Validación de catálogo, normalización de unidades, screening e idempotencia viven **solo** en
   la API (`IngestService`). Las Lambdas son delgadas: mueven objetos y llaman al endpoint.
2. Las Lambdas no conocen PostgreSQL ni reciben `DATABASE_URL`. Su rol IAM se limita al bucket y
   a los prefijos que realmente usan (mínimo privilegio).
3. Tests de las Lambdas con `moto` (S3 falso) y una API falsa; `boto3` es la única dependencia
   empaquetada. Nada de LocalStack: suma Docker al camino de test sin dar fidelidad extra.
4. Toda la infraestructura va como código en `infra/template.yaml` (SAM), con lifecycle de S3.

## Consecuencias

**Positivas**
- Una sola definición de «lote válido»: lo que entra, entró validado; lo que no, no dejó rastro.
- El camino crítico queda en Python tipado y testeado, no repartido entre handlers.
- El pipeline es reemplazable (otra fuente, otro broker) sin tocar el dominio, y el dominio no
  sabe que AWS existe.

**Negativas / riesgos**
- Hay latencia de batch: el sensor escribe en S3 y la observación aparece en la API segundos
  después. Para datos de calidad de agua (frecuencia horaria) es irrelevante.
- Un 4xx deja el objeto en `quarantine/` y requiere revisión humana; no se reintenta en bucle a
  propósito, porque un error de contrato no se arregla reintentando.
- El pipeline AWS es **lo primero que se recorta** si hay atraso (`.clinerules/03` §5), y la demo
  viva no depende de él (ADR-004).

## Referencias

- `.clinerules/01-project-context.md` §3 (flujo del pipeline) y §4 (ADR-002)
- `.clinerules/03-automation-workflows.md` §4–§5 (orden de construcción y recorte)
- `docs/adr/004-render-not-lambda.md`, `docs/adr/009-atomic-ingest.md`
- `infra/template.yaml`, `lambdas/simulator_tick/handler.py`, `lambdas/ingest_processor/handler.py`
- `docs/architecture.md` §Pipeline AWS

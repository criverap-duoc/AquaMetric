# ADR-004: API en Render, no en Lambda

- **Estado**: aceptado
- **Fecha**: 2026-10-24
- **Contexto**: ver `.clinerules/01-project-context.md` §2 (AWS Free Tier) y §4 (ADR-004)
- **Decisores**: Cristóbal Vera (químico + dev)

## Contexto

La demo viva es el entregable que un reclutador abre en el navegador: si no responde, el resto
del trabajo no se ve. La opción «todo en AWS» (API en Lambda + Function URL) parecía coherente
con el pipeline, pero el plan gratuito cambió en julio de 2025: las cuentas nuevas eligen entre
plan Free y Paid, el Free **termina a los 6 meses o al agotar créditos** y entonces la cuenta se
cierra; Lambda conserva 1 M de requests/mes gratis, pero **S3 no tiene cuota gratuita
permanente** y consume créditos. Una demo que caduca a los 6 meses no sirve de portafolio, y una
que consume créditos sin avisar es peor.

Hay además un motivo técnico: FastAPI en Lambda exige un adaptador (Mangum) y cold starts de
varios segundos, mientras que la primera petición de un reclutador debe sentirse instantánea.

## Decisión

La API corre en **Render** (Docker, plan free), la base en **Neon** (PostgreSQL free) y el
frontend en **Vercel**. AWS queda **solo** para el pipeline del ADR-002, documentado con SAM y
desmontable sin afectar la demo.

- `render.yaml` declara el build con contexto en la raíz (`dockerfilePath: ./api/Dockerfile`,
  `dockerContext: .`, ver ADR-016) y las variables no secretas.
- La demo se alimenta del simulador por CLI (Fase C) y de los pocos lotes de TerraPlan: no
  necesita S3 ni EventBridge para tener datos.
- El pipeline AWS se presenta con IaC reproducible, diagrama y este ADR que explica el límite de
  6 meses; si se recorta (`.clinerules/03` §5), la demo sigue igual.

## Consecuencias

**Positivas**
- La demo no caduca con el plan Free de AWS ni depende de créditos.
- Despliegue simple: push a `main`, imagen Docker, migraciones Alembic y `GET /health` verde.
- Sin adaptador ASGI: la app es exactamente la misma que se testea en local.

**Negativas / riesgos**
- **Cold start de Render free (~30 s)** tras 15 minutos de inactividad. Mitigación: monitoreo
  externo (UptimeRobot) contra `/api/v1/health` cada pocos minutos; el README lo advierte.
- **Conexiones de Neon free**: el pooler limita conexiones simultáneas, así que el engine usa
  pool pequeño y `pool_pre_ping`; no hay margen para cargas concurrentes altas.
- Todo el relato AWS queda en el pipeline y no en la API: hay que explicarlo bien en
  `docs/architecture.md` para que no parezca que AWS no se usó.
- Si Render cambia su plan free, hay que migrar (Fly.io, Railway o un contenedor propio).

## Referencias

- `.clinerules/01-project-context.md` §2 (AWS Free Tier, verificado oct-2026) y §4 (ADR-004)
- `docs/adr/002-aws-pipeline-s3-lambda-api.md`, `docs/adr/016-docker-build-context.md`
- `render.yaml`, `api/Dockerfile`, `docs/architecture.md` §Despliegue

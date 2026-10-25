# ADR-007: Región AWS `us-east-1` para todos los servicios

- **Estado**: aceptado
- **Fecha**: 2026-10-24
- **Contexto**: ver `.clinerules/01-project-context.md` §2 y §4 (ADR-007)
- **Decisores**: Cristóbal Vera (químico + dev)

## Contexto

El pipeline del ADR-002 usa cuatro servicios (EventBridge Scheduler, dos Lambdas, S3) que deben
vivir en la misma región: un bucket en una región y una Lambda en otra obliga a transferencia
entre regiones (latencia y, sobre todo, costo) y complica los permisos. Hay que elegir una.

Los criterios reales son: (1) que el plan Free tenga disponibilidad amplia de los servicios
necesarios, (2) que el costo y la latencia sean irrelevantes para un proceso por lotes, (3) que
el portafolio use lo que un reclutador reconoce como estándar. La cercanía a Chile
(`sa-east-1`, São Paulo) sería la respuesta intuitiva, pero solo se justifica con usuarios
interactivos: aquí el consumidor es una Lambda que llama a un endpoint en Render, no una persona
esperando.

## Decisión

Todos los recursos AWS del proyecto viven en **`us-east-1`**: bucket S3, ambas Lambdas,
EventBridge Scheduler y el stack SAM. La región se fija como parámetro en
`infra/template.yaml` y como `AWS_REGION` en la configuración de la API y de las Lambdas, para
que no dependa del perfil local de quien despliega.

## Consecuencias

**Positivas**
- Mayor disponibilidad de servicios y de tipos de instancia en el plan Free; menos sorpresas al
  desplegar.
- Permisos y lifecycle en una sola región: un bucket, un stack, un lugar donde mirar.
- La latencia Santiago ⇄ `us-east-1` (≈150–200 ms) es invisible en un proceso horario.

**Negativas / riesgos**
- Si algún día hay lecturas de sensores con requisito de baja latencia desde Chile, habría que
  mover el pipeline a `sa-east-1` (ADR nuevo) o empujar por la API directa.
- Los datos «viven» en EE. UU.: para datos demo no es un problema, pero un despliegue con datos
  reales de terceros exige revisar el aspecto legal antes de reutilizar este diseño.
- `us-east-1` concentra más incidentes históricos que otras regiones; el pipeline es batch y
  reintentable, así que el riesgo aceptado es bajo.

## Referencias

- `.clinerules/01-project-context.md` §2 (AWS) y §4 (ADR-007)
- `docs/adr/002-aws-pipeline-s3-lambda-api.md`
- `infra/template.yaml`, `api/.env.example` (`AWS_REGION`)

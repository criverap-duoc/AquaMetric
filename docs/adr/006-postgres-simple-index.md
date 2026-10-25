# ADR-006: PostgreSQL estándar, sin TimescaleDB ni PostGIS

- **Estado**: aceptado
- **Fecha**: 2026-10-24
- **Contexto**: ver `.clinerules/01-project-context.md` §2 (BD) y §4 (ADR-006)
- **Decisores**: Cristóbal Vera (químico + dev)

## Contexto

AquaMetric guarda series temporales de calidad de agua: observaciones indexadas por sitio,
parámetro y fecha. La reacción automática es pedir una base de series temporales
(TimescaleDB) o extensiones geoespaciales (PostGIS), y ambas traen costos concretos: Neon free
no las habilita por defecto, complican la migración, agregan dependencias al contenedor local y
alejan el proyecto del objetivo del MVP, que es estadística correcta y no infraestructura
exótica.

El volumen real del portafolio es modesto: cuatro sitios simulados × cinco parámetros × 30–90
días de lecturas horarias, más unos pocos lotes de laboratorio. Estamos en el orden de decenas
de miles de filas, no de miles de millones. Con ese volumen, un índice compuesto bien elegido
resuelve las consultas del SPC y del dashboard.

## Decisión

PostgreSQL 16 estándar (Neon en producción, contenedor en local), sin extensiones de series
temporales ni geoespaciales.

- **Índice compuesto** `ix_obs_site_param_time (site_id, parameter_code, analyzed_at)`: cubre el
  patrón de acceso dominante —«la serie de este sitio y este parámetro en este rango de fechas»—
  que es exactamente lo que alimenta la carta de control y el cálculo de línea base.
- **Sin particionamiento** en el MVP. Se documenta la ruta (particionar `observation` por rango
  de `analyzed_at`) como plan de crecimiento, no como trabajo pendiente.
- **Downsampling en el servidor** (`max_points` en los endpoints de lectura): las series largas
  se reducen antes de salir por HTTP, así el navegador nunca recibe 50 000 puntos.
- Coordenadas de `site` como `numeric` simples (WGS84); no hay consultas espaciales en el MVP.

## Consecuencias

**Positivas**
- Compatible con Neon free sin trámites: la demo no depende de extensiones que el plan no
  garantiza.
- Migraciones Alembic simples y reversibles; `docker compose up -d postgres` basta en local.
- El índice compuesto hace que la consulta más caliente del SPC sea un *index scan*.

**Negativas / riesgos**
- Si el simulador creciera a millones de filas (varios sitios × frecuencia de minutos × años),
  habría que particionar o reconsiderar TimescaleDB; a ese volumen también habría que revisar el
  diseño de la carta (no solo la BD).
- `numeric(18, 6)` en vez de `double precision` cuesta algo de velocidad; se elige por exactitud
  en datos analíticos y porque el volumen no lo nota.
- El downsampling es una decisión de servidor con parámetros: si la UI pide demasiados puntos,
  el gráfico se degrada sin avisar (la UI debe mostrar `n` y el rango).

## Referencias

- `.clinerules/01-project-context.md` §2 y §4 (ADR-006)
- `.clinerules/02-coding-standards.md` §9 (índices y constraints)
- `api/app/models/observation.py` (`ix_obs_site_param_time`, `uq_obs_natural_key`)
- `docs/adr/008-aquametric-schema.md`

# ADR-008: Esquema PostgreSQL `aquametric` (nunca `public`)

- **Estado**: aceptado
- **Fecha**: 2026-10-24
- **Contexto**: ver `.clinerules/01-project-context.md` §5 y `.clinerules/02-coding-standards.md` §9
- **Decisores**: Cristóbal Vera (químico + dev)

## Contexto

AquaMetric y TerraPlan comparten catálogo y convenciones, y es plausible que algún día compartan
una misma base de datos (o que alguien apunte las dos aplicaciones al mismo PostgreSQL de
desarrollo). Si AquaMetric creara `site`, `sample` y `observation` en `public`, cualquier intento
de fusión chocaría con las tablas de TerraPlan: nombres idénticos, estructuras distintas,
migraciones que se pisan. Ese conflicto se descubre tarde y se arregla mal.

Al mismo tiempo, la convención de nombres de tablas y columnas **debe** seguir siendo la misma
que la de TerraPlan (`site`, `sample`, `observation`): el contrato de ingesta y de lectura se
entiende entre ambos proyectos porque las entidades tienen los mismos nombres. Cambiar de
esquema es barato; cambiar de nombres, no.

## Decisión

Todas las tablas de AquaMetric viven en el esquema **`aquametric`**, nunca en `public`:

- `api/app/core/db.py`: `SCHEMA = "aquametric"` y una única `MetaData(schema=SCHEMA,
  naming_convention=NAMING_CONVENTION)`. El esquema es propiedad del `MetaData`, no de cada
  mapper: no hay forma de «olvidarlo» en una tabla nueva.
- La `naming_convention` genera nombres predecibles (`pk_site`, `fk_observation_site_id`,
  `ck_...`), con excepciones explícitas donde el nombre generado superaría los 63 bytes de
  PostgreSQL (`uq_obs_natural_key`).
- `api/alembic/env.py`: `include_schemas=True`, `version_table_schema="aquametric"` y
  `include_name` filtrando por esquema, así que autogenerate **no ve** lo de `public` (ni lo
  borra) y la tabla de versiones de Alembic también vive en `aquametric`.
- La migración inicial ejecuta `CREATE SCHEMA IF NOT EXISTS aquametric` antes de crear tablas; es
  idempotente y deja el esquema listo en una base recién creada.
- Nombres de tabla y columna idénticos a TerraPlan (`site`, `sample`, `observation`) para que una
  fusión futura solo requiera un `search_path` o un prefijo, no una reescritura.

## Consecuencias

**Positivas**
- Cero colisión con TerraPlan en una base compartida; la fusión futura sigue siendo posible.
- Migraciones acotadas: `alembic downgrade` sobre la migración inicial borra el esquema completo
  de AquaMetric sin tocar `public` (ADR-013).
- Inspeccionar la base es inequívoco: `SET search_path TO aquametric` y todo lo visible es
  nuestro.

**Negativas / riesgos**
- Ninguna herramienta externa puede asumir `public`: conexiones manuales, `psql` y clientes
  gráficos necesitan el `search_path` o nombres calificados.
- Si un día se decide fusionar bases, la unicidad de `code` en `site` y los `CHECK` deben
  revisarse por colisión semántica (mismo nombre, distinto dominio).
- Los tests de integración crean el esquema en cada contenedor: un poco más lento, y por eso
  hay un `conftest.py` compartido en `tests/integration/`.

## Referencias

- `.clinerules/01-project-context.md` §5, `.clinerules/02-coding-standards.md` §9
- `docs/adr/013-alembic-downgrade-note.md`, `docs/adr/006-postgres-simple-index.md`
- `api/app/core/db.py`, `api/alembic/env.py`, `api/alembic/versions/`
- `docs/architecture.md` §Base de datos

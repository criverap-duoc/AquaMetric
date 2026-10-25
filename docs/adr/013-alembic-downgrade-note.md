# ADR 013 · `alembic downgrade` destruye datos: el reset de desarrollo es un script

- **Estado:** aceptado
- **Fecha:** 2026-10-24
- **Fase:** A-4 (ingesta atómica; cierre de la Fase A)
- **Relacionado:** ADR-008 (esquema `aquametric` + Alembic con `version_table_schema`)

## 1. Contexto

La migración inicial (`20261024_0001_initial_schema.py`) se escribió con un `downgrade` que
**elimina el esquema completo**:

```python
op.drop_table("site", schema=SCHEMA)
...
op.execute("DROP SCHEMA IF EXISTS aquametric CASCADE")
op.execute("CREATE SCHEMA IF NOT EXISTS aquametric")
op.execute("CREATE TABLE aquametric.alembic_version (...)")
op.execute("INSERT INTO aquametric.alembic_version (version_num) VALUES ('20261024_0001')")
```

Es la traducción literal de «deshacer la migración inicial»: no existe una versión anterior a la
que volver, así que el único estado previo posible es *sin esquema*. El `CREATE SCHEMA` y la fila
de `alembic_version` se reponen porque Alembic borra su fila **después** de que la función
retorna, en la misma transacción; sin ellos el `downgrade` fallaría con `UndefinedTable`.

La consecuencia práctica no es obvia para quien lo ejecuta por primera vez:

- `uv run alembic downgrade -1` **borra todas las filas** de `site`, `sample`, `observation`,
  `ingest_idempotency` y `spc_baseline` (es el `DROP SCHEMA … CASCADE`).
- La fila de `alembic_version` también desaparece, y con ella la noción de «base migrada».
- Volver a `head` deja el esquema **vacío**: no es un rollback de un cambio, es un borrado.

Un `downgrade` silencioso y destructivo, ejecutado contra Neon por reflejo, arruinaría la demo y
los datos de TerraPlan que se hubieran cargado.

## 2. Decisión

1. **`alembic downgrade` queda reservado a migraciones futuras incrementales**, donde sí existe un
   estado anterior razonable. Sobre la migración inicial se usa solo para verificar que la
   reversibilidad no rompe Alembic, y siempre contra una base desechable (Testcontainers o
   `scripts/db_reset.sh`).
2. **El «reset» de desarrollo es un script explícito**, no un flag de Alembic:
   `scripts/db_reset.sh` lee `DATABASE_URL` y `ENV` de `api/.env`, se niega a correr si `ENV` es
   `staging` o `production`, ejecuta
   `DROP SCHEMA IF EXISTS aquametric CASCADE; CREATE SCHEMA aquametric;` con `psql` y termina con
   `uv run alembic upgrade head`. El nombre del script dice lo que hace; el de Alembic, no.
3. **La documentación lo repite en un solo lugar**: este ADR. Los README y los scripts apuntan
   aquí en vez de reexplicarlo.
4. **Las migraciones aplicadas no se editan** (02 §9). Si un `downgrade` resulta destructivo por
   diseño, se documenta; no se «arregla» reescribiendo la migración ya aplicada.

## 3. Consecuencias

- **A favor:** nadie pierde datos por escribir `downgrade -1` creyendo que deshace el último
  cambio; el reset es reproducible y auditable (`psql` + `alembic`, nada oculto).
- **A favor:** la reversibilidad sigue probada: `upgrade head` → `downgrade -1` → `upgrade head`
  funciona sobre una base limpia, que es la condición que interesa verificar en CI.
- **En contra:** un `downgrade` de la migración inicial nunca es seguro en una base con datos; el
  script es obligatorio para reiniciar. Se asume: es una decisión de operación, no un defecto.
- **En contra:** `scripts/db_reset.sh` requiere `psql` en el equipo (no basta Docker Desktop). Se
  documenta en el encabezado del script; la alternativa es `docker compose exec postgres psql`.

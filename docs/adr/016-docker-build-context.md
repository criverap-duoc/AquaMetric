# ADR-016: Contexto de build en la raíz (la imagen lleva el catálogo)

- **Estado:** aceptado
- **Fecha:** 2026-10-24
- **Fase:** A-5 (detección de la deuda H1-A4 al cerrar la ingesta)
- **Relacionado:** ADR-005 (catálogo sincronizado), ADR-004 (API en Render)

## 1. Contexto

`api/Dockerfile` se construía con `api/` como contexto y copiaba solo `pyproject.toml`,
`uv.lock`, `app/`, `alembic/` y `alembic.ini`. El catálogo vive en `catalog/`, **fuera** de
`api/`, así que la imagen arrancaba sin él: `load_catalog()` lanzaba `CatalogLoadError` en la
primera lectura del catálogo y la API respondía 500 en `/catalog/*` y en `/screening/evaluate`
(hallazgo H1-A4). En local nunca se notó porque `CATALOG_DIR` resuelve a la raíz del repo.

`docker build api/` no puede copiar un directorio hermano del contexto: no hay acceso a él.

## 2. Decisión

1. El **contexto de build es la raíz del repositorio** y el Dockerfile se invoca explícitamente:
   `docker build -f api/Dockerfile -t aquametric-api:test .`
2. El Dockerfile copia con prefijo (`COPY api/app ./app`, `COPY api/alembic ./alembic`, …) y
   añade `COPY catalog ./catalog`, con `ENV CATALOG_DIR=/app/catalog` para no depender del `cwd`.
3. `.dockerignore` vive en la **raíz** (el de `api/` deja de aplicarse): excluye `.git`, `docs/`,
   `web/`, `api/tests/`, cachés y `.env`.
4. `render.yaml` (raíz) declara `dockerfilePath: ./api/Dockerfile` y `dockerContext: .`, de modo
   que el despliegue no depende de recordar el comando.

## 3. Consecuencias

- **Positivas:** la imagen es autocontenida y verificable en un paso
  (`docker run --rm aquametric-api:test ls /app/catalog`); el catálogo entra como copia de solo
  lectura, sin que la app pueda escribirlo; el build local y el de Render usan el mismo contexto.
- **Costos:** el contexto abarca el repo entero, por lo que `.dockerignore` pasa a ser
  obligatorio (sin él se enviarían `.venv/` y `web/node_modules/`); cualquier comando de build
  que asuma `api/` como contexto queda inválido.
- **Regla:** un cambio futuro que agregue un directorio consumido en runtime (por ejemplo
  `docs/`) debe agregarse como `COPY` **y** documentarse aquí.

## 4. Verificación

1. `docker build -f api/Dockerfile -t aquametric-api:test .` desde la raíz.
2. `docker run --rm aquametric-api:test ls /app/catalog` lista los 5 archivos del catálogo.
3. `GET /api/v1/catalog/meta` responde 200 con la versión del catálogo (no 500).

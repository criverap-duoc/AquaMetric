# Despliegue de AquaMetric

Guía paso a paso para publicar la demo viva: **API en Render** (Docker), **PostgreSQL en Neon** y
**web en Vercel**. Las decisiones están en [ADR-004](adr/004-render-not-lambda.md) (Render y no
Lambda) y [ADR-016](adr/016-docker-build-context.md) (contexto de build). El pipeline AWS
(ADR-002) es opcional y no hace falta para esta guía.

| Servicio | Qué corre | Plan gratuito |
|---|---|---|
| Neon | PostgreSQL 16, esquema `aquametric` | 0,5 GB, compute que se suspende por inactividad |
| Render | imagen Docker de `api/` (`render.yaml`) | web service free: se duerme tras 15 min sin tráfico |
| Vercel | build estático de `web/` (React + Vite) | hobby, builds ilimitados en repos públicos |

## Prerrequisitos

1. Cuenta en **Neon**, **Render** y **Vercel** (las tres aceptan login con GitHub).
2. El repositorio en GitHub, con `main` como rama de despliegue, y el CI
   ([`.github/workflows/ci.yml`](../.github/workflows/ci.yml)) en verde: si el CI está rojo, el
   despliegue no aporta información nueva.
3. Una **`INGEST_API_KEY`** de al menos 16 caracteres (`Settings` la exige y la API no arranca sin
   ella). `render.yaml` la genera sola; si prefieres generarla tú:

   ```bash
   openssl rand -hex 32
   ```

4. `uv` instalado en tu máquina (solo para las migraciones y el seed) y Git Bash o WSL si usas
   Windows.
5. `catalog/` sincronizado: la imagen copia esa carpeta dentro de `/app/catalog` y, sin ella, toda
   lectura del catálogo responde 500 (hallazgo H1-A4).

Variables de producción, **sin valores** (ningún secreto se commitea):

| Variable | Dónde se define | Ejemplo de forma |
|---|---|---|
| `DATABASE_URL` | panel de Render (y en tu shell para migrar) | `postgresql+asyncpg://…?ssl=require` |
| `INGEST_API_KEY` | generada por `render.yaml` (se lee del panel) | 64 hex |
| `CORS_ORIGINS` | panel de Render | `https://aquametric.vercel.app` |
| `CATALOG_DIR` | fija en `render.yaml` | `/app/catalog` |
| `VITE_API_URL` | panel de Vercel | `https://aquametric-api.onrender.com` |

## 1. Neon (base de datos)

1. Crea un proyecto nuevo, región **us-east-2** o la más cercana al servicio de Render, y una base
   `aquametric`. Neon crea el rol dueño automáticamente.
2. Copia la cadena de conexión (*Connect* → *Connection string*). Viene como
   `postgresql://USUARIO:CLAVE@ep-…neon.tech/aquametric?sslmode=require`.
3. Conviértela a la forma que usa SQLAlchemy + asyncpg:

   ```text
   postgresql+asyncpg://USUARIO:CLAVE@ep-…neon.tech/aquametric?ssl=require
   ```

   - `postgresql://` → `postgresql+asyncpg://` (el driver async que usa la API).
   - `sslmode=require` → `ssl=require`, y elimina `channel_binding=…`: **asyncpg no acepta
     `sslmode`** y la API falla al conectar con `invalid DSN`.
   - Usa el host **directo** (el que **no** lleva `-pooler`). El pooler de Neon es PgBouncer en
     modo transacción y asyncpg usa sentencias preparadas, que ese modo no soporta; con una sola
     instancia de API no hace falta pooler.

4. Guarda esa cadena: es la `DATABASE_URL` de Render y la de las migraciones. **No** la pegas en
   el repositorio.

## 2. Render (API)

1. *New* → **Blueprint** → conecta GitHub → elige este repositorio. Render detecta `render.yaml`
   y propone el servicio `aquametric-api` (runtime Docker, `dockerfilePath: ./api/Dockerfile`,
   `dockerContext: .`, health check `/api/v1/health`).
2. Antes de aplicar, pega las variables que `render.yaml` marca como `sync: false`:
   - `DATABASE_URL`: la cadena del paso 1.
   - `CORS_ORIGINS`: por ahora `http://localhost:5174`; el paso 5 la corrige.
   `INGEST_API_KEY` se genera sola: cópiala del panel (*Environment*) porque la necesitas para el
   seed y para TerraPlan.
3. Aplica. El primer build tarda **unos 8 minutos** (compila la imagen multi-stage con `uv`).
4. Verifica cuando el servicio esté *Live*:

   ```bash
   curl -fsS https://aquametric-api.onrender.com/api/v1/health
   ```

   Debe responder 200 con `{"status":"ok",…}`. Ojo: **`/health` es solo liveness** — no toca la
   base de datos, así que un 200 todavía no prueba que Neon esté conectada ni migrada (paso 3).

## 3. Migraciones (esquema `aquametric`)

Render **no** corre migraciones al desplegar (el comando previo al deploy es de los planes pagos),
así que se aplican desde tu máquina cada vez que cambia `api/alembic/versions/`.

```bash
cd api
export DATABASE_URL='postgresql+asyncpg://USUARIO:CLAVE@ep-…neon.tech/aquametric?ssl=require'
export INGEST_API_KEY='<la misma que generó Render>'
uv run alembic upgrade head
```

En PowerShell:

```powershell
$env:DATABASE_URL = "postgresql+asyncpg://USUARIO:CLAVE@ep-…neon.tech/aquametric?ssl=require"
$env:INGEST_API_KEY = "<la misma que generó Render>"
uv run alembic upgrade head
```

Por qué hacen falta **las dos** variables: `alembic/env.py` toma la URL de `Settings` (ADR-008), y
`Settings` valida todas sus variables, no solo la de la base. Las variables exportadas en la shell
tienen prioridad sobre `api/.env`, así que puedes migrar sin tocar tu configuración local.

La primera migración crea el esquema `aquametric` (nunca `public`) y las cinco tablas de la fase A.
Para comprobar que la base responde y está migrada —esto sí toca la base:

```bash
curl -fsS "https://aquametric-api.onrender.com/api/v1/sites?page=1&pageSize=1"
```

`{"data":[],…}` con 200 es lo esperado antes del seed. Un 500 aquí significa migraciones
pendientes o `DATABASE_URL` mal formada (paso 8).

## 4. Vercel (web)

1. *Add New* → **Project** → importa el mismo repositorio.
2. **Root Directory: `web`**. El repositorio es un monorepo pnpm (`pnpm-workspace.yaml` y
   `pnpm-lock.yaml` en la raíz): Vercel instala desde la raíz y construye solo la app.
3. Framework **Vite** (se detecta). No cambies el build: `web/vercel.json` ya fija
   `pnpm build`, `dist` y el *rewrite* de todo a `index.html`, que es lo que necesita React Router
   para que `/control` y `/screening` no devuelvan 404 al recargar.
4. *Environment Variables* → `VITE_API_URL = https://aquametric-api.onrender.com` (sin `/` final y
   sin `/api/v1`: el cliente agrega el prefijo). Márcala para *Production*; si quieres probar
   *Preview*, agrégala también ahí.
5. **Deploy**. Abre la URL: el dashboard tiene que mostrar datos, no un error de red. Si la consola
   del navegador dice «blocked by CORS policy», falta el paso 5.

`VITE_*` se **incrusta en el bundle al construir**: si después cambias la URL de la API hay que
volver a desplegar, no basta con guardar la variable.

## 5. CORS (que la web pueda llamar a la API)

1. Copia el dominio que te dio Vercel, exacto y **sin barra final** (`https://aquametric.vercel.app`).
2. En Render → `aquametric-api` → *Environment* → `CORS_ORIGINS` = ese dominio (varios, separados
   por coma; nunca `*`). Guarda: Render redespliega solo.
3. Verifica que la cabecera viaja:

   ```bash
   curl -sS -D - -o /dev/null -H "Origin: https://aquametric.vercel.app" \
     https://aquametric-api.onrender.com/api/v1/health | grep -i access-control-allow-origin
   ```

   Tiene que aparecer el dominio. Si el navegador bloquea, la petición ni siquiera llega a los logs
   de Render: es la señal de que el origen no está en la lista.

## 6. Datos demo (simulador contra producción)

El seed escribe por `POST /api/v1/ingest/observations` con `X-API-Key` e `Idempotency-Key`, el
mismo camino que usa TerraPlan (ADR-009): **no** necesita `DATABASE_URL`, solo la URL de la API y
la key de producción.

```bash
cd aquametric-fastapi
cp api/.env.example api/.env      # el script exige que exista; su contenido local no se usa
API_URL=https://aquametric-api.onrender.com \
INGEST_API_KEY='<la que generó Render>' \
bash scripts/seed_demo.sh
```

Qué hace: 4 sitios `SIM-…` × 5 parámetros (`PH`, `DO`, `COND`, `TURB`, `N_NO3`) × 30 días de
lecturas horarias ≈ **14 400 observaciones** en 20 lotes, con una firma de anomalías distinta por
parámetro (la tabla está en el README, sección *Datos demo*).

- Es **determinista**: misma semilla y misma ventana ⇒ mismo gráfico. Para congelar las capturas del
  README: `DEMO_START=2026-10-01T00:00:00Z`.
- Es **idempotente**: repetirlo el mismo día devuelve `aceptadas 0 · duplicadas 720` por lote (la
  respuesta guardada), no filas nuevas. Si el primer lote falla por *cold start*, vuelve a correrlo.
- Verificación: `curl -fsS "https://aquametric-api.onrender.com/api/v1/sites?page=1&pageSize=1"`
  informa `"total":4`; en la web, el dashboard tiene alertas reales (al menos una serie con R1).

## 7. UptimeRobot (mitigar el cold start)

1. *Add New Monitor* → tipo **HTTP(s)** → URL
   `https://aquametric-api.onrender.com/api/v1/health`.
2. Intervalo **5 minutos** (el mínimo del plan gratuito) y, si quieres señal más fina, *keyword
   monitoring* con `"status":"ok"`.
3. Alerta a tu correo. El monitor no solo avisa si la demo se cae: mantiene despierta la instancia
   free de Render, que se duerme tras 15 minutos sin tráfico (ADR-004).

## 8. Problemas frecuentes

| Síntoma | Causa | Arreglo |
|---|---|---|
| La primera petición tarda 30–60 s | cold start del plan free de Render | esperar; el monitor del paso 7 lo evita casi siempre |
| 500 con `relation "aquametric.site" does not exist` | faltan migraciones | paso 3 |
| La API no arranca: `ingest_api_key` «at least 16 characters» | key vacía o corta | regenerar `INGEST_API_KEY` en Render |
| 500 en todas las lecturas del catálogo | la imagen se construyó sin `catalog/` (`CATALOG_DIR` mal) | desplegar desde la raíz del repo; en local, `docker run --rm aquametric-api:test ls /app/catalog` |
| «blocked by CORS policy» en el navegador | falta el dominio de Vercel en `CORS_ORIGINS` | paso 5 (sin `/` final) |
| `invalid DSN: invalid connection option "sslmode"` | cadena de Neon sin convertir | `?ssl=require`, paso 1.3 |
| `TimeoutError` o `Connection refused` contra Neon | host `-pooler`, o compute suspendido por inactividad | host directo y reintentar (Neon despierta en ~1 s) |
| `alembic` falla con `ingest_api_key` «Field required» | `Settings` valida todas sus variables | exportar `INGEST_API_KEY` antes de migrar (paso 3) |
| Vercel: `vite: not found` al construir | el workspace pnpm no se resolvió | *Root Directory* = `web` y `pnpm-lock.yaml` en la raíz |
| La web carga pero no muestra datos | `VITE_API_URL` se incrusta al construir | corregir la variable y **redeploy** |

## Verificación final

- [ ] `GET /api/v1/health` responde 200.
- [ ] `GET /api/v1/sites` responde 200 con 4 sitios y `GET /api/v1/spc/control-charts` devuelve
      series (prueba de que la base está migrada y con datos).
- [ ] La web en Vercel muestra el dashboard con alertas y la carta de control sin errores de CORS.
- [ ] Un `POST /api/v1/ingest/observations` sin `X-API-Key` responde 401 (la escritura sigue
      cerrada; el resto es lectura pública, ADR-011).
- [ ] UptimeRobot en *Up* y badge del CI en verde.
- [ ] Capturas/GIF del dashboard y de la carta de control en el README.

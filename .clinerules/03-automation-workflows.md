# 03 · Flujos de automatización — AquaMetric

> Objetivo: **máximo avance con mínimo gasto de tokens y verificación proporcional al riesgo.**
> Proyecto greenfield de 2–3 semanas: priorizar *MVP desplegado* (con estadística correcta) sobre perfección.

## 1. Economía de tokens (REGLAS DURAS)

1. **Reportar diff stat, no archivos.** Tras editar: archivo + `+N/−M` + 1 línea del porqué. Jamás pegar archivos completos en el chat.
2. **Máximo 2 edits por archivo por turno.** Si hace falta más, reescribir la función/clase completa en un solo edit.
3. **Leer con rango** (`offset/limit`) o `grep` para ubicar. No releer un archivo recién editado.
4. **No listar el repo** (`ls -R`, `tree`) ni abrir `.venv`, `node_modules`, `__pycache__`, `.aws-sam`, lockfiles. Usar rutas conocidas (ver `01`).
5. **Un plan corto** (≤ 5 viñetas) antes de tareas de > 3 archivos; no re-planificar a cada paso.
6. **Respuesta final ≤ 8 líneas:** qué se hizo · nivel de verificación y resultado · qué queda.
7. **No correr la suite completa tras cada edit** (ver niveles). Nada "por si acaso".
8. No repetir contexto de `.clinerules` ni explicar código obvio.
9. **Preguntar solo si bloquea**; agrupar dudas en un mensaje (máx. 3, con opción recomendada).
10. Salida de comandos acotada: `pytest -q --tb=short -x`, `ruff check --output-format=concise`, `| tail -30`. Reportar solo fallas.
11. **Python es sensible a la indentación:** si un edit rompe la sintaxis o la indentación, **revertir** (`git checkout -- <archivo>`) y **rehacer la función/clase completa** en un solo bloque. Nunca apilar parches sobre un error.
12. Datasets/volcados: nunca imprimirlos; mostrar `head(5)` o conteos.

## 2. Niveles de verificación (proporcionales al riesgo)

| Nivel | Cuándo | Qué correr | Costo |
|---|---|---|---|
| **N0** | Docs/markdown/comentarios/CSS puro | Nada (revisión del diff) | ≈ 0 |
| **N1** | Cambios locales sin lógica nueva: schemas, constantes, router delgado, estilos, copy, componente presentacional | `uv run python -m py_compile <archivos>` + `uv run ruff check <archivos>` + `uv run ruff format --check <archivos>` · en web: `pnpm --filter web typecheck` | bajo |
| **N2** | Lógica: service, repository, `spc/`, simulador, hook con efectos | N1 + `uv run mypy app` + `uv run pytest -q -x -m "not integration" -k <patrón>` | medio |
| **N3** | Migraciones, ingesta, auth, config, Docker, catálogo, Lambdas/SAM; antes de commit de feature/PR | `ruff check` + `ruff format --check` + `mypy app` + `pytest -q` (unit **e** integration) + `docker build` · si cambió Alembic: `upgrade head` → `downgrade -1` → `upgrade head` en BD limpia · si cambió `infra/`/`lambdas/`: `sam validate` + `sam build` · web: `typecheck + lint + build` | alto |

Reglas de selección:
- **Duda entre dos niveles → el menor**, salvo que toque: `alembic/`, `routers/ingest.py`, `services/ingest_service.py`, `core/security.py`, `core/config.py`, `catalog/`, `infra/`, `lambdas/`, `docker-compose.yml`. Esos son **N3**.
- **Cualquier cambio en `spc/` ⇒ mínimo N2 incluyendo los tests golden** (un error estadístico silencioso es el peor fallo posible del proyecto).
- Integración (Testcontainers) solo si cambió BD/repositories/ingesta. Si Docker no está disponible: **avisar**, no fingir verificación.
- Frontend: N1 por defecto; N2 si hay lógica; `build` solo en N3.

## 3. Comandos (palabras clave de Cristóbal)

### `verificación post-edit` (automática, tras cada tarea)
1. Determinar nivel (N0–N3). 2. Ejecutar solo lo de ese nivel. 3. Reportar: `Nivel Nx · OK` o `Nivel Nx · FALLA: <1–3 líneas>`. Arreglar solo fallos de la propia edición; lo preexistente se reporta (ver `05`).

### `health check`
Diagnóstico sin modificar nada:
1. `git status -sb`. 2. `docker compose ps` (¿postgres arriba?). 3. `uv run ruff check . --output-format=concise` y `uv run mypy app`. 4. `uv run pytest -q -m "not integration"`. 5. `pnpm --filter web typecheck`. 6. Verificar: `catalog/` coincide con `sha256` de `catalog.meta.json`; `api/.env.example` ↔ variables usadas; sin `requirements.txt` fuera de `lambdas/`; `.env` ignorado.
**Salida:** tabla de ≤ 8 filas `Chequeo · Estado · Nota`. No arreglar; proponer.
(Verificar además: ninguna tabla fuera del esquema `aquametric`; ningún endpoint de escritura sin `IngestKeyDep`.)

### `sync catalog`
1. Ejecutar `uv run python ../scripts/sync_catalog.py --from-path <ruta TerraPlan>/catalog`. 2. Verificar `sha256` y `version`. 3. Reportar `git diff --stat catalog/` + versión anterior → nueva. 4. Si cambió el **major**: avisar (ADR + revisar ingesta). 5. Correr tests de ingesta (N2).

### `clean commit`
1. `git status -sb` + `git diff --stat`. 2. **Verificación mínima** (`05` §5). 3. Revisar basura (print, breakpoint, TODO sin dueño, archivos fuera de lugar, secretos, lockfiles ajenos, `.aws-sam/`). **Reportar, no arreglar sin aprobación.** 4. Proponer **mensaje Conventional Commit en inglés** (`feat(spc): add I-MR control limits`), ≤ 72 caracteres + cuerpo opcional ≤ 3 líneas. 5. Esperar aprobación antes de `git commit`. Un commit = un cambio lógico; añadir archivos por nombre (no `git add .` a ciegas).

**Tipos:** `feat` · `fix` · `refactor` · `test` · `docs` · `chore` · `perf` · `ci` · `build`.
**Scopes:** `auth` · `sites` · `catalog` · `observations` · `ingest` · `screening` · `spc` · `simulator` · `pipeline` · `lambda` · `infra` · `db` · `web` · `docker` · `docs`.

### `cerrar feature`
Checklist (reportar solo pendientes):
1. [ ] Criterio de aceptación cumplido (a mano o por test).
2. [ ] **N3** del área afectada en verde.
3. [ ] Migración revisada y reversible; `catalog/` sincronizado si aplica.
4. [ ] OpenAPI con ejemplos y descripciones (revisar `/docs`).
5. [ ] `api/.env.example` actualizado si hay variables nuevas.
6. [ ] **README:** sección de la feature / tabla de endpoints / badge.
7. [ ] **ADR** si hubo decisión de arquitectura (`docs/adr/NNN-*.md`).
8. [ ] **Diagrama** (`docs/architecture.md`, Mermaid) al día si cambió un flujo (incl. pipeline AWS).
9. [ ] `docs/spc-methods.md` actualizado si cambió un método/regla/constante.
10. [ ] **Glosario** (`docs/glossary.md`) con términos nuevos, en lenguaje simple para el químico.
11. [ ] UI: checklist de `docs/design-system.md` §13 + estados carga/vacío/datos insuficientes/error.
12. [ ] Recordar a Cristóbal: **capturar GIF/pantallazo** (dashboard, carta de control) para el README.
13. [ ] `clean commit` propuesto.

### `cerrar semana`
Resumen (≤ 10 líneas) contra el plan de 3 semanas (`01` §1): hecho · pendiente · riesgo de plazo · **qué recortar**. Actualizar tabla de progreso del README.

### `preparar deploy`
1. Variables de producción listadas (sin valores). 2. `docker build` de `api` OK. 3. `alembic upgrade head` contra Neon. 4. `GET /api/v1/health` OK. 5. CORS apunta al dominio de Vercel. 6. Datos demo cargados (simulador, con anomalías). 7. UptimeRobot a `/health`. 8. **AWS:** `sam validate` + `sam build` OK; **despliegue solo con aprobación**; alarma de presupuesto creada; ADR sobre el límite de 6 meses del plan Free escrito. 9. README con enlace a la demo viva y a TerraPlan. Verificar condiciones vigentes de los free tiers.

## 4. Orden de construcción (greenfield) — rebanadas verticales

Una rebanada completa a la vez, cerrándola con `cerrar feature`:

`migración → model → repository → service/dominio → router + schemas → test (nivel justo) → UI mínima`

Orden de fases (híbrido; **no saltarse la Fase A**):

- **A · Contrato:** (1) scaffold `uv` + Docker + config + `/health` → (2) `sync_catalog.py` con el **catálogo real** de TerraPlan + loader → (3) esquema `aquametric` + modelos/migraciones (`site`, `sample`, `observation`, `ingest_idempotency`) → (4) **ingesta atómica e idempotente** + tests de contrato. *Nada de SPC, simulador, UI ni AWS hasta que A esté en verde.*
- **B · Lectura y screening:** (5) `screen_observation()` puro + tests con límites reales → (6) endpoints de lectura (`sites`, `observations` paginado/downsampling, `catalog/*`, screening).
- **C · Simulador (CLI, sin AWS):** (7) generador determinista + CLI que inserta vía `IngestService`, sitios `SIM-…`.
- **D · SPC:** (8) ★ **núcleo SPC puro + tests golden** → (9) endpoints SPC (línea base, carta, reglas, capacidad).
- **E · UI:** (10) las 7 pantallas de `04`, públicas y de solo lectura, con datos demo.
- **F · Deploy:** (11) Render + Neon + Vercel, README, ADRs.
- **G · Pipeline AWS (SAM):** (12) S3 + 2 Lambdas + scheduler. **Se recorta primero** si hay atraso; la demo viva no depende de esto.

## 5. Guardarraíles de plazo (MVP)

- **Regla de las 8 h:** si una tarea supera ~1 jornada, parar y proponer un recorte (con opciones) antes de seguir.
- Prioridad ante atraso (de lo que más importa a lo primero que se recorta): **ingesta idempotente > SPC correcto > simulador CLI (alimenta SPC y la demo) > dashboard > pipeline AWS (Lambdas) > escenarios extra del simulador > EWMA/CUSUM**.
- No agregar librerías, módulos ni pantallas fuera de `01` §1 sin aprobación.
- "Estadísticamente correcto y desplegado" > "sofisticado y local".

## 6. Rigor estadístico (cuando se toque `spc/`)

- Antes de implementar: confirmar la fórmula en `docs/spc-methods.md` (o añadirla primero).
- Cada resultado nuevo ⇒ al menos un **caso golden** con valor esperado calculado de forma independiente (documentar cómo se obtuvo).
- Si una fórmula, constante o política es dudosa: **no adivinar**; reportar y dejar `NotImplementedError` con TODO con dueño. La política de censurados y los límites normativos los valida el químico.

## 7. Datos demo (para que el portafolio luzca)

Con el simulador (sitios `SIM-…`; **no** usar lotes reales de TerraPlan como demo: son escasos y no alcanzan la línea base de 20 puntos), generar ≥ 30 días × ≥ 4 sitios × ≥ 5 parámetros **con los códigos del catálogo real** (p. ej. `PH`, `TURB`; confirmar los demás) con **escenarios visibles**: 1 *shift* de nivel, 1 *spike*, 1 *drift* lento, 1 tramo de *dropout* y valores *censurados*. Misma `seed` ⇒ mismo demo (reproducible para el GIF del README).

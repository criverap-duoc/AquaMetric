# 05 · Reglas de limpieza — AquaMetric

> Objetivo: repo **siempre presentable** (lo revisa un reclutador) con **cero desperdicio de tokens**.
> Principio: **reportar, no arreglar sin aprobación** todo lo que quede fuera del alcance de la tarea actual.

## 1. Anti-basura (prohibido commitear / dejar en el repo)

| Categoría | Ejemplos |
|---|---|
| Depuración | `print()`, `breakpoint()`, `import pdb`, `console.log`, `debugger` (usar `logging`) |
| Código muerto | Código comentado, imports/variables/funciones sin uso (`ruff F401/F841`), archivos huérfanos |
| Pendientes sin dueño | `TODO` sin formato. Permitido solo: `# TODO(#<issue>): <acción>` |
| Silenciadores | `except Exception: pass`, `except:` desnudo, `# type: ignore` sin código ni motivo, `# noqa` sin regla |
| Tests deshabilitados | `@pytest.mark.skip`/`xfail` sin motivo, `.only` en tests web |
| Artefactos | `.venv/`, `__pycache__/`, `*.pyc`, `.mypy_cache/`, `.pytest_cache/`, `.ruff_cache/`, `.coverage`, `htmlcov/`, `dist/`, `node_modules/`, `.aws-sam/`, `*.zip` de Lambda, `*.log`, `.DS_Store` |
| Secretos | `.env`, claves AWS, `INGEST_API_KEY`, URLs con credenciales (⇒ **detener y avisar**) |
| Gestores ajenos | `requirements.txt` (fuera de `lambdas/`), `poetry.lock`, `Pipfile`, `package-lock.json`, `yarn.lock` |
| Datos | Volcados de BD, CSV/JSON > 1 MB, notebooks con salidas, datos reales de personas |
| Archivos de trabajo | `notes.md`, `temp.*`, `test2.py`, `copy of …`, `*.bak`, `*.orig` |
| Tipos flojos | `Any` injustificado, `any` en TS, `// @ts-ignore` |
| Estilos | Colores hex/oklch sueltos, clases de paleta Tailwind, `style={{…}}` con valores fijos |
| Dependencias | Paquetes agregados sin necesidad, duplicados o no usados |
| Catálogo | Ediciones manuales en `catalog/` (es copia de solo lectura) |
| Relleno | "Lorem ipsum", "foo/bar", "Sitio 1", datos demo sin sentido |

`.gitignore` mínimo: `.venv`, `__pycache__`, `*.pyc`, `.mypy_cache`, `.pytest_cache`, `.ruff_cache`, `.coverage`, `htmlcov`, `.env`, `.env.*` (excepto `.env.example`), `node_modules`, `dist`, `.aws-sam`, `*.log`, `.DS_Store`, `.idea`, `.vscode/*` (excepto `extensions.json` y `settings.json`), `pgdata`.

## 2. Reportar, no arreglar (protocolo)

Si durante una tarea se detecta algo **fuera del alcance** (bug preexistente, deuda, inconsistencia, basura de la sección 1):

1. **No tocarlo.**
2. Reportar al final, **≤ 3 líneas** por hallazgo:
   `⚠ <archivo>:<línea> — <qué es> — Propuesta: <arreglo en 1 frase> (esfuerzo S/M/L)`
3. Agrupar en un único bloque "Hallazgos" (máx. 5; si hay más, resumir por categoría).
4. Esperar aprobación. Excepción (se arregla sin preguntar): errores introducidos **por la propia edición**.
5. **Hallazgos estadísticos** (fórmula/constante/regla dudosa en `spc/`) se reportan **siempre**, con prioridad alta.

## 3. Indentación y formato (estricto — Python es sensible)

| Tipo de archivo | Regla |
|---|---|
| `.py` | **4 espacios**. **Nunca tabs.** `ruff format` es la autoridad (`line-length = 100`) |
| `.ts` `.tsx` `.js` `.json` `.yml` `.yaml` `.css` `.md` `.toml` | **2 espacios** (excepto `pyproject.toml`: seguir el estilo existente) |
| `infra/template.yaml` (SAM/CloudFormation) | 2 espacios; sin tabs; claves en el orden estándar |
| `.sql` / migraciones | Palabras clave en MAYÚSCULAS; statements separados |
| `Dockerfile`, `.sh` | 2 espacios |
| Fin de línea | **LF**. UTF-8. Línea en blanco final |

`.editorconfig` en la raíz con `[*] end_of_line = lf, insert_final_newline = true, trim_trailing_whitespace = true`, `[*.py] indent_style = space, indent_size = 4`, `[*.{ts,tsx,js,json,yml,yaml,css,md}] indent_style = space, indent_size = 2`.

**Reglas especiales para editar Python (evitan la mayoría de roturas):**

1. **Respetar la indentación del archivo.** No reformatear archivos enteros salvo que se pida (diffs enormes = tokens perdidos).
2. En bloques anidados o con decoradores, **reescribir la función o clase completa** en un solo edit; nunca insertar líneas sueltas dentro de un bloque indentado.
3. **Después de CADA edición de `.py`:** `uv run python -m py_compile <archivo>` (barato) y, si el cambio es mayor a unas pocas líneas, `uv run ruff format --check <archivo>`.
4. Si la sintaxis o la indentación quedó rota ⇒ **revertir** (`git checkout -- <archivo>`) y **rehacer el bloque completo**. Jamás encadenar parches sobre un error.
5. Strings multilínea / docstrings: mantener la indentación del bloque que los contiene.
6. YAML/JSON: sin claves duplicadas ni comas colgantes; validar tras editar (`sam validate` para `template.yaml`).

## 4. Tamaño y claridad

- Archivo > 300 líneas o función > 50 líneas ⇒ **reportar** (no refactorizar sin aprobación).
- Un módulo = una responsabilidad. Nada de `utils.py`/`helpers.py` cajón de sastre: nombrar por función (`format_duration.py`).
- Nombres que se expliquen solos; comentarios solo para el *porqué*; fórmulas en docstrings de `spc/`.
- Sin imports circulares; sin imports relativos profundos (usar `app.…` en Python y `@/` en web).

## 5. Verificación mínima ANTES de cada commit

| Si el cambio toca… | Mínimo exigido |
|---|---|
| Solo docs/markdown | Revisión del diff (N0) |
| Schemas / constantes / router delgado / UI presentacional | `py_compile` + `ruff check` + `ruff format --check` (y `typecheck` web) (N1) |
| Lógica (service/repository/`spc/`/simulador/hook) | N1 + `mypy app` + tests del módulo (**`spc/` ⇒ incluir tests golden**) (N2) |
| Alembic, ingesta, auth, config, Docker, catálogo, `lambdas/`, `infra/` | N3 completo (ver `03` §2) |

Además, **siempre**: `git diff --stat` revisado · sin secretos · sin archivos de la sección 1 · `catalog/` intacto salvo `sync catalog` · mensaje Conventional Commit en inglés propuesto y **aprobado** por Cristóbal.

## 6. Higiene de dependencias, config y AWS

- Antes de agregar un paquete: ¿ya existe algo equivalente en el stack? Si no, justificar en 1 línea y fijar versión (`uv add` / `pnpm add`).
- `api/.env.example` siempre sincronizado con las variables reales (sin valores secretos).
- Migraciones: nunca editar una aplicada; nombres descriptivos (`add_observation_unique_idx`).
- **AWS:** nunca credenciales en el repo; no ejecutar `aws`/`sam deploy` que **creen o borren** recursos sin aprobación explícita; permisos IAM de mínimo privilegio; lifecycle de S3 definido en `template.yaml`; alarma de presupuesto documentada en el README.
- Lambdas: si `requirements.txt` cambia, regenerarlo con `uv export`, no editarlo a mano.

## 7. Higiene de documentación (portafolio)

Al cerrar cada feature o semana, verificar y **recordar a Cristóbal**:

- [ ] README actualizado (badges vigentes, tabla de endpoints, quickstart que funciona en limpio).
- [ ] ADR creado/actualizado por cada decisión relevante (incl. límite de 6 meses del plan Free de AWS).
- [ ] Diagrama de arquitectura (Mermaid) al día, con el pipeline AWS.
- [ ] `docs/spc-methods.md` y `docs/glossary.md` al día, en lenguaje simple.
- [ ] GIF/capturas nuevas (dashboard, carta de control) para el README.
- [ ] Enlace cruzado a TerraPlan y a la demo viva.

## 8. Anti-desperdicio (recordatorio final)

- No releer archivos recién editados; no listar directorios completos; no pegar archivos ni datasets en el chat.
- No correr suites completas fuera de N3; no repetir una verificación que ya pasó y no cambió.
- Un hallazgo = una línea. Un cierre de tarea = ≤ 8 líneas.
- Si algo es ambiguo y **no bloquea**, tomar la opción recomendada, decirlo en una línea y seguir.

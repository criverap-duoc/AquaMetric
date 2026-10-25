# ADR-014: Exposición de metadatos del catálogo y guarda de unidades en screening

- **Estado**: aceptado
- **Fecha**: 2026-10-24
- **Contexto**: ver `.clinerules/01-project-context.md` §4 y ADR-005
- **Decisores**: Cristóbal Vera (químico + dev)

## Contexto

Durante la rebanada A-5 (Fase B — screening referencial) aparecieron dos necesidades que no estaban previstas en el diseño original:

1. El endpoint público `GET /api/v1/catalog/meta` debía exponer `version`, `sha256`, `generatedAt`, `status`, `validatedBy` y `validatedAt`. El dataclass `Catalog` (definido en A-2) solo tenía `version`, `sha256` y `generated_at`; faltaban los tres últimos, que son **críticos para la UI** (indicador "Pendiente de validación" cuando `status != "validated"`).

2. El screening de una observación individual comparaba el valor contra un límite del catálogo, pero **no verificaba que la unidad del valor fuera compatible con la unidad del límite**. Ejemplo: un valor en `MG_N_L` (nitrógeno) contra un límite en `MG_L` (masa total) es una comparación inválida que produciría un falso positivo silencioso.

## Decisión

1. **Extender el dataclass `Catalog`** con `status`, `validated_by`, `validated_at` (todos `str | None` salvo `status` que es `str`). El loader los lee de `catalog.meta.json`. El endpoint `/catalog/meta` los expone sin releer el JSON en el router.

2. **Añadir guarda de dimensión** en `screen_observation()`: si la dimensión de `unit_code` del valor no coincide con la dimensión de `unit_code` del límite (usando `Unit.dimension` del catálogo), el resultado es `not_evaluable` con `reason="Unidad incompatible con el límite (dimensión distinta)."`. Esta guarda es **pura** (sin I/O) y complementa la validación de ingesta (que ya rechaza unidades desconocidas).

3. **Exponer `qualityLevel` en `LimitApplied`** (respuesta de `/screening/evaluate`). Sin él, un límite D.S. 53/2014 (que depende de `monitoringAreaCode` + `qualityLevel`) no es reproducible por el usuario final.

## Consecuencias

**Positivas**
- La UI puede mostrar "Pendiente de validación por el químico" de forma fiable sin leer archivos.
- Se elimina una clase entera de falsos positivos por unidades incompatibles.
- Los límites D.S. 53 quedan trazables end-to-end.

**Negativas / riesgos**
- El dataclass `Catalog` ahora depende de `catalog.meta.json` en más campos. Si TerraPlan cambia el esquema de `catalog.meta.json`, hay que actualizar el loader.
- La guarda de dimensión es más estricta que la normativa: la NCh 1.333 permite comparar algunas unidades con factores de conversión (ver `conversionNotes` en `units.v1.json`). Esa conversión explícita queda **fuera del MVP**; se hace `not_evaluable` hasta que exista un ADR específico.

## Referencias

- `.clinerules/01-project-context.md` §4 (tabla de ADRs)
- ADR-005 (sincronización del catálogo)
- ADR-010 (screening no es cumplimiento)
- ADR-012 (screening de observación individual)
- `api/app/catalog/entities.py`, `api/app/screening/screener.py`

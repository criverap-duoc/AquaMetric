# ADR-003: Política de datos censurados (`< LOQ`)

- **Estado**: aceptado, con la política de sustitución **pendiente de la firma del químico**
- **Fecha**: 2026-10-24
- **Contexto**: ver `.clinerules/01-project-context.md` §4 (ADR-003) y §5
- **Decisores**: Cristóbal Vera (químico + dev)

## Contexto

El laboratorio no informa un número cuando la concentración está por debajo del límite de
cuantificación (LOQ): informa `< LOQ`. Eso no es un cero (el cero no existe como resultado) y
tampoco es el LOQ (no se midió hasta ahí). Guardarlo como `0` envenena cualquier estadístico:
arrastra la media hacia abajo, infla artificialmente la variabilidad y puede convertir un sitio
limpio en un sitio «fuera de control».

La tentación habitual es reemplazar por `LOQ/2` en el momento de guardar. Es cómodo y es
irreversible: se pierde el hecho de que no se midió, y cualquier cambio futuro de política exige
rehacer la base. La política de censurados afecta estadística, reportes legales y trazabilidad,
así que la firma el químico, no el programador.

## Decisión

**Almacenamiento (no negociable, ya implementado):**
- `value = NULL`, `qualifier = "<"`, `loq = <número>` y `unit_code` del catálogo. Nunca `0`,
  nunca `LOQ/2`. La base conserva el dato tal como lo entregó el laboratorio.
- `CHECK` en la tabla `observation` (`censored_coherence`): o hay `value` y no hay `qualifier`,
  o hay `qualifier = "<"` con `loq` y no hay `value`. Un estado intermedio se rechaza en la
  ingesta (`400 VALIDATION_ERROR`), no se «arregla» con un valor por defecto.

**Cálculo (solo en memoria):**
- SPC: la sustitución `LOQ/2` ocurre dentro de `app/spc/baseline.py` y no sale de ahí; el
  resultado informa `censored_count` y `censored_fraction` para que la carta pueda explicarlo.
- Si la fracción censurada supera `CENSORED_MAX_FRACTION` (0,2 ⇒ más del 20 %), no se publican
  límites: la serie se declara «datos insuficientes» (`422 INSUFFICIENT_DATA`) porque la
  sustitución ya domina la estadística. Con exactamente 20 % se acepta (umbral estricto `>`).
- Screening: una observación censurada es `not_evaluable` (con su motivo en español). No se
  compara un `<` contra un máximo normativo: la respuesta honesta es que no se sabe.

## Consecuencias

**Positivas**
- Trazabilidad total: el dato original sobrevive y toda decisión de cálculo es reproducible.
- Cambiar la política (p. ej. adoptar métodos de máxima verosimilitud) no requiere migrar datos,
  solo `spc/baseline.py` y este ADR.
- El 20 % como corte es explícito en configuración, no un número enterrado en el código.

**Negativas / riesgos**
- **Pendiente de validación por el químico**: `LOQ/2` y el corte de 20 % son práctica común
  (EPA QA/G-9R, Helsel), no un consenso normativo chileno. Mientras no esté firmado, la UI debe
  rotular la sustitución como criterio del proyecto.
- `LOQ/2` sesga la media en series con muchos censurados; por eso existe el corte de 20 %.
- Dos caminos de sustitución (SPC y screening) deben mantenerse coherentes: el screening no
  sustituye, así que una observación censurada puede estar «dentro de rango» y aun así no ser
  evaluable. Es correcto, y hay que explicarlo en la UI.

## Referencias

- `.clinerules/01-project-context.md` §5 (censurados) y §4 (ADR-003)
- `api/app/spc/baseline.py` (`apply_censored_policy`, `CENSORED_MAX_FRACTION`)
- `api/app/models/observation.py` (`censored_coherence`), `api/app/screening/screener.py`
- US EPA *QA/G-9R* (2023), cap. 4 «Data Qualifiers / non-detects»
- Helsel, D.R. *Statistics for Censored Environmental Data Using Minitab and R* (2ª ed., 2012)
- `docs/spc-methods.md` §5

# ADR-010: Screening referencial, no dictamen de cumplimiento

- **Estado**: aceptado
- **Fecha**: 2026-10-24
- **Contexto**: ver `.clinerules/01-project-context.md` §5 y §4 (ADR-010)
- **Decisores**: Cristóbal Vera (químico + dev)

## Contexto

La pregunta que un regulador hace es «¿este sitio cumple la norma?». AquaMetric **no puede**
responderla, y no por falta de tiempo: la normativa chilena no se evalúa observación por
observación. El D.S. 53/2014 (Tabla 2) se verifica con percentiles P95/P5 sobre ventanas de tres
años según el uso del agua; la NCh 1.333 fija límites según el uso y el área de monitoreo, con
estadísticos propios. Comparar un valor aislado contra un máximo y escribir «excede» produce una
afirmación legal falsa, emitida por un sistema que nadie auditó.

Al mismo tiempo, el analista necesita algo útil **hoy**: «este valor de turbidez está por encima
del rango que el catálogo publica para este contexto». Eso es información, no un veredicto.

El catálogo real v1.0.0 tiene 60 límites, **todos en `draft-verified`** (ninguno `validated`) y
sus estadísticos son P95 (33), P5 (11), P5_P95 (11), `max_absolute` (3), `min_absolute` (1) y
`maxIncreaseOverNatural` (1). Es decir: hoy casi nada es evaluable con honestidad.

## Decisión

**Tres estados separados**, cada uno con su dueño, que la API y la UI nunca mezclan:

| Estado | Qué responde | Dónde vive en el MVP |
|---|---|---|
| `screeningFlag` | ¿el valor está dentro del rango que el catálogo publica para este contexto? | `POST /screening/evaluate` → `normal` / `above_range` / `below_range` / `not_evaluable` |
| `dataQualityStatus` | ¿el dato es confiable? (`ok` / `suspect` / `failed`, censurado, sin valor) | campo `qcFlag` de la observación; se informa junto al flag, nunca lo sustituye |
| `regulatoryStatus` | ¿el sitio cumple la norma? | **no implementado**: reservado y siempre `not_evaluable` en el MVP |

Reglas de evaluación:

1. Solo se compara contra límites `status = "validated"` **y** con estadístico absoluto
   (`max_absolute`, `min_absolute`). Un límite `draft-verified` se muestra como «Pendiente de
   validación» y produce `not_evaluable` con motivo.
2. `maxIncreaseOverNatural` es `not_evaluable`: requiere una `baselineReference` del sitio que el
   catálogo actual no entrega.
3. Los estadísticos del D.S. 53/2014 (P95, P5, P5_P95) son `not_evaluable` por observación: el
   análisis trienal está fuera del MVP y necesita la serie completa, no un punto.
4. Un valor censurado o sin valor es `not_evaluable` (ADR-003).
5. Ambigüedad de límite (dos candidatos, contexto faltante) ⇒ `not_evaluable`, nunca una
   suposición silenciosa.
6. La respuesta siempre incluye `warnings[]` con la advertencia de que es referencial, para que
   ningún cliente pueda pintar un flag sin el contexto que lo califica.

En la UI: rango fuera de lo esperado se marca en **ámbar**, nunca en rojo; los textos son «Dentro
del rango (referencial)», «Sobre el rango (referencial)», «Bajo el rango (referencial)» y «No
evaluable». Las palabras «Cumple» y «Excede» están prohibidas en el producto.

## Consecuencias

**Positivas**
- El sistema no puede emitir una afirmación legal que no puede sostener: el peor error posible
  en este dominio queda imposible por diseño.
- Con el catálogo actual **todo devuelve `not_evaluable` hasta que el químico firme**; la UI lo
  dice con un motivo concreto (qué falta), no con un error.
- El día que un límite pase a `validated`, el screening funciona sin tocar código: es dato, no
  lógica.

**Negativas / riesgos**
- La pantalla de screening se ve «vacía» en la demo hasta que haya límites firmados; se compensa
  mostrando el límite seleccionado, su estado y el motivo, que es información real.
- Hay dos estados que el MVP no calcula (`regulatoryStatus` y `dataQualityStatus` como campo
  propio); documentarlo así evita que la UI prometa algo que la API no entrega.
- Existe solapamiento deliberado con ADR-012 (mecánica de una observación aislada): este ADR fija
  la política, ADR-012 el detalle de implementación y los hallazgos del catálogo.

## Referencias

- `.clinerules/01-project-context.md` §5 (screening) y §4 (ADR-010)
- `docs/adr/012-screening-single-observation.md`, `docs/adr/003-censored-data-policy.md`
- `docs/adr/015-regulation-naming.md` (`regulation` ↔ `regulationCode`)
- `api/app/screening/screener.py`, `api/app/schemas/screening.py`, `api/app/routers/screening.py`
- D.S. 53/2014 (MMA, Chile), Tabla 2 — percentiles P95/P5 en ventanas de tres años
- NCh 1.333 (usos del agua), US EPA *Freshwater Screening Benchmarks*

# Métodos estadísticos de AquaMetric

Documento en lenguaje simple, escrito para el químico del proyecto y para quien revise el
portafolio. Cada método se explica con su fórmula, sus supuestos y qué **no** se puede concluir.

> Estado: este archivo cubre hoy el **screening referencial** (Fase B). Las cartas de control
> (I-MR, X̄-R), las reglas de Nelson y la capacidad de proceso se agregan en la Fase D, con sus
> casos de referencia (`tests/golden/README.md`).

## 1. Screening referencial

### 1.1 Qué pregunta responde

Dado **un valor** y **un límite del catálogo**, ¿está dentro del rango que la norma publica?

Lo que **no** responde: si el sitio cumple la norma. Ninguna norma del catálogo se evalúa con una
observación aislada:

| Regulación | Cómo evalúa | ¿Se puede comparar un dato suelto? |
|---|---|---|
| **NCh 1.333** (usos del agua) | límites absolutos por uso del agua (`vida_acuatica`, `riego`); en turbidez, *aumento* sobre el valor natural | sí, para los límites absolutos; no para el aumento sobre natural |
| **D.S. 53/2014 MMA** | percentiles P95 (la mayoría), P5 (oxígeno disuelto) y P5/P95 (pH) sobre **ventana trienal**, con 4 campañas estacionales por año | no: un dato no es un percentil trienal |

Ver `docs/adr/012-screening-single-observation.md` (el ADR-010 del brief se redacta junto con el
resto de la serie 001–011).

### 1.2 Estados del screening

`screen_observation()` devuelve exactamente uno de cuatro estados (`screening_flag`):

| Estado | Significado | Cuándo se produce |
|---|---|---|
| `normal` | dentro del rango de referencia | valor dentro de `[min, max]` del límite validado |
| `above_range` | sobre el rango (referencial) | `max_absolute` y `valor > max` |
| `below_range` | bajo el rango (referencial) | `valor < min` (`min_absolute` con piso, o `max_absolute` con `min` informado) |
| `not_evaluable` | no corresponde comparar | observación censurada o sin valor, sin límite aplicable, límite no validado, estadístico fuera del MVP, ambigüedad de contexto |

`not_evaluable` siempre viaja con un **motivo en español** («límite pendiente de validación»,
«la norma evalúa un percentil trienal», «observación censurada», …), nunca con un código de error.
El estado de calidad del dato y el estado regulatorio se informan por separado (ADR-012 §2.1); en
el MVP el estado regulatorio es siempre «No evaluado: fuera del alcance».

### 1.3 Fórmulas de los estadísticos evaluables

Solo dos estadísticos producen comparación: `max_absolute` y `min_absolute`, y solo si el límite
tiene `status = validated`.

```
max_absolute:   above_range  si  valor > max
                below_range  si  min ≠ ∅ y valor < min
                normal       en otro caso

min_absolute:   below_range  si  valor < min
                normal       en otro caso
```

Alejamiento respecto del límite (`exceedance_ratio`, sin unidad, solo si hay excedencia):

```
above_range y max ≠ 0:   exceedance_ratio = valor / max        (> 1)
below_range y valor ≠ 0: exceedance_ratio = min / valor         (> 1)
en otro caso:            null
```

Ejemplo: pH 9,5 con máximo 9,0 ⇒ `above_range`, `exceedance_ratio = 1,056`.

### 1.4 Estadísticos que **no** se evalúan en el MVP

| `statistic` | Regulación | Motivo | Respuesta |
|---|---|---|---|
| `maxIncreaseOverNatural` | NCh 1.333 (turbidez, vida acuática) | requiere el valor natural de referencia del sitio, que el catálogo no contiene | `not_evaluable` |
| `P95`, `P5` | D.S. 53/2014 | percentil sobre ventana trienal con cobertura estacional | `not_evaluable` |
| `P5_P95` | D.S. 53/2014 (pH) | percentil doble sobre la misma ventana trienal | `not_evaluable` |

### 1.5 Selección del límite (una sola respuesta posible)

1. Se filtran los límites del par (parámetro, regulación).
2. Si los candidatos tienen `context` (NCh 1.333 ⇒ uso del agua), el contexto es obligatorio y
   debe coincidir exactamente.
3. Si los candidatos tienen `monitoring_area_code` y `quality_level` (D.S. 53/2014), ambos son
   obligatorios y deben coincidir exactamente.
4. Si sobrevive **exactamente un** límite, se usa; si quedan **cero** o **dos o más**, el
   resultado es `not_evaluable`. El screening nunca elige uno al azar.

### 1.6 Unidades

El valor debe llegar en la **unidad canónica del parámetro** (`parameter.canonical_unit_code`). Si
el usuario envía otra unidad de la misma dimensión, el servicio la convierte de forma explícita
con el factor del catálogo y **agrega una advertencia** con el factor usado. Si el límite está
expresado en una unidad distinta de la canónica del parámetro, no se compara: `not_evaluable`.

### 1.7 Advertencias de interfaz obligatorias

Cada respuesta de `/screening/evaluate` incluye `warnings[]` con el aviso referencial y una frase
propia de la regulación. Además, la UI debe cumplir (ADR-012 §6):

1. Aviso fijo: «Referencial: no es un dictamen de cumplimiento legal».
2. Nunca «Cumple» ni «Excede»: usar «Dentro del rango», «Sobre el rango (referencial)», «Bajo el
   rango (referencial)» y «No evaluable».
3. Todo límite `draft` / `draft-verified` se muestra como «Pendiente de validación».
4. Cada resultado indica qué se comparó: regulación, contexto o área de vigilancia, `statistic`,
   versión del catálogo y `status` del límite.
5. `screening_flag`, `data_quality_status` y `regulatory_status` se muestran por separado; el
   último como «No evaluado: fuera del alcance del MVP».
6. Límite de control (SPC), límite normativo y LOQ nunca se agrupan bajo «límites».
7. Un `not_evaluable` explica el motivo en texto, no con un código.

### 1.8 Estado actual del catálogo

Los 60 límites sincronizados están en `status = draft-verified` y `catalog.meta.json` declara
`validatedBy = null`. Por eso **toda** evaluación responde hoy `not_evaluable` con el motivo
«pendiente de validación». El día que el químico firme los límites (`status = validated`) el
screening empieza a comparar sin cambiar una línea de código.

### 1.9 Supuestos y límites conocidos

- El valor se compara con el límite tal como está publicado: no se corrige por temperatura ni por
  matriz (agua dulce/salada).
- No se aplica la regla de «dos excedencias consecutivas» de D.S. 53/2014: es parte de la
  evaluación trienal, fuera del MVP.
- Un resultado `normal` no borra un `qcFlag` distinto de `ok`: la calidad del dato se informa
  aparte y manda sobre el screening.

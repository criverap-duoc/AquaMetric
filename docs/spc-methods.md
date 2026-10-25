# Métodos estadísticos de AquaMetric

Documento en lenguaje simple, escrito para el químico del proyecto y para quien revise el
portafolio. Cada método se explica con su fórmula, sus supuestos y qué **no** se puede concluir.

> Estado: este archivo cubre el **screening referencial** (Fase B) y el **núcleo SPC** (Fase D:
> cartas I-MR y X̄-R, reglas de Nelson, capacidad de proceso y política de datos censurados).
> Los casos de referencia con sus derivaciones están en `api/tests/golden/README.md`.


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

## 2. Cartas de control I-MR (individuales y rango móvil)

Es la carta por defecto cuando solo hay **una** medición por fecha (el caso normal en campañas
de muestreo y en sensores).

### 2.1 Cómo se construye (Fase I, línea base)

1. Se toman las primeras `n ≥ 20` observaciones **válidas** de la serie `(sitio, parámetro)`
   (`qcFlag = ok`, no censuradas o dentro de la política de la §5).
2. Se calculan los límites y se **guardan** junto con el rango de datos, el método y la versión
   del código: lo que se publicó ayer debe poder reproducirse mañana (ADR-001).

### 2.2 Fórmulas

```
MR_i      = |x_i − x_(i−1)|            i = 2..n            (rangos móviles)
MR̄         = promedio de los MR
σ̂         = MR̄ / d2,  d2 = 1,128 para n = 2
CL        = x̄  (promedio de las observaciones)
UCL, LCL  = x̄ ± 2,66 · MR̄             (2,66 = 3/d2 ⇒ 3 sigmas)

Carta MR  CL = MR̄,  UCL = 3,267 · MR̄ (D4 para n = 2),  LCL = 0
```

`d2` y `D4` son constantes tabuladas (Montgomery, apéndice VI; ISO 7870-2:2023), verificadas
una a una en `api/tests/golden/test_constants.py`.

### 2.3 Por qué `MR̄/d2` y no la desviación estándar

La desviación estándar de **toda** la serie mezcla el ruido normal con el cambio de nivel que se
quiere detectar: si el proceso sube de golpe, la desviación crece, los límites se ensanchan y la
carta "no ve" el cambio. `MR̄/d2` mide solo la variación **punto a punto** (ruido de corto plazo),
así que los límites quedan fijos y el escalón se ve. Ejemplo numérico en
`api/tests/golden/README.md` §3: mismos datos, `UCL` 15,44 con `MR̄/d2` frente a ≈18,85 con la
desviación global.

### 2.4 Qué no se puede concluir

- Con menos de 20 puntos no hay línea base: el sistema responde «datos insuficientes», no publica
  límites débiles.
- Una serie constante (todos los rangos móviles en cero) no tiene variación estimable: también se
  rechaza, porque los límites colapsarían sobre la línea central y todo punto parecería fuera.
- Un punto fuera de límites **no** dice si el agua cumple una norma: eso es la §1 (screening) y
  **no** es un dictamen legal.

### 2.5 El rango normativo dibujado junto a la carta

La carta puede mostrar, además de los límites de control, el rango de una regulación
(`specLimits`). Se dibuja con **otro estilo** (punto-raya) y otra etiqueta justamente para que
nadie los confunda: el límite de control describe el proceso, el normativo describe la referencia
legal. Reglas de publicación:

- Solo se publica un límite con `status = validated`; uno `draft-verified` sigue pendiente de la
  firma del químico y no se dibuja.
- Se prefiere `NCh1333`; si el parámetro no tiene límites firmados ahí, se usa `DS53-2014-MMA`.
- Si la regulación elegida tiene **más de un** límite firmado (varios usos del agua o varias áreas
  de vigilancia), no hay una sola banda que dibujar y la respuesta es `null` en lugar de elegir
  una arbitrariamente.
- Los valores se convierten a la unidad canónica del parámetro con el factor del catálogo; si la
  unidad del límite no existe en el catálogo, la banda se omite.

## 3. Cartas X̄-R (subgrupos racionales, n = 2…10)

Se usa cuando hay 2 a 10 mediciones comparables por ocasión (réplicas de laboratorio, varias
profundidades, varios puntos del mismo sitio).

```
x̄_j = promedio del subgrupo j        R_j = máx(subgrupo j) − mín(subgrupo j)
R̄    = promedio de los R_j            σ̂   = R̄ / d2(n)

Carta X̄: CL = promedio de los x̄_j,  UCL/LCL = CL ± A2(n) · R̄
Carta R: CL = R̄,  UCL = D4(n) · R̄,  LCL = D3(n) · R̄
```

`d2`, `A2`, `D3` y `D4` dependen del tamaño de subgrupo y son tabulados. Los subgrupos fuera de
`2…10` se rechazan: las constantes simplemente no están tabuladas para ellos.

Nota fina (importante para las reglas): la desviación de la **media** de un subgrupo es
`σ̂/√n`. El código la guarda así, de modo que `CL ± k·σ` reproduce las zonas de 1σ y 2σ de la
carta X̄; con `σ̂` sin dividir, las reglas R4/R5 se dispararían con cualquier fluctuación.

## 4. Reglas de Nelson / Western Electric

Se evalúan contra los límites de la carta correspondiente (Fase II: los límites congelados de la
línea base). Códigos de la interfaz y su equivalencia:

| Código | Regla | Qué describe | Puntos |
|---|---|---|---|
| `R1` | Nelson 1 | un punto fuera de los límites de control (±3σ) | 1 |
| `R2` | Nelson 2 | 9 consecutivos del mismo lado de la línea central | 9 |
| `R3` | Nelson 3 | 6 consecutivos crecientes o 6 decrecientes | 6 |
| `R4` | Nelson 5 | 2 de 3 consecutivos más allá de 2σ, del mismo lado | 3 |
| `R5` | Nelson 6 | 4 de 5 consecutivos más allá de 1σ, del mismo lado | 5 |

Convenciones (las mismas en el código y en la UI):

1. Un punto **exactamente** sobre un límite de control no es violación de `R1`; uno exactamente
   sobre la línea central rompe la racha de `R2` (no es «de un lado»).
2. En `R3`, un valor repetido corta la racha: una meseta no es una tendencia.
3. Se informa **una señal por patrón**: una racha de 12 puntos del mismo lado es una señal de
   `R2`, y una excursión sostenida en 2σ se reporta una vez por tramo, no una vez por ventana.
4. Cada señal describe el punto en español claro («Punto 9: nueve puntos consecutivos por encima
   de la línea central»), sin códigos para el usuario.

## 5. Datos censurados (`< LOQ`) — ADR-003

Un valor censurado (`value = null`, `qualifier = "<"`, `loq`) entra al cálculo como `LOQ/2` y
**solo** ahí: la base de datos conserva el dato original y el reporte dice qué se hizo.

| Censurados en la serie | Qué ocurre |
|---|---|
| 0 % | nada que sustituir |
| hasta 20 % | se sustituye `LOQ/2` y el metadato informa `censored_count` y `censored_fraction` |
| más de 20 % | «datos insuficientes»: no se publican límites |

Una observación con `value = null` y sin `qualifier = "<"` no es una observación válida y se
rechaza (no se rellena con cero). La política exacta (20 %) la valida el químico.

## 6. Capacidad de proceso (Cp, Cpk)

Responde otra pregunta: **qué tan lejos está la dispersión del proceso de los límites
normativos**. Solo tiene sentido si hay al menos un límite normativo **validado** por el químico
y el proceso está en control; el cálculo recibe los límites como argumento y comprueba lo
primero, mientras que lo segundo lo garantiza el servicio que lo invoca (la UI lo dice).

```
s   = desviación estándar muestral (ddof = 1)
Cp  = (USL − LSL) / (6·s)                        solo con ambos límites
Cpk = min((USL − x̄)/(3s), (x̄ − LSL)/(3s))       con ambos
      (USL − x̄)/(3s)  ó  (x̄ − LSL)/(3s)          con un solo límite
```

Supuestos y advertencias que viajan con el número:

1. Normalidad: con `|asimetría| > 1` se sugiere `transform = "log10"` (turbidez, coliformes). La
   transformación se aplica a los datos **y** a los límites normativos; si solo se transformaran
   los datos, la división mezclaría escalas y el resultado no significaría nada.
2. Tamaño: con `n < 30` el índice es orientativo y así se muestra.
3. Aquí **sí** se usa la desviación estándar muestral: la capacidad describe la dispersión de
   todas las observaciones, no la variación de corto plazo de la carta (§2.3).

Cp/Cpk nunca se calculan contra los límites de control: límite de control ≠ límite normativo ≠
LOQ (ADR-012 §6).



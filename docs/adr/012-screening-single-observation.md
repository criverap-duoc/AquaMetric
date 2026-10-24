# ADR 012 · Screening de una observación aislada, no dictamen de cumplimiento

- **Estado:** aceptado
- **Fecha:** 2026-10-24
- **Fase:** A-2 (loader del catálogo compartido)
- **Relacionado:** ADR-005 (catálogo sincronizado), ADR-010 (screening referencial)

## 1. Contexto

AquaMetric recibe observaciones sueltas: lecturas del simulador y resultados de laboratorio de
TerraPlan. La pregunta natural del usuario es «¿este valor cumple la norma?», pero las normas del
catálogo **no se evalúan así**:

| Regulación | Cómo evalúa | ¿Admite una observación aislada? |
|---|---|---|
| **NCh 1.333** (usos del agua) | límites absolutos (rango o umbral) y, en turbidez, *aumento* sobre el valor natural | sí para los límites absolutos; **no** para el aumento sobre natural (falta la referencia) |
| **D.S. 53/2014 MMA** (cuenca del Maipo) | percentiles P95 (la mayoría), P5 (oxígeno disuelto) y P5/P95 (pH) sobre **ventana trienal**, con 4 campañas estacionales por año y regla de dos excedencias consecutivas | **no**: una observación no es un percentil trienal |

El propio `catalog/regulations.v1.json` lo declara para D.S. 53/2014: `evaluationWindowYears: 3`,
`minimumSeasonalCoverage: 4`, `samplesPerYearTarget: 12`.

Emitir «Cumple» o «Excede» con un dato suelto sería estadísticamente falso y legalmente
irresponsable. Al mismo tiempo, el analista necesita alguna señal al mirar un valor: la respuesta
correcta es una comparación **explícitamente referencial** y, cuando no corresponde comparar,
decirlo sin ambigüedad.

## 2. Decisión

### 2.1 Tres estados separados (nunca uno combinado)

El resultado de evaluar una observación se expresa con **tres campos independientes**. Un solo
campo obliga a mezclar «el dato es dudoso» con «el valor está fuera del rango» y con «no
corresponde evaluar», que son problemas distintos y con dueños distintos.

| Campo | Valores | Quién lo determina |
|---|---|---|
| `screening_flag` | `normal` · `above_range` · `below_range` · `not_evaluable` | comparación con un límite del catálogo |
| `data_quality_status` | `ok` · `censored` (valor `< LOQ`) · `qc_not_ok` (`qcFlag` ≠ `ok`) · `no_value` | la observación misma (laboratorio o sensor) |
| `regulatory_status` | `not_assessed` (único valor del MVP) | módulo de cumplimiento, **fuera del MVP** |

`data_quality_status` manda: si una observación es censurada, no tiene valor o tiene QC fallido,
el `screening_flag` es `not_evaluable` aunque el número caiga dentro del rango.

### 2.2 Qué es evaluable con una sola observación

1. Solo límites con `statistic` ∈ {`max_absolute`, `min_absolute`} **y** `status = validated`.
2. `maxIncreaseOverNatural` (turbidez NCh 1.333) exige un `baselineReference` (valor natural del
   sitio y parámetro) que el catálogo **no** contiene: sin esa referencia ⇒ `not_evaluable`.
3. `P95`, `P5` y `P5_P95` (todo D.S. 53/2014) están **fuera del MVP** ⇒ siempre `not_evaluable`.
4. Ambos lados del límite se respetan: `min_absolute` compara contra el piso y `max_absolute`
   contra el techo; un límite con `min` y `max` informa `below_range` o `above_range` según
   corresponda.
5. Un límite `draft` / `draft-verified` **no** se usa para comparar: se muestra como «Pendiente de
   validación» y la observación queda `not_evaluable`.
6. Ambigüedad ⇒ `not_evaluable`: si más de un límite aplica al par (parámetro, regulación,
   contexto/área), o si no se indicó regulación y contexto/área, no se elige uno al azar.

La evaluación es **pura** y se calcula **al leer**; no se persiste, para que no quede obsoleta
cuando cambie la versión del catálogo.

### 2.3 Mapeo por defecto sitio → regulación/contexto (pendiente de validación del químico)

El screening resuelve el límite con `regulationCode` + `context` (NCh 1.333) o
`monitoringAreaCode` (D.S. 53/2014) **explícitos** en la consulta. Los defaults propuestos son
solo una comodidad de la UI y quedan marcados como pendientes:

| `Site.waterBodyType` | `regulationCode` por defecto | `context` por defecto |
|---|---|---|
| `river`, `lake`, `estuary` | `NCh1333` | `vida_acuatica` |
| `effluent` | `NCh1333` | `riego` (referencial; el caudal y la norma de descarga no están en el catálogo) |
| `groundwater`, `drinking` | `NCh1333` | `riego` (referencial; NCh 409 no está en el catálogo) |
| sitios de la cuenca del Maipo | `DS53-2014-MMA` | **sin default**: el `monitoringAreaCode` debe indicarse; sin él ⇒ `not_evaluable` |

Los sitios `SIM-…` del simulador no pertenecen a ninguna área de vigilancia: se evalúan con
NCh 1.333.

## 3. Hallazgos del catálogo real v1.0.0 (por qué hoy casi todo es `not_evaluable`)

1. **0 de 60 límites están `validated`**: los 60 tienen `status = draft-verified` (lo verifica
   `api/tests/unit/catalog/test_loader.py`). Con la regla 2.2.5, **`not_evaluable` es el resultado
   correcto** de todo screening hasta que el químico firme. No es un bug ni un dato faltante.
2. **55 de 60 límites son de D.S. 53/2014** (P95/P5/P5_P95, ventana trienal): quedan fuera del MVP
   por definición de método, independiente de su `status`.
3. **4 límites son absolutos y evaluables en cuanto se validen**: NCh 1.333 pH `vida_acuatica`
   (6,0–9,0), pH `riego` (5,5–9,0), oxígeno disuelto `vida_acuatica` (≥ 5,0 mg/L) y conductividad
   `riego` (≤ 750 µS/cm).
4. **1 límite usa `maxIncreaseOverNatural`**: turbidez NCh 1.333 `vida_acuatica`, +30 unidades de
   sílice (≈ 4 NTU). Requiere valor natural de referencia ⇒ `not_evaluable` sin baseline.
5. **`catalog.meta.json` declara el sha256 del bundle lógico** (`a44c217…`), no el del archivo
   (`39ccf5…`). Un archivo no puede contener su propio hash: `scripts/sync_catalog.py` lo
   documenta y el loader guarda el valor declarado **sin** intentar recomputarlo.

## 4. Consecuencias

- **Positivas:** no se publica ningún juicio de cumplimiento; la UI aprende a decir «No evaluable»
  con motivo; el día que el químico cambie el `status` a `validated`, el screening empieza a
  comparar **sin tocar código ni catálogo**; el loader no filtra nada, así que la política vive en
  un solo lugar (el servicio de screening).
- **Costos:** durante el MVP el screening luce conservador (todo «No evaluable», o «Fuera del
  rango referencial» cuando existan límites validados); hace falta un paso humano (firma) para que
  la pantalla muestre comparaciones reales; `data_quality_status` y `regulatory_status` suman
  conceptos que el usuario debe aprender (mitigado con el glosario y textos claros).
- **Prohibido en el MVP:** percentiles P95/P5, ventanas de 3 años, editor de normas en la UI,
  textos «Cumple» / «Excede», y presentar un límite `draft` como si estuviera vigente.

## 5. Evidencia

Revisión de métodos (investigación con Perplexity, oct-2026) para confirmar que comparar una
observación aislada contra un percentil regulatorio no es defendible. De estas fuentes se tomó
**solo el criterio de evaluación**; los valores numéricos provienen únicamente del catálogo:

- **EPA — *screening benchmarks***: se usan como cribado para priorizar inspecciones, no como
  juicio de cumplimiento; el resultado se comunica como señal de atención, no como veredicto.
- **EU WFD (Directiva 2000/60/CE, Anexo V)**: el estado de una masa de agua se evalúa con series de
  datos en periodos plurianuales, nunca con una muestra puntual.
- **D.S. 53/2014 MMA**: evaluación **trienal** con P95 (mayoría de parámetros), P5 (oxígeno
  disuelto), P5/P95 (pH), cobertura de 4 campañas estacionales por año y regla de dos excedencias
  consecutivas; coincide con los campos ya publicados en `catalog/regulations.v1.json`.

## 6. Advertencias de UI obligatorias

1. Aviso fijo en la pantalla de screening: «**Referencial: no es un dictamen de cumplimiento
   legal**».
2. Nunca las palabras «Cumple» ni «Excede»; usar «Dentro del rango», «Sobre el rango (referencial)»,
   «Bajo el rango (referencial)» y «No evaluable».
3. Todo límite `draft` / `draft-verified` se muestra como «Pendiente de validación».
4. Cada resultado indica qué se comparó: regulación, contexto o área de vigilancia, `statistic`,
   versión del catálogo y `status` del límite.
5. `screening_flag`, `data_quality_status` y `regulatory_status` se muestran por separado, este
   último como «No evaluado: fuera del alcance del MVP».
6. Límite de control (SPC), límite normativo y LOQ tienen estilos y etiquetas distintos; nunca se
   agrupan bajo «límites».
7. Un `not_evaluable` explica el motivo («límite pendiente de validación», «observación censurada»,
   «la norma evalúa un percentil trienal», «falta el área de vigilancia»), no un código de error.

## 7. Cuándo se revisa este ADR

- Cuando el químico cambie al menos un límite a `validated` (actualizar el test del hallazgo 1 y las
  expectativas de la pantalla de screening).
- Si TerraPlan agrega límites con otros `statistic` ⇒ revisar §2.2 y el mapeo de §2.3.
- Si se aprueba el módulo de cumplimiento (percentiles y ventana trienal): nuevo ADR y nueva versión
  de la API.

# Glosario de AquaMetric

Términos del proyecto en lenguaje simple, para el químico, el analista y quien revise el
portafolio. Los detalles estadísticos están en `docs/spc-methods.md`; las decisiones, en
`docs/adr/`.

## 1. Dominio químico

**Observación**
Un valor medido de un parámetro en un sitio y un momento: `7,8` de pH en el río Maipo el 12 de
octubre a las 09:00. Es la unidad mínima de datos del sistema; todo lo demás se calcula a partir
de ellas.

**Sitio**
El lugar donde se toma la muestra o está el sensor (`RIO-MAIPO-01`, `SIM-ESTERO-02`). Tiene
código único, nombre, tipo de cuerpo de agua y coordenadas.

**Muestra**
La porción física recogida en una campaña de muestreo (frasco, cadena de frío, recepción en el
laboratorio). Varias observaciones de distintos parámetros pueden venir de la misma muestra. Los
sensores no tienen muestra: informan lecturas directas.

**Parámetro**
Lo que se mide: pH, turbidez, conductividad, oxígeno disuelto, nitrato. Se identifica con un
código del catálogo (`PH`, `TURB`, `COND`, `DO`, `N_NO3`), nunca con texto libre.

**Unidad**
La escala en que viene el valor (`NTU`, `µS/cm`, `mg/L`, `°C`). Cada parámetro tiene una unidad
canónica; el sistema guarda la unidad original y convierte de forma explícita, nunca en
silencio.

**Límite normativo**
El valor que fija una norma (D.S. 53/2014, NCh 1.333) para un uso y un contexto del agua. **No**
es un límite de control: la norma dice qué se exige, la carta dice cómo se comporta el proceso.

**LOQ (límite de cuantificación)**
El valor más bajo que el laboratorio puede medir con confianza. Por debajo de él el resultado se
informa como `< LOQ`, no como un número.

**Valor censurado**
Una observación por debajo del LOQ. Se guarda como `value = null`, `qualifier = "<"` y `loq`; el
cálculo puede usar `LOQ/2`, pero ese valor **no** se almacena y el dato original nunca se pierde.

**QC / `qcFlag`**
El control de calidad de un dato: `ok` (confiable), `suspect` (dudoso) o `failed` (descartable).
Es un juicio sobre la medición, distinto de si el valor está dentro de un rango.

**Fase I y Fase II**
Fase I es aprender cómo se comporta el proceso «en calma» y fijar la línea base (los límites de
control). Fase II es vigilar los datos nuevos contra esos límites ya congelados.

## 2. Control estadístico de procesos (SPC)

**SPC (control estadístico de procesos)**
Conjunto de técnicas para distinguir la variación normal de un proceso («ruido») de un cambio
real. En AquaMetric se aplica a series de calidad de agua: primero se aprende el ruido, después se
avisa cuando el proceso se sale del patrón.

**Carta de control**
Un gráfico de la serie en el tiempo con tres líneas horizontales —límite superior, línea central y
límite inferior— que se dibujan a partir de la variabilidad del propio proceso. Un punto fuera de
ellas indica algo que no es ruido.

**Límite de control (UCL / LCL)**
Los bordes de la carta (Upper/Lower Control Limit), calculados a ±3 desviaciones estándar del
proceso. **No** son límites normativos ni un objetivo: describen el comportamiento habitual, no
lo que exige la ley.

**Carta I-MR**
La carta para observaciones individuales (I) más su rango móvil (MR). Es la carta por defecto
cuando hay una sola medición por fecha, como en campañas de muestreo.

**Carta X̄-R**
La carta para subgrupos de 2 a 10 mediciones comparables por ocasión: se vigila el promedio del
subgrupo (X̄) y su rango (R). Sirve cuando hay réplicas de laboratorio o varias profundidades.

**Reglas de Nelson (R1–R5)**
Patrones que delatan un cambio aunque ningún punto salga de los límites:
`R1` un punto fuera de ±3σ · `R2` nueve seguidos del mismo lado de la línea central ·
`R3` seis seguidos subiendo o bajando · `R4` dos de tres más allá de 2σ del mismo lado ·
`R5` cuatro de cinco más allá de 1σ del mismo lado. Una señal no es un diagnóstico: es una
invitación a mirar.

**Capacidad de proceso (Cp / Cpk)**
Cuánto margen tiene el proceso respecto a los límites normativos. `Cp` compara la amplitud de la
norma con la dispersión; `Cpk` además castiga que el proceso esté descentrado. Solo se informa con
límites validados y proceso en control, y supone normalidad.

## 3. Screening

**Screening referencial**
Comparar un valor con el rango que el catálogo publica para un contexto. Es una referencia
técnica: **no** es un dictamen de cumplimiento legal y no puede usarse como tal.

**`screeningFlag`**
El resultado de esa comparación: `normal` (dentro del rango), `above_range` (sobre el rango),
`below_range` (bajo el rango) o `not_evaluable` (no se puede evaluar, con el motivo en español).

**`dataQualityStatus`**
El estado de confianza del dato (`qcFlag` de la observación, o censurado/sin valor). Va aparte del
screening: un dato dudoso puede estar dentro del rango, y las dos cosas se informan por separado.

**`regulatoryStatus`**
El estado de cumplimiento legal. En el MVP **no se calcula**: siempre `not_evaluable`, porque la
normativa se evalúa con percentiles en ventanas de tres años y no con una observación.

**Pendiente de validación**
Etiqueta de todo límite del catálogo con `status = "draft-verified"`: existe, se muestra, pero no
produce comparación hasta que el químico lo firme (`validated`). Hoy son los 60 límites.

## 4. Infraestructura

**Catálogo**
La copia de solo lectura (en `catalog/`) de parámetros, unidades, límites y regulaciones que
**TerraPlan** administra. Trae versión y `sha256`; se sincroniza con un script y el CI verifica
que no fue editado a mano.

**Ingesta**
El proceso por el que las observaciones entran a AquaMetric: se valida el lote completo contra el
catálogo, se normaliza y se escribe en una sola transacción. Es el **único** camino de escritura
(`POST /api/v1/ingest/observations`).

**Idempotencia**
Garantía de que reintentar no duplica ni corrompe. AquaMetric la resuelve en dos niveles: por
petición (`Idempotency-Key` + hash del cuerpo, que devuelve la respuesta guardada) y por fila
(`ON CONFLICT DO NOTHING` sobre la clave natural de la observación).

**Línea base**
El conjunto de puntos y límites de control calculados en Fase I para un sitio y un parámetro, y
guardado para poder reproducirlo. Es lo que permite decir «esto es lo normal para este sitio».

**Pipeline AWS**
El camino opcional, en la nube, que genera lecturas de sensor y las envía a la API: EventBridge
schedules → Lambda `simulator_tick` → S3 → Lambda `ingest_processor` → API. Se documenta con SAM
y se despliega al final; **no** sostiene la demo viva.

## 5. El proyecto

**MVP**
El alcance mínimo que se entrega en 2–3 semanas y que se sostiene en pie sin nada de lo recortado:
ingesta idempotente, screening referencial, SPC correcto, simulador, UI pública y despliegue.

**Rebanada (slice)**
Una parte vertical y terminada de una funcionalidad: migración → modelo → repositorio → servicio →
router → tests → UI. Se cierra una antes de abrir la siguiente, para que el repo nunca quede a
medio construir.

**Niveles de verificación (N0–N3)**
Cuánto se comprueba según el riesgo del cambio. `N0` solo docs (revisión del diff) · `N1` cambios
locales sin lógica (compilar, `ruff`, `typecheck`) · `N2` lógica (además `mypy` y tests del
módulo) · `N3` todo lo delicado (migraciones, ingesta, seguridad, Docker, infra): suite completa,
migración reversible y `docker build`.



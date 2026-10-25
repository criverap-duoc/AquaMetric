# Casos de referencia (golden) del núcleo SPC

Cada valor esperado de esta carpeta se obtuvo **antes** de escribir el código de producción y se
puede recalcular a mano con lápiz y papel a partir de los datos de esta página. Cuando un caso
necesitó una comprobación numérica adicional se indica explícitamente cómo se hizo; ninguno se
copió de la salida del propio módulo.

Fuente de constantes y fórmulas: Montgomery, *Introduction to Statistical Quality Control*,
7th ed., cap. 6 y apéndice VI (tabla de constantes de cartas de control); ISO 7870-2:2023.
Ver también `docs/spc-methods.md` y `docs/adr/001-spc-phase-1-control-limits.md`.

Los tests viven en `test_constants.py`, `test_imr_golden.py`, `test_xbar_r_golden.py`,
`test_rules_golden.py` y `test_capability_golden.py`, y se ejecutan sin base de datos
(`uv run pytest -q tests/golden`).

## 1. Constantes (d2, D3, D4, A2)

Los 37 valores de las tablas se reescribieron a mano desde la tabla del libro en
`test_constants.py` (`BOOK_D2`, `BOOK_D3`, `BOOK_D4`, `BOOK_A2`) y se comparan uno a uno con
cada constante nombrada del módulo. Además se comprueban dos relaciones que el libro cumple:

| Comprobación | Valor esperado | Cómo se obtuvo |
|---|---|---|
| `K_IMR = 3/d2(2)` | `3/1,128 = 2,6596` → publicado como `2,66` | división a mano; tolerancia `1e-3` |
| `A2(n) = 3/(d2(n)·√n)` | tabla | reconstrucción de la fórmula de A2 con la d2 de la misma fila |

La segunda comprobación es la que impide que un error de tecleo sobreviva: para pasar, tendría
que repetirse igual en dos columnas distintas de la tabla.

## 2. Carta I-MR, caso A — serie alternante `[9, 10] × 10`

| Estadístico | Derivación | Valor |
|---|---|---|
| `x̄` | `(9+10)×10/20` | `9,5` |
| `MR` | 19 rangos, todos `1` | `MR̄ = 1` |
| `σ̂` | `MR̄/d2 = 1/1,128` | `0,886524822695` |
| `UCL` | `9,5 + 2,66×1` | `12,16` |
| `LCL` | `9,5 − 2,66×1` | `6,84` |
| `UCL_MR` | `D4(2)×MR̄ = 3,267×1` | `3,267` |
| `LCL_MR` | `D3(2)×MR̄ = 0` | `0` |

Ningún punto cae fuera de `[6,84; 12,16]`: la carta está en control y `detect_rules` debe
devolver una lista vacía (se comprueba también en `test_rules_golden.py`).

## 3. Carta I-MR, caso B — cambio de nivel (por qué no se usa la desviación global)

Serie: `[10, 11] × 5` seguida de `[14, 15] × 5`.

| Estadístico | Derivación | Valor |
|---|---|---|
| `x̄` | `(105 + 145)/20` | `12,5` |
| `MR` | 9 rangos de `1` + `1` rango de `3` + 9 rangos de `1` | suma `21` |
| `MR̄` | `21/19` | `1,105263157895` |
| `σ̂` | `1,105263157895/1,128` | `0,979843225084` |
| `UCL` | `12,5 + 2,66×(21/19) = 12,5 + 2,94` | `15,44` |
| `LCL` | `12,5 − 2,94` | `9,56` |
| `UCL_MR` | `3,267×21/19` | `3,610894736842` |

Contraste que justifica el ADR-001: la desviación estándar global de esta serie es
`2,115108557622` (suma de cuadrados `85`, `ddof = 1`), de modo que una carta construida con
`x̄ ± 3s` tendría `UCL ≈ 18,85` y **no** marcaría el escalón. Con `MR̄/d2` el límite es `15,44` y
la regla R2 detecta la racha por encima de la línea central en los puntos 9 y 19.

## 4. Carta X̄-R, subgrupos de n = 3

Veinte subgrupos `(m−1, m, m+1)` con medias `m = 11, 13, 12, 14, …, 20, 22`. Por construcción
la media de cada subgrupo es exactamente `m` y su rango exactamente `2`.

| Estadístico | Derivación | Valor |
|---|---|---|
| media de medias | `330/20` | `16,5` |
| `R̄` | 20 rangos de `2` | `2` |
| `UCL_X̄` | `16,5 + A2(3)×2 = 16,5 + 1,023×2` | `18,546` |
| `LCL_X̄` | `16,5 − 2,046` | `14,454` |
| `UCL_R` | `D4(3)×2 = 2,574×2` | `5,148` |
| `LCL_R` | `D3(3)×2 = 0` | `0` |
| `σ̂` | `R̄/d2(3) = 2/1,693` | `1,181334908447` |
| `σ` de la media | `σ̂/√3` | `0,682044027395` |

Comprobación cruzada: `3×σ` de la media trazada debe reproducir `A2(3)×R̄ = 2,046`. Da
`2,046132` — la diferencia de `1,3×10⁻⁴` es el redondeo a tres decimales de la tabla
(`3/(1,693×√3) = 1,02315`), no un error de fórmula; por eso ese test usa tolerancia `5e-4`.

## 5. Capacidad de proceso

Serie simétrica de 20 valores alrededor de 10: `8,5 ×4`, `9,5 ×2`, `10 ×8`, `10,5 ×2`,
`11,5 ×4`.

| Cantidad | Derivación | Valor |
|---|---|---|
| media | simetría alrededor de 10 | `10` |
| suma de cuadrados | `4×2,25 + 2×0,25 + 2×0,25 + 4×2,25` | `19` |
| `s` | `√(19/19)` con `ddof = 1` | `1` |
| `Cp` | `(13,99 − 6,01)/(6×1) = 7,98/6` | `1,33` |
| `Cpk` | `min(3,99/3, 3,99/3)` | `1,33` |
| `Cpk` (solo USL 12) | `(12 − 10)/3` | `0,666…` |
| `Cpk` (serie desplazada +0,5) | `(13,99 − 10,5)/3 = 3,49/3` | `1,1633…` |

Transformación `log10`: se aplica a los datos **y** a los límites normativos. Comprobación
numérica independiente (numpy sobre los logaritmos, fuera del módulo): media `0,997914643649`,
`s = 0,043810079094`, `Cp = (log10 13,99 − log10 6,01)/(6s) = 1,395962033080` y
`Cpk = (log10 13,99 − 0,997914643649)/(3s) = 1,125335188469`.

Aviso de asimetría: `[10 ×19, 30]` tiene `g1 > 1`, por lo que el resultado debe viajar con la
sugerencia de `transform='log10'`.

## 6. Reglas R1–R5

Límites fijados a mano en todos los casos: centro `10`, `σ = 1`, `UCL 13`, `LCL 7`
(`2σ = 12`, `1σ = 11`).

| Regla | Caso positivo | Esperado | Caso negativo | Esperado |
|---|---|---|---|---|
| R1 (3σ) | `[10, 10, 13.5, 10, 10]` | `R1 @ índice 2` | `[10, 13, 7, 10]` (justo en el límite) | nada |
| R2 (9 del mismo lado) | `[10.5] × 9` | `R2 @ índice 8` | `[10.5] × 8, 10, 10.5, 10.5` | nada |
| R3 (6 en aumento/descenso) | `[9, 9.5, 10, 10.5, 11, 11.5]` | `R3 @ índice 5` | `[9, 9.5, 10, 10.5, 11, 11]` (meseta) | nada |
| R4 (2 de 3 en 2σ) | `[10, 12.5, 10.2, 12.5]` | `R4 @ índice 3` | `[10, 12.5, 10.2, 7.9]` (lados opuestos) | nada |
| R5 (4 de 5 en 1σ) | `[11.5, 11.5, 10, 11.5, 11.5]` | `R5 @ índice 4` | `[11.5, 11.5, 10, 11.5, 10.6]` | nada |

Convención de reporte, verificada en los mismos tests: una racha de 12 puntos del mismo lado
produce **una** señal (R2 en el punto 9), no cuatro; una excursión de 6 puntos en 2σ produce
**dos** señales de R4 (ventanas 1-3 y 4-6). Es lo que un analista necesita ver: una marca por
patrón, no una marca por ventana solapada.

## 7. Política de datos censurados (no golden, pero con números)

`tests/unit/spc/test_baseline.py` fija los tres regímenes: 0 % censurado (serie intacta),
10 % (2 de 20 → `LOQ/2`) y 30 % (6 de 20 → `InsufficientDataError`). El umbral es estricto
(`> 20 %` se rechaza, `= 20 %` se acepta) y la sustitución nunca sale del cálculo: la base de
datos conserva `value = null`, `qualifier = "<"` y el `loq` originales (ADR-003).



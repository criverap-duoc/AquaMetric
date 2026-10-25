# ADR-001: Límites de control 3σ estimados en Fase I

- **Estado**: aceptado
- **Fecha**: 2026-10-24
- **Contexto**: ver `.clinerules/01-project-context.md` §4.1
- **Decisores**: Cristóbal Vera (químico + dev)

## Contexto

El núcleo SPC es la pieza que más pesa en el portafolio de AquaMetric. Debe ser estadísticamente correcto, no una aproximación. Dos métodos compiten para estimar la variabilidad de una serie de observaciones individuales:

1. **Desviación estándar muestral** `s = sqrt(Σ(xᵢ - x̄)² / (n - 1))`.
2. **Rango móvil medio dividido por la constante d₂** `σ̂ = MR̄ / d₂`.

Con la desviación estándar muestral, un cambio de nivel (un *shift* real del proceso) infla `s` y **ensancha los límites de control**, justo cuando el proceso está fuera de control. Es el peor comportamiento posible para una herramienta de detección.

## Decisión

**Fase I (línea base)**:
- Las primeras `n ≥ 20` observaciones válidas (`qcFlag = "ok"`, no censuradas) por `(site_id, parameter_code)` forman la línea base.
- Los límites se estiman con `σ̂ = MR̄ / d₂`, donde `d₂ = 1.128` para `n = 2` (rangos móviles de tamaño 2).
- `CL = x̄`; `UCL = x̄ + 2.66 · MR̄`; `LCL = x̄ - 2.66 · MR̄` (con `2.66 = 3 / d₂`).
- Se **persisten** los límites junto con: rango de datos usado, método, versión del catálogo, fecha de cálculo. Reproducibilidad obligatoria.

**Fase II (monitoreo)**:
- Las observaciones nuevas se evalúan contra los límites congelados de la Fase I.
- Un cambio de nivel sostenido dispara reglas de Nelson, no re-estima los límites automáticamente.

**Carta X̄-R** (subgrupos `n = 2..10`): constantes `A₂`, `D₃`, `D₄` de tabla estándar en `spc/constants.py`, cada una verificada por test contra valor de libro.

## Consecuencias

**Positivas**
- Los límites reflejan la variabilidad *a corto plazo*, no la variabilidad total. Detección correcta de *shifts*.
- Método estándar en la industria (Montgomery, *Introduction to Statistical Quality Control*).
- Reproducibilidad completa: cualquier analista puede recalcular y verificar.

**Negativas / riesgos**
- Con series cortas (`n < 20`) no hay línea base: `INSUFFICIENT_DATA`. Es una restricción intencional, no un bug.
- Requiere persistir el rango y la versión del catálogo (Fase D).

## Referencias

- `.clinerules/01-project-context.md` §4.1
- Montgomery, D.C. *Introduction to Statistical Quality Control* (7ª ed.), cap. 6.
- ISO 7870-2:2023 *Control charts — Part 2: Shewhart control charts*.
- `docs/spc-methods.md` (fórmulas en lenguaje claro para el químico).

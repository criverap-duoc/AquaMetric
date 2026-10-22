# AquaMetric — Design System

> **Nombre de trabajo:** AquaMetric (renombrable). Monitoreo de calidad de agua: control estadístico de procesos (SPC), simulador de sensores y pipeline en AWS.
> **Stack visual:** React 19 + Vite + Tailwind CSS 4 + shadcn/ui (Radix) + shadcn `chart` (Recharts) + lucide-react. Gestor de paquetes: **pnpm**.
> **Fuente de verdad:** este archivo. Los tokens viven en `web/src/styles/globals.css` y deben coincidir con el bloque CSS de la sección 3.
> **Proyecto hermano:** TerraPlan (NestJS). Misma filosofía, identidad distinta (ver sección 12).

---

## 0. Guía rápida para no programadores (léelo primero)

Un *design system* es el "manual de estilo" de la aplicación: define colores, letras, tamaños y **qué significa cada uno**, para que todas las pantallas sean coherentes y se lean sin esfuerzo.

**Cómo opinar sobre la UI sin ser técnico** (mirando la pantalla, sin hablar de código):

1. ¿Un analista entendería de dónde viene cada dato y cómo se calculó?
2. ¿Las unidades, símbolos (µg/L, NTU, µS/cm) y nombres de parámetros están bien escritos?
3. ¿Se distingue claramente un **límite de control** (estadístico, del proceso) de un **límite normativo** (legal)? *Son cosas distintas y esta app las muestra distinto a propósito.*
4. ¿Los valores "bajo el límite de cuantificación" (`< LOQ`) se ven como tales y no como un número cualquiera?
5. ¿Algún color o símbolo podría malinterpretarse?

**Qué significa cada color (en simple):**

| Color | Significa | Ejemplo en la app |
|---|---|---|
| Azul océano | "Marca / acción principal / dato central" | Botón principal, línea de la serie |
| Turquesa | "Selección, énfasis analítico" | Filtro activo, serie secundaria |
| Verde | "Dentro de control / dentro de rango" | Punto en control, valor dentro del rango de referencia |
| Ámbar | "Alerta temprana / fuera de rango (referencial)" | Regla de advertencia (p. ej. 2 de 3 puntos fuera de 2σ); valor fuera del rango de referencia |
| Rojo ladrillo | "Fuera de control" | Punto que viola una regla SPC (el rojo **no** se usa para el screening normativo: no es un dictamen legal) |
| Violeta-índigo | "Información / nota metodológica" | Avisos, explicación de cálculo |
| Gris azulado | "Neutro / secundario" | Ejes, grillas, textos de apoyo |

**Regla de oro:** el color **nunca** va solo; siempre acompaña a forma, texto o patrón de línea (punteada, etc.).

---

## 1. Principios de diseño

| # | Principio | Qué significa en práctica |
|---|---|---|
| 1 | **Rigor visible** | Cada gráfico muestra unidad, periodo, n, método y fuente. Nada "mágico". |
| 2 | **Los datos primero** | Interfaz sobria, tinta mínima, el gráfico es el protagonista. |
| 3 | **Distinguir lo que se parece** | Límite de control ≠ límite normativo ≠ límite de detección. Estilos de línea y etiquetas distintos. |
| 4 | **Transparencia** | Panel "¿Cómo se calculó?" en cada análisis; valores censurados y calidad de dato siempre marcados. |
| 5 | **Densidad con respiro** | Alta densidad de información, pero con jerarquía clara y espaciado consistente. |
| 6 | **Accesible por diseño** | Forma + patrón + texto además de color; teclado y lector de pantalla. |

---

## 2. Identidad

- **Sensación:** laboratorio, instrumento científico, transparencia institucional.
- **Paleta base:** azul océano (rigor, agua) + turquesa (análisis) + grises azulados técnicos; rojo ladrillo solo para lo crítico.
- **Forma:** radio pequeño (`0.375rem`), bordes finos, casi sin sombras (planitud tipo "papel científico").
- **Tono de voz (es-CL):** preciso y neutral. "Observación fuera de límites de control (regla 1)", no "¡Alerta!".

---

## 3. Tokens de color (CSS variables · Tailwind 4 + shadcn/ui)

Valores en **OKLCH**, ajustados al gamut sRGB. Contraste **verificado por script**: texto normal ≥ 5,91:1 (mínimo AA = 4,5:1), elementos de UI ≥ 3,27:1 (mínimo AA = 3:1). Ver sección 10.

```css
/* web/src/styles/globals.css */
@import "tailwindcss";
@import "tw-animate-css";

@custom-variant dark (&:is(.dark *));

:root {
  --radius: 0.375rem;

  /* Neutrales (grises azulados técnicos) */
  --background: oklch(0.985 0.004 235);
  --foreground: oklch(0.21 0.03 250);
  --card: oklch(1 0 0);
  --card-foreground: var(--foreground);
  --popover: var(--card);
  --popover-foreground: var(--foreground);
  --muted: oklch(0.96 0.006 240);
  --muted-foreground: oklch(0.47 0.03 245);
  --border: oklch(0.91 0.01 240);           /* decorativo */
  --input: oklch(0.62 0.025 245);           /* borde de campos: cumple 3:1 */
  --ring: oklch(0.55 0.12 250);

  /* Marca */
  --primary: oklch(0.44 0.12 250);          /* azul océano */
  --primary-foreground: oklch(0.985 0.004 235);
  --secondary: oklch(0.94 0.03 195);        /* turquesa muy suave */
  --secondary-foreground: oklch(0.30 0.054 205);
  --accent: oklch(0.88 0.07 195);           /* turquesa (selección, hover) */
  --accent-foreground: oklch(0.28 0.052 210);

  /* Semánticos (sólidos) */
  --destructive: oklch(0.50 0.19 25);
  --destructive-foreground: oklch(0.985 0 0);
  --success: oklch(0.48 0.11 160);
  --success-foreground: oklch(0.985 0 0);
  --warning: oklch(0.82 0.15 85);
  --warning-foreground: oklch(0.28 0.06 70);
  --info: oklch(0.50 0.15 275);             /* índigo: distinto de la marca */
  --info-foreground: oklch(0.985 0 0);

  /* Semánticos (suaves, para badges y banners) */
  --success-soft: oklch(0.95 0.05 160);
  --success-soft-foreground: oklch(0.34 0.08 160);
  --warning-soft: oklch(0.96 0.05 90);
  --warning-soft-foreground: oklch(0.38 0.08 70);
  --destructive-soft: oklch(0.95 0.024 25);
  --destructive-soft-foreground: oklch(0.42 0.16 25);
  --info-soft: oklch(0.95 0.024 275);
  --info-soft-foreground: oklch(0.40 0.13 275);

  /* Series de gráficos (distinguibles también por forma/patrón) */
  --chart-1: oklch(0.52 0.148 250);         /* azul */
  --chart-2: oklch(0.62 0.106 195);         /* turquesa */
  --chart-3: oklch(0.66 0.16 55);           /* naranja */
  --chart-4: oklch(0.55 0.17 305);          /* violeta */
  --chart-5: oklch(0.58 0.02 245);          /* gris */

  /* Control estadístico de procesos */
  --spc-limit: oklch(0.55 0.19 27);         /* UCL / LCL (control) */
  --spc-spec: oklch(0.62 0.146 60);         /* límite normativo / especificación */
  --spc-center: var(--primary);             /* línea central / media */
  --spc-violation: var(--destructive);      /* punto que viola una regla */
  --spc-warning: var(--warning);            /* punto en alerta temprana */

  /* Sidebar (alias de tokens ya verificados) */
  --sidebar: var(--card);
  --sidebar-foreground: var(--foreground);
  --sidebar-primary: var(--primary);
  --sidebar-primary-foreground: var(--primary-foreground);
  --sidebar-accent: var(--accent);
  --sidebar-accent-foreground: var(--accent-foreground);
  --sidebar-border: var(--border);
  --sidebar-ring: var(--ring);
}

.dark {
  --background: oklch(0.16 0.025 250);
  --foreground: oklch(0.96 0.005 235);
  --card: oklch(0.20 0.03 250);
  --muted: oklch(0.24 0.025 250);
  --muted-foreground: oklch(0.72 0.025 240);
  --border: oklch(0.30 0.025 250);
  --input: oklch(0.58 0.03 250);
  --ring: oklch(0.65 0.12 245);

  --primary: oklch(0.72 0.12 245);
  --primary-foreground: oklch(0.16 0.03 250);
  --secondary: oklch(0.27 0.04 215);
  --secondary-foreground: oklch(0.92 0.03 200);
  --accent: oklch(0.78 0.11 195);
  --accent-foreground: oklch(0.20 0.04 210);

  --destructive: oklch(0.68 0.19 25);
  --destructive-foreground: oklch(0.17 0.03 25);
  --success: oklch(0.74 0.15 160);
  --success-foreground: oklch(0.17 0.03 160);
  --warning: oklch(0.84 0.14 85);
  --warning-foreground: oklch(0.22 0.04 80);
  --info: oklch(0.74 0.12 275);
  --info-foreground: oklch(0.17 0.03 275);

  --success-soft: oklch(0.30 0.06 160);
  --success-soft-foreground: oklch(0.88 0.10 160);
  --warning-soft: oklch(0.32 0.06 90);
  --warning-soft-foreground: oklch(0.90 0.10 90);
  --destructive-soft: oklch(0.30 0.07 25);
  --destructive-soft-foreground: oklch(0.88 0.062 25);
  --info-soft: oklch(0.30 0.07 275);
  --info-soft-foreground: oklch(0.88 0.058 275);

  --chart-1: oklch(0.72 0.12 245);
  --chart-2: oklch(0.78 0.11 195);
  --chart-3: oklch(0.76 0.15 55);
  --chart-4: oklch(0.72 0.15 305);
  --chart-5: oklch(0.70 0.02 245);

  --spc-limit: oklch(0.70 0.19 27);
  --spc-spec: oklch(0.80 0.14 65);
}

@theme inline {
  --font-sans: "Geist Variable", ui-sans-serif, system-ui, sans-serif;
  --font-mono: "Geist Mono Variable", ui-monospace, "SF Mono", monospace;

  --radius-sm: calc(var(--radius) - 2px);
  --radius-md: var(--radius);
  --radius-lg: calc(var(--radius) + 2px);
  --radius-xl: calc(var(--radius) + 6px);

  --color-background: var(--background);
  --color-foreground: var(--foreground);
  --color-card: var(--card);
  --color-card-foreground: var(--card-foreground);
  --color-popover: var(--popover);
  --color-popover-foreground: var(--popover-foreground);
  --color-primary: var(--primary);
  --color-primary-foreground: var(--primary-foreground);
  --color-secondary: var(--secondary);
  --color-secondary-foreground: var(--secondary-foreground);
  --color-muted: var(--muted);
  --color-muted-foreground: var(--muted-foreground);
  --color-accent: var(--accent);
  --color-accent-foreground: var(--accent-foreground);
  --color-destructive: var(--destructive);
  --color-destructive-foreground: var(--destructive-foreground);
  --color-success: var(--success);
  --color-success-foreground: var(--success-foreground);
  --color-warning: var(--warning);
  --color-warning-foreground: var(--warning-foreground);
  --color-info: var(--info);
  --color-info-foreground: var(--info-foreground);
  --color-success-soft: var(--success-soft);
  --color-success-soft-foreground: var(--success-soft-foreground);
  --color-warning-soft: var(--warning-soft);
  --color-warning-soft-foreground: var(--warning-soft-foreground);
  --color-destructive-soft: var(--destructive-soft);
  --color-destructive-soft-foreground: var(--destructive-soft-foreground);
  --color-info-soft: var(--info-soft);
  --color-info-soft-foreground: var(--info-soft-foreground);
  --color-border: var(--border);
  --color-input: var(--input);
  --color-ring: var(--ring);
  --color-chart-1: var(--chart-1);
  --color-chart-2: var(--chart-2);
  --color-chart-3: var(--chart-3);
  --color-chart-4: var(--chart-4);
  --color-chart-5: var(--chart-5);
  --color-spc-limit: var(--spc-limit);
  --color-spc-spec: var(--spc-spec);
  --color-spc-center: var(--spc-center);
  --color-spc-violation: var(--spc-violation);
  --color-spc-warning: var(--spc-warning);
  --color-sidebar: var(--sidebar);
  --color-sidebar-foreground: var(--sidebar-foreground);
  --color-sidebar-primary: var(--sidebar-primary);
  --color-sidebar-primary-foreground: var(--sidebar-primary-foreground);
  --color-sidebar-accent: var(--sidebar-accent);
  --color-sidebar-accent-foreground: var(--sidebar-accent-foreground);
  --color-sidebar-border: var(--sidebar-border);
  --color-sidebar-ring: var(--sidebar-ring);
}

@theme {
  --shadow-card: 0 1px 2px oklch(0.21 0.03 250 / 0.05);
  --shadow-pop: 0 4px 12px oklch(0.21 0.03 250 / 0.12), 0 1px 3px oklch(0.21 0.03 250 / 0.08);
}

@layer base {
  * { @apply border-border outline-ring/50; }
  body {
    @apply bg-background text-foreground font-sans antialiased text-sm;
  }
  .tabular, [data-numeric] { font-variant-numeric: tabular-nums; }
  @media (prefers-reduced-motion: reduce) {
    *, *::before, *::after { animation-duration: 0.01ms !important; transition-duration: 0.01ms !important; }
  }
}
```

### 3.1 Semántica de datos científicos → tokens (no inventar colores nuevos)

| Concepto | Token | Estilo de línea / marcador | Etiqueta obligatoria |
|---|---|---|---|
| Serie observada | `--chart-1` | línea 2 px + círculo 4 px | nombre del parámetro + unidad |
| Línea central (media/mediana) | `--spc-center` | línea sólida 1 px | "CL" o "Media" |
| Límites de control UCL/LCL | `--spc-limit` | **discontinua** `6 4` | "UCL" / "LCL" + valor |
| Límite normativo / especificación | `--spc-spec` | **punto-raya** `2 4 8 4` | norma + valor + unidad, tal como vienen del catálogo (formato: `<regulación> · <valor> <unidad>`)* |
| Punto en alerta temprana | `--spc-warning` | **triángulo** relleno | número de regla |
| Punto que viola regla | `--spc-violation` | **rombo** relleno, mayor tamaño | número de regla (R1…) |
| Valor censurado (`< LOQ`) | `--chart-5` | **círculo hueco** + "<" | "< LOQ" |
| Dato con flag de calidad | `--muted-foreground` | marcador con borde punteado | flag (p. ej. "QC fallido") |

\* Los nombres y valores normativos salen del catálogo compartido (`catalog/`), **nunca** se escriben a mano en la UI.

**Screening referencial (`ScreeningBadge`)** — valores del API `screeningFlag`. **Nunca** usar "Cumple" ni "Excede": el screening compara una observación con un rango de referencia del catálogo y **no** es un dictamen de cumplimiento legal.

| `screeningFlag` | Etiqueta UI | Tokens | Ícono |
|---|---|---|---|
| `normal` | Dentro de rango | `success-soft` | `CheckCircle2` |
| `above_range` | Sobre el rango (referencial) | `warning-soft` | `ArrowUpCircle` |
| `below_range` | Bajo el rango (referencial) | `warning-soft` | `ArrowDownCircle` |
| `not_evaluable` | No evaluable | `muted` | `MinusCircle` |

Se usa **ámbar** (no rojo) a propósito: fuera de rango referencial ≠ infracción. Si el límite está en `draft`, agregar la nota "Pendiente de validación".

**Estado de proceso (SPC):** *En control* → `success-soft` · *Alerta temprana* → `warning-soft` · *Fuera de control* → `destructive-soft` · *Datos insuficientes (n < 20 en línea base)* → `info-soft`.

---

## 4. Tipografía

**Familias** (autoalojadas con Fontsource):

- UI: **Geist Variable** → `pnpm add @fontsource-variable/geist`
- Datos: **Geist Mono Variable** → `pnpm add @fontsource-variable/geist-mono`
- Importar en `web/src/main.tsx`: `import "@fontsource-variable/geist"; import "@fontsource-variable/geist-mono";`
- (Verificar los nombres exactos de `font-family` tras instalar: deben coincidir con `--font-sans` / `--font-mono`. Alternativa sin riesgo: `@fontsource-variable/inter` + `@fontsource-variable/jetbrains-mono`, pero eso acerca la identidad a TerraPlan.)

**Escala** (base 14 px, orientada a densidad analítica):

| Rol | Clase Tailwind | Tamaño / interlineado | Peso | Uso |
|---|---|---|---|---|
| h1 | `text-2xl font-semibold tracking-tight` | 24 / 32 | 600 | Título de página |
| h2 | `text-xl font-semibold tracking-tight` | 20 / 28 | 600 | Sección |
| h3 | `text-base font-semibold` | 16 / 24 | 600 | Título de card/gráfico |
| h4 | `text-sm font-semibold uppercase tracking-wide` | 14 / 20 | 600 | Sub-etiqueta |
| body | `text-sm` | 14 / 20 | 400 | Texto general |
| small | `text-xs` | 12 / 16 | 400–500 | Celdas de tablas densas, badges |
| caption | `text-xs text-muted-foreground` | 12 / 16 | 400 | Fuentes, notas al pie de gráfico |
| data | `font-mono tabular-nums` | hereda | 400–500 | Valores, unidades, límites, timestamps, IDs |
| kpi | `text-3xl font-mono font-semibold tabular-nums` | 30 / 36 | 600 | Cifra de `StatTile` |

Pesos permitidos: 400, 500, 600. Mínimo absoluto 12 px (solo caption y celdas).
Símbolos: usar `µ` (U+00B5), `°C`, `σ`, `x̄`, subíndices con `<sub>`; unidades siempre con espacio fino ("12,4 mg/L").

---

## 5. Espaciado, layout y responsive

- **Base 4 px** (escala Tailwind). Prohibido valores arbitrarios salvo dimensiones de gráficos.
- **Contenedor:** `mx-auto w-full max-w-[1440px] px-4 sm:px-6 lg:px-8`.
- **Breakpoints (mobile-first):** `sm 640` · `md 768` · `lg 1024` · `xl 1280` · `2xl 1536`.
- **App shell:**
  - `≥ lg`: **sidebar** 240 px (colapsable a 56 px) + **barra de filtros globales** sticky (sitio, parámetro, rango de fechas).
  - `< lg`: top bar con menú (sheet) y filtros dentro de un `Sheet` ("Filtros").
- **Grid de dashboards:** `grid grid-cols-1 gap-4 md:grid-cols-6 xl:grid-cols-12`.
  - Fila KPI: 4 `StatTile` (`xl:col-span-3` c/u).
  - Gráfico principal: `xl:col-span-8`; panel de reglas/alertas: `xl:col-span-4`.
  - Tabla de observaciones: `xl:col-span-12`.
- **Alturas de control:** `sm 32 px` · `md 36 px` (defecto) · `lg 44 px`.
- **Sombras/radio/movimiento:** sombras casi nulas (`shadow-card` apenas perceptible); `rounded-md` en casi todo; transiciones 120 ms `ease-out`; respeta `prefers-reduced-motion`.

---

## 6. Componentes base

Todos salen de **shadcn/ui** (`pnpm dlx shadcn@latest add ...`) usando solo tokens.

### 6.1 Botones

| Variante | Clases clave | Cuándo |
|---|---|---|
| `primary` | `bg-primary text-primary-foreground hover:bg-primary/90` | Acción principal (ej. "Calcular límites") |
| `secondary` | `bg-secondary text-secondary-foreground hover:bg-secondary/80` | Acción alternativa |
| `outline` | `border border-input bg-background hover:bg-accent` | Exportar, filtros |
| `ghost` | `hover:bg-accent hover:text-accent-foreground` | Acciones en tablas/toolbars de gráfico |
| `danger` (`destructive`) | `bg-destructive text-destructive-foreground hover:bg-destructive/90` | Eliminar sensor/serie |

Tamaños: `sm` 32 px · `md` 36 px (defecto) · `lg` 44 px. Foco: `focus-visible:ring-2 ring-ring ring-offset-2`. Botones solo-ícono con `aria-label`.

### 6.2 Cards

`rounded-md border bg-card text-card-foreground shadow-card`. Padding `p-4` (gráficos: `p-4 pb-2`). Hover solo si es clicable (`hover:border-ring/50`). Estructura de card de gráfico: **título (h3) · subtítulo con rango y n · acciones (exportar PNG/CSV) · gráfico · pie con fuente y método**.

### 6.3 Inputs / Selects / Textareas

| Estado | Estilo |
|---|---|
| default | `h-9 rounded-md border border-input bg-background px-3 text-sm` |
| focus | `ring-2 ring-ring ring-offset-2` |
| error | `border-destructive`, `aria-invalid`, mensaje con `AlertCircle` + `aria-describedby` |
| disabled | `bg-muted text-muted-foreground cursor-not-allowed` |

`ParameterSelect` y `SiteSelect` con búsqueda (Combobox). Rango de fechas con presets (24 h, 7 d, 30 d, personalizado). Fechas en `America/Santiago` visible, UTC almacenado.

### 6.4 Badges

`inline-flex items-center gap-1 rounded-sm px-2 py-0.5 text-xs font-medium` + par `*-soft`/`*-soft-foreground` + ícono 12–14 px + texto. Códigos de regla SPC (`R1`, `R2`…) en `font-mono`.

### 6.5 Tablas de datos (TanStack Table)

- Densidad compacta: fila `h-9`, texto `text-xs`; cabecera sticky `uppercase tracking-wide text-muted-foreground`.
- Orden multicolumna con `aria-sort`; filtros por columna; selector de columnas.
- Valores numéricos alineados a la **derecha** en `font-mono tabular-nums`; **mismo número de decimales por parámetro** (lo define el catálogo).
- Valor censurado: `< 0,5` con el operador visible. Flag de calidad: badge pequeño al lado.
- Paginación server-side (25 / 50 / 100) + "Mostrando 1–50 de 12.480". Exportar CSV (respeta filtros).
- `< md`: columnas prioritarias + fila expandible (no scroll horizontal oculto).

### 6.6 Navegación

Sidebar: **Resumen · Sitios · Series · Control (SPC) · Screening · Pipeline · Ajustes**. Ítem activo `bg-sidebar-accent` + `aria-current="page"`. Skip-link al inicio.

### 6.7 Estados de carga, vacío y error (obligatorios)

| Estado | Patrón |
|---|---|
| Carga | `Skeleton` con la **forma del gráfico/tabla** (ejes fantasma), `aria-busy="true"` |
| Vacío | Ícono + "Sin observaciones en este rango" + sugerencia (ampliar rango / cambiar sitio) |
| Datos insuficientes | `info-soft` + explicación ("Se requieren ≥ 20 observaciones para la línea base") |
| Error | Banner `destructive-soft` + mensaje humano + "Reintentar" + `requestId` en `font-mono text-xs` |
| Dato obsoleto | Chip "Última observación hace 3 h" en `warning-soft` si supera la frecuencia esperada |

---

## 7. Gráficos (shadcn `chart` sobre Recharts)

Todos dentro de `ChartContainer`, colores vía `var(--chart-n)` / `var(--spc-*)` (nunca hex).

| Gráfico | Especificación |
|---|---|
| **Tendencia (línea)** | Serie `--chart-1` 2 px; media móvil opcional `--chart-2` discontinua fina; banda de incertidumbre al 15 % de opacidad; eje X temporal en `America/Santiago`; eje Y con unidad en el título del eje. |
| **Dispersión (scatter)** | Puntos 4–5 px con borde; recta de regresión + `R²` y `n` visibles; ejes con unidades; opción de escala log. |
| **Carta de control (I-MR / X̄-R)** | Panel superior: observaciones + CL + UCL/LCL (discontinuas) + límites normativos (punto-raya). Panel inferior: rangos móviles con UCL. Puntos que violan reglas: **rombo + etiqueta Rn**. Zonas A/B/C opcionales sombreadas (σ). Tooltip: valor, unidad, timestamp, sitio, regla violada. |
| **Histograma** | Barras `--chart-1` 70 % opacidad, bins explícitos, línea de límite normativo. |
| **Sparkline (KPI)** | 1 px `--chart-1`, sin ejes, `aria-hidden` con texto alternativo en el KPI. |

**Reglas comunes de gráficos**
1. Eje con **unidad** y nombre; títulos que dicen *qué* y *dónde*.
2. Leyenda o etiquetado directo; nunca depender solo del color.
3. Pie del gráfico: `Fuente: <sitio> · <parámetro> · método <x> · catálogo v<n> · actualizado <hora>`.
4. Panel **"¿Cómo se calculó?"** (acordeón) con fórmula, constantes (p. ej. `2,66·MR̄`), periodo de línea base y reglas activas.
5. Gráficos **no interactivos son accesibles**: tabla equivalente disponible ("Ver como tabla") y `aria-label` descriptivo del hallazgo principal.
6. Máx. 5 series por gráfico.

---

## 8. Accesibilidad (WCAG 2.2 AA)

- Contraste: texto ≥ 4,5:1; UI y series ≥ 3:1 (validado, sección 10).
- Foco visible siempre; teclado completo; diálogos de Radix con trampa de foco.
- Íconos informativos con `aria-label`; decorativos `aria-hidden`.
- Estados con **color + forma/ícono + texto**; series con patrones de línea distintos.
- Gráficos con alternativa tabular y resumen textual (`aria-describedby`).
- Objetivo táctil mínimo 24 px (WCAG 2.5.8); controles de 32–36 px en escritorio.
- Respeta `prefers-reduced-motion` y `prefers-color-scheme`. `<html lang="es-CL">`.
- Números: `Intl.NumberFormat("es-CL")` (coma decimal, punto de miles). Documentarlo en el README; el validador de dominio puede pedir cambiar la convención.

---

## 9. Modo oscuro

Tokens `.dark` definidos desde el inicio. Toggle posterior: clase `dark` en `<html>`, preferencia en `localStorage` (con `try/catch`), por defecto `prefers-color-scheme`. En oscuro, las series usan versiones más claras (ya definidas) y los límites `--spc-limit` / `--spc-spec` mantienen sus estilos de línea.

---

## 10. Validación de contraste

Script reproducible (`scripts/contrast-check.py`, convierte OKLCH → sRGB y calcula la razón WCAG):

| Tema | Mínimo texto (req. 4,5) | Mínimo UI (req. 3,0) |
|---|---|---|
| Light | 5,91 | 3,27 |
| Dark | 6,12 | 4,24 |

Pares verificados: `foreground/background|card`, `*-foreground` sobre su fondo, `muted-foreground` sobre `background|card|muted`, pares `*-soft`, `input` y `ring` sobre `background|card`, `chart-1…5`, `spc-limit` y `spc-spec` sobre `card`.
**Regla:** si se cambia un token, repetir la verificación antes de commitear.

---

## 11. Referencias visuales (qué tomamos y qué no)

Verificadas durante el diseño:

- **Lough Neagh Water Quality Dashboard** (DAERA, Irlanda del Norte): visor público de telemetría (sondas cada 30 min: temperatura, oxígeno disuelto, turbidez, conductividad, ficocianina) sobre nueve sitios, con FAQ metodológica y vínculo a la plataforma científica. *Tomamos:* selección clara de sitio/parámetro, FAQ y transparencia de fuente (→ panel "¿Cómo se calculó?").
- **HawkesburyWatch** (Hornsby Shire Council, Australia): siete estaciones en tiempo real (15–30 min), salud del estuario, notas metodológicas embebidas y alertas por umbral. *Tomamos:* explicación del método dentro del dashboard y alertas ligadas a umbrales.
- **Cartas de control (Shewhart) estándar de la literatura SPC:** *Tomamos:* convención de CL/UCL/LCL, zonas A/B/C y reglas numeradas.
- **Red Dot Award de monitoreo de agua:** mencionado en el brief, **no se pudo verificar** una referencia concreta; no se usa como fuente.
- Estilo general inspirado en consolas de observabilidad/analítica (tinta mínima, tablas densas, ejes sobrios). No se copian layouts ni marcas.

Fuentes: [DAERA – Lough Neagh Water Quality Dashboard FAQ](https://www.daera-ni.gov.uk/articles/lough-neagh-water-quality-dashboard-faq) · [DAERA – Lough Neagh data viewer](https://www.daera-ni.gov.uk/news/daera-launches-lough-neagh-blue-green-data-viewer) · [HawkesburyWatch – data.nsw.gov.au](https://data.nsw.gov.au/data/dataset/5c2d7648-93b8-4f37-b1b0-2b420f5b9b75) · [Hornsby Shire Council – Latest catchment health results](https://www.hornsby.nsw.gov.au/Environment/Waterways/Using-water-quality-information/Latest-catchment-health-results)

---

## 12. Relación con TerraPlan (NestJS)

| Aspecto | AquaMetric (este) | TerraPlan |
|---|---|---|
| Color primario | Azul océano (hue ≈ 250) | Verde profundo (hue ≈ 158) |
| Acento | Turquesa | Ámbar cálido (alertas) |
| Info | Índigo | Azul |
| Radio | 0.375 rem (preciso) | 0.5 rem (amigable) |
| Densidad | Densa, analítica (base 14 px) | Cómoda, táctil (base 16 px) |
| Fuente UI / datos | Geist / Geist Mono | Inter / JetBrains Mono |
| Navegación | Sidebar + filtros globales | Bottom nav + sidebar |
| Ancla visual | Carta de control | Línea de tiempo de recursos |

**Misma filosofía:** tokens semánticos con los mismos nombres base, mismos estados (éxito/advertencia/peligro/info), mismas reglas de accesibilidad, cifras en monoespaciada, estado = color + forma/ícono + texto. Los **nombres de parámetros, unidades y límites** son idénticos porque salen del **catálogo compartido** (ver `.clinerules/01-project-context.md`).

---

## 13. Checklist de revisión de UI (antes de cerrar una pantalla)

- [ ] Solo tokens (ni hex, ni `bg-blue-600`, ni valores arbitrarios).
- [ ] Carga, vacío, datos insuficientes y error implementados.
- [ ] Se ve bien a 390 px (filtros en Sheet) y a 1440 px.
- [ ] Foco visible; teclado completo; alternativa tabular en gráficos.
- [ ] Límite de control ≠ límite normativo (estilos distintos y etiquetados).
- [ ] Valores censurados y flags de calidad visibles.
- [ ] Unidades, decimales y fuente/método presentes en cada gráfico.
- [ ] Textos de UI en español claro, formato es-CL.

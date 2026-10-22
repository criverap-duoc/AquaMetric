# 04 · Directivas UI/UX — AquaMetric (frontend `web/`)

> **Fuente de verdad visual: `docs/design-system.md`.** Este archivo dice *cómo aplicarlo*. No duplicar tokens aquí.
> Leer el design system **solo al crear o modificar UI** y **solo la sección necesaria** (ahorro de tokens). Nunca pegarlo en las respuestas.
> Meta: que parezca una herramienta científica profesional (lo que ve el reclutador) **sin** retrasar el MVP.

## 1. Orden de arranque del frontend (una sola vez)

1. `pnpm create vite web --template react-ts` → limpiar demo. Alias `@/` en `tsconfig` y `vite.config.ts`.
2. `pnpm --filter web add tailwindcss @tailwindcss/vite tw-animate-css lucide-react` (Tailwind 4 por plugin de Vite; sin `tailwind.config.js`).
3. `pnpm dlx shadcn@latest init` (estilo *new-york*, base *neutral*; **luego sustituir** `globals.css` por el bloque de `docs/design-system.md` §3).
4. Fuentes: `pnpm --filter web add @fontsource-variable/geist @fontsource-variable/geist-mono` e importarlas en `main.tsx`. Verificar nombres de `font-family` vs `--font-sans`/`--font-mono` (alternativa: Inter + JetBrains Mono, pero perdería diferenciación con TerraPlan).
5. `<html lang="es-CL">`; clase `dark` aplicable a `<html>` (toggle después).
6. Componentes base: `pnpm dlx shadcn@latest add button card input label select textarea badge table skeleton dialog sheet dropdown-menu tabs tooltip sonner form popover command calendar accordion chart` (`chart` trae Recharts).
7. Instalar `@tanstack/react-query @tanstack/react-table react-router`.
8. Crear `lib/format.ts`, `lib/api-client.ts`, `components/domain/`.

## 2. Reglas de oro (obligatorias en TODO cambio de UI)

1. **Solo tokens semánticos.** Prohibido: hex, `rgb()`, `oklch()` sueltos, clases de paleta (`bg-blue-600`, `text-slate-500`), valores arbitrarios (`p-[13px]`) — salvo dimensiones de gráficos.
2. **Estado = color + forma/ícono + texto.** Nunca solo color (carta de control: rombo/triángulo/hueco + etiqueta `R1…R5`).
3. **Todo dato remoto tiene estados:** carga (Skeleton con la forma del gráfico/tabla), vacío, **datos insuficientes** (`info-soft`), error (`destructive-soft` + reintentar + `requestId`), éxito.
4. **Rigor visible:** todo gráfico lleva unidad en el eje, rango y `n`, y un pie con **fuente · método · versión de catálogo · hora de actualización**. Panel "¿Cómo se calculó?" en análisis SPC.
5. **Límite de control ≠ límite normativo ≠ LOQ.** Estilos y etiquetas distintos (ver tabla §3.1 del design system). Nunca mezclarlos ni llamarlos "límites" sin apellido.
6. **Números, unidades, timestamps y límites** en `font-mono tabular-nums` vía `lib/format.ts`; decimales por parámetro desde el catálogo; censurados como `< 0,5 mg/L`.
7. **Componentes shadcn primero.** No reinventar; extender con `cva` y tokens.
8. **Accesibilidad:** foco visible, `label` visible, `aria-label` en botones-ícono, teclado completo, y **alternativa tabular** ("Ver como tabla") para cada gráfico.
9. **Densidad con respiro:** base 14 px, tablas `text-xs`, pero con jerarquía y espaciado de la escala (múltiplos de 4).
10. **Textos en español claro (es-CL)**; terminología del glosario (§5). Sin jerga de programador en pantalla.
11. **Sin librerías de UI/gráficos nuevas** (MUI, Chart.js, Plotly…). Solo shadcn + Recharts + `lucide-react`.
12. **Un h1 por página**; una acción `primary` por vista.

## 3. Cheat-sheet de tokens (resumen; detalle en el design system)

| Necesito… | Usar |
|---|---|
| Fondo / texto | `bg-background text-foreground` (body ya es `text-sm`) |
| Card | `bg-card text-card-foreground border rounded-md shadow-card p-4` |
| Texto secundario | `text-muted-foreground` |
| Acción principal / alternativa / neutra / sutil / peligrosa | `<Button>` (default) · `secondary` · `outline` · `ghost` · `destructive` |
| Borde de campo | `border-input` · foco `ring-2 ring-ring ring-offset-2` |
| Badge OK / alerta / error / info | `bg-success-soft text-success-soft-foreground` · `warning-soft` · `destructive-soft` · `info-soft` |
| Radio / sombra | `rounded-md` · `shadow-card` (casi nula) · `shadow-pop` (menús) |
| Series | `var(--chart-1…5)` (azul, turquesa, naranja, violeta, gris) |
| SPC | `var(--spc-center)` · `--spc-limit` (UCL/LCL, discontinua) · `--spc-spec` (norma, punto-raya) · `--spc-violation` · `--spc-warning` |
| Tipografía | h1 `text-2xl font-semibold tracking-tight` · h2 `text-xl` · h3 `text-base font-semibold` · body `text-sm` · caption `text-xs text-muted-foreground` · KPI `text-3xl font-mono font-semibold tabular-nums` |
| Contenedor | `mx-auto w-full max-w-[1440px] px-4 sm:px-6 lg:px-8` |
| Grid dashboard | `grid grid-cols-1 gap-4 md:grid-cols-6 xl:grid-cols-12` |
| Alturas de control | `sm` 32 · `md` 36 (def.) · `lg` 44 px |

## 4. Layout y responsive

- **App shell:** `≥ lg` sidebar 240 px (colapsable a 56) + **barra de filtros globales** sticky (Sitio · Parámetro · Rango de fechas). `< lg` top bar con menú (Sheet) y filtros en un Sheet "Filtros".
- Filtros globales **en la URL** (`?site=…&param=…&from=…&to=…`) para enlaces compartibles (útil para reguladores).
- Tablas: `≥ md` tabla densa (sticky header, orden multicolumna, paginación server-side 25/50/100, exportar CSV); `< md` columnas prioritarias + fila expandible.
- Dashboard: fila de 4 `StatTile` → gráfico principal (`xl:col-span-8`) + panel de reglas/alertas (`xl:col-span-4`) → tabla (`xl:col-span-12`).
- Probar mentalmente a **390 px** y **1440 px** antes de cerrar.

## 5. Pantallas del MVP, componentes y glosario

| Pantalla | Contenido clave | Componentes de dominio |
|---|---|---|
| **Resumen** | KPIs (observaciones 24 h, sitios activos, series fuera de control, observaciones fuera de rango referencial), últimas alertas, última ingesta | `StatTile`, `ScreeningBadge`, `ProcessStatusBadge` |
| Sitios | Lista + detalle (últimos valores por parámetro, frescura del dato) | `SiteSelect`, `StatTile`, `QcFlag` |
| **Series** | Tendencia + dispersión + tabla de observaciones | `TrendChart`, `ScatterPlot`, `DataTable`, `QcFlag` |
| **Control (SPC)** | Carta I-MR/X̄-R, reglas violadas, línea base, capacidad, panel de método | `ControlChart`, `MethodPanel`, `ProcessStatusBadge` |
| **Screening** | Observaciones vs rango de referencia del catálogo, con selector de **regulación/contexto** y aviso fijo "Referencial: no es un dictamen de cumplimiento legal" (tabla + resumen) | `ScreeningBadge`, `LimitBadge` |
| Pipeline | Últimas ingestas (desde `ingest_idempotency`), última lectura por sitio. Estado AWS/cuarentena **solo si el pipeline existe**; si no, estado vacío "Pipeline AWS no desplegado" (no es un error) | `StatTile`, `DataTable` |
| Ajustes | Versión del catálogo, parámetros/unidades/límites (lectura) con "Pendiente de validación" | `ParameterChip`, `LimitBadge` |

Componentes de dominio en `web/src/components/domain/`; especificación en `docs/design-system.md` §3.1, §6 y §7.

**Glosario de copy (usar estos términos):** *Observación* · *Sitio* · *Parámetro* · *Límite de control (UCL/LCL)* · *Límite normativo* · *Línea base* · *En control / Fuera de control / Alerta temprana* · *Límite de cuantificación (LOQ)* · *Valor censurado* · *Pendiente de validación* · *Dentro de rango / Sobre el rango (referencial) / Bajo el rango (referencial) / No evaluable* (**nunca** "Cumple" ni "Excede") · *Datos insuficientes*. Mensajes de error: decir **qué falta o qué hacer** ("Se requieren 20 observaciones para la línea base; hay 12"), nunca "Error 422".

## 6. Gráficos (implementación)

- Siempre dentro de `ChartContainer` (shadcn) con `config` que referencia `var(--chart-n)` / `var(--spc-*)`.
- **Carta de control:** `ComposedChart` con panel superior (observaciones + `ReferenceLine` CL sólida, UCL/LCL `strokeDasharray="6 4"`, norma `strokeDasharray="2 4 8 4"`) y panel inferior MR. Puntos que violan reglas: `shape` personalizada (**rombo** + etiqueta `R1…R5`); alerta temprana: **triángulo**; censurado: **círculo hueco** + `<`.
- Tooltip: valor + unidad (mono), timestamp `America/Santiago`, sitio, `qcFlag`, regla violada.
- Series > 2 000 puntos: pedir `max_points` al API (downsampling en servidor); nunca renderizar decenas de miles de nodos SVG.
- `role="img"` + `aria-label` con el hallazgo principal ("3 puntos fuera de límites de control, regla R1") + `aria-describedby` al resumen; botón **"Ver como tabla"** accesible por teclado.
- Máx. 5 series por gráfico; etiquetas directas cuando sea posible.
- Pie de gráfico obligatorio: `Fuente: … · Método: … · Catálogo v… · Actualizado …`.

## 7. Formato (es-CL)

`lib/format.ts` es el único lugar que formatea:
- Fechas/horas: `Intl.DateTimeFormat("es-CL", { timeZone: "America/Santiago" })`.
- Números: `Intl.NumberFormat("es-CL")` (coma decimal, punto de miles), **decimales por parámetro** (`Parameter.decimals`).
- Unidades con espacio fino y símbolos correctos (`µg/L`, `µS/cm`, `°C`, `NTU`).
- Censurados: `< 0,5 mg/L`. Sin valor: `—`.
- Documentar en el README que la convención decimal es es-CL; el químico puede pedir cambiarla.

## 8. Modo oscuro

Tokens `.dark` ya definidos. **No** implementar el toggle hasta desplegar el MVP, pero verificar que ningún componente nuevo use colores fijos (así el modo oscuro "funciona solo" después).

## 9. Datos de demo para que la UI luzca

Cargar con el simulador (`seed` fija): ≥ 30 días × ≥ 4 sitios × ≥ 5 parámetros, con *shift*, *spike*, *drift*, *dropout* y censurados, de modo que **al menos una carta muestre violaciones R1 y R2** y el Resumen tenga alertas reales. Sin "Lorem ipsum" ni "Sitio 1".

## 10. Definición de terminado (UI)

Antes de cerrar una pantalla (ver también `docs/design-system.md` §13):

- [ ] Cero colores/valores fuera de los tokens.
- [ ] Carga, vacío, datos insuficientes y error implementados.
- [ ] Correcta a 390 px y 1440 px; filtros en Sheet en móvil.
- [ ] Foco visible, teclado completo, alternativa tabular en gráficos.
- [ ] Límite de control ≠ límite normativo (estilos y etiquetas).
- [ ] Valores censurados y flags de calidad visibles; pie con fuente/método.
- [ ] Números/unidades en mono, es-CL, decimales del catálogo.
- [ ] `pnpm --filter web typecheck` y `lint` en verde (**N1**).
- [ ] Recordar a Cristóbal: **capturar GIF/pantallazo** para el README.

## 11. Colaboración con el químico (no programador)

- Al cambiar una pantalla, describir el cambio en **1–2 frases en lenguaje simple** (qué ve el analista), para que pueda opinar.
- Los textos y valores de dominio (parámetros, unidades, límites, política de censurados) los **valida él**: marcarlos "Pendiente de validación" y no inventarlos.
- Mantener `docs/glossary.md` y `docs/spc-methods.md` en lenguaje simple y al día.

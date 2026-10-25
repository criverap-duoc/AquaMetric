import { Download, Table2 } from "lucide-react";
import { useMemo, useState } from "react";
import {
  CartesianGrid,
  ComposedChart,
  Line,
  ReferenceLine,
  XAxis,
  YAxis,
  type DotItemDotProps,
  type TooltipContentProps,
} from "recharts";

import { DataTable } from "@/components/domain/DataTable";
import { ProcessStatusBadge } from "@/components/domain/ProcessStatusBadge";
import { QcFlagBadge } from "@/components/domain/QcFlagBadge";
import { Button } from "@/components/ui/button";
import { Card, CardAction, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { ChartContainer, ChartTooltip, type ChartConfig } from "@/components/ui/chart";
import {
  SIGNAL_BEYOND_LIMIT,
  SIGNAL_WARNING,
  buildChartRows,
  chartDomain,
  describeSignal,
  type ChartRow,
} from "@/features/control/chart-rows";
import { createControlColumns } from "@/features/control/control-columns";
import type { ControlObservation, ControlSpecLimit } from "@/features/control/types";
import { formatDateTime, formatDay, formatNumber, formatUnit } from "@/lib/format";
import type { ControlLimits, RuleViolation } from "@/types/api";

export interface ControlChartProps {
  /** Values of the series, ascending by `analyzedAt`. */
  observations: ControlObservation[];
  /** Controls limits of the chart of individuals, estimated in Phase I by `app/spc/`. */
  individuals: ControlLimits;
  /** Limits of the moving-range chart; `null` when the API could not build them. */
  movingRange: ControlLimits | null;
  /** Signals the R1–R5 scan found in the monitoring window. */
  violations: RuleViolation[];
  /**
   * Normative range, if one is validated. It is drawn with its own style and label: a normative
   * limit is not a control limit (04 §2.5).
   */
  specLimits?: ControlSpecLimit | null;
  parameterName: string;
  unitCode: string;
  /** Decimals of the parameter, read from the catalog. */
  decimals: number;
  siteCode: string;
  catalogVersion: string;
  /** Instant of the last successful fetch, for the mandatory footnote. */
  updatedAt: Date;
}

const INDIVIDUALS_CONFIG = {
  value: { label: "Observación", color: "var(--chart-1)" },
} satisfies ChartConfig;

const RANGE_CONFIG = {
  movingRange: { label: "Rango móvil", color: "var(--chart-2)" },
} satisfies ChartConfig;

const AXIS_TICK_STYLE = { fontSize: 11 } as const;
const Y_AXIS_WIDTH = 64;
const Y_AXIS_LABEL_STYLE = { fontSize: 11, textAnchor: "middle" } as const;
const DIAMOND_RADIUS = 6;
const WARNING_RADIUS = 5;
const DOT_RADIUS = 3;
const SUMMARY_ID = "control-chart-summary";
const TABLE_ID = "control-chart-table";

/** Diamond for a rule violation, triangle for the early-warning band, dot for everything else. */
function IndividualDot(props: DotItemDotProps) {
  const row = props.payload as ChartRow;
  const { cx, cy } = props;

  if (typeof cx !== "number" || typeof cy !== "number") {
    return <g />;
  }

  if (row.signal === SIGNAL_BEYOND_LIMIT) {
    return (
      <g>
        <polygon
          points={`${cx},${cy - DIAMOND_RADIUS} ${cx + DIAMOND_RADIUS},${cy} ${cx},${cy + DIAMOND_RADIUS} ${cx - DIAMOND_RADIUS},${cy}`}
          fill="var(--spc-violation)"
        />
        <text
          x={cx + DIAMOND_RADIUS + 2}
          y={cy - DIAMOND_RADIUS}
          className="fill-foreground font-mono text-[10px]"
        >
          {SIGNAL_BEYOND_LIMIT}
        </text>
      </g>
    );
  }

  if (row.signal === SIGNAL_WARNING) {
    return (
      <g>
        <polygon
          points={`${cx},${cy - WARNING_RADIUS - 1} ${cx + WARNING_RADIUS + 1},${cy + WARNING_RADIUS} ${cx - WARNING_RADIUS - 1},${cy + WARNING_RADIUS}`}
          fill="var(--spc-warning)"
        />
        <text
          x={cx + WARNING_RADIUS + 3}
          y={cy - WARNING_RADIUS}
          className="fill-muted-foreground font-mono text-[10px]"
        >
          {SIGNAL_WARNING}
        </text>
      </g>
    );
  }

  return <circle cx={cx} cy={cy} r={DOT_RADIUS} fill="var(--chart-1)" />;
}

/** A censored value is drawn at its LOQ, hollow and labelled: it is never a zero. */
function CensoredDot(props: DotItemDotProps) {
  const { cx, cy } = props;

  if (typeof cx !== "number" || typeof cy !== "number") {
    return <g />;
  }

  return (
    <g>
      <circle
        cx={cx}
        cy={cy}
        r={DOT_RADIUS + 1}
        fill="none"
        stroke="var(--chart-5)"
        strokeWidth={1.5}
      />
      <text
        x={cx + DOT_RADIUS + 3}
        y={cy + 3}
        className="fill-muted-foreground font-mono text-[10px]"
      >
        {"<"}
      </text>
    </g>
  );
}

type ControlTooltipProps = TooltipContentProps & {
  unitCode: string;
  decimals: number;
  isRangePanel: boolean;
};

function ControlTooltip({
  active,
  payload,
  unitCode,
  decimals,
  isRangePanel,
}: ControlTooltipProps) {
  const row = payload?.[0]?.payload as ChartRow | undefined;

  if (!active || !row) {
    return null;
  }

  return (
    <div className="grid gap-1 rounded-lg border border-border/50 bg-background px-2.5 py-1.5 text-xs shadow-pop">
      <p className="font-medium">{formatDateTime(row.analyzedAt)}</p>
      <p className="font-mono tabular-nums">
        {isRangePanel ? "MR" : "Valor"}:{" "}
        {isRangePanel
          ? row.movingRange === null
            ? "—"
            : formatUnit(row.movingRange, unitCode, decimals)
          : row.value === null
            ? row.loq === null
              ? "—"
              : `< ${formatNumber(row.loq, decimals)} ${unitCode}`
            : formatUnit(row.value, unitCode, decimals)}
      </p>
      <div className="flex items-center gap-1.5">
        <span className="text-muted-foreground">Calidad:</span>
        <QcFlagBadge flag={row.qcFlag} />
      </div>
      {row.signal ? <p className="max-w-56">{describeSignal(row.signal)}</p> : null}
    </div>
  );
}

/** Symbol key of the two panels: every state is shape **and** colour **and** text (04 §2.2). */
function MarkerLegend({ hasSpecLimit }: { hasSpecLimit: boolean }) {
  return (
    <ul className="flex flex-wrap items-center gap-x-4 gap-y-1 text-xs text-muted-foreground">
      <li className="flex items-center gap-1.5">
        <svg aria-hidden="true" viewBox="0 0 10 10" className="size-2.5">
          <circle cx="5" cy="5" r="4" fill="var(--chart-1)" />
        </svg>
        observación
      </li>
      <li className="flex items-center gap-1.5">
        <svg aria-hidden="true" viewBox="0 0 10 10" className="size-2.5">
          <polygon points="5,0 10,5 5,10 0,5" fill="var(--spc-violation)" />
        </svg>
        fuera de límite (R1)
      </li>
      <li className="flex items-center gap-1.5">
        <svg aria-hidden="true" viewBox="0 0 10 10" className="size-2.5">
          <polygon points="5,0 10,9 0,9" fill="var(--spc-warning)" />
        </svg>
        alerta temprana (2 σ)
      </li>
      <li className="flex items-center gap-1.5">
        <svg aria-hidden="true" viewBox="0 0 10 10" className="size-2.5">
          <circle cx="5" cy="5" r="3.5" fill="none" stroke="var(--chart-5)" strokeWidth="1.5" />
        </svg>
        censurado (&lt; LOQ)
      </li>
      <li className="flex items-center gap-1.5">
        <svg aria-hidden="true" viewBox="0 0 24 6" className="h-1.5 w-6">
          <line x1="0" y1="3" x2="24" y2="3" stroke="var(--spc-limit)" strokeDasharray="6 4" strokeWidth="1.5" />
        </svg>
        límite de control (UCL/LCL)
      </li>
      {hasSpecLimit ? (
        <li className="flex items-center gap-1.5">
          <svg aria-hidden="true" viewBox="0 0 24 6" className="h-1.5 w-6">
            <line x1="0" y1="3" x2="24" y2="3" stroke="var(--spc-spec)" strokeDasharray="2 4 8 4" strokeWidth="1.5" />
          </svg>
          límite normativo
        </li>
      ) : null}
    </ul>
  );
}

/**
 * I-MR control chart: individual values on top, moving range below, both inside one card.
 *
 * Recharts cannot stack two panels in one `ComposedChart`, so the card holds two charts that share
 * margins and axis width: the panels line up and the lower one carries the calendar axis. Every
 * limit, sigma and signal arrives from `app/spc/`; this component only draws them.
 */
export function ControlChart({
  observations,
  individuals,
  movingRange,
  violations,
  specLimits = null,
  parameterName,
  unitCode,
  decimals,
  siteCode,
  catalogVersion,
  updatedAt,
}: ControlChartProps) {
  const [isTableVisible, setIsTableVisible] = useState(false);

  const rows = useMemo(
    () => buildChartRows(observations, individuals),
    [observations, individuals],
  );
  const columns = useMemo(() => createControlColumns(unitCode, decimals), [unitCode, decimals]);

  const domain = useMemo(
    () =>
      chartDomain(rows, [
        individuals.center,
        individuals.ucl,
        individuals.lcl,
        specLimits?.min ?? Number.NaN,
        specLimits?.max ?? Number.NaN,
      ]),
    [rows, individuals, specLimits],
  );

  const rangeRows = useMemo(
    () => rows.map((row) => ({ ...row, value: row.movingRange, censoredAt: null })),
    [rows],
  );

  const rangeDomain = useMemo<[number, number]>(() => {
    if (!movingRange) {
      return [0, 1];
    }

    return chartDomain(rangeRows, [movingRange.center, movingRange.ucl, movingRange.lcl]);
  }, [rangeRows, movingRange]);

  const outOfLimits = rows.filter((row) => row.signal === SIGNAL_BEYOND_LIMIT).length;
  const summary =
    `Carta I-MR de ${parameterName}: ${rows.length} observaciones, línea central ` +
    `${formatNumber(individuals.center, decimals)} ${unitCode} y límites de control de ` +
    `${formatNumber(individuals.lcl, decimals)} a ${formatNumber(individuals.ucl, decimals)} ` +
    `${unitCode}. ${outOfLimits} puntos fuera de los límites de control y ${violations.length} ` +
    `señales de las reglas R1 a R5 en la ventana de monitoreo.`;

  const specLabel = (value: number) =>
    `${specLimits?.regulationCode ?? ""} · ${formatNumber(value, decimals)} ${unitCode}`;

  return (
    <Card className="gap-2 p-4">
      <CardHeader className="p-0">
        <CardTitle>
          <h3 className="text-base font-semibold">Carta I-MR · {parameterName}</h3>
        </CardTitle>
        <p className="text-xs text-muted-foreground">
          n={individuals.nPoints} · método {individuals.method} · {rows.length} puntos dibujados
        </p>
        <CardAction className="flex items-center gap-1">
          <Button
            type="button"
            variant="ghost"
            size="sm"
            aria-pressed={isTableVisible}
            aria-controls={TABLE_ID}
            onClick={() => setIsTableVisible((visible) => !visible)}
          >
            <Table2 aria-hidden="true" />
            Ver como tabla
          </Button>
          {/* TODO(#E-1e): exportar la carta como PNG; el botón queda inerte hasta entonces (04 §2.8). */}
          <Button
            type="button"
            variant="ghost"
            size="icon-sm"
            aria-label="Descargar PNG (disponible en una próxima versión)"
            aria-disabled="true"
            title="Disponible en una próxima versión"
          >
            <Download aria-hidden="true" />
          </Button>
        </CardAction>
      </CardHeader>

      <CardContent className="flex flex-col gap-3 p-0">
        <p id={SUMMARY_ID} className="sr-only">
          {summary}
        </p>

        <div
          role="img"
          aria-label={summary}
          aria-describedby={SUMMARY_ID}
          className="flex flex-col gap-2"
        >
          <ChartContainer config={INDIVIDUALS_CONFIG} className="aspect-auto h-64 w-full">
            <ComposedChart data={rows} margin={{ top: 12, right: 16, bottom: 0, left: 0 }}>
              <CartesianGrid vertical={false} strokeDasharray="3 3" />
              <XAxis
                dataKey="timestamp"
                type="number"
                scale="time"
                domain={["dataMin", "dataMax"]}
                tick={false}
                height={8}
              />
              <YAxis
                domain={domain}
                tickFormatter={(value: number) => value.toFixed(decimals)}
                tick={AXIS_TICK_STYLE}
                width={Y_AXIS_WIDTH}
                label={{
                  value: unitCode,
                  angle: -90,
                  position: "insideLeft",
                  style: Y_AXIS_LABEL_STYLE,
                }}
              />
              <ChartTooltip
                content={(props) => (
                  <ControlTooltip
                    {...props}
                    unitCode={unitCode}
                    decimals={decimals}
                    isRangePanel={false}
                  />
                )}
              />
              <ReferenceLine
                y={individuals.ucl}
                stroke="var(--spc-limit)"
                strokeDasharray="6 4"
                label={{
                  value: `UCL ${formatNumber(individuals.ucl, decimals)}`,
                  position: "insideTopRight",
                  fontSize: 10,
                  fill: "var(--spc-limit)",
                }}
              />
              <ReferenceLine
                y={individuals.center}
                stroke="var(--spc-center)"
                label={{
                  value: `CL ${formatNumber(individuals.center, decimals)}`,
                  position: "insideTopLeft",
                  fontSize: 10,
                  fill: "var(--spc-center)",
                }}
              />
              <ReferenceLine
                y={individuals.lcl}
                stroke="var(--spc-limit)"
                strokeDasharray="6 4"
                label={{
                  value: `LCL ${formatNumber(individuals.lcl, decimals)}`,
                  position: "insideBottomRight",
                  fontSize: 10,
                  fill: "var(--spc-limit)",
                }}
              />
              {specLimits?.max !== undefined ? (
                <ReferenceLine
                  y={specLimits.max}
                  stroke="var(--spc-spec)"
                  strokeDasharray="2 4 8 4"
                  label={{
                    value: specLabel(specLimits.max),
                    position: "insideTopLeft",
                    fontSize: 10,
                    fill: "var(--spc-spec)",
                  }}
                />
              ) : null}
              {specLimits?.min !== undefined ? (
                <ReferenceLine
                  y={specLimits.min}
                  stroke="var(--spc-spec)"
                  strokeDasharray="2 4 8 4"
                  label={{
                    value: specLabel(specLimits.min),
                    position: "insideBottomLeft",
                    fontSize: 10,
                    fill: "var(--spc-spec)",
                  }}
                />
              ) : null}
              <Line
                type="linear"
                dataKey="value"
                stroke="var(--color-value)"
                strokeWidth={2}
                dot={IndividualDot}
                activeDot={{ r: 4 }}
                connectNulls={false}
                isAnimationActive={false}
              />
              <Line
                type="linear"
                dataKey="censoredAt"
                stroke="none"
                dot={CensoredDot}
                activeDot={false}
                connectNulls={false}
                isAnimationActive={false}
              />
            </ComposedChart>
          </ChartContainer>

          {movingRange ? (
            <ChartContainer config={RANGE_CONFIG} className="aspect-auto h-32 w-full">
              <ComposedChart data={rangeRows} margin={{ top: 8, right: 16, bottom: 0, left: 0 }}>
                <CartesianGrid vertical={false} strokeDasharray="3 3" />
                <XAxis
                  dataKey="timestamp"
                  type="number"
                  scale="time"
                  domain={["dataMin", "dataMax"]}
                  tickFormatter={(value: number) => formatDay(new Date(value))}
                  tick={AXIS_TICK_STYLE}
                  tickMargin={8}
                  minTickGap={24}
                />
                <YAxis
                  domain={rangeDomain}
                  tickFormatter={(value: number) => value.toFixed(decimals)}
                  tick={AXIS_TICK_STYLE}
                  width={Y_AXIS_WIDTH}
                  label={{
                    value: `MR (${unitCode})`,
                    angle: -90,
                    position: "insideLeft",
                    style: Y_AXIS_LABEL_STYLE,
                  }}
                />
                <ChartTooltip
                  content={(props) => (
                    <ControlTooltip
                      {...props}
                      unitCode={unitCode}
                      decimals={decimals}
                      isRangePanel
                    />
                  )}
                />
                <ReferenceLine
                  y={movingRange.ucl}
                  stroke="var(--spc-limit)"
                  strokeDasharray="6 4"
                  label={{
                    value: `UCL ${formatNumber(movingRange.ucl, decimals)}`,
                    position: "insideTopRight",
                    fontSize: 10,
                    fill: "var(--spc-limit)",
                  }}
                />
                <ReferenceLine y={movingRange.center} stroke="var(--spc-center)" />
                <ReferenceLine
                  y={movingRange.lcl}
                  stroke="var(--spc-limit)"
                  strokeDasharray="6 4"
                />
                <Line
                  type="linear"
                  dataKey="value"
                  stroke="var(--color-movingRange)"
                  strokeWidth={1.5}
                  dot={{ r: 2, fill: "var(--color-movingRange)" }}
                  activeDot={{ r: 3 }}
                  connectNulls={false}
                  isAnimationActive={false}
                />
              </ComposedChart>
            </ChartContainer>
          ) : null}
        </div>

        <MarkerLegend hasSpecLimit={specLimits !== null} />

        {violations.length > 0 ? (
          <div className="rounded-md border border-border p-3">
            <div className="flex flex-wrap items-center gap-2">
              <ProcessStatusBadge status="out_of_control" />
              <p className="text-xs text-muted-foreground">
                {violations.length} señales de las reglas en la ventana de monitoreo
              </p>
            </div>
            <ul className="mt-2 flex flex-col gap-1">
              {violations.map((violation) => (
                <li
                  key={`${violation.rule}-${violation.index}`}
                  className="flex flex-wrap items-baseline gap-1.5 text-xs"
                >
                  <span className="rounded-sm bg-destructive-soft px-1 py-0.5 font-mono font-medium text-destructive-soft-foreground">
                    {violation.rule}
                  </span>
                  <span>{violation.description}</span>
                </li>
              ))}
            </ul>
            <p className="mt-2 text-xs text-muted-foreground">
              Las posiciones de la lista se cuentan desde el inicio de la ventana de monitoreo, no
              desde el primer punto dibujado.
            </p>
          </div>
        ) : (
          <div className="flex flex-wrap items-center gap-2">
            <ProcessStatusBadge status="in_control" />
            <p className="text-xs text-muted-foreground">
              Ninguna regla de R1 a R5 se activó en la ventana de monitoreo.
            </p>
          </div>
        )}

        {isTableVisible ? (
          <div id={TABLE_ID}>
            <DataTable
              columns={columns}
              data={rows}
              pageSize={25}
              caption={`Carta I-MR de ${parameterName} en ${siteCode}: valor, rango móvil, calidad y señal.`}
            />
          </div>
        ) : null}

        <p className="text-xs text-muted-foreground">
          Fuente: {siteCode} · {parameterName} · método {individuals.method} · catálogo v
          {catalogVersion} · actualizado {formatDateTime(updatedAt)}
        </p>
      </CardContent>
    </Card>
  );
}




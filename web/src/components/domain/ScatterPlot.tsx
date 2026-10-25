import { useState } from "react";
import { CartesianGrid, ComposedChart, Line, Scatter, XAxis, YAxis } from "recharts";

import { Button } from "@/components/ui/button";
import {
  ChartContainer,
  ChartTooltip,
  ChartTooltipContent,
  type ChartConfig,
} from "@/components/ui/chart";
import type { TrendPoint } from "@/components/domain/TrendChart";
import { formatDateTime, formatDay, formatNumber, formatUnit } from "@/lib/format";
import { cn } from "@/lib/utils";

export interface ScatterPlotProps {
  data: TrendPoint[];
  unitCode: string;
  parameterName: string;
  decimals: number;
  source: string;
  className?: string;
}

const CHART_CONFIG = {
  value: { label: "Observación", color: "var(--chart-1)" },
  trend: { label: "Recta de regresión", color: "var(--chart-2)" },
} satisfies ChartConfig;

const AXIS_TICK_STYLE = { fontSize: 11 } as const;

const MS_PER_DAY = 86_400_000;

interface Regression {
  r2: number;
  n: number;
  /** Predicted value at a given timestamp, in the parameter's unit. */
  predict: (timestamp: number) => number;
}

/** Ordinary least squares on (days since the first point, value). Pure and local. */
function fitRegression(points: Array<{ timestamp: number; value: number }>): Regression | null {
  const n = points.length;

  if (n < 3) {
    return null;
  }

  const origin = points[0].timestamp;
  const xs = points.map((point) => (point.timestamp - origin) / MS_PER_DAY);
  const ys = points.map((point) => point.value);
  const meanX = xs.reduce((sum, x) => sum + x, 0) / n;
  const meanY = ys.reduce((sum, y) => sum + y, 0) / n;

  let sxx = 0;
  let sxy = 0;
  let sst = 0;

  for (let index = 0; index < n; index += 1) {
    const dx = xs[index] - meanX;
    const dy = ys[index] - meanY;
    sxx += dx * dx;
    sxy += dx * dy;
    sst += dy * dy;
  }

  if (sxx === 0) {
    return null;
  }

  const slope = sxy / sxx;
  const intercept = meanY - slope * meanX;

  let ssr = 0;

  for (let index = 0; index < n; index += 1) {
    const residual = ys[index] - (intercept + slope * xs[index]);
    ssr += residual * residual;
  }

  return {
    n,
    r2: sst === 0 ? 0 : 1 - ssr / sst,
    predict: (timestamp: number) => intercept + slope * ((timestamp - origin) / MS_PER_DAY),
  };
}

/**
 * Dispersion of one parameter over time with its least-squares line, R² and n visible
 * (design-system §7). Censored values are excluded: their true value is unknown.
 */
export function ScatterPlot({
  data,
  unitCode,
  parameterName,
  decimals,
  source,
  className,
}: ScatterPlotProps) {
  const [isTableVisible, setIsTableVisible] = useState(false);

  const points = data
    .filter((point): point is { timestamp: Date; value: number } => point.value !== null)
    .map((point) => ({ timestamp: point.timestamp.getTime(), value: point.value }));

  const regression = fitRegression(points);
  const lineData =
    regression && points.length > 0
      ? [
          { timestamp: points[0].timestamp, value: regression.predict(points[0].timestamp) },
          {
            timestamp: points[points.length - 1].timestamp,
            value: regression.predict(points[points.length - 1].timestamp),
          },
        ]
      : [];

  const summary = regression
    ? `Dispersión de ${regression.n} observaciones de ${parameterName}; recta de regresión con R² = ${formatNumber(regression.r2, 2)}.`
    : `Dispersión de ${points.length} observaciones de ${parameterName}; no hay puntos suficientes para ajustar una recta.`;

  return (
    <figure className={cn("flex flex-col gap-2", className)}>
      <div role="img" aria-label={summary}>
        <ChartContainer config={CHART_CONFIG} className="aspect-auto h-64 w-full">
          <ComposedChart data={points} margin={{ top: 8, right: 12, bottom: 0, left: 0 }}>
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
              dataKey="value"
              type="number"
              domain={["auto", "auto"]}
              tickFormatter={(value: number) => value.toFixed(decimals)}
              tick={AXIS_TICK_STYLE}
              width={56}
              label={{
                value: unitCode,
                angle: -90,
                position: "insideLeft",
                style: { fontSize: 11, textAnchor: "middle" },
              }}
            />
            <ChartTooltip
              content={
                <ChartTooltipContent
                  indicator="dot"
                  labelFormatter={(_, payload) => {
                    const timestamp = payload?.[0]?.payload?.timestamp;
                    return timestamp ? formatDateTime(new Date(timestamp)) : "";
                  }}
                  formatter={(value) =>
                    typeof value === "number" ? formatUnit(value, unitCode, decimals) : "—"
                  }
                />
              }
            />
            <Scatter dataKey="value" fill="var(--color-value)" isAnimationActive={false} />
            <Line
              data={lineData}
              dataKey="value"
              stroke="var(--color-trend)"
              strokeWidth={2}
              strokeDasharray="6 4"
              dot={false}
              isAnimationActive={false}
              legendType="none"
            />
          </ComposedChart>
        </ChartContainer>
      </div>

      <figcaption className="flex flex-wrap items-center justify-between gap-2 text-xs text-muted-foreground">
        <span>
          {regression
            ? `Recta de regresión (mínimos cuadrados) · R² = ${formatNumber(regression.r2, 2)} · n = ${regression.n}`
            : "No hay puntos suficientes para ajustar una recta"}
        </span>
        <Button
          type="button"
          variant="ghost"
          size="sm"
          aria-pressed={isTableVisible}
          aria-controls="scatter-plot-table"
          onClick={() => setIsTableVisible((visible) => !visible)}
        >
          {isTableVisible ? "Ocultar tabla" : "Ver como tabla"}
        </Button>
      </figcaption>

      <p className="text-xs text-muted-foreground">{source}</p>

      {isTableVisible ? (
        <div
          id="scatter-plot-table"
          className="max-h-64 overflow-y-auto rounded-md border border-border"
        >
          <table className="w-full text-xs">
            <caption className="sr-only">{summary}</caption>
            <thead className="bg-muted/50 uppercase tracking-wide text-muted-foreground">
              <tr>
                <th scope="col" className="px-2 py-1 text-left font-medium">
                  Fecha y hora
                </th>
                <th scope="col" className="px-2 py-1 text-right font-medium">
                  Valor ({unitCode})
                </th>
                <th scope="col" className="px-2 py-1 text-right font-medium">
                  Regresión
                </th>
              </tr>
            </thead>
            <tbody>
              {points.map((point) => (
                <tr key={point.timestamp} className="border-t border-border">
                  <td className="px-2 py-1">{formatDateTime(new Date(point.timestamp))}</td>
                  <td className="px-2 py-1 text-right font-mono tabular-nums">
                    {formatUnit(point.value, unitCode, decimals)}
                  </td>
                  <td className="px-2 py-1 text-right font-mono tabular-nums text-muted-foreground">
                    {regression
                      ? formatUnit(regression.predict(point.timestamp), unitCode, decimals)
                      : "—"}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : null}
    </figure>
  );
}

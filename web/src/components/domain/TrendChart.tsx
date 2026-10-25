import { useState } from "react";
import { CartesianGrid, Line, LineChart, XAxis, YAxis } from "recharts";

import {
  ChartContainer,
  ChartTooltip,
  ChartTooltipContent,
  type ChartConfig,
} from "@/components/ui/chart";
import { Button } from "@/components/ui/button";
import { formatDateTime, formatDay, formatUnit } from "@/lib/format";
import { cn } from "@/lib/utils";

export interface TrendPoint {
  timestamp: Date;
  /** `null` is a censored result (`< LOQ`): it is a gap, never a zero. */
  value: number | null;
}

export interface TrendChartProps {
  data: TrendPoint[];
  unitCode: string;
  parameterName: string;
  decimals: number;
  /** Mandatory footnote: source, method, catalog version and refresh time. */
  source: string;
  className?: string;
}

const CHART_CONFIG = {
  value: { label: "Valor observado", color: "var(--chart-1)" },
} satisfies ChartConfig;

const AXIS_TICK_STYLE = { fontSize: 11 } as const;

/**
 * Time series of one parameter: line 2 px in `--chart-1`, censored values left as gaps and a
 * tabular alternative for screen readers (design-system §7).
 */
export function TrendChart({
  data,
  unitCode,
  parameterName,
  decimals,
  source,
  className,
}: TrendChartProps) {
  const [isTableVisible, setIsTableVisible] = useState(false);

  const chartData = data.map((point) => ({
    timestamp: point.timestamp.getTime(),
    value: point.value,
  }));

  const observedCount = data.filter((point) => point.value !== null).length;
  const firstTimestamp = data.at(0)?.timestamp;
  const lastTimestamp = data.at(-1)?.timestamp;
  const summary =
    firstTimestamp && lastTimestamp
      ? `Serie temporal de ${observedCount} observaciones de ${parameterName} entre ${formatDateTime(firstTimestamp)} y ${formatDateTime(lastTimestamp)}.`
      : `Serie temporal de ${parameterName} sin observaciones.`;

  return (
    <figure className={cn("flex flex-col gap-2", className)}>
      <div role="img" aria-label={summary}>
        <ChartContainer config={CHART_CONFIG} className="aspect-auto h-64 w-full">
          <LineChart data={chartData} margin={{ top: 8, right: 12, bottom: 0, left: 0 }}>
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
                  indicator="line"
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
            <Line
              type="monotone"
              dataKey="value"
              stroke="var(--color-value)"
              strokeWidth={2}
              dot={{ r: 2, fill: "var(--color-value)" }}
              activeDot={{ r: 4 }}
              connectNulls={false}
              isAnimationActive={false}
            />
          </LineChart>
        </ChartContainer>
      </div>

      <figcaption className="flex flex-wrap items-center justify-between gap-2 text-xs text-muted-foreground">
        <span>{source}</span>
        <Button
          type="button"
          variant="ghost"
          size="sm"
          aria-pressed={isTableVisible}
          aria-controls="trend-chart-table"
          onClick={() => setIsTableVisible((visible) => !visible)}
        >
          {isTableVisible ? "Ocultar tabla" : "Ver como tabla"}
        </Button>
      </figcaption>

      {isTableVisible ? (
        <div id="trend-chart-table" className="max-h-64 overflow-y-auto rounded-md border border-border">
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
              </tr>
            </thead>
            <tbody>
              {data.map((point) => (
                <tr key={point.timestamp.toISOString()} className="border-t border-border">
                  <td className="px-2 py-1">{formatDateTime(point.timestamp)}</td>
                  <td className="px-2 py-1 text-right font-mono tabular-nums">
                    {point.value === null ? "< LOQ" : formatUnit(point.value, unitCode, decimals)}
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

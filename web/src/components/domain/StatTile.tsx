import { Minus, TrendingDown, TrendingUp, type LucideIcon } from "lucide-react";

import { Card } from "@/components/ui/card";
import { cn } from "@/lib/utils";

export type StatTileStatus = "normal" | "warning" | "critical";

export interface StatTileProps {
  label: string;
  /** Already formatted in es-CL by `lib/format.ts`; the tile only decides the typography. */
  value: string | number;
  unit?: string;
  hint?: string;
  trend?: "up" | "down" | "flat";
  icon?: LucideIcon;
  status?: StatTileStatus;
}

const STATUS_STYLES: Record<StatTileStatus, string> = {
  normal: "border-border",
  warning: "border-warning/40 bg-warning-soft/20",
  critical: "border-destructive/40 bg-destructive-soft/20",
};

const TREND_ICONS = { up: TrendingUp, down: TrendingDown, flat: Minus } as const;

const TREND_LABELS = { up: "Tendencia al alza", down: "Tendencia a la baja", flat: "Sin tendencia" } as const;

/** KPI tile of the dashboard: label, figure in mono, optional unit and hint (design-system §4). */
export function StatTile({
  label,
  value,
  unit,
  hint,
  trend,
  icon: Icon,
  status = "normal",
}: StatTileProps) {
  const TrendIcon = trend ? TREND_ICONS[trend] : null;
  const trendLabel = trend ? TREND_LABELS[trend] : null;
  const accessibleValue = `${label}: ${value}${unit ? ` ${unit}` : ""}`;

  return (
    <Card
      role="status"
      aria-label={accessibleValue}
      className={cn("gap-1 border p-4", STATUS_STYLES[status])}
    >
      <div className="flex items-start justify-between gap-2">
        <span className="text-xs text-muted-foreground">{label}</span>
        {Icon ? <Icon aria-hidden="true" className="size-4 shrink-0 text-muted-foreground" /> : null}
      </div>

      <div className="flex items-baseline gap-1.5">
        <span className="font-mono text-3xl font-semibold tabular-nums">{value}</span>
        {unit ? <span className="text-sm text-muted-foreground">{unit}</span> : null}
        {TrendIcon ? (
          <span className="flex items-center gap-1 text-xs text-muted-foreground">
            <TrendIcon aria-hidden="true" className="size-3.5" />
            <span className="sr-only">{trendLabel}</span>
          </span>
        ) : null}
      </div>

      {hint ? <p className="text-xs text-muted-foreground">{hint}</p> : null}
    </Card>
  );
}

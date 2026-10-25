import { AlertTriangle, CheckCircle2, MinusCircle, XOctagon, type LucideIcon } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";

export type ProcessStatus = "in_control" | "warning" | "out_of_control" | "insufficient_data";

interface StatusStyle {
  label: string;
  icon: LucideIcon;
  className: string;
}

/**
 * Process status of a series (design-system §3.1): colour + icon + text, never colour alone.
 * `insufficient_data` is informational, not an error: it only means n < 20 for the baseline.
 */
const STATUS_STYLES: Record<ProcessStatus, StatusStyle> = {
  in_control: {
    label: "En control",
    icon: CheckCircle2,
    className: "bg-success-soft text-success-soft-foreground",
  },
  warning: {
    label: "Alerta temprana",
    icon: AlertTriangle,
    className: "bg-warning-soft text-warning-soft-foreground",
  },
  out_of_control: {
    label: "Fuera de control",
    icon: XOctagon,
    className: "bg-destructive-soft text-destructive-soft-foreground",
  },
  insufficient_data: {
    label: "Datos insuficientes",
    icon: MinusCircle,
    className: "bg-info-soft text-info-soft-foreground",
  },
};

export function ProcessStatusBadge({ status }: { status: ProcessStatus }) {
  const { label, icon: Icon, className } = STATUS_STYLES[status];

  return (
    <Badge className={cn("rounded-sm", className)}>
      <Icon aria-hidden="true" />
      {label}
    </Badge>
  );
}

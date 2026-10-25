import {
  ArrowDownCircle,
  ArrowUpCircle,
  CheckCircle2,
  MinusCircle,
  type LucideIcon,
} from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Tooltip, TooltipContent, TooltipTrigger } from "@/components/ui/tooltip";
import { cn } from "@/lib/utils";
import type { ScreeningFlag } from "@/types/api";

interface ScreeningStyle {
  label: string;
  icon: LucideIcon;
  className: string;
}

/**
 * Referential screening badge (ADR-010, design-system §3.1).
 *
 * Amber —not red— on purpose: being outside the reference range is not an infringement, and
 * the wording never says «Cumple» or «Excede» because a single observation cannot be a
 * compliance verdict.
 */
const SCREENING_STYLES: Record<ScreeningFlag, ScreeningStyle> = {
  normal: {
    label: "Dentro de rango",
    icon: CheckCircle2,
    className: "bg-success-soft text-success-soft-foreground",
  },
  above_range: {
    label: "Sobre el rango (referencial)",
    icon: ArrowUpCircle,
    className: "bg-warning-soft text-warning-soft-foreground",
  },
  below_range: {
    label: "Bajo el rango (referencial)",
    icon: ArrowDownCircle,
    className: "bg-warning-soft text-warning-soft-foreground",
  },
  not_evaluable: {
    label: "No evaluable",
    icon: MinusCircle,
    className: "bg-muted text-muted-foreground",
  },
};

export function ScreeningBadge({ flag, reason }: { flag: ScreeningFlag; reason?: string }) {
  const { label, icon: Icon, className } = SCREENING_STYLES[flag];

  const badge = (
    <Badge className={cn("rounded-sm", className)}>
      <Icon aria-hidden="true" />
      {label}
    </Badge>
  );

  if (!reason) {
    return badge;
  }

  return (
    <Tooltip>
      <TooltipTrigger asChild>{badge}</TooltipTrigger>
      <TooltipContent>{reason}</TooltipContent>
    </Tooltip>
  );
}

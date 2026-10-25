import { AlertTriangle, CheckCircle2, XOctagon, type LucideIcon } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";
import type { QcFlag } from "@/types/api";

interface QcStyle {
  label: string;
  icon: LucideIcon;
  className: string;
}

/** Quality flag of an observation, with the Spanish wording the analyst sees. */
const QC_STYLES: Record<QcFlag, QcStyle> = {
  ok: {
    label: "OK",
    icon: CheckCircle2,
    className: "bg-success-soft text-success-soft-foreground",
  },
  suspect: {
    label: "Sospechoso",
    icon: AlertTriangle,
    className: "bg-warning-soft text-warning-soft-foreground",
  },
  failed: {
    label: "Fallido",
    icon: XOctagon,
    className: "bg-destructive-soft text-destructive-soft-foreground",
  },
};

export function QcFlagBadge({ flag }: { flag: QcFlag }) {
  const { label, icon: Icon, className } = QC_STYLES[flag];

  return (
    <Badge className={cn("rounded-sm", className)}>
      <Icon aria-hidden="true" />
      {label}
    </Badge>
  );
}

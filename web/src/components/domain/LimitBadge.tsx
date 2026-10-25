import { BadgeCheck, Clock3 } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";

/**
 * Validation state of a catalog limit (design-system §3.1).
 *
 * Amber —not green— for `draft-verified`: the value exists but the chemist has not signed it, so
 * the UI may show it and must never treat it as an enforceable threshold (ADR-010).
 */
export function LimitBadge({ status }: { status: string }) {
  if (status === "validated") {
    return (
      <Badge className={cn("rounded-sm", "bg-success-soft text-success-soft-foreground")}>
        <BadgeCheck aria-hidden="true" />
        Validado
      </Badge>
    );
  }

  return (
    <Badge className={cn("rounded-sm", "bg-warning-soft text-warning-soft-foreground")}>
      <Clock3 aria-hidden="true" />
      Pendiente de validación
    </Badge>
  );
}

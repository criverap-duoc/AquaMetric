import { AlertTriangle, RotateCcw } from "lucide-react";

import { Button } from "@/components/ui/button";
import { ApiError } from "@/lib/api-client";
import { cn } from "@/lib/utils";

export interface ErrorStateProps {
  error: unknown;
  onRetry?: () => void;
  className?: string;
}

const CONNECTION_HINT =
  "No se pudo conectar con la API. Verifica que esté corriendo en el puerto 8000.";

/**
 * Error banner of design-system §6.7: soft destructive surface, human message, retry button and
 * the `requestId` so a report can be traced in the server logs.
 */
export function ErrorState({ error, onRetry, className }: ErrorStateProps) {
  const isApiError = error instanceof ApiError;
  const detail = isApiError ? error.problem.detail : CONNECTION_HINT;
  const requestId = isApiError ? error.problem.requestId : "";
  const code = isApiError ? error.problem.code : "NETWORK_ERROR";

  return (
    <div
      role="alert"
      className={cn(
        "flex flex-col gap-2 rounded-md border border-destructive/30 bg-destructive-soft p-4 text-destructive-soft-foreground",
        className,
      )}
    >
      <div className="flex items-start gap-2">
        <AlertTriangle aria-hidden="true" className="mt-0.5 size-4 shrink-0" />
        <div className="flex flex-col gap-1">
          <p className="text-sm font-medium">No se pudieron cargar los datos.</p>
          <p className="text-xs">{detail}</p>
          <p className="font-mono text-xs text-muted-foreground">
            Código: {code}
            {requestId ? ` · requestId: ${requestId}` : ""}
          </p>
        </div>
      </div>

      {onRetry ? (
        <div>
          <Button type="button" variant="outline" size="sm" onClick={onRetry}>
            <RotateCcw aria-hidden="true" />
            Reintentar
          </Button>
        </div>
      ) : null}
    </div>
  );
}

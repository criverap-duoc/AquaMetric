import { AlertTriangle, RotateCcw } from "lucide-react";

import { Button } from "@/components/ui/button";
import { ApiError, ContractError } from "@/lib/api-client";
import { cn } from "@/lib/utils";

export interface ErrorStateProps {
  error: unknown;
  onRetry?: () => void;
  className?: string;
  /** Headline of the banner; the default fits a failed query. */
  title?: string;
  /** Overrides the message derived from `error` (used by the render-error boundary). */
  detail?: string;
  /** Overrides the code derived from `error`. */
  code?: string;
}

const CONNECTION_HINT =
  "No se pudo conectar con la API. Verifica que esté corriendo en el puerto 8000.";

/**
 * Error banner of design-system §6.7: soft destructive surface, human message, retry button and
 * the `requestId` so a report can be traced in the server logs.
 *
 * Three kinds of failure reach this component: an API `problem+json` (`ApiError`), a payload with
 * an unexpected shape (`ContractError`, usually a backend older than the frontend) and a network
 * failure, which gets the connection hint.
 */
export function ErrorState({
  error,
  onRetry,
  className,
  title = "No se pudieron cargar los datos.",
  detail,
  code,
}: ErrorStateProps) {
  const isApiError = error instanceof ApiError;
  const isContractError = error instanceof ContractError;
  const computedDetail = isApiError
    ? error.problem.detail
    : isContractError
      ? error.message
      : CONNECTION_HINT;
  const requestId = isApiError ? error.problem.requestId : "";
  const computedCode = isApiError
    ? error.problem.code
    : isContractError
      ? "CONTRACT_MISMATCH"
      : "NETWORK_ERROR";
  const shownDetail = detail ?? computedDetail;
  const shownCode = code ?? computedCode;

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
          <p className="text-sm font-medium">{title}</p>
          <p className="text-xs">{shownDetail}</p>
          <p className="font-mono text-xs text-muted-foreground">
            Código: {shownCode}
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

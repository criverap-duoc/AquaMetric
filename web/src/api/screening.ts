import { useMutation } from "@tanstack/react-query";

import { apiFetch, ApiError } from "@/lib/api-client";
import type { ScreeningRequest, ScreeningResponse } from "@/types/api";

/**
 * Screen one observation against a catalog limit.
 *
 * A mutation, not a query: the form submits a value and `POST /screening/evaluate` stores
 * nothing, so there is no cache entry worth keeping. The flag is referential — `warnings[]`
 * always carries the disclaimer (ADR-010).
 */
export function useScreeningEvaluate() {
  return useMutation<ScreeningResponse, ApiError, ScreeningRequest>({
    mutationFn: (request) =>
      apiFetch<ScreeningResponse>("/api/v1/screening/evaluate", {
        method: "POST",
        body: JSON.stringify(request),
      }),
  });
}

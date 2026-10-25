import { useQuery } from "@tanstack/react-query";

import { apiFetch, toListEnvelope } from "@/lib/api-client";
import type {
  CatalogLimit,
  CatalogMeta,
  LimitsMeta,
  LimitsResponse,
  Parameter,
  Regulation,
  Unit,
} from "@/types/api";

/** Filters of `GET /api/v1/catalog/limits`; `regulation` in, `regulationCode` out (ADR-015). */
export interface LimitsParams {
  parameterCode?: string;
  regulation?: string;
  /** `validated` lists only signed limits; `draft-verified` only the pending ones. */
  status?: "draft-verified" | "validated";
}

/** Query keys in one place: the cache is shared by the Resumen, Series and Ajustes pages. */
export const catalogKeys = {
  all: ["catalog"] as const,
  meta: ["catalog", "meta"] as const,
  parameters: ["catalog", "parameters"] as const,
  units: ["catalog", "units"] as const,
  limits: (params: LimitsParams = {}) =>
    [
      "catalog",
      "limits",
      params.parameterCode ?? null,
      params.regulation ?? null,
      params.status ?? null,
    ] as const,
  regulations: ["catalog", "regulations"] as const,
};

function buildQuery(params: Record<string, string | undefined>): string {
  const search = new URLSearchParams();

  for (const [key, value] of Object.entries(params)) {
    if (value) {
      search.set(key, value);
    }
  }

  const query = search.toString();

  return query ? `?${query}` : "";
}

/** Catalog provenance: version, sha256 and whether the chemist already signed the values. */
export function useCatalogMeta() {
  return useQuery<CatalogMeta>({
    queryKey: catalogKeys.meta,
    queryFn: () => apiFetch<CatalogMeta>("/api/v1/catalog/meta"),
    // The catalog changes only when someone runs `sync catalog`, so five minutes is cheap.
    staleTime: 5 * 60_000,
  });
}

/** Every parameter with the canonical unit and the decimals the UI must show. */
export function useParameters() {
  return useQuery<Parameter[]>({
    queryKey: catalogKeys.parameters,
    queryFn: () => apiFetch<Parameter[]>("/api/v1/catalog/parameters"),
    staleTime: 5 * 60_000,
  });
}

export function useUnits() {
  return useQuery<Unit[]>({
    queryKey: catalogKeys.units,
    queryFn: () => apiFetch<Unit[]>("/api/v1/catalog/units"),
    staleTime: 5 * 60_000,
  });
}

/**
 * Catalog limits, optionally narrowed by parameter, regulation and validation status.
 *
 * The list includes limits still pending validation: the catalog browser shows what exists,
 * and `status` is what the UI renders as «Pendiente de validación» (ADR-010). `meta` counts how
 * many of the returned limits are signed. The envelope is checked at runtime so a backend older
 * than the frontend shows an error instead of an empty screen.
 */
export function useLimits(params: LimitsParams = {}) {
  const path = "/api/v1/catalog/limits";

  return useQuery<LimitsResponse>({
    queryKey: catalogKeys.limits(params),
    queryFn: async () => {
      const payload = await apiFetch<unknown>(`${path}${buildQuery({ ...params })}`);

      return toListEnvelope<CatalogLimit, LimitsMeta>(payload, path);
    },
    staleTime: 5 * 60_000,
  });
}

export function useRegulations() {
  return useQuery<Regulation[]>({
    queryKey: catalogKeys.regulations,
    queryFn: () => apiFetch<Regulation[]>("/api/v1/catalog/regulations"),
    staleTime: 5 * 60_000,
  });
}

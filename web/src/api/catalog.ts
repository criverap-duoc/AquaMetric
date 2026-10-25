import { useQuery } from "@tanstack/react-query";

import { apiFetch } from "@/lib/api-client";
import type { CatalogLimit, CatalogMeta, Parameter, Regulation, Unit } from "@/types/api";

/** Query keys in one place: the cache is shared by the Resumen, Series and Ajustes pages. */
export const catalogKeys = {
  all: ["catalog"] as const,
  meta: ["catalog", "meta"] as const,
  parameters: ["catalog", "parameters"] as const,
  units: ["catalog", "units"] as const,
  limits: (parameterCode?: string, regulation?: string) =>
    ["catalog", "limits", parameterCode ?? null, regulation ?? null] as const,
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
 * Catalog limits, optionally narrowed by parameter and regulation.
 *
 * The list includes limits still pending validation: the catalog browser shows what exists,
 * and `status` is what the UI renders as «Pendiente de validación» (ADR-010).
 */
export function useLimits(parameterCode?: string, regulation?: string) {
  return useQuery<CatalogLimit[]>({
    queryKey: catalogKeys.limits(parameterCode, regulation),
    queryFn: () =>
      apiFetch<CatalogLimit[]>(
        `/api/v1/catalog/limits${buildQuery({ parameterCode, regulation })}`,
      ),
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

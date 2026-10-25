import { useQuery } from "@tanstack/react-query";

import { apiFetch, toListEnvelope } from "@/lib/api-client";
import type { Site, SiteListMeta, SiteListResponse } from "@/types/api";

const SITES_PATH = "/api/v1/sites";

/** Filters the selectors of Series and Control use; `isActive` is optional on purpose. */
export interface SitesParams {
  page?: number;
  pageSize?: number;
  isActive?: boolean;
}

export const siteKeys = {
  all: ["sites"] as const,
  list: (params: SitesParams) =>
    ["sites", "list", params.page ?? 1, params.pageSize ?? 50, params.isActive ?? null] as const,
};

function sitesQuery({ page = 1, pageSize = 50, isActive }: SitesParams): string {
  const search = new URLSearchParams({ page: String(page), pageSize: String(pageSize) });

  if (isActive !== undefined) {
    search.set("isActive", String(isActive));
  }

  return search.toString();
}

/**
 * Paginated site list, ordered by `code`.
 *
 * The uuid of each site is the `siteId` the SPC endpoints expect, which is why the chart and the
 * series selector read the list from here instead of deriving it from the demo data.
 */
export function useSites(params: SitesParams = {}) {
  return useQuery<SiteListResponse>({
    queryKey: siteKeys.list(params),
    queryFn: async () => {
      const payload = await apiFetch<unknown>(`${SITES_PATH}?${sitesQuery(params)}`);

      return toListEnvelope<Site, SiteListMeta>(payload, SITES_PATH);
    },
    // Sites change when a batch introduces one, which is rare; a minute is conservative.
    staleTime: 60_000,
  });
}

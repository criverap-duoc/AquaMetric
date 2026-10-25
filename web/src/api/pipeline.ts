import { useQuery } from "@tanstack/react-query";

import { apiFetch, toObject } from "@/lib/api-client";
import type { PipelineStatusResponse } from "@/types/api";

const PIPELINE_STATUS_PATH = "/api/v1/pipeline/status";

export interface PipelineStatusParams {
  /** How many recent batches to show (1…50). */
  limit?: number;
}

export const pipelineKeys = {
  all: ["pipeline"] as const,
  status: (limit: number) => ["pipeline", "status", limit] as const,
};

/**
 * Recent ingest batches and the newest reading of each site.
 *
 * Polls every 30 s because the screen answers «how fresh is the data?»; the endpoint only reads
 * two indexed tables, so the tick is cheap. `awsDeployed` tells the screen whether the S3 →
 * Lambda path exists (ADR-004).
 */
export function usePipelineStatus({ limit = 10 }: PipelineStatusParams = {}) {
  return useQuery<PipelineStatusResponse>({
    queryKey: pipelineKeys.status(limit),
    queryFn: async () => {
      const payload = await apiFetch<unknown>(
        `${PIPELINE_STATUS_PATH}?limit=${String(limit)}`,
      );

      return toObject<PipelineStatusResponse>(payload, PIPELINE_STATUS_PATH);
    },
    refetchInterval: 30_000,
  });
}

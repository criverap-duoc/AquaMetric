import { useQuery } from "@tanstack/react-query";

import { apiFetch } from "@/lib/api-client";
import type { ControlChartResponse, RuleViolation } from "@/types/api";

/** Minimum Phase I baseline: the number ADR-001 fixes, mirroring `spc/constants.py`. */
export const MIN_BASELINE_POINTS = 20;

/**
 * Phase I size every chart opens with, in the Control screen and in the dashboard alike.
 *
 * 20 points is the ADR-001 minimum and the number the SPC core enforces, but a sigma estimated
 * from 19 moving ranges is itself unstable: on the demo series it lands anywhere between 0.6 and
 * 1.3 true standard deviations, so an innocent chart shows a handful of false excursions. 40
 * points keeps the limits honest without eating the monitored window. The API defaults to 20, so
 * the client always sends the number explicitly and both screens count signals on the same
 * baseline.
 */
export const DEFAULT_BASELINE_POINTS = 40;

export interface ControlChartParams {
  siteId: string;
  parameterCode: string;
  /** Observations of Phase I used to estimate the limits (20…200). */
  baselinePoints?: number;
  /** Observations after the baseline scanned against the limits (1…500). */
  monitoringPoints?: number;
}

/**
 * Query string of the chart endpoints.
 *
 * Exported because the dashboard probes every (site, parameter) pair at once and must build the
 * same URL the single-series hook builds, cache key included.
 */
export function chartSearch({
  siteId,
  parameterCode,
  baselinePoints = DEFAULT_BASELINE_POINTS,
  monitoringPoints,
}: ControlChartParams) {
  const search = new URLSearchParams({ siteId, parameterCode });

  search.set("baselinePoints", String(baselinePoints));

  if (monitoringPoints !== undefined) {
    search.set("monitoringPoints", String(monitoringPoints));
  }

  return search.toString();
}

export const spcKeys = {
  all: ["spc"] as const,
  chart: (params: ControlChartParams) =>
    [
      "spc",
      "chart",
      params.siteId,
      params.parameterCode,
      params.baselinePoints ?? DEFAULT_BASELINE_POINTS,
      params.monitoringPoints ?? null,
    ] as const,
  rules: (params: ControlChartParams) =>
    [
      "spc",
      "rules",
      params.siteId,
      params.parameterCode,
      params.baselinePoints ?? DEFAULT_BASELINE_POINTS,
    ] as const,
};

/**
 * I-MR chart of one series: control limits estimated in Phase I plus the signals the rules
 * found in the monitoring window. These are control limits, not normative limits.
 *
 * Disabled until both a site UUID and a parameter code are known, because the endpoint needs
 * a real series to answer; `siteId` must be the UUID stored in `aquametric.site`.
 */
export function useControlChart(params: ControlChartParams) {
  return useQuery<ControlChartResponse>({
    queryKey: spcKeys.chart(params),
    queryFn: () =>
      apiFetch<ControlChartResponse>(`/api/v1/spc/control-charts?${chartSearch(params)}`),
    enabled: Boolean(params.siteId) && Boolean(params.parameterCode),
  });
}

/** Only the signals of the monitoring window: the list the chart response returns. */
export function useRuleViolations(params: ControlChartParams) {
  return useQuery<RuleViolation[]>({
    queryKey: spcKeys.rules(params),
    queryFn: () => apiFetch<RuleViolation[]>(`/api/v1/spc/rules?${chartSearch(params)}`),
    enabled: Boolean(params.siteId) && Boolean(params.parameterCode),
  });
}

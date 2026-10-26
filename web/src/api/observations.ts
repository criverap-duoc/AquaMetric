import { useQueries, useQuery } from "@tanstack/react-query";

import { chartSearch, spcKeys } from "@/api/spc";
import { ApiError, apiFetch, toListEnvelope, toObject } from "@/lib/api-client";
import type {
  ControlChartResponse,
  ObservationAggregate,
  ObservationRead,
  ObservationsMeta,
  ObservationsResponse,
  RuleViolation,
} from "@/types/api";

const OBSERVATIONS_PATH = "/api/v1/observations";

/**
 * Filters of `GET /observations`.
 *
 * `order` exists because the two screens want the same rows in opposite directions: the table
 * shows the newest first, and the control chart needs the chronological window that
 * `GET /spc/control-charts` actually scanned.
 */
export interface ObservationsParams {
  siteId?: string;
  parameterCode?: string;
  /** ISO-8601 instant, inclusive. */
  from?: string;
  /** ISO-8601 instant, inclusive. */
  to?: string;
  page?: number;
  pageSize?: number;
  order?: "asc" | "desc";
}

export const observationKeys = {
  all: ["observations"] as const,
  list: (params: ObservationsParams) => ["observations", "list", params] as const,
  aggregate: (params: ObservationsParams) => ["observations", "aggregate", params] as const,
};

function observationsSearch({
  siteId,
  parameterCode,
  from,
  to,
  page = 1,
  pageSize = 100,
  order,
}: ObservationsParams): string {
  const search = new URLSearchParams({ page: String(page), pageSize: String(pageSize) });

  if (siteId) {
    search.set("siteId", siteId);
  }

  if (parameterCode) {
    search.set("parameterCode", parameterCode);
  }

  if (from) {
    search.set("from", from);
  }

  if (to) {
    search.set("to", to);
  }

  if (order) {
    search.set("order", order);
  }

  return search.toString();
}

/**
 * One page of stored observations, with the site code embedded in every row.
 *
 * Disabled until a parameter is chosen: the endpoint answers every parameter of every site at
 * once, which is far more than a screen showing one series needs.
 */
export function useObservations(params: ObservationsParams = {}) {
  return useQuery<ObservationsResponse>({
    queryKey: observationKeys.list(params),
    queryFn: async () => {
      const search = observationsSearch(params);
      const payload = await apiFetch<unknown>(`${OBSERVATIONS_PATH}?${search}`);

      return toListEnvelope<ObservationRead, ObservationsMeta>(payload, OBSERVATIONS_PATH);
    },
    enabled: Boolean(params.parameterCode ?? params.siteId),
    // New rows only arrive with a batch; a minute keeps the screen responsive without polling.
    staleTime: 60_000,
  });
}

/**
 * Counters of the same window in a single query: «n», the mean and the range.
 *
 * The Series screen prints `n` next to the charts; asking the list for it would mean downloading
 * 1400 rows to count them.
 */
export function useObservationsAggregate(params: ObservationsParams = {}) {
  return useQuery<ObservationAggregate>({
    queryKey: observationKeys.aggregate(params),
    queryFn: async () => {
      const search = observationsSearch({ ...params, page: undefined, pageSize: undefined });
      const payload = await apiFetch<unknown>(`${OBSERVATIONS_PATH}/aggregate?${search}`);

      return toObject<ObservationAggregate>(payload, `${OBSERVATIONS_PATH}/aggregate`);
    },
    enabled: Boolean(params.parameterCode ?? params.siteId),
    staleTime: 60_000,
  });
}

/**
 * Overview of the stored series, composed from endpoints that already exist.
 *
 * What the dashboard needs is «how many series, and which ones moved». What it can ask is the
 * I-MR chart of every (site, parameter) pair: the response carries the limits, the baseline size
 * and the signals of the monitoring window. Aggregating in the client keeps this slice off the
 * backend.
 */

/** A pair the API can hold a series for: the key of one control chart. */
export interface SeriesKey {
  siteId: string;
  siteCode: string;
  parameterCode: string;
}

/** A pair the API answered for, with the chart that was computed for it. */
export interface SeriesOverview extends SeriesKey {
  chart: ControlChartResponse;
}

export interface SeriesOverviewResult {
  /** Only the pairs with data: a pair the API rejected is not a series of the demo. */
  series: SeriesOverview[];
  /** Pairs that failed for a reason other than «no data»; the screen warns instead of hiding. */
  failedCount: number;
  isPending: boolean;
}

/** `422 INSUFFICIENT_DATA` means «this pair has no observations», not a failure of the screen. */
export function isInsufficientData(error: unknown): boolean {
  return error instanceof ApiError && error.status === 422;
}

/**
 * Chart of every (site, parameter) pair at once.
 *
 * Not every catalog parameter is measured at every site: `TEMP` and `P_PO4` are in the catalog
 * and absent from the demo, so a fraction of the requests answers 422. Those pairs are dropped
 * instead of retried (`retry: false`), which keeps the count of series measured rather than
 * hardcoded. `useQueries` is what allows a list whose length is only known at runtime — calling
 * `useControlChart` inside a loop would break the order of the hooks.
 */
export function useSeriesCharts(pairs: SeriesKey[]): SeriesOverviewResult {
  const queries = useQueries({
    queries: pairs.map((pair) => ({
      queryKey: spcKeys.chart(pair),
      queryFn: () =>
        apiFetch<ControlChartResponse>(`/api/v1/spc/control-charts?${chartSearch(pair)}`),
      // The limits change only when a batch arrives; the whole dashboard shares this cache.
      staleTime: 5 * 60_000,
      retry: false,
    })),
  });

  const series: SeriesOverview[] = [];
  let failedCount = 0;
  let isPending = false;

  queries.forEach((query, index) => {
    const pair = pairs[index];

    if (!pair) {
      return;
    }

    if (query.isPending) {
      isPending = true;
    }

    if (query.data) {
      series.push({ ...pair, chart: query.data });
    } else if (query.isError && !isInsufficientData(query.error)) {
      failedCount += 1;
    }
  });

  return { series, failedCount, isPending };
}

/* -------------------------------------------------------------- summary --- */

export interface SeriesSummary {
  /** Pairs with data: the denominator of «X de Y series». */
  totalSeries: number;
  /** Series with at least one signal in the monitoring window. */
  seriesWithSignals: number;
  /** Series with a signal that means the process moved, not just an early warning. */
  outOfControlSeries: number;
}

/** `R1`–`R3` mean the process changed; `R4`/`R5` are the early warnings of Nelson's rules. */
export type SignalSeverity = "out_of_control" | "warning";

const OUT_OF_CONTROL_RULES = new Set(["R1", "R2", "R3"]);

/** Severity order of the rules, used to rank the alert list. */
const RULE_ORDER = ["R1", "R2", "R3", "R4", "R5"] as const;

export function severityOf(rule: string): SignalSeverity {
  return OUT_OF_CONTROL_RULES.has(rule) ? "out_of_control" : "warning";
}

function ruleRank(rule: string): number {
  const rank = RULE_ORDER.indexOf(rule as (typeof RULE_ORDER)[number]);

  return rank === -1 ? RULE_ORDER.length : rank;
}

/** Counts the signals of a set of series; every figure is derived from the charts themselves. */
export function summarizeSeries(series: SeriesOverview[]): SeriesSummary {
  return {
    totalSeries: series.length,
    seriesWithSignals: series.filter((item) => item.chart.violations.length > 0).length,
    outOfControlSeries: series.filter((item) =>
      item.chart.violations.some((violation) => severityOf(violation.rule) === "out_of_control"),
    ).length,
  };
}

/** One signal of one series, ready for the «Últimas alertas» list. */
export interface SeriesSignal {
  id: string;
  siteCode: string;
  parameterCode: string;
  rule: string;
  index: number;
  description: string;
  severity: SignalSeverity;
}

/**
 * The most severe signal of each series, most severe first.
 *
 * One row per series keeps the dashboard readable: a single chart can carry dozens of signals.
 * Within a series the strongest rule wins (`R1` before `R2`…), and among equals the latest point,
 * because that is the one an analyst wants to look at first.
 */
export function rankSignals(series: SeriesOverview[], limit: number): SeriesSignal[] {
  const worstPerSeries: SeriesSignal[] = [];

  for (const item of series) {
    const worst = item.chart.violations.reduce<RuleViolation | null>((best, violation) => {
      if (!best) {
        return violation;
      }

      const byRule = ruleRank(violation.rule) - ruleRank(best.rule);

      if (byRule !== 0) {
        return byRule < 0 ? violation : best;
      }

      return violation.index > best.index ? violation : best;
    }, null);

    if (worst) {
      worstPerSeries.push({
        id: `${item.siteCode}-${item.parameterCode}-${worst.rule}-${worst.index}`,
        siteCode: item.siteCode,
        parameterCode: item.parameterCode,
        rule: worst.rule,
        index: worst.index,
        description: worst.description,
        severity: severityOf(worst.rule),
      });
    }
  }

  worstPerSeries.sort((a, b) => ruleRank(a.rule) - ruleRank(b.rule) || b.index - a.index);

  return worstPerSeries.slice(0, limit);
}

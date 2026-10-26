import { useQueries } from "@tanstack/react-query";

import { chartSearch, spcKeys } from "@/api/spc";
import { ApiError, apiFetch } from "@/lib/api-client";
import type { ControlChartResponse, RuleViolation } from "@/types/api";

/**
 * Overview of the stored series, composed from endpoints that already exist.
 *
 * `GET /observations` is not published yet, so the dashboard cannot ask «how many observations
 * are there?» directly. What it can ask is for the I-MR chart of every (site, parameter) pair:
 * the response carries the limits, the baseline size and the signals of the monitoring window,
 * which is what the summary needs. Aggregating in the client keeps this slice off the backend.
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

import { findDemoSeries } from "@/features/series/demo-data";
import type { ControlObservation } from "@/features/control/types";

/**
 * A site the API can answer for.
 *
 * `id` is `uuid5(NAMESPACE_DNS, code)`, the id `app/simulator/generator.py` writes, so the
 * selector can call `GET /api/v1/spc/control-charts` with a real key of `aquametric.site`.
 *
 * TODO(#E-1f): read the list from `GET /api/v1/sites` when it exists; until then the four `SIM-*`
 * series of `scripts/seed_demo.sh` are the only ones the demo has.
 */
export interface ControlSiteOption {
  id: string;
  code: string;
  name: string;
}

export const CONTROL_SITES: ControlSiteOption[] = [
  {
    id: "8d2de285-ea38-5fef-9ae9-9a1b1df6bf59",
    code: "SIM-RIO-MAIPO-01",
    name: "Río Maipo — Puente Alto",
  },
  {
    id: "2681585d-2d29-5bd2-9990-cfd3f296ff97",
    code: "SIM-RIO-MAPOCHO-01",
    name: "Río Mapocho — Pudahuel",
  },
  {
    id: "e0162788-b684-5dd8-adb1-1b8ad41597ed",
    code: "SIM-ESTERO-LAMPA-01",
    name: "Estero Lampa — Lampa",
  },
  {
    id: "2b9021dd-dfa0-5c12-b1e4-6828c05bc5b8",
    code: "SIM-LAGO-RANCO-01",
    name: "Lago Ranco — Llifén",
  },
];

export const DEFAULT_SITE_CODE = CONTROL_SITES[0].code;
export const DEFAULT_PARAMETER_CODE = "PH";
export const DEFAULT_BASELINE_POINTS = 20;

/** Baseline sizes the analyst can choose: 20 is the Phase I minimum of ADR-001. */
export const BASELINE_POINT_OPTIONS = [20, 30, 40, 50] as const;

export interface ControlSeries {
  siteCode: string;
  parameterCode: string;
  unitCode: string;
  decimals: number;
  observations: ControlObservation[];
}

/**
 * Values the chart plots, taken from the deterministic demo series of the simulator.
 *
 * TODO(#E-1f): replace with `GET /api/v1/observations` when it exists. The demo series is the
 * replica of what `scripts/seed_demo.sh` ingests, so the values are close to the stored ones but
 * not the stored ones: the limits and the signals below always come from the API.
 */
export function controlSeriesFor(
  siteCode: string,
  parameterCode: string,
): ControlSeries | null {
  const series = findDemoSeries(siteCode, parameterCode);

  if (!series) {
    return null;
  }

  return {
    siteCode: series.site.code,
    parameterCode: series.parameterCode,
    unitCode: series.unitCode,
    decimals: series.decimals,
    observations: series.observations.map((observation, index) => ({
      index,
      analyzedAt: observation.analyzedAt,
      value: observation.value,
      qualifier: observation.qualifier,
      loq: observation.loq,
      qcFlag: observation.qcFlag,
    })),
  };
}

/** The site UUID the SPC endpoints expect, or `null` for a code outside the demo list. */
export function controlSiteFor(siteCode: string): ControlSiteOption | null {
  return CONTROL_SITES.find((site) => site.code === siteCode) ?? null;
}

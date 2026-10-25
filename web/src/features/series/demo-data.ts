import type { Observation, QcFlag, WaterBodyType } from "@/types/api";

/**
 * Demo series for the Series screen.
 *
 * `GET /observations` is not published yet (Fase F), so the page plots this deterministic
 * replica of what `scripts/seed_demo.sh` loads: same four `SIM-*` sites, same five parameters
 * and the same anomalies per parameter. Values are generated with a linear congruential
 * generator instead of `Math.random`, so the screenshots of the README are reproducible.
 *
 * TODO(#E-1f): replace this module with `useObservations()` once the endpoint exists.
 */

export interface DemoSite {
  id: string;
  code: string;
  name: string;
  waterBodyType: WaterBodyType;
}

export interface DemoSeries {
  site: DemoSite;
  parameterCode: string;
  unitCode: string;
  decimals: number;
  /** Ascending by `analyzedAt`. */
  observations: Observation[];
  /** Anomalies the profile injects, so the UI can explain what to look for. */
  events: EventKind[];
}

export type EventKind = "shift" | "spike" | "drift" | "dropout" | "censored";

interface ParameterProfile {
  code: string;
  unitCode: string;
  decimals: number;
  base: number;
  /** Daily cycle amplitude; the simulator models the same diurnal shape. */
  dailyAmplitude: number;
  sigma: number;
  events: EventKind[];
}

const SITES: DemoSite[] = [
  {
    id: "8f1d1c52-5c1a-4f5e-9d0b-0f1c2a3b4c01",
    code: "SIM-RIO-MAIPO-01",
    name: "Río Maipo — Puente Alto",
    waterBodyType: "river",
  },
  {
    id: "8f1d1c52-5c1a-4f5e-9d0b-0f1c2a3b4c02",
    code: "SIM-RIO-MAPOCHO-01",
    name: "Río Mapocho — Pudahuel",
    waterBodyType: "river",
  },
  {
    id: "8f1d1c52-5c1a-4f5e-9d0b-0f1c2a3b4c03",
    code: "SIM-ESTERO-LAMPA-01",
    name: "Estero Lampa — Colina",
    waterBodyType: "river",
  },
  {
    id: "8f1d1c52-5c1a-4f5e-9d0b-0f1c2a3b4c04",
    code: "SIM-ESTERO-PUANGUE-01",
    name: "Estero Puangue — Curacaví",
    waterBodyType: "river",
  },
];

const PROFILES: ParameterProfile[] = [
  {
    code: "PH",
    unitCode: "UPH",
    decimals: 2,
    base: 7.62,
    dailyAmplitude: 0.12,
    sigma: 0.05,
    events: ["shift", "spike"],
  },
  {
    code: "DO",
    unitCode: "MG_L",
    decimals: 2,
    base: 8.4,
    dailyAmplitude: 0.55,
    sigma: 0.18,
    events: ["drift"],
  },
  {
    code: "COND",
    unitCode: "US_CM",
    decimals: 0,
    base: 618,
    dailyAmplitude: 22,
    sigma: 9,
    events: ["dropout", "censored"],
  },
  {
    code: "TURB",
    unitCode: "NTU",
    decimals: 1,
    base: 8.6,
    dailyAmplitude: 2.4,
    sigma: 0.9,
    events: ["shift", "drift"],
  },
  {
    code: "N_NO3",
    unitCode: "MG_N_L",
    decimals: 3,
    base: 1.24,
    dailyAmplitude: 0.06,
    sigma: 0.035,
    events: ["spike", "censored"],
  },
];

/** One reading every six hours for 30 days: 121 points per series, enough for an I-MR chart. */
const SAMPLE_INTERVAL_HOURS = 6;
const SERIES_DAYS = 30;
const POINT_COUNT = (SERIES_DAYS * 24) / SAMPLE_INTERVAL_HOURS + 1;

/** Offset added by each site so the four sites do not plot the same line. */
const SITE_OFFSETS: Record<string, number> = {
  "SIM-RIO-MAIPO-01": 0,
  "SIM-RIO-MAPOCHO-01": 0.06,
  "SIM-ESTERO-LAMPA-01": -0.04,
  "SIM-ESTERO-PUANGUE-01": 0.12,
};

/** Linear congruential generator (Numerical Recipes constants): same seed, same series. */
function createRandom(seed: number): () => number {
  let state = seed >>> 0;

  return () => {
    state = (Math.imul(state, 1_664_525) + 1_013_904_223) >>> 0;
    return state / 4_294_967_296;
  };
}

function seedFor(siteCode: string, parameterCode: string): number {
  let hash = 42;

  for (const character of `${siteCode}:${parameterCode}`) {
    hash = (Math.imul(hash, 31) + character.charCodeAt(0)) >>> 0;
  }

  return hash;
}

function round(value: number, decimals: number): number {
  const factor = 10 ** decimals;
  return Math.round(value * factor) / factor;
}


const MS_PER_HOUR = 3_600_000;

const DRIFT_START_INDEX = 60;
const SHIFT_RANGE = { from: 70, to: 90 };
const SPIKE_INDEX = 96;
const OUTAGE_RANGE = { from: 74, to: 79 };
const CENSORED_INDEXES = [40, 41, 42];

function buildSeries(site: DemoSite, profile: ParameterProfile): DemoSeries {
  const random = createRandom(seedFor(site.code, profile.code));
  const siteOffset = SITE_OFFSETS[site.code] ?? 0;
  const level = profile.base * (1 + siteOffset);
  const start = Date.now() - SERIES_DAYS * 24 * MS_PER_HOUR;

  const observations: Observation[] = [];
  let previousNoise = 0;

  for (let index = 0; index < POINT_COUNT; index += 1) {
    const isOutage =
      profile.events.includes("dropout") &&
      index >= OUTAGE_RANGE.from &&
      index <= OUTAGE_RANGE.to;

    // A dropout is a gap in the series, never a zero: the sensor simply did not report.
    if (isOutage) {
      continue;
    }

    const noise = 0.7 * previousNoise + profile.sigma * (random() - 0.5);
    previousNoise = noise;

    let value = level + profile.dailyAmplitude * Math.sin((2 * Math.PI * index) / 4) + noise;

    if (profile.events.includes("shift") && index >= SHIFT_RANGE.from && index <= SHIFT_RANGE.to) {
      value += 3 * profile.sigma;
    }

    if (profile.events.includes("spike") && index === SPIKE_INDEX) {
      value += 8 * profile.sigma;
    }

    if (profile.events.includes("drift") && index >= DRIFT_START_INDEX) {
      value += (index - DRIFT_START_INDEX) * 0.35 * profile.sigma;
    }

    const isCensored = profile.events.includes("censored") && CENSORED_INDEXES.includes(index);
    const analyzedAt = new Date(start + index * SAMPLE_INTERVAL_HOURS * MS_PER_HOUR).toISOString();
    const qcFlag: QcFlag = index === 55 ? "suspect" : "ok";

    observations.push({
      id: `demo-${site.code}-${profile.code}-${index}`,
      siteId: site.id,
      sampleId: null,
      parameterCode: profile.code,
      value: isCensored ? null : round(value, profile.decimals),
      unitCode: profile.unitCode,
      qualifier: isCensored ? "<" : null,
      loq: isCensored ? round(profile.sigma * 0.4, profile.decimals) : null,
      method: null,
      analyzedAt,
      qcFlag,
      source: "sensor",
    });
  }

  return {
    site,
    parameterCode: profile.code,
    unitCode: profile.unitCode,
    decimals: profile.decimals,
    observations,
    events: profile.events,
  };
}

/** Every demo series, built once at module load (4 sites × 5 parameters). */
export const DEMO_SERIES: DemoSeries[] = SITES.flatMap((site) =>
  PROFILES.map((profile) => buildSeries(site, profile)),
);

export const DEMO_SITES = SITES;

export const DEMO_PARAMETER_CODES = PROFILES.map((profile) => profile.code);

export function findDemoSeries(
  siteCode: string | null,
  parameterCode: string | null,
): DemoSeries | null {
  if (!siteCode || !parameterCode) {
    return null;
  }

  return (
    DEMO_SERIES.find(
      (series) => series.site.code === siteCode && series.parameterCode === parameterCode,
    ) ?? null
  );
}

export interface DemoOverview {
  observationsLast24h: number;
  siteCount: number;
  seriesWithAnomalies: number;
  censoredCount: number;
  lastObservationAt: Date | null;
  totalObservations: number;
}

function buildOverview(): DemoOverview {
  const all = DEMO_SERIES.flatMap((series) => series.observations);
  const lastTimestamp = all.reduce((latest, observation) => {
    const timestamp = new Date(observation.analyzedAt).getTime();
    return timestamp > latest ? timestamp : latest;
  }, 0);

  const last24h = all.filter(
    (observation) =>
      new Date(observation.analyzedAt).getTime() >= Date.now() - 24 * MS_PER_HOUR,
  );

  return {
    observationsLast24h: last24h.length,
    siteCount: SITES.length,
    seriesWithAnomalies: DEMO_SERIES.filter((series) => series.events.length > 0).length,
    censoredCount: all.filter((observation) => observation.qualifier === "<").length,
    lastObservationAt: lastTimestamp ? new Date(lastTimestamp) : null,
    totalObservations: all.length,
  };
}

export const DEMO_OVERVIEW: DemoOverview = buildOverview();

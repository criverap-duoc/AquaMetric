/**
 * Types of the public API contract. They mirror `api/app/schemas/*.py`, where every model
 * serializes with camelCase aliases (`CamelModel`), so the field names here are the ones that
 * travel on the wire — no mapping layer in between.
 *
 * Domain types that the API does not expose yet are marked with the slice that will add the
 * endpoint; until then they only document the shape the pages expect.
 */

/* ---------------------------------------------------------------- errors --- */

export interface ProblemError {
  field: string;
  message: string;
}

/** RFC 9457 payload returned by the API for every error (02 §8). */
export interface ProblemJson {
  type: string;
  title: string;
  status: number;
  code: string;
  detail: string;
  requestId: string;
  errors: ProblemError[];
}

/* ---------------------------------------------------------------- health --- */

/** `GET /api/v1/health` — `app/routers/health.py`. */
export interface HealthResponse {
  status: string;
  service: string;
  version: string;
  env: string;
  timestamp: string;
  requestId: string;
}

/* --------------------------------------------------------------- catalog --- */

/** `GET /api/v1/catalog/meta` — `app/schemas/catalog.py::CatalogMetaResponse`. */
export interface CatalogMeta {
  version: string;
  sha256: string;
  generatedAt: string;
  /** `draft-verified` until the chemist signs the values, then `validated`. */
  status: string;
  validatedBy: string | null;
  validatedAt: string | null;
}

/**
 * `GET /api/v1/catalog/parameters` — `app/schemas/catalog.py::ParameterRead`.
 *
 * The endpoint publishes only these eight fields: `holdingTimeHours`, `preservation`,
 * `container`, `methodReference`, `reportingBasis` and `sourceNote` live in `catalog/` but are
 * not part of the public contract yet.
 */
export interface Parameter {
  code: string;
  nameEs: string;
  category: string;
  canonicalUnitCode: string;
  /** Decimals the UI must show for this parameter (design-system §6.5). */
  decimals: number;
  measurementType: string;
  status: string;
  mvpOptional: boolean;
}

/** `GET /api/v1/catalog/units` — `app/schemas/catalog.py::UnitRead`. */
export interface Unit {
  code: string;
  nameEs: string;
  dimension: string;
  factorToCanonical: number;
}

/** `GET /api/v1/catalog/regulations` — `app/schemas/catalog.py::RegulationRead`. */
export interface Regulation {
  code: string;
  name: string;
  jurisdiction: string;
  scope: string;
}

/** The limit a screening comparison used — `app/schemas/screening.py::LimitApplied`. */
export interface LimitApplied {
  regulationCode: string;
  statistic: string;
  min: number | null;
  max: number | null;
  unitCode: string;
  /** `draft-verified` limits are shown as «Pendiente de validación», never as enforceable. */
  status: string;
  context: string | null;
  monitoringAreaCode: string | null;
  qualityLevel: string | null;
}

/** `GET /api/v1/catalog/limits` — the identified version of a limit. */
export interface CatalogLimit extends LimitApplied {
  parameterCode: string;
}

/* ----------------------------------------------------------- screening --- */

export type ScreeningFlag = "normal" | "above_range" | "below_range" | "not_evaluable";

/**
 * Public screening result. Never a compliance verdict (ADR-010): `warnings[]` always carries
 * the referential disclaimer.
 */
export interface ScreeningResponse {
  flag: ScreeningFlag;
  reason: string;
  limitApplied: LimitApplied | null;
  exceedanceRatio: number | null;
  warnings: string[];
}

/* ------------------------------------------------------------------- SPC --- */

/** One chart: center line, 3-sigma control limits and the sigma behind them. */
export interface ControlLimits {
  center: number;
  ucl: number;
  lcl: number;
  sigma: number;
  /** `imr_individuals`, `imr_moving_range`, `xbar_r_xbar` or `xbar_r_range`. */
  method: string;
  nPoints: number;
}

/** One signal of the Nelson / Western Electric scan (`R1`…`R5`). */
export interface RuleViolation {
  rule: string;
  /** Position of the point that completes the pattern, from 0. */
  index: number;
  description: string;
}

/**
 * `GET /api/v1/spc/control-charts` — `app/schemas/spc.py::ControlChartResponse`.
 *
 * The payload carries the limits, the signals and the baseline metadata, but **no series of
 * observations**: the plotted values come from `GET /observations`, which does not exist yet
 * (slice E-1c).
 */
export interface ControlChartResponse {
  individuals: ControlLimits;
  movingRange: ControlLimits | null;
  xbar: ControlLimits | null;
  r: ControlLimits | null;
  violations: RuleViolation[];
  /** `false` means the limits were computed on the fly and are not frozen. */
  baselinePersisted: boolean;
  baselineMetadata: Record<string, string | number>;
  warnings: string[];
}

/* ----------------------------------------------- domain (endpoints TBD) --- */

export type QcFlag = "ok" | "suspect" | "failed";

export type ObservationSource = "lab" | "field" | "sensor";

/** `"<"` marks a censored result (`value = null`, `loq` carries the detection limit). */
export type Qualifier = "<" | ">" | null;

export type WaterBodyType =
  | "river"
  | "lake"
  | "estuary"
  | "groundwater"
  | "effluent"
  | "drinking";

/**
 * Shape of `aquametric.site`. `GET /sites` is not published yet (Fase F): until then the UI
 * derives the site list from the demo series.
 */
export interface Site {
  id: string;
  code: string;
  name: string;
  waterBodyType: WaterBodyType;
  latitude: number;
  longitude: number;
  isActive: boolean;
}

/**
 * Shape of `aquametric.observation`. `GET /observations` is not published yet (Fase F); the
 * Series page renders demo rows with this shape so the table and the charts share one type.
 */
export interface Observation {
  id: string;
  siteId: string;
  sampleId: string | null;
  parameterCode: string;
  value: number | null;
  unitCode: string;
  qualifier: Qualifier;
  loq: number | null;
  method: string | null;
  analyzedAt: string;
  qcFlag: QcFlag;
  source: ObservationSource;
}

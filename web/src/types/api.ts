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

/**
 * `GET /api/v1/catalog/limits` — the identified version of a limit.
 *
 * The payload wraps the rows: `{ data, meta }`, where `meta.validatedCount` says how many of the
 * returned limits can actually produce a screening flag (ADR-010).
 */
export interface CatalogLimit extends LimitApplied {
  parameterCode: string;
}

export interface LimitsMeta {
  total: number;
  validatedCount: number;
  draftCount: number;
}

export interface LimitsResponse {
  data: CatalogLimit[];
  meta: LimitsMeta;
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

/**
 * `POST /api/v1/screening/evaluate` — one value plus the scope that selects a single limit.
 *
 * `regulation` with `context` (NCh 1.333) or with `monitoringArea` + `qualityLevel`
 * (D.S. 53/2014): an ambiguous scope answers `not_evaluable`, never a guess.
 */
export interface ScreeningRequest {
  parameterCode: string;
  value: number;
  unitCode: string;
  analyzedAt: string;
  regulation: string;
  context?: string | null;
  monitoringArea?: string | null;
  qualityLevel?: string | null;
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
 * Normative range published beside the control limits (ADR-010).
 *
 * Only a limit the chemist signed reaches this object; the UI draws it with its own style and
 * label because a control limit and a regulation threshold are different things (04 §2.5).
 */
export interface SpecLimitsRead {
  min: number | null;
  max: number | null;
  unitCode: string;
  regulationCode: string;
  /** Always `validated`: the backend never publishes a draft band. */
  status: string;
}

/**
 * `GET /api/v1/spc/control-charts` — `app/schemas/spc.py::ControlChartResponse`.
 *
 * The payload carries the limits, the signals and the baseline metadata, but **no series of
 * observations**: the plotted values come from `GET /observations` (slice F-1a), which is what
 * the Control screen reads with `order = asc`.
 */
export interface ControlChartResponse {
  individuals: ControlLimits;
  movingRange: ControlLimits | null;
  xbar: ControlLimits | null;
  r: ControlLimits | null;
  /** Normative band, when a single `validated` limit exists for the parameter. */
  specLimits: SpecLimitsRead | null;
  violations: RuleViolation[];
  /** `false` means the limits were computed on the fly and are not frozen. */
  baselinePersisted: boolean;
  baselineMetadata: Record<string, string | number>;
  warnings: string[];
}

/* -------------------------------------------------------------- domain --- */

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
 * `GET /api/v1/sites` — shape of `aquametric.site` (`app/schemas/site.py::SiteRead`).
 *
 * The uuid is the `siteId` the SPC endpoints expect, so the selectors no longer derive it from
 * the demo series.
 */
export interface Site {
  id: string;
  code: string;
  name: string;
  waterBodyType: WaterBodyType;
  latitude: number | null;
  longitude: number | null;
  isActive: boolean;
}

export interface SiteListMeta {
  page: number;
  pageSize: number;
  total: number;
}

/** One page of sites: the paginated envelope of 02 §4. */
export interface SiteListResponse {
  data: Site[];
  meta: SiteListMeta;
}

/* -------------------------------------------------------------- pipeline --- */

/** `GET /api/v1/pipeline/status` — one accepted batch, from `ingest_idempotency` (ADR-002). */
export interface BatchSummary {
  key: string;
  receivedAt: string;
  status: string;
  accepted: number;
  duplicates: number;
}

/** Newest observation of one site, with the parameter it measured. */
export interface SiteLastRead {
  siteId: string;
  siteCode: string;
  parameterCode: string;
  analyzedAt: string;
  value: number | null;
  unitCode: string;
}

/**
 * Status of the pipeline screen.
 *
 * `awsDeployed = false` means the S3 → Lambda path is not running and the demo feeds the API
 * directly: an informative state, not an error (ADR-004).
 */
export interface PipelineStatusResponse {
  awsDeployed: boolean;
  recentBatches: BatchSummary[];
  lastObservationPerSite: SiteLastRead[];
  limit: number;
}

/**
 * `GET /api/v1/observations` — one stored measurement (`app/schemas/observation.py`).
 *
 * `siteCode` travels inside the row on purpose: the table and the charts label rows by code, and
 * embedding it saves the screen a second request against `/sites`.
 */
export interface ObservationRead {
  id: string;
  siteId: string;
  siteCode: string;
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

/** Pagination envelope of the observation list, with the window that was applied. */
export interface ObservationsMeta {
  page: number;
  pageSize: number;
  total: number;
  from: string | null;
  to: string | null;
}

export interface ObservationsResponse {
  data: ObservationRead[];
  meta: ObservationsMeta;
}

/**
 * `GET /api/v1/observations/aggregate` — counters of one window (`ObservationAggregateRead`).
 *
 * The three statistics use measured values only: a censored row has no number, so substituting
 * `LOQ/2` would publish an invented measurement (ADR-003).
 */
export interface ObservationAggregate {
  count: number;
  censoredCount: number;
  minValue: number | null;
  maxValue: number | null;
  meanValue: number | null;
}

import type { QcFlag, Qualifier } from "@/types/api";

/**
 * One point of the plotted series.
 *
 * The control chart endpoint publishes limits, signals and baseline metadata but **no series**
 * (`app/schemas/spc.py`), so the values arrive from elsewhere and are adapted to this shape.
 */
export interface ControlObservation {
  /** Position in the plotted series, from 0. */
  index: number;
  /** UTC instant, ISO-8601 with `Z`. */
  analyzedAt: string;
  /** `null` is a censored result (`< LOQ`) or a dropout: never a zero. */
  value: number | null;
  qualifier: Qualifier;
  loq: number | null;
  qcFlag: QcFlag;
}

/**
 * Normative range of a regulation, drawn with its own style (04 §2.5) and never merged with the
 * control limits: one describes the process, the other a reference range (ADR-010).
 */
export interface ControlSpecLimit {
  min?: number;
  max?: number;
  regulationCode: string;
}

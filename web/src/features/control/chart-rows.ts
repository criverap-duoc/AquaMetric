import type { ControlObservation } from "@/features/control/types";
import type { ControlLimits, QcFlag } from "@/types/api";

/** Signal of a single point that the chart can prove on its own. */
export const SIGNAL_BEYOND_LIMIT = "R1";
/** Early-warning band: the point sits between 2σ and 3σ of the center line (R4/R5 territory). */
export const SIGNAL_WARNING = "2σ";

/** One row of the two panels: the individual value and the moving range that follows it. */
export interface ChartRow {
  /** Position in the plotted series, from 0: the x axis is the sequence, not the calendar. */
  index: number;
  /** Epoch milliseconds, for the time scale of the axis and the tooltip. */
  timestamp: number;
  analyzedAt: string;
  value: number | null;
  /** `|x[i] - x[i-1]|`; `null` when either neighbour has no value (censored or dropout). */
  movingRange: number | null;
  /** Quantification limit of a censored point, drawn as a hollow marker; `null` otherwise. */
  censoredAt: number | null;
  loq: number | null;
  qcFlag: QcFlag;
  signal: string | null;
}

/**
 * Join the values with the limits the API estimated.
 *
 * The chart only labels what a single point can prove: `R1` when the value falls outside a control
 * limit, `2σ` when it is beyond two sigmas. `R2`…`R5` describe a *sequence* and `app/spc/` reports
 * them as a list with the position that completes the pattern, so the panel below lists them
 * instead of guessing which dot belongs to which run.
 */
export function buildChartRows(
  observations: ControlObservation[],
  individuals: ControlLimits,
): ChartRow[] {
  const warningLimit = 2 * individuals.sigma;

  return observations.map((observation, position) => {
    const previous = observations[position - 1];
    const movingRange =
      previous && previous.value !== null && observation.value !== null
        ? Math.abs(observation.value - previous.value)
        : null;

    return {
      index: observation.index,
      timestamp: new Date(observation.analyzedAt).getTime(),
      analyzedAt: observation.analyzedAt,
      value: observation.value,
      movingRange,
      censoredAt: observation.value === null ? observation.loq : null,
      loq: observation.loq,
      qcFlag: observation.qcFlag,
      signal: signalOf(observation.value, individuals, warningLimit),
    };
  });
}

function signalOf(
  value: number | null,
  individuals: ControlLimits,
  warningLimit: number,
): string | null {
  if (value === null) {
    return null;
  }

  if (value > individuals.ucl || value < individuals.lcl) {
    return SIGNAL_BEYOND_LIMIT;
  }

  if (warningLimit > 0 && Math.abs(value - individuals.center) > warningLimit) {
    return SIGNAL_WARNING;
  }

  return null;
}

export function describeSignal(signal: string): string {
  if (signal === SIGNAL_BEYOND_LIMIT) {
    return "Fuera de los límites de control: un punto más allá de 3 σ (regla R1).";
  }

  return "Alerta temprana: el punto está en la banda de 2 σ a 3 σ (reglas R4 y R5).";
}

/** Bounds of the vertical axis: the data and every reference line, with a small margin. */
export function chartDomain(rows: ChartRow[], references: number[]): [number, number] {
  const values = rows.flatMap((row) =>
    [row.value, row.censoredAt].filter((value): value is number => value !== null),
  );
  const candidates = [...values, ...references.filter((value) => Number.isFinite(value))];

  if (candidates.length === 0) {
    return [0, 1];
  }

  const minimum = Math.min(...candidates);
  const maximum = Math.max(...candidates);
  const padding = (maximum - minimum) * 0.08 || 0.5;

  return [minimum - padding, maximum + padding];
}

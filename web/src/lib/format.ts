/**
 * Single place for locale formatting: dates are stored in UTC and shown in
 * America/Santiago, numbers use es-CL (comma decimal separator).
 */
const TIME_ZONE = "America/Santiago";

/** Thin space between value and unit, as required by the design system. */
const THIN_SPACE = "\u2009";

const EM_DASH = "—";

export function formatDate(
  value: Date | string,
  options: Intl.DateTimeFormatOptions = {},
): string {
  const date = typeof value === "string" ? new Date(value) : value;

  if (Number.isNaN(date.getTime())) {
    return EM_DASH;
  }

  // dateStyle/timeStyle cannot be mixed with individual fields, so callers that
  // need components must pass both of them explicitly as undefined.
  return new Intl.DateTimeFormat("es-CL", {
    timeZone: TIME_ZONE,
    dateStyle: "medium",
    timeStyle: "short",
    ...options,
  }).format(date);
}

export function formatNumber(value: number, decimals = 2): string {
  return new Intl.NumberFormat("es-CL", {
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals,
  }).format(value);
}

export function formatUnit(value: number, unitCode: string, decimals = 2): string {
  return `${formatNumber(value, decimals)}${THIN_SPACE}${unitCode}`;
}

/** Short day label for chart axes (`24-10`), always in America/Santiago. */
export function formatDay(value: Date | string): string {
  // `dateStyle` / `timeStyle` must be cleared explicitly: Intl rejects combining them with
  // individual fields.
  return formatDate(value, {
    dateStyle: undefined,
    timeStyle: undefined,
    day: "2-digit",
    month: "2-digit",
  });
}

/** Date and time on two lines' worth of content, used in tooltips and table cells. */
export function formatDateTime(value: Date | string): string {
  return formatDate(value);
}

/**
 * Freshness of a reading, e.g. «hace 5 minutos».
 *
 * Relative on purpose: the dashboard answers «how old is the newest reading?», and an absolute
 * timestamp in Santiago would make the reader do the subtraction. Arguments are explicit so the
 * caller can pass a fixed `now` in a test.
 */
export function formatRelativeTime(value: Date | string, now: Date = new Date()): string {
  const date = typeof value === "string" ? new Date(value) : value;
  const delta = date.getTime() - now.getTime();

  if (Number.isNaN(delta)) {
    return EM_DASH;
  }

  if (Math.abs(delta) < 60_000) {
    return "hace unos segundos";
  }

  const formatter = new Intl.RelativeTimeFormat("es-CL", { numeric: "auto" });

  if (Math.abs(delta) >= 86_400_000) {
    return formatter.format(Math.round(delta / 86_400_000), "day");
  }

  if (Math.abs(delta) >= 3_600_000) {
    return formatter.format(Math.round(delta / 3_600_000), "hour");
  }

  return formatter.format(Math.round(delta / 60_000), "minute");
}

/**
 * Age of a reading for a dashboard caption, or `null` when its timestamp is in the future.
 *
 * A future timestamp means the producer clock ran ahead of the server — the simulator can be
 * seeded with a fixed start — and «dentro de 29 días» is noise instead of information: the caller
 * shows the absolute date in that case.
 */
export function formatPastAge(value: Date | string, now: Date = new Date()): string | null {
  const date = typeof value === "string" ? new Date(value) : value;

  if (Number.isNaN(date.getTime()) || date.getTime() > now.getTime()) {
    return null;
  }

  return formatRelativeTime(date, now);
}

export function formatCensored(loq: number, unitCode: string, decimals = 2): string {
  return `<${THIN_SPACE}${formatUnit(loq, unitCode, decimals)}`;
}

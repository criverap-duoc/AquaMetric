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

export function formatCensored(loq: number, unitCode: string, decimals = 2): string {
  return `<${THIN_SPACE}${formatUnit(loq, unitCode, decimals)}`;
}

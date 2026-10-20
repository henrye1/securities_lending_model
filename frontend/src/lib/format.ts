// Shared formatting helpers.

/** Fraction as a percentage string; null/undefined renders "—". */
export const pct = (v: number | null | undefined, dp = 2) =>
  v === null || v === undefined || Number.isNaN(v) ? "—" : `${(v * 100).toFixed(dp)}%`;

/** Plain number with thousands separators. */
export const num = (v: number | null | undefined, dp = 0) =>
  v === null || v === undefined || Number.isNaN(v)
    ? "—"
    : v.toLocaleString(undefined, { maximumFractionDigits: dp, minimumFractionDigits: dp });

/** Currency amount, 0 decimals, thousands separators. */
export const money = (v: number | null | undefined) => num(v, 0);

/** Cover multiple, e.g. 2.29x. */
export const ratio = (v: number | null | undefined, dp = 2) =>
  v === null || v === undefined || Number.isNaN(v) ? "—" : `${v.toFixed(dp)}x`;

export const dateStr = (iso: string | null | undefined) =>
  iso ? new Date(iso).toLocaleDateString() : "—";

/** "Not Applicable" for null amounts (the workbook's convention). */
export const amountOrNa = (v: number | null | undefined) =>
  v === null || v === undefined ? "Not Applicable" : money(v);

export const rateOrNa = (v: number | null | undefined) =>
  v === null || v === undefined ? "Not Applicable" : pct(v);

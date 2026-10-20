// Client-side mirrors of the Input / Portfolio page formulas, used for the live
// read-only cells (Total Stock Value, Initial Cover Ratio, Time to unwind,
// Outputs (Combined)). The backend recomputes everything on calculate.
import type { PortfolioPayload, StockPayload } from "./api";

export const MAX_STOCKS = 10;

/** VBA CInt: round half to even. */
export function cint(x: number): number {
  const f = Math.floor(x);
  const diff = x - f;
  if (diff > 0.5) return f + 1;
  if (diff < 0.5) return f;
  return f % 2 === 0 ? f : f + 1;
}

/** VBA Equity_Duration: years to sell all shares at `pct` of average daily volume. */
export function equityDuration(shares: number, adtv: number, pct = 0.25, days = 251): number {
  if (shares <= 0 || adtv <= 0 || pct <= 0) return 0;
  const n = cint(shares / adtv / pct);
  return n <= 0 ? 0 : (n + 1) / 2 / days;
}

/** Calculations!E44 liquidity flag. */
export function liquidityFlag(listing: string, shares: number, adtv: number): string {
  if (listing === "Unlisted") return "";
  return shares / 40 > adtv * 0.25 ? "Illiquid" : "Liquid";
}

export function identity(n = MAX_STOCKS): number[][] {
  return Array.from({ length: n }, (_, i) => Array.from({ length: n }, (_, j) => (i === j ? 1 : 0)));
}

export function zeros(n = MAX_STOCKS): number[][] {
  return Array.from({ length: n }, () => Array(n).fill(0));
}

export function emptyStock(): StockPayload {
  return {
    name: "",
    number_of_shares: 0,
    share_price: 0,
    volatility: 0,
    dividend_yield: 0,
    average_daily_volume: 0,
    country: "South Africa",
    risk_grade: "SB11",
    revenue_size: "Revenue > R500m",
    sector: "",
    ebitda: 0,
    market_cap: 0,
    total_liabilities: 0,
    time_to_unwind: 0,
    unlisted_haircut: 0.5,
    illiquid_haircut: 0.3,
    currency_pair: "ZAR/ZAR",
    currency_volatility: 0,
  };
}

export function emptyPortfolio(): PortfolioPayload {
  return {
    stocks: [emptyStock()],
    equity_correlation: identity(),
    currency_correlation: identity(),
    currency_equity_correlation: zeros(),
  };
}

export interface PortfolioCombinedLite {
  number_of_shares: number;
  share_price: number;
  stock_volatility: number;
  dividend_yield: number;
  average_daily_volume: number;
  time_to_unwind: number;
  unlisted_haircut: number;
  illiquid_haircut: number;
  risk_free_rate: number;
  stock_values: number[];
  weights: number[];
}

/** Portfolio Transactions "Outputs (Combined)" block, E84:E93 (minus Equity LGD). */
export function combinePortfolio(
  p: PortfolioPayload,
  rfByCountry: Record<string, number>,
): PortfolioCombinedLite {
  const stocks: StockPayload[] = [...p.stocks];
  while (stocks.length < MAX_STOCKS) stocks.push(emptyStock());
  const values = stocks.map((s) => s.number_of_shares * s.share_price);
  const total = values.reduce((a, b) => a + b, 0);
  const shares = stocks.reduce((a, s) => a + s.number_of_shares, 0);
  const weighted = (f: (s: StockPayload) => number) =>
    total ? stocks.reduce((a, s, i) => a + f(s) * values[i], 0) / total : 0;

  const n = MAX_STOCKS;
  const w = [
    ...stocks.map((s, i) => (total ? (values[i] / total) * s.volatility : 0)),
    ...stocks.map((s, i) => (total ? (values[i] / total) * s.currency_volatility : 0)),
  ];
  const cell = (m: number[][], i: number, j: number) => Number(m?.[i]?.[j] ?? 0) || 0;
  const big = Array.from({ length: 2 * n }, () => Array(2 * n).fill(0));
  for (let i = 0; i < n; i++) {
    for (let j = 0; j < n; j++) {
      big[i][j] = cell(p.equity_correlation, i, j);
      big[n + i][n + j] = cell(p.currency_correlation, i, j);
      const fxeq = Math.max(0, cell(p.currency_equity_correlation, i, j));
      big[n + i][j] = fxeq;
      big[j][n + i] = fxeq;
    }
  }
  let variance = 0;
  for (let i = 0; i < 2 * n; i++) for (let j = 0; j < 2 * n; j++) variance += w[i] * big[i][j] * w[j];

  return {
    number_of_shares: shares,
    share_price: shares ? total / shares : 0,
    stock_volatility: variance > 0 ? Math.sqrt(variance) : 0,
    dividend_yield: weighted((s) => s.dividend_yield),
    average_daily_volume: weighted((s) => s.average_daily_volume),
    time_to_unwind: weighted((s) => s.time_to_unwind),
    unlisted_haircut: weighted((s) => s.unlisted_haircut),
    illiquid_haircut: weighted((s) => s.illiquid_haircut),
    risk_free_rate: weighted((s) => rfByCountry[s.country] ?? 0),
    stock_values: values,
    weights: values.map((v) => (total ? v / total : 0)),
  };
}

/** Mirror a symmetric matrix edit: set [i][j] and [j][i]. */
export function setSymmetric(m: number[][], i: number, j: number, v: number): number[][] {
  const out = m.map((row) => [...row]);
  out[i][j] = v;
  out[j][i] = v;
  return out;
}

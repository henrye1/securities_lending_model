// Typed API client for the Securities Lending (Share Cover) Model backend.

export type Structure =
  | "Bullet Payment"
  | "Straight Amortisation"
  | "Interest Only Repayments"
  | "Straight Amortisation & Bullet";
export type Listing = "Listed" | "Unlisted";

// ---- reference / capture config --------------------------------------------

export interface CountryOption {
  name: string;
  risk_free_rate: number | null;
}

export interface MasterscaleRow {
  grade: string;
  fitted_pd: number;
  lower: number;
  upper: number;
}

export interface CaptureConfig {
  structures: Structure[];
  yes_no: string[];
  listings: Listing[];
  dividend_options: string[];
  recovery_policies: string[];
  grades: string[];
  revenue_sizes: string[];
  sectors: string[];
  countries: CountryOption[];
  pd_masterscale: MasterscaleRow[];
  defaults: {
    default_cover_ratio: number;
    unlisted_haircut: number;
    illiquid_haircut: number;
    min_pd: number;
    trading_days: number;
    unwind_pct: number;
  };
}

// ---- transaction capture ------------------------------------------------------

export interface DcrChange {
  time: number;
  dcr: number;
}

export interface RateBucket {
  lower_bound: number;
  rate: number;
}

export interface SectorWeight {
  sector: string;
  weight: number;
}

export interface StockPayload {
  name: string;
  number_of_shares: number;
  share_price: number;
  volatility: number;
  dividend_yield: number;
  average_daily_volume: number;
  country: string;
  risk_grade: string;
  revenue_size: string;
  sector: string;
  ebitda: number;
  market_cap: number;
  total_liabilities: number;
  time_to_unwind: number;
  unlisted_haircut: number;
  illiquid_haircut: number;
  currency_pair: string;
  currency_volatility: number;
}

export interface PortfolioPayload {
  stocks: StockPayload[];
  equity_correlation: number[][];
  currency_correlation: number[][];
  currency_equity_correlation: number[][];
}

/** The workbook's Input page. `null` on an amount = "Not Applicable". */
export interface TransactionPayload {
  client_cif: string;
  client_name: string;
  client_country: string;
  portfolio_of_shares: boolean;
  start_date: string;
  maturity_date: string;
  structure: Structure;
  amortised_loan_amount: number | null;
  bullet_loan_amount: number | null;
  number_of_shares: number;
  share_price: number;
  average_daily_volume: number;
  dcr_changes: boolean;
  default_cover_ratio: number;
  dcr_schedule: DcrChange[];
  bullet_interest_rate: number | null;
  rate_linked_to_cover: boolean;
  amortised_interest_rate: number | null;
  rate_schedule: RateBucket[];
  dividend_yield: number;
  dividends_repaid: number;
  stock_volatility: number;
  liabilities_ahead: number | null;
  liabilities_pari_passu: number | null;
  liabilities_subordinate: number | null;
  other_collateral: number | null;
  collateral_pari_passu: number | null;
  other_pari_passu_liabilities: number | null;
  reference_cif: string;
  reference_name: string;
  reference_country: string;
  listing: Listing;
  risk_grade: string;
  revenue_size: string;
  sectors: SectorWeight[];
  unlisted_haircut: number;
  illiquid_haircut: number;
  risk_free_rate: number | null;
  currency_mismatch: boolean;
  currency_volatility: number;
  currency_correlation: number;
  recovery_approach: number;
  random_seed: number | null;
  portfolio: PortfolioPayload | null;
}

export interface Transaction extends TransactionPayload {
  id: string;
  batch_id: string;
  created_at: string;
  updated_at: string;
  latest_run_id: string | null;
  latest_pd: number | null;
  latest_risk_grade: string | null;
  latest_lgd: number | null;
  latest_el: number | null;
  status: string; // draft | calculated
}

export interface Batch {
  id: string;
  name: string;
  created_at: string;
  transaction_count: number;
}

// ---- run result -----------------------------------------------------------------

export interface YearRow {
  year: number;
  dt: number;
  dcr: number;
  avg_loan: number;
  avg_share_value: number;
  spv_pd_covenant: number;
  spv_pd: number;
  spv_pd_no_covenant: number;
  issuer_default_rate: number;
  issuer_lgd: number;
  spv_lgd: number;
  covenant_effectiveness: number;
  combined_pd: number;
  combined_lgd: number;
}

export interface ResultsBlock {
  pd_client_avg: number;
  pd_client_weighted: number;
  pd_client_grade: string;
  pd_issuer_avg: number;
  pd_issuer_weighted: number;
  pd_issuer_grade: string;
  pd_total: number;
  lgd_client_avg: number;
  lgd_client_weighted: number;
  lgd_issuer_avg: number;
  lgd_issuer_weighted: number;
  lgd_total: number;
  el: number;
  risk_grade: string;
  rwa_pct: number;
}

export interface ReportColumn {
  pd: number;
  grade: string;
  lgd: number;
  el: number;
  el_grade: string;
  rwa_pct: number;
}

export interface Derived {
  years_total: number;
  initial_cover_ratio: number;
  initial_dcr: number;
  dcr_by_year: number[];
  discount_factor: number;
  unwind_years: number;
  unwind_days: number;
  fsh: number;
  reference_pd: number;
  volatility: number;
  n_paths: number;
  workbook_draws: boolean;
  quirks_applied: boolean;
  share_value: number;
  number_of_shares: number;
  share_price: number;
  liquidity: string;
  dividend_yield: number;
  risk_free_rate: number;
  recovery_policy: string;
  amortised_amount: number;
  bullet_amount: number;
  bullet_rate: number;
}

export interface PortfolioCombined {
  number_of_shares: number;
  share_price: number;
  stock_volatility: number;
  dividend_yield: number;
  average_daily_volume: number;
  time_to_unwind: number;
  unlisted_haircut: number;
  illiquid_haircut: number;
  risk_free_rate: number;
  equity_lgd: number | null;
  stock_values: number[];
  weights: number[];
}

export interface EngineResultPayload {
  years: YearRow[];
  results: ResultsBlock;
  report: { reference: ReportColumn; client: ReportColumn; combined: ReportColumn };
  derived: Derived;
  portfolio: PortfolioCombined | null;
  warnings: string[];
  report_date: string;
}

export interface Run {
  id: string;
  transaction_id: string;
  created_at: string;
  inputs: TransactionPayload;
  result: EngineResultPayload;
  pd_total: number;
  risk_grade: string;
  lgd_total: number;
  el: number;
  rwa_pct: number;
}

// ---- fetch helpers ------------------------------------------------------------

class ApiError extends Error {
  constructor(
    public status: number,
    message: string,
  ) {
    super(message);
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const resp = await fetch(path, {
    headers: { "Content-Type": "application/json" },
    ...init,
  });
  if (!resp.ok) {
    let detail = resp.statusText;
    try {
      const body = await resp.json();
      detail = typeof body.detail === "string" ? body.detail : JSON.stringify(body.detail);
    } catch {
      /* keep statusText */
    }
    throw new ApiError(resp.status, detail);
  }
  if (resp.status === 204) return undefined as T;
  return resp.json() as Promise<T>;
}

export const api = {
  health: () => request<{ status: string; model: string }>("/api/health"),
  captureConfig: () => request<CaptureConfig>("/api/reference/capture-config"),
  listBatches: () => request<Batch[]>("/api/batches"),
  createBatch: (name: string) =>
    request<Batch>("/api/batches", { method: "POST", body: JSON.stringify({ name }) }),
  getBatch: (id: string) => request<Batch>(`/api/batches/${id}`),
  deleteBatch: (id: string) => request<void>(`/api/batches/${id}`, { method: "DELETE" }),
  listTransactions: (batchId: string) =>
    request<Transaction[]>(`/api/batches/${batchId}/transactions`),
  createTransaction: (batchId: string, payload: TransactionPayload) =>
    request<Transaction>(`/api/batches/${batchId}/transactions`, {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  getTransaction: (id: string) => request<Transaction>(`/api/transactions/${id}`),
  updateTransaction: (id: string, payload: TransactionPayload) =>
    request<Transaction>(`/api/transactions/${id}`, {
      method: "PUT",
      body: JSON.stringify(payload),
    }),
  deleteTransaction: (id: string) =>
    request<void>(`/api/transactions/${id}`, { method: "DELETE" }),
  calculate: (txId: string) =>
    request<Run>(`/api/transactions/${txId}/calculate`, { method: "POST" }),
  listRuns: (txId: string) => request<Run[]>(`/api/transactions/${txId}/runs`),
  getRun: (runId: string) => request<Run>(`/api/runs/${runId}`),
  exportUrl: (runId: string) => `/api/runs/${runId}/export.xlsx`,
};

import type { CaptureConfig, PortfolioPayload, StockPayload, TransactionPayload } from "../../lib/api";
import { money, num, pct, ratio } from "../../lib/format";
import { MAX_STOCKS, emptyStock, normaliseMatrix, removeStockAt, setSymmetric, type PortfolioCombinedLite } from "../../lib/model";
import { NumberField, Select } from "../../components/fields";

interface Props {
  config: CaptureConfig;
  payload: TransactionPayload;
  onChange: (p: TransactionPayload) => void;
  combined: PortfolioCombinedLite | null;
  busy: boolean;
  onBack: () => void;
  onCalculate: () => void;
}

type NumKey = {
  [K in keyof StockPayload]: StockPayload[K] extends number ? K : never;
}[keyof StockPayload];

const NUMERIC_ROWS: { key: NumKey; label: string; scale?: number; suffix?: string; step?: number }[] = [
  { key: "number_of_shares", label: "Number of Shares" },
  { key: "share_price", label: "Share Price", step: 0.01 },
  { key: "volatility", label: "Stock Volatility", scale: 100, suffix: "%" },
  { key: "dividend_yield", label: "Dividend Yield", scale: 100, suffix: "%" },
  { key: "average_daily_volume", label: "Average Daily Traded Volumes" },
];

const REFERENCE_ROWS: { key: NumKey; label: string; scale?: number; suffix?: string; step?: number }[] = [
  { key: "ebitda", label: "EBITDA" },
  { key: "market_cap", label: "Total Stock Market Capitalisation" },
  { key: "total_liabilities", label: "Total Liabilities" },
  { key: "time_to_unwind", label: "Time to unwind share in market (years)", step: 0.05 },
  { key: "unlisted_haircut", label: "Unlisted Share Haircut", scale: 100, suffix: "%" },
  { key: "illiquid_haircut", label: "Illiquid Share Haircut", scale: 100, suffix: "%" },
];

export function PortfolioStep({ config, payload, onChange, combined, busy, onBack, onCalculate }: Props) {
  const portfolio: PortfolioPayload = payload.portfolio ?? {
    stocks: [emptyStock()],
    equity_correlation: [],
    currency_correlation: [],
    currency_equity_correlation: [],
  };
  const setPortfolio = (patch: Partial<PortfolioPayload>) =>
    onChange({ ...payload, portfolio: { ...portfolio, ...patch } });
  const stocks = portfolio.stocks;
  const setStock = (i: number, patch: Partial<StockPayload>) => {
    const next = stocks.map((s, k) => (k === i ? { ...s, ...patch } : s));
    setPortfolio({ stocks: next });
  };
  const addStock = () => stocks.length < MAX_STOCKS && setPortfolio({ stocks: [...stocks, emptyStock()] });
  // Drop the stock AND its row/column in all three matrices (keeps correlations aligned).
  const removeStock = (i: number) => onChange({ ...payload, portfolio: removeStockAt(portfolio, i) });
  const countryNames = config.countries.map((c) => c.name);
  const cols = stocks.map((_, i) => i);
  const rfByCountry = Object.fromEntries(config.countries.map((c) => [c.name, c.risk_free_rate ?? 0]));

  const matrix = (
    title: string,
    m: number[][],
    key: "equity_correlation" | "currency_correlation" | "currency_equity_correlation",
    rowLabel: (i: number) => string,
    colLabel: (j: number) => string,
    symmetric: boolean,
  ) => (
    <div className="card">
      <div className="section-header">{title}</div>
      <div className="overflow-x-auto p-4">
        <table className="text-xs">
          <thead>
            <tr>
              <th className="px-2 py-1 text-left" />
              {cols.map((j) => (
                <th key={j} className="px-2 py-1 text-center font-semibold text-slate-600">{colLabel(j)}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {cols.map((i) => (
              <tr key={i}>
                <td className="px-2 py-1 font-semibold text-slate-600">{rowLabel(i)}</td>
                {cols.map((j) => {
                  const v = m?.[i]?.[j] ?? (symmetric && i === j ? 1 : 0);
                  const fixed = symmetric && (i === j || j < i);
                  return (
                    <td key={j} className="px-1 py-0.5">
                      <div className="w-20">
                        <NumberField
                          value={v}
                          readOnly={fixed}
                          step={0.01}
                          onChange={(raw) => {
                            const n = raw ?? 0;
                            const base = normaliseMatrix(m, (r, c) => (symmetric && r === c ? 1 : 0));
                            const next = symmetric
                              ? setSymmetric(base, i, j, n)
                              : base.map((row, r) => row.map((cell, c) => (r === i && c === j ? n : cell)));
                            setPortfolio({ [key]: next } as Partial<PortfolioPayload>);
                          }}
                        />
                      </div>
                    </td>
                  );
                })}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );

  const inputRow = (label: string, render: (s: StockPayload, i: number) => React.ReactNode) => (
    <tr key={label} className="odd:bg-slate-50">
      <td className="sticky left-0 bg-inherit px-3 py-1 text-xs font-semibold text-slate-600">{label}</td>
      {stocks.map((s, i) => (
        <td key={i} className="px-1 py-0.5">{render(s, i)}</td>
      ))}
    </tr>
  );

  return (
    <div className="space-y-4">
      <div className="card">
        <div className="section-header">
          <span>Inputs — up to {MAX_STOCKS} stocks</span>
          <button className="btn-secondary py-1" onClick={addStock} disabled={stocks.length >= MAX_STOCKS}>+ Add stock</button>
        </div>
        <div className="overflow-x-auto p-2">
          <table className="min-w-full">
            <thead>
              <tr>
                <th className="px-3 py-1 text-left text-xs font-semibold text-slate-500">Stock</th>
                {stocks.map((_, i) => (
                  <th key={i} className="px-1 py-1 text-xs font-semibold text-cyte-navyDark">
                    STOCK {i + 1}
                    {stocks.length > 1 && (
                      <button className="ml-2 text-cyte-ragRed" title="Remove" onClick={() => removeStock(i)}>×</button>
                    )}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {inputRow("Name", (s, i) => (
                <input className="field-input min-w-[9rem]" value={s.name} onChange={(e) => setStock(i, { name: e.target.value })} />
              ))}
              {NUMERIC_ROWS.map((r) =>
                inputRow(r.label, (s, i) => (
                  <div className="min-w-[9rem]">
                    <NumberField value={s[r.key]} scale={r.scale} suffix={r.suffix} step={r.step} onChange={(v) => setStock(i, { [r.key]: v ?? 0 })} />
                  </div>
                )),
              )}
              {inputRow("Stock Value", (s) => (
                <span className="block px-2 text-right text-sm">{money(s.number_of_shares * s.share_price)}</span>
              ))}
              <tr><td colSpan={stocks.length + 1} className="px-3 pt-3 text-xs font-bold uppercase tracking-wide text-cyte-navyDark">Reference Share Details</td></tr>
              {inputRow("Country of Risk", (s, i) => (
                <div className="min-w-[9rem]"><Select value={s.country} options={countryNames} onChange={(v) => setStock(i, { country: v })} /></div>
              ))}
              {inputRow("Risk Grade of Reference Entity", (s, i) => (
                <div className="min-w-[9rem]"><Select value={s.risk_grade} options={config.grades} onChange={(v) => setStock(i, { risk_grade: v })} /></div>
              ))}
              {inputRow("Revenue Size", (s, i) => (
                <div className="min-w-[9rem]"><Select value={s.revenue_size} options={config.revenue_sizes} onChange={(v) => setStock(i, { revenue_size: v })} /></div>
              ))}
              {inputRow("Corporate Sector", (s, i) => (
                <div className="min-w-[9rem]"><Select value={s.sector} options={config.sectors} allowEmpty onChange={(v) => setStock(i, { sector: v })} /></div>
              ))}
              {REFERENCE_ROWS.map((r) =>
                inputRow(r.label, (s, i) => (
                  <div className="min-w-[9rem]">
                    <NumberField value={s[r.key]} scale={r.scale} suffix={r.suffix} step={r.step} onChange={(v) => setStock(i, { [r.key]: v ?? 0 })} />
                  </div>
                )),
              )}
              {inputRow("Risk Free Rate", (s) => (
                <span className="block px-2 text-right text-sm">{pct(rfByCountry[s.country] ?? 0)}</span>
              ))}
              <tr><td colSpan={stocks.length + 1} className="px-3 pt-3 text-xs font-bold uppercase tracking-wide text-cyte-navyDark">Currency Risk</td></tr>
              {inputRow("Currency Pair", (s, i) => (
                <input className="field-input min-w-[9rem]" value={s.currency_pair} onChange={(e) => setStock(i, { currency_pair: e.target.value })} />
              ))}
              {inputRow("Currency Pair - Volatility", (s, i) => (
                <div className="min-w-[9rem]"><NumberField value={s.currency_volatility} scale={100} suffix="%" onChange={(v) => setStock(i, { currency_volatility: v ?? 0 })} /></div>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {matrix("Correlation Matrix - Equity", portfolio.equity_correlation, "equity_correlation", (i) => `STOCK ${i + 1}`, (j) => `STOCK ${j + 1}`, true)}
      {matrix("Correlation Matrix - Currency Pairs", portfolio.currency_correlation, "currency_correlation", (i) => `PAIR ${i + 1}`, (j) => `PAIR ${j + 1}`, true)}
      {matrix("Correlation Matrix - Currency Pairs and Equity", portfolio.currency_equity_correlation, "currency_equity_correlation", (i) => `PAIR ${i + 1}`, (j) => `STOCK ${j + 1}`, false)}

      <div className="card">
        <div className="section-header">Outputs (Combined)</div>
        {combined ? (
          <div className="grid grid-cols-2 gap-x-8 gap-y-1 p-4 text-sm md:grid-cols-3">
            {[
              ["Number of Shares", num(combined.number_of_shares)],
              ["Share Price", num(combined.share_price, 4)],
              ["Stock Volatility", pct(combined.stock_volatility)],
              ["Dividend Yield", pct(combined.dividend_yield)],
              ["Average Daily Traded Volumes", num(combined.average_daily_volume, 2)],
              ["Time to unwind share in market (years)", ratio(combined.time_to_unwind, 4).replace("x", "")],
              ["Unlisted Share Haircut", pct(combined.unlisted_haircut)],
              ["Illiquid Share Haircut", pct(combined.illiquid_haircut)],
              ["Risk Free Rate", pct(combined.risk_free_rate)],
              ["Total Stock Value", money(combined.stock_values.reduce((a, b) => a + b, 0))],
            ].map(([k, v]) => (
              <div key={k} className="flex justify-between border-b border-slate-100 py-1">
                <span className="text-slate-600">{k}</span>
                <span className="font-semibold">{v}</span>
              </div>
            ))}
          </div>
        ) : (
          <div className="p-4 text-sm text-slate-500">Capture at least one stock.</div>
        )}
        <p className="px-4 pb-3 text-xs text-slate-500">
          Equity LGD per stock (the Obligor Specific Inputs block) is computed by the backend on calculate when available.
        </p>
      </div>

      <div className="flex justify-between">
        <button className="btn-secondary" onClick={onBack} disabled={busy}>← Back to Input</button>
        <button className="btn-primary" onClick={onCalculate} disabled={busy || stocks.length === 0}>
          {busy ? "Calculating…" : "Save & Calculate →"}
        </button>
      </div>
    </div>
  );
}

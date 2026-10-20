import type { Run, YearRow } from "../../lib/api";
import { money, num, pct, ratio } from "../../lib/format";
import { GradeChip } from "../../components/GradeChip";

interface Props {
  run: Run;
  busy: boolean;
  onRecalculate: () => void;
  onNext: () => void;
}

type Fmt = (v: number) => string;
const pct4: Fmt = (v) => pct(v, 4);
const pct2: Fmt = (v) => pct(v, 2);
const x2: Fmt = (v) => ratio(v);
const r3: Fmt = (v) => num(v, 3);

const YEAR_ROWS: { key: keyof YearRow; label: string; fmt: Fmt }[] = [
  { key: "dt", label: "Time Change", fmt: r3 },
  { key: "dcr", label: "Default Cover Ratio", fmt: x2 },
  { key: "avg_loan", label: "Average Loan Amount", fmt: money },
  { key: "avg_share_value", label: "Average Share Value", fmt: money },
  { key: "spv_pd_covenant", label: "SPV Annual PD [Covenant Breach]", fmt: pct4 },
  { key: "spv_pd", label: "SPV Annual PD [SPV]", fmt: pct4 },
  { key: "spv_pd_no_covenant", label: "SPV Annual PD [No Covenant]", fmt: pct4 },
  { key: "issuer_default_rate", label: "Issuer Default Rate", fmt: pct4 },
  { key: "issuer_lgd", label: "Issuer Loss Given Default", fmt: pct2 },
  { key: "spv_lgd", label: "SPV Loss Given Default", fmt: pct2 },
  { key: "covenant_effectiveness", label: "Covenant Effectiveness Index", fmt: r3 },
  { key: "combined_pd", label: "Combined Risk", fmt: pct4 },
  { key: "combined_lgd", label: "Combined LGD", fmt: pct2 },
];

export function CalculateStep({ run, busy, onRecalculate, onNext }: Props) {
  const { years, results, derived, warnings, portfolio } = run.result;
  const active = years.filter((y) => y.dt > 0);

  const Line = ({ label, value }: { label: string; value: React.ReactNode }) => (
    <div className="flex items-center justify-between border-b border-slate-100 py-1 text-sm">
      <span className="text-slate-600">{label}</span>
      <span className="font-semibold">{value}</span>
    </div>
  );

  return (
    <div className="space-y-4">
      {warnings.length > 0 && (
        <div className="rounded border border-cyte-ragAmber bg-cyte-ragAmberBg px-3 py-2 text-sm text-cyte-ragAmber">
          {warnings.map((w) => (
            <div key={w}>{w}</div>
          ))}
        </div>
      )}

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-3">
        <div className="card">
          <div className="section-header">Results — PD</div>
          <div className="p-4">
            <Line label="PD Client · Average PD" value={pct4(results.pd_client_avg)} />
            <Line label="PD Client · Weighted PD" value={pct4(results.pd_client_weighted)} />
            <Line label="PD Client · Risk Grade" value={<GradeChip grade={results.pd_client_grade} />} />
            <Line label="PD Issuer · Average PD" value={pct4(results.pd_issuer_avg)} />
            <Line label="PD Issuer · Weighted PD" value={pct4(results.pd_issuer_weighted)} />
            <Line label="PD Issuer · Risk Grade" value={<GradeChip grade={results.pd_issuer_grade} />} />
            <Line label="Total Transaction PD" value={<b className="text-cyte-navy">{pct4(results.pd_total)}</b>} />
          </div>
        </div>
        <div className="card">
          <div className="section-header">Results — LGD, EL, RWA</div>
          <div className="p-4">
            <Line label="LGD Client · Average LGD" value={pct2(results.lgd_client_avg)} />
            <Line label="LGD Client · Weighted LGD" value={pct2(results.lgd_client_weighted)} />
            <Line label="LGD Issuer · Average LGD" value={pct2(results.lgd_issuer_avg)} />
            <Line label="LGD Issuer · Weighted LGD" value={pct2(results.lgd_issuer_weighted)} />
            <Line label="Total Transaction LGD" value={<b className="text-cyte-navy">{pct2(results.lgd_total)}</b>} />
            <Line label="EL" value={pct4(results.el)} />
            <Line label="RG" value={<GradeChip grade={results.risk_grade} />} />
            <Line label="RWA%" value={<b className="text-cyte-navy">{pct2(results.rwa_pct)}</b>} />
          </div>
        </div>
        <div className="card">
          <div className="section-header">Calculation Factors</div>
          <div className="p-4">
            <Line label="Years" value={num(derived.years_total, 2)} />
            <Line label="Initial Share Value" value={money(derived.share_value)} />
            <Line label="Initial Cover Ratio" value={ratio(derived.initial_cover_ratio)} />
            <Line label="Initial Default Cover Ratio" value={ratio(derived.initial_dcr)} />
            <Line label="PD of Reference Entity" value={pct4(derived.reference_pd)} />
            <Line label="Share Price Volatility" value={pct2(derived.volatility)} />
            <Line label="Time to unwind" value={`${num(derived.unwind_years, 4)} y · ${num(derived.unwind_days, 1)} d`} />
            <Line label="Discount Factor" value={num(derived.discount_factor, 6)} />
            <Line label="Liquidity" value={derived.liquidity || "—"} />
            <Line label="Fire-sale haircut (FSH)" value={pct(derived.fsh, 0)} />
            <Line label="Recovery Policy" value={derived.recovery_policy} />
            <Line label="Random draws" value={derived.workbook_draws ? "Workbook draw set" : `Seed ${run.inputs.random_seed}`} />
            <Line label="Simulation paths" value={num(derived.n_paths)} />
          </div>
        </div>
      </div>

      <div className="card overflow-hidden">
        <div className="section-header">Year-by-year — {run.inputs.client_name}</div>
        <div className="overflow-x-auto">
          <table className="min-w-full">
            <thead>
              <tr>
                <th className="table-head">Year</th>
                {active.map((y) => (
                  <th key={y.year} className="table-head text-right">{num(y.year, y.year % 1 ? 2 : 0)}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {YEAR_ROWS.map((r) => (
                <tr key={r.key} className="odd:bg-slate-50">
                  <td className="table-cell font-medium">{r.label}</td>
                  {active.map((y) => (
                    <td key={y.year} className="table-cell text-right tabular-nums">{r.fmt(y[r.key] as number)}</td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {portfolio && (
        <div className="card">
          <div className="section-header">Portfolio — Outputs (Combined) used in this run</div>
          <div className="grid grid-cols-2 gap-x-8 p-4 md:grid-cols-3">
            <Line label="Number of Shares" value={num(portfolio.number_of_shares)} />
            <Line label="Share Price" value={num(portfolio.share_price, 4)} />
            <Line label="Stock Volatility" value={pct2(portfolio.stock_volatility)} />
            <Line label="Dividend Yield" value={pct2(portfolio.dividend_yield)} />
            <Line label="Time to unwind (years)" value={num(portfolio.time_to_unwind, 4)} />
            <Line label="Risk Free Rate" value={pct2(portfolio.risk_free_rate)} />
            <Line label="Equity LGD" value={portfolio.equity_lgd == null ? "n/a" : pct2(portfolio.equity_lgd)} />
          </div>
        </div>
      )}

      <div className="flex justify-between">
        <button className="btn-secondary" onClick={onRecalculate} disabled={busy}>
          {busy ? "Calculating…" : "Recalculate"}
        </button>
        <button className="btn-primary" onClick={onNext}>Next: Print Report &amp; Results →</button>
      </div>
    </div>
  );
}

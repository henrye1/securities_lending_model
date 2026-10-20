import type { ReportColumn, Run, Transaction } from "../../lib/api";
import { api } from "../../lib/api";
import { money, num, pct, ratio } from "../../lib/format";
import { GradeChip } from "../../components/GradeChip";

interface Props {
  tx: Transaction;
  run: Run;
}

const REPORT_ROWS: { key: keyof ReportColumn; label: string; render: (v: number | string) => React.ReactNode }[] = [
  { key: "pd", label: "PD", render: (v) => pct(v as number, 4) },
  { key: "grade", label: "Risk Grade", render: (v) => <GradeChip grade={v as string} /> },
  { key: "lgd", label: "Downturn LGD", render: (v) => pct(v as number) },
  { key: "el", label: "EL", render: (v) => pct(v as number, 4) },
  { key: "el_grade", label: "EL Grade", render: (v) => <GradeChip grade={v as string} /> },
  { key: "rwa_pct", label: "RWA%", render: (v) => pct(v as number) },
];

export function ReportStep({ tx, run }: Props) {
  const { report, derived, report_date } = run.result;
  const amortLabel =
    tx.structure === "Interest Only Repayments" ? "Interest Only Loan Amount" : "Amortised Loan Amount";

  const details: [string, string][] = [
    ["Start Date", tx.start_date],
    ["Maturity Date", tx.maturity_date],
    ["Years", num(derived.years_total, 2)],
    [amortLabel, money(derived.amortised_amount)],
    ["Bullet Loan Amount", money(derived.bullet_amount)],
    ["Interest Rate on Bullet Loan", pct(derived.bullet_rate)],
    ["Number of Shares", num(derived.number_of_shares)],
    ["Share Price", num(derived.share_price, 4)],
    ["Initial Share Value", money(derived.share_value)],
    ["Initial Cover Ratio", ratio(derived.initial_cover_ratio)],
    ["Initial Default Cover Ratio", ratio(derived.initial_dcr)],
    ["PD of Reference Entity", pct(derived.reference_pd, 2)],
    ["Dividend Yield", pct(derived.dividend_yield)],
    ["Percentage of Dividends Repayed", pct(tx.dividends_repaid, 0)],
    ["Share Price Volatility", pct(derived.volatility)],
    ["Liabilities Ranking Ahead", money(tx.liabilities_ahead ?? 0)],
    ["Liabilities Ranking Parri-Passu", money(tx.liabilities_pari_passu ?? 0)],
    ["Liabilities Ranking Subordinate", money(tx.liabilities_subordinate ?? 0)],
    ["Transaction Structure", tx.structure],
  ];

  return (
    <div className="space-y-4">
      <div className="flex justify-end gap-2 print:hidden">
        <button className="btn-secondary" onClick={() => window.print()}>Print</button>
        <a className="btn-primary" href={api.exportUrl(run.id)}>Download Excel</a>
      </div>

      <div className="card print-report p-6">
        <div className="mb-4 flex items-start justify-between border-b-4 border-cyte-navy pb-3">
          <div>
            <div className="text-xs font-semibold uppercase tracking-[0.3em] text-cyte-navy">Stock Lending Model</div>
            <h2 className="text-xl font-bold text-cyte-navyDark">Share Cover Risk Report for: {tx.client_name}</h2>
          </div>
          <div className="text-right">
            <span className="text-lg font-bold tracking-widest text-cyte-navy">CYTE</span>
            <span className="ml-2 text-xs uppercase tracking-[0.3em] text-slate-500">Risk Suite</span>
          </div>
        </div>

        <dl className="mb-6 grid grid-cols-2 gap-x-8 gap-y-1 text-sm md:grid-cols-4">
          <dt className="text-slate-600">CIF Code of Client / Borrower</dt>
          <dd className="font-semibold">{tx.client_cif || "—"}</dd>
          <dt className="text-slate-600">Date</dt>
          <dd className="font-semibold">{report_date}</dd>
          <dt className="text-slate-600">Reference Share</dt>
          <dd className="font-semibold">{tx.portfolio_of_shares ? `Portfolio (${tx.portfolio?.stocks.length ?? 0} stocks) · ${tx.reference_name || "—"}` : tx.reference_name || "—"}</dd>
          <dt className="text-slate-600">CIF Code of Reference Entity</dt>
          <dd className="font-semibold">{tx.reference_cif || "—"}</dd>
        </dl>

        <h3 className="mb-2 text-sm font-bold uppercase tracking-wide text-cyte-navyDark">Transaction Details</h3>
        <div className="mb-6 grid grid-cols-1 gap-x-12 md:grid-cols-2">
          {details.map(([k, v]) => (
            <div key={k} className="flex justify-between border-b border-slate-100 py-1 text-sm">
              <span className="text-slate-600">{k}</span>
              <span className="font-semibold tabular-nums">{v}</span>
            </div>
          ))}
        </div>

        <h3 className="mb-2 text-sm font-bold uppercase tracking-wide text-cyte-navyDark">Results</h3>
        <table className="w-full">
          <thead>
            <tr>
              <th className="table-head" />
              <th className="table-head text-center">Reference Entity</th>
              <th className="table-head text-center">Client/Borrower</th>
              <th className="table-head text-center">Combined</th>
            </tr>
          </thead>
          <tbody>
            {REPORT_ROWS.map((r) => (
              <tr key={r.key} className="odd:bg-slate-50">
                <td className="table-cell font-medium">{r.label}</td>
                {(["reference", "client", "combined"] as const).map((col) => (
                  <td key={col} className="table-cell text-center tabular-nums">
                    {r.render(report[col][r.key])}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>

        {run.result.warnings.length > 0 && (
          <div className="mt-4 text-xs text-cyte-ragAmber">
            {run.result.warnings.map((w) => (
              <div key={w}>{w}</div>
            ))}
          </div>
        )}
        <p className="mt-6 text-xs text-slate-500">
          CYTE Risk Suite — Securities Lending (Share Cover) Model · {derived.n_paths.toLocaleString()} simulation paths ·
          {derived.workbook_draws ? " workbook draw set" : ` seed ${tx.random_seed}`} · run {run.id} · {new Date(run.created_at).toLocaleString()}
        </p>
      </div>
    </div>
  );
}

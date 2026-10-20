import { useEffect, useMemo, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import clsx from "clsx";
import { api, type CaptureConfig, type Run, type Transaction, type TransactionPayload } from "../lib/api";
import { combinePortfolio, emptyPortfolio } from "../lib/model";
import { pct } from "../lib/format";
import { GradeChip } from "../components/GradeChip";
import { InputStep } from "./wizard/InputStep";
import { PortfolioStep } from "./wizard/PortfolioStep";
import { CalculateStep } from "./wizard/CalculateStep";
import { ReportStep } from "./wizard/ReportStep";

export type StepId = "input" | "portfolio" | "calculate" | "report";

const today = new Date();
const inTenYears = new Date(today.getFullYear() + 5, today.getMonth(), today.getDate());

export const EMPTY: TransactionPayload = {
  client_cif: "",
  client_name: "",
  client_country: "South Africa",
  portfolio_of_shares: false,
  start_date: today.toISOString().slice(0, 10),
  maturity_date: inTenYears.toISOString().slice(0, 10),
  structure: "Bullet Payment",
  amortised_loan_amount: null,
  bullet_loan_amount: null,
  number_of_shares: 0,
  share_price: 0,
  average_daily_volume: 0,
  dcr_changes: false,
  default_cover_ratio: 1.75,
  dcr_schedule: [],
  bullet_interest_rate: null,
  rate_linked_to_cover: false,
  amortised_interest_rate: null,
  rate_schedule: [],
  dividend_yield: 0,
  dividends_repaid: 1,
  stock_volatility: 0,
  liabilities_ahead: null,
  liabilities_pari_passu: null,
  liabilities_subordinate: null,
  other_collateral: null,
  collateral_pari_passu: null,
  other_pari_passu_liabilities: null,
  reference_cif: "",
  reference_name: "",
  reference_country: "South Africa",
  listing: "Listed",
  risk_grade: "SB11",
  revenue_size: "Revenue > R500m",
  sectors: [],
  unlisted_haircut: 0.5,
  illiquid_haircut: 0.3,
  risk_free_rate: null,
  currency_mismatch: false,
  currency_volatility: 0,
  currency_correlation: 0,
  recovery_approach: 1,
  random_seed: null,
  portfolio: null,
};

export function TransactionWizard() {
  const { batchId, txId } = useParams();
  const navigate = useNavigate();
  const [config, setConfig] = useState<CaptureConfig | null>(null);
  const [payload, setPayload] = useState<TransactionPayload>(EMPTY);
  const [tx, setTx] = useState<Transaction | null>(null);
  const [run, setRun] = useState<Run | null>(null);
  const [step, setStep] = useState<StepId>("input");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    api
      .captureConfig()
      .then((cfg) => {
        setConfig(cfg);
        setPayload((p) =>
          p.risk_free_rate === null
            ? { ...p, risk_free_rate: cfg.countries.find((c) => c.name === p.reference_country)?.risk_free_rate ?? null }
            : p,
        );
      })
      .catch((e) => setError(String(e.message ?? e)));
  }, []);

  useEffect(() => {
    if (!txId) return;
    api
      .getTransaction(txId)
      .then((loaded) => {
        setTx(loaded);
        setPayload(loaded);
        if (loaded.latest_run_id) {
          api.getRun(loaded.latest_run_id).then(setRun).catch(() => undefined);
        }
      })
      .catch((e) => setError(String(e.message ?? e)));
  }, [txId]);

  // Keep a portfolio object around as soon as "Portfolio of Shares?" is Yes.
  useEffect(() => {
    if (payload.portfolio_of_shares && !payload.portfolio) {
      setPayload((p) => ({ ...p, portfolio: emptyPortfolio() }));
    }
  }, [payload.portfolio_of_shares, payload.portfolio]);

  const combined = useMemo(() => {
    if (!config || !payload.portfolio_of_shares || !payload.portfolio) return null;
    const rf = Object.fromEntries(config.countries.map((c) => [c.name, c.risk_free_rate ?? 0]));
    return combinePortfolio(payload.portfolio, rf);
  }, [config, payload.portfolio_of_shares, payload.portfolio]);

  const steps: { id: StepId; label: string; enabled: boolean }[] = useMemo(
    () => [
      { id: "input", label: "1 · Input", enabled: true },
      { id: "portfolio", label: "2 · Portfolio Transactions", enabled: payload.portfolio_of_shares },
      { id: "calculate", label: "3 · Calculations", enabled: !!run },
      { id: "report", label: "4 · Print Report & Results", enabled: !!run },
    ],
    [run, payload.portfolio_of_shares],
  );

  const save = async (): Promise<Transaction> => {
    setBusy(true);
    setError("");
    try {
      const saved = tx
        ? await api.updateTransaction(tx.id, payload)
        : await api.createTransaction(batchId!, payload);
      setTx(saved);
      if (!tx) navigate(`/transactions/${saved.id}`, { replace: true });
      return saved;
    } catch (e) {
      setError(String((e as Error).message));
      throw e;
    } finally {
      setBusy(false);
    }
  };

  const calculate = async () => {
    setBusy(true);
    setError("");
    try {
      const saved = tx ? await api.updateTransaction(tx.id, payload) : await save();
      setTx(saved);
      const newRun = await api.calculate(saved.id);
      setRun(newRun);
      setTx({ ...saved, latest_run_id: newRun.id, status: "calculated", latest_pd: newRun.pd_total,
        latest_risk_grade: newRun.risk_grade, latest_lgd: newRun.lgd_total, latest_el: newRun.el });
      setStep("calculate");
    } catch (e) {
      setError(String((e as Error).message));
    } finally {
      setBusy(false);
    }
  };

  if (!config) {
    return <div className="p-8 text-sm text-slate-500">{error || "Loading configuration…"}</div>;
  }

  const backLink = tx ? `/batches/${tx.batch_id}` : batchId ? `/batches/${batchId}` : "/batches";

  return (
    <div>
      <div className="mb-1 text-xs text-slate-500 print:hidden">
        <Link to="/batches" className="hover:underline">Batches</Link> /{" "}
        <Link to={backLink} className="hover:underline">Batch</Link> / {payload.client_name || "New transaction"}
      </div>
      <h1 className="mb-4 text-2xl font-bold text-cyte-navyDark print:hidden">
        {payload.client_name || "New Transaction"}
        <span className="ml-3 align-middle text-sm font-normal text-slate-500">Stock Lending Model</span>
        {run && (
          <span className="ml-3 align-middle text-sm font-normal text-slate-500">
            Combined PD <b className="text-cyte-navy">{pct(run.pd_total, 3)}</b> · <GradeChip grade={run.risk_grade} /> ·
            LGD <b className="text-cyte-navy">{pct(run.lgd_total)}</b> · RWA <b className="text-cyte-navy">{pct(run.rwa_pct)}</b>
          </span>
        )}
      </h1>

      <div className="mb-5 flex flex-wrap gap-1 print:hidden">
        {steps.map((s) => (
          <button
            key={s.id}
            disabled={!s.enabled}
            onClick={() => setStep(s.id)}
            className={clsx(
              "rounded-t border-b-2 px-4 py-2 text-sm font-semibold transition",
              step === s.id
                ? "border-cyte-navy bg-white text-cyte-navy shadow-sm"
                : s.enabled
                  ? "border-transparent text-slate-600 hover:bg-cyte-panel"
                  : "border-transparent text-slate-300",
            )}
          >
            {s.label}
          </button>
        ))}
      </div>

      {error && <div className="error-banner mb-4 print:hidden">{error}</div>}

      {step === "input" && (
        <InputStep
          config={config}
          payload={payload}
          onChange={setPayload}
          combined={combined}
          busy={busy}
          onNext={async () => {
            await save();
            setStep("portfolio");
          }}
          onCalculate={calculate}
        />
      )}
      {step === "portfolio" && (
        <PortfolioStep
          config={config}
          payload={payload}
          onChange={setPayload}
          combined={combined}
          busy={busy}
          onBack={() => setStep("input")}
          onCalculate={calculate}
        />
      )}
      {step === "calculate" && run && (
        <CalculateStep run={run} busy={busy} onRecalculate={calculate} onNext={() => setStep("report")} />
      )}
      {step === "report" && run && tx && <ReportStep tx={tx} run={run} />}
    </div>
  );
}

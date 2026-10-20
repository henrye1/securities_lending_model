import { useMemo } from "react";
import type { CaptureConfig, Listing, Structure, TransactionPayload } from "../../lib/api";
import { money, num, pct, ratio } from "../../lib/format";
import { equityDuration, liquidityFlag, type PortfolioCombinedLite } from "../../lib/model";
import { Field, NumberField, ReadOnly, Select, YesNo } from "../../components/fields";

interface Props {
  config: CaptureConfig;
  payload: TransactionPayload;
  onChange: (p: TransactionPayload) => void;
  combined: PortfolioCombinedLite | null;
  busy: boolean;
  onNext: () => void;
  onCalculate: () => void;
}

const BULLET_TYPES: Structure[] = ["Bullet Payment", "Straight Amortisation & Bullet"];
const AMORT_TYPES: Structure[] = [
  "Straight Amortisation",
  "Interest Only Repayments",
  "Straight Amortisation & Bullet",
];

export function InputStep({ config, payload, onChange, combined, busy, onNext, onCalculate }: Props) {
  const set = (patch: Partial<TransactionPayload>) => onChange({ ...payload, ...patch });

  const hasBullet = BULLET_TYPES.includes(payload.structure);
  const hasAmort = AMORT_TYPES.includes(payload.structure);
  const amortLabel =
    payload.structure === "Interest Only Repayments"
      ? "Interest Only Loan Amount"
      : "Amortised Loan Amount";
  const portfolio = payload.portfolio_of_shares;

  // Mirrors of the sheet's computed cells (H33, H35, H84, H87, E44)
  const shares = portfolio && combined ? combined.number_of_shares : payload.number_of_shares;
  const price = portfolio && combined ? combined.share_price : payload.share_price;
  const stockValue = shares * price;
  const loanTotal =
    (hasAmort ? payload.amortised_loan_amount ?? 0 : 0) +
    (hasBullet ? payload.bullet_loan_amount ?? 0 : 0);
  const initialCover = loanTotal ? stockValue / loanTotal : 0;
  const unwindYears =
    portfolio && combined
      ? combined.time_to_unwind
      : equityDuration(shares, payload.average_daily_volume, config.defaults.unwind_pct, config.defaults.trading_days);
  const liquidity = liquidityFlag(payload.listing, shares, portfolio && combined ? combined.average_daily_volume : payload.average_daily_volume);

  const rfByCountry = useMemo(
    () => Object.fromEntries(config.countries.map((c) => [c.name, c.risk_free_rate ?? 0])),
    [config.countries],
  );
  const countryNames = useMemo(() => config.countries.map((c) => c.name), [config.countries]);

  const setStructure = (structure: Structure) => {
    // The sheet's ComboBox16 macro: blank / "Not Applicable" the cells that do not apply.
    const bullet = BULLET_TYPES.includes(structure);
    const amort = AMORT_TYPES.includes(structure);
    set({
      structure,
      amortised_loan_amount: amort ? payload.amortised_loan_amount : null,
      bullet_loan_amount: bullet ? payload.bullet_loan_amount : null,
      bullet_interest_rate: bullet ? payload.bullet_interest_rate : null,
      amortised_interest_rate: amort ? payload.amortised_interest_rate : null,
      rate_linked_to_cover: amort ? payload.rate_linked_to_cover : false,
      rate_schedule: amort ? payload.rate_schedule : [],
    });
  };

  const setReferenceCountry = (reference_country: string) =>
    set({ reference_country, risk_free_rate: rfByCountry[reference_country] ?? payload.risk_free_rate });

  const dcrRows = payload.dcr_schedule;
  const rateRows = payload.rate_schedule;
  const sectors = payload.sectors;
  const sectorAt = (i: number) => sectors[i] ?? { sector: "", weight: 0 };
  const setSector = (i: number, patch: { sector?: string; weight?: number }) => {
    const next = [0, 1, 2].map((k) => ({ ...sectorAt(k), ...(k === i ? patch : {}) }));
    set({ sectors: next.filter((s) => s.sector) });
  };

  // Mirrors the backend's validation_errors so the button is only live when a run can succeed.
  const missing: string[] = [];
  if (payload.client_name.trim() === "") missing.push("client name");
  if (loanTotal <= 0) missing.push("loan amount");
  if (!portfolio && stockValue <= 0) missing.push("shares and price");
  if (!portfolio && payload.average_daily_volume <= 0) missing.push("average daily trading volume");
  if (!portfolio && payload.stock_volatility <= 0) missing.push("stock volatility");
  if (hasBullet && payload.bullet_interest_rate === null) missing.push("bullet interest rate");
  if (hasAmort && payload.amortised_interest_rate === null) missing.push("interest rate charged");
  const canCalculate = missing.length === 0;

  return (
    <div className="space-y-4">
      {/* ---- Client / Borrower Details ---- */}
      <div className="card">
        <div className="section-header">Client / Borrower Details</div>
        <div className="grid grid-cols-1 gap-4 p-4 md:grid-cols-4">
          <Field label="CIF Code of Client / Borrower" hint="CIF Code of the Borrowing Entity">
            <input className="field-input" value={payload.client_cif} onChange={(e) => set({ client_cif: e.target.value })} />
          </Field>
          <Field label="Client / Borrowing Entity Name *" hint="Name or Exchange Code of the Borrowing Entity">
            <input className="field-input" value={payload.client_name} onChange={(e) => set({ client_name: e.target.value })} />
          </Field>
          <Field label="Country of Risk" hint="Country Where the Borrower Operates">
            <Select value={payload.client_country} onChange={(v) => set({ client_country: v })} options={countryNames} />
          </Field>
          <Field label="Portfolio of Shares?" hint='If "Yes", complete the Portfolio Transactions tab'>
            <YesNo value={portfolio} onChange={(v) => set({ portfolio_of_shares: v })} />
          </Field>
        </div>
      </div>

      {/* ---- Transaction Details ---- */}
      <div className="card">
        <div className="section-header">Transaction Details</div>
        <div className="grid grid-cols-1 gap-4 p-4 md:grid-cols-4">
          <Field label="Start Date" hint="Transaction Start Date">
            <input type="date" className="field-input" value={payload.start_date} onChange={(e) => set({ start_date: e.target.value })} />
          </Field>
          <Field label="Maturity Date" hint="Transaction Maturity Date (within 10 years)">
            <input type="date" className="field-input" value={payload.maturity_date} onChange={(e) => set({ maturity_date: e.target.value })} />
          </Field>
          <Field label="Transaction Structure" hint="The Structure of the Loan Repayments">
            <Select value={payload.structure} onChange={setStructure} options={config.structures} />
          </Field>
          <div />
          <Field label={amortLabel} hint="Amount of the Loan that is Amortised (Without Rolled-Up Interest)">
            <NumberField value={payload.amortised_loan_amount} onChange={(v) => set({ amortised_loan_amount: v })} disabled={!hasAmort} nullable />
          </Field>
          <Field label="Bullet Loan Amount" hint="Amount of the Bullet Loan (Without Rolled-Up Interest)">
            <NumberField value={payload.bullet_loan_amount} onChange={(v) => set({ bullet_loan_amount: v })} disabled={!hasBullet} nullable />
          </Field>
          <Field label="Number of Shares" hint={portfolio ? "From the Portfolio Transactions tab" : "Number of Shares Pledged"}>
            {portfolio ? <ReadOnly value={num(shares)} /> : (
              <NumberField value={payload.number_of_shares} onChange={(v) => set({ number_of_shares: v ?? 0 })} />
            )}
          </Field>
          <Field label="Share Price" hint={portfolio ? "Value-weighted, from the Portfolio Transactions tab" : "Current Spot Price of Share"}>
            {portfolio ? <ReadOnly value={num(price, 4)} /> : (
              <NumberField value={payload.share_price} onChange={(v) => set({ share_price: v ?? 0 })} />
            )}
          </Field>
          <Field label="Total Stock Value" hint="Total Value of Stock Pledged">
            <ReadOnly value={money(stockValue)} />
          </Field>
          <Field label="Initial Cover Ratio" hint="Initial Cover Ratio on the Loan">
            <ReadOnly value={ratio(initialCover)} />
          </Field>
          <Field label="Average Daily Trading Volumes" hint="Number of Shares Traded Daily on Average">
            <NumberField value={payload.average_daily_volume} onChange={(v) => set({ average_daily_volume: v ?? 0 })} />
          </Field>
          <Field label="Time to unwind share in market" hint={`${num(unwindYears * config.defaults.trading_days, 1)} days at ${pct(config.defaults.unwind_pct, 0)} of daily volume · ${liquidity || "n/a"}`}>
            <ReadOnly value={`${unwindYears.toFixed(4)} years`} />
          </Field>
          <Field label="Does Default Cover Ratio Change?" hint="Does the Default Cover Ratio Change in Future Years?">
            <YesNo value={payload.dcr_changes} onChange={(v) => set({ dcr_changes: v, dcr_schedule: v ? payload.dcr_schedule : [] })} />
          </Field>
          <Field label="Default Cover Ratio" hint="The Default Cover Ratio">
            <NumberField value={payload.default_cover_ratio} onChange={(v) => set({ default_cover_ratio: v ?? 0 })} step={0.01} />
          </Field>
          {payload.dcr_changes && (
            <div className="md:col-span-4">
              <label className="field-label">Time of Change (years) → Default Cover Ratio</label>
              <div className="flex flex-wrap gap-3">
                {Array.from({ length: 6 }, (_, i) => dcrRows[i] ?? null).map((row, i) => (
                  <div key={i} className="flex items-center gap-1">
                    <NumberField value={row?.time ?? null} nullable step={0.5} placeholder="t" onChange={(t) => {
                      const next = [...dcrRows];
                      next[i] = { time: t ?? 0, dcr: row?.dcr ?? payload.default_cover_ratio };
                      set({ dcr_schedule: next.filter((r) => r && r.time > 0) });
                    }} />
                    <span className="text-slate-400">→</span>
                    <NumberField value={row?.dcr ?? null} nullable step={0.01} placeholder="DCR" onChange={(d) => {
                      const next = [...dcrRows];
                      next[i] = { time: row?.time ?? 0, dcr: d ?? 0 };
                      set({ dcr_schedule: next.filter((r) => r && r.time > 0) });
                    }} />
                  </div>
                ))}
              </div>
              <p className="mt-1 text-xs text-slate-500">The Time (in Years) at Which the Default Cover Ratio Changes. A change at year t applies from year t+1.</p>
            </div>
          )}
        </div>
      </div>

      {/* ---- Interest ---- */}
      <div className="card">
        <div className="section-header">
          {hasAmort ? `Interest Charged on ${payload.structure === "Interest Only Repayments" ? "Interest Only" : "Amortised"} Loan` : "Interest Charged on Bullet Loan"}
          {hasAmort && hasBullet && " & Bullet Loan"}
        </div>
        <div className="grid grid-cols-1 gap-4 p-4 md:grid-cols-4">
          <Field label="Current Interest Rate on Bullet Loan" hint="Current Interest Rate Charged on the Bullet Loan">
            <NumberField value={payload.bullet_interest_rate} onChange={(v) => set({ bullet_interest_rate: v })} disabled={!hasBullet} nullable scale={100} suffix="%" />
          </Field>
          <Field label="Is Interest Rate Linked to Cover Ratio?" hint="Is There Different Interest Rates for Different Cover Ratios?">
            <YesNo value={payload.rate_linked_to_cover} disabled={!hasAmort} onChange={(v) => set({ rate_linked_to_cover: v, rate_schedule: v ? payload.rate_schedule : [] })} />
          </Field>
          <Field label="Current Interest Rate Charged" hint={hasAmort ? "Rate on the amortised / interest-only loan (cover ratio from 0)" : "Not applicable to a Bullet Payment"}>
            <NumberField value={payload.amortised_interest_rate} onChange={(v) => set({ amortised_interest_rate: v })} disabled={!hasAmort} nullable scale={100} suffix="%" />
          </Field>
          {payload.rate_linked_to_cover && hasAmort && (
            <div className="md:col-span-4">
              <label className="field-label">Cover Ratio Lower Boundary → Current Interest Rate Charged</label>
              <div className="flex flex-wrap gap-3">
                {Array.from({ length: 5 }, (_, i) => rateRows[i] ?? null).map((row, i) => (
                  <div key={i} className="flex items-center gap-1">
                    <NumberField value={row?.lower_bound ?? null} nullable step={0.1} placeholder="e.g. 1.5" onChange={(b) => {
                      const next = [...rateRows];
                      next[i] = { lower_bound: b ?? 0, rate: row?.rate ?? 0 };
                      set({ rate_schedule: next.filter((r) => r && r.lower_bound > 0) });
                    }} />
                    <span className="text-slate-400">→</span>
                    <NumberField value={row?.rate ?? null} nullable scale={100} suffix="%" placeholder="e.g. 12" onChange={(r) => {
                      const next = [...rateRows];
                      next[i] = { lower_bound: row?.lower_bound ?? 0, rate: r ?? 0 };
                      set({ rate_schedule: next.filter((x) => x && x.lower_bound > 0) });
                    }} />
                  </div>
                ))}
              </div>
              <p className="mt-1 text-xs text-slate-500">The Different Cover Ratio Lower Boundaries and the rate charged for each cover interval.</p>
            </div>
          )}
        </div>
      </div>

      {/* ---- Stock Details ---- */}
      <div className="card">
        <div className="section-header">Stock Details</div>
        <div className="grid grid-cols-1 gap-4 p-4 md:grid-cols-4">
          <Field label="Dividend Yield" hint={portfolio ? "Value-weighted, from the Portfolio Transactions tab" : "Average Dividend Yield Over the Preceding 3 Years"}>
            {portfolio && combined ? <ReadOnly value={pct(combined.dividend_yield)} /> : (
              <NumberField value={payload.dividend_yield} onChange={(v) => set({ dividend_yield: v ?? 0 })} scale={100} suffix="%" />
            )}
          </Field>
          <Field label="Percentage of Dividends Paid Back" hint="What Proportion of SPV Total Dividend-Income is Repaid on the Loan?">
            <div className="flex gap-2">
              <Select value={payload.dividends_repaid === 1 ? "100%" : "Custom"} options={config.dividend_options} onChange={(v) => set({ dividends_repaid: v === "100%" ? 1 : 0 })} />
              {payload.dividends_repaid !== 1 && (
                <NumberField value={payload.dividends_repaid} onChange={(v) => set({ dividends_repaid: v ?? 0 })} scale={100} suffix="%" />
              )}
            </div>
          </Field>
          <Field label="Stock Volatility" hint={portfolio ? "Correlation-matrix volatility from the Portfolio Transactions tab" : "Average Stock Price Volatility on the Preceding 3 Years"}>
            {portfolio && combined ? <ReadOnly value={pct(combined.stock_volatility)} /> : (
              <NumberField value={payload.stock_volatility} onChange={(v) => set({ stock_volatility: v ?? 0 })} scale={100} suffix="%" />
            )}
          </Field>
        </div>
      </div>

      {/* ---- Other Liabilities and Collateral ---- */}
      <div className="card">
        <div className="section-header">Other Liabilities and Collateral</div>
        <div className="grid grid-cols-1 gap-4 p-4 md:grid-cols-3">
          <Field label="Liabilities Ranking Ahead of Facility" hint="Within Borrowing Entity · reported">
            <NumberField value={payload.liabilities_ahead} onChange={(v) => set({ liabilities_ahead: v })} nullable />
          </Field>
          <Field label="Liabilities Ranking Parri-Passu with Facility" hint="Within Borrowing Entity · reported">
            <NumberField value={payload.liabilities_pari_passu} onChange={(v) => set({ liabilities_pari_passu: v })} nullable />
          </Field>
          <Field label="Liabilities Subordinate to Facility" hint="Within Borrowing Entity · reported">
            <NumberField value={payload.liabilities_subordinate} onChange={(v) => set({ liabilities_subordinate: v })} nullable />
          </Field>
          <Field label="Other Collateral Pledged to Facility" hint="Value of Collateral Pledged Besides Shares · report only, not used by the engine">
            <NumberField value={payload.other_collateral} onChange={(v) => set({ other_collateral: v })} nullable />
          </Field>
          <Field label="Collateral Pledged to Parri-Passu Liabilities" hint="Report only, not used by the engine">
            <NumberField value={payload.collateral_pari_passu} onChange={(v) => set({ collateral_pari_passu: v })} nullable />
          </Field>
          <Field label="Other Parri-Passu Liabilities to Which Collateral is Pledged" hint="Report only, not used by the engine">
            <NumberField value={payload.other_pari_passu_liabilities} onChange={(v) => set({ other_pari_passu_liabilities: v })} nullable />
          </Field>
        </div>
      </div>

      {/* ---- Reference Share Details ---- */}
      <div className="card">
        <div className="section-header">Reference Share Details</div>
        <div className="grid grid-cols-1 gap-4 p-4 md:grid-cols-4">
          <Field label="CIF Code of Reference Entity" hint="CIF Code of the Reference Entity">
            <input className="field-input" value={payload.reference_cif} onChange={(e) => set({ reference_cif: e.target.value })} />
          </Field>
          <Field label="Reference Entity / Share Name" hint="Name or Exchange Code of Reference Entity / Share">
            <input className="field-input" value={payload.reference_name} onChange={(e) => set({ reference_name: e.target.value })} />
          </Field>
          <Field label="Country of Risk" hint="Country Where the Reference Entity Operates (sets the risk free rate)">
            <Select value={payload.reference_country} onChange={setReferenceCountry} options={countryNames} />
          </Field>
          <Field label="Reference Entity Share Listing" hint="Is the Reference Share Listed or Unlisted">
            <Select value={payload.listing} onChange={(v) => set({ listing: v as Listing })} options={config.listings} />
          </Field>
          <Field label="Risk Grade of Reference Entity" hint="Probability of Default of the Reference Entity">
            <Select value={payload.risk_grade} onChange={(v) => set({ risk_grade: v })} options={config.grades} />
          </Field>
          <Field label="Revenue Size" hint="Revenue Size of the Reference Entity">
            <Select value={payload.revenue_size} onChange={(v) => set({ revenue_size: v })} options={config.revenue_sizes} />
          </Field>
          <Field label="Risk Free Rate" hint="The applicable risk free rate (bond rate) for the country of risk">
            <NumberField value={payload.risk_free_rate} onChange={(v) => set({ risk_free_rate: v })} nullable scale={100} suffix="%" />
          </Field>
          <div />
          {[0, 1, 2].map((i) => (
            <Field key={i} label="Corporate Sector" hint={i === 0 ? "Business Sector of the Reference Entity and its weight" : undefined}>
              <div className="flex gap-2">
                <Select value={sectorAt(i).sector} options={config.sectors} allowEmpty onChange={(v) => setSector(i, { sector: v, weight: sectorAt(i).weight || (i === 0 ? 1 : 0) })} />
                <div className="w-24">
                  <NumberField value={sectorAt(i).weight} onChange={(v) => setSector(i, { weight: v ?? 0 })} scale={100} suffix="%" disabled={!sectorAt(i).sector} />
                </div>
              </div>
            </Field>
          ))}
          <div />
          <Field label="Unlisted Share Haircut" hint="Suggested 30% · report only, not used by the engine">
            <NumberField value={payload.unlisted_haircut} onChange={(v) => set({ unlisted_haircut: v ?? 0 })} scale={100} suffix="%" />
          </Field>
          <Field label="Illiquid Share Haircut" hint="Suggested 50% · report only, not used by the engine">
            <NumberField value={payload.illiquid_haircut} onChange={(v) => set({ illiquid_haircut: v ?? 0 })} scale={100} suffix="%" />
          </Field>
        </div>
      </div>

      {/* ---- Currency Risk ---- */}
      <div className="card">
        <div className="section-header">Currency Risk</div>
        <div className="grid grid-cols-1 gap-4 p-4 md:grid-cols-4">
          <Field label="Is the equity and loan in different currencies?" hint="Adjusts for the currency mismatch between the loan and equity currency">
            <YesNo value={payload.currency_mismatch} onChange={(v) => set({ currency_mismatch: v, currency_volatility: v ? payload.currency_volatility : 0, currency_correlation: v ? payload.currency_correlation : 0 })} />
          </Field>
          {payload.currency_mismatch && (
            <>
              <Field label="Currency (loan/equity) volatility" hint="e.g. R/$ volatility">
                <NumberField value={payload.currency_volatility} onChange={(v) => set({ currency_volatility: v ?? 0 })} scale={100} suffix="%" />
              </Field>
              <Field label="Correlation between currency and equity" hint="The correlation between the equity prices and the currency exchange rates">
                <NumberField value={payload.currency_correlation} onChange={(v) => set({ currency_correlation: v ?? 0 })} step={0.01} />
              </Field>
            </>
          )}
        </div>
      </div>

      {/* ---- Calculation Settings ---- */}
      <div className="card">
        <div className="section-header">Calculation Settings</div>
        <div className="grid grid-cols-1 gap-4 p-4 md:grid-cols-4">
          <Field label="Recovery Policy" hint="The LGD approach at default (Calculations sheet)">
            <Select value={config.recovery_policies[payload.recovery_approach - 1] ?? config.recovery_policies[0]} options={config.recovery_policies} onChange={(v) => set({ recovery_approach: config.recovery_policies.indexOf(v) + 1 })} />
          </Field>
          <Field label="Random draws" hint="Workbook draw set reproduces the Excel model exactly; a seed draws fresh paths">
            <div className="flex gap-2">
              <Select value={payload.random_seed === null ? "Workbook draw set" : "Seed"} options={["Workbook draw set", "Seed"]} onChange={(v) => set({ random_seed: v === "Seed" ? 1 : null })} />
              {payload.random_seed !== null && (
                <NumberField value={payload.random_seed} onChange={(v) => set({ random_seed: Math.max(0, Math.floor(v ?? 0)) })} step={1} />
              )}
            </div>
          </Field>
        </div>
      </div>

      <div className="flex justify-end gap-2">
        {portfolio ? (
          <button className="btn-primary" disabled={busy || payload.client_name.trim() === ""} onClick={onNext}>
            Save &amp; Next: Portfolio Transactions →
          </button>
        ) : (
          <div className="flex items-center gap-3">
            {!canCalculate && (
              <span className="text-xs text-slate-500">Required: {missing.join(", ")}</span>
            )}
            <button className="btn-primary" disabled={busy || !canCalculate} onClick={onCalculate}>
              {busy ? "Calculating…" : "Save & Calculate →"}
            </button>
          </div>
        )}
      </div>
    </div>
  );
}

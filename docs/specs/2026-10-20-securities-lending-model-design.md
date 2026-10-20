# Securities Lending (Share Cover) Model — technical design

Date: 2026-10-20 · CYTE Risk Suite sibling of `../global-finance-model`,
`../global-banking-model`, `../global-insurance-model` · Source prototype:
`Equity Finance Model Final V1.5 (Henry Adjusted)v1.2.xlsm` (repo root).

## Purpose

Web application that reproduces the Excel "Stock Lending Model" (share-backed
lending / equity finance) as a CYTE-branded Risk Suite tool. A user captures a
share-cover transaction exactly as on the workbook's **Input** page (plus the
**Portfolio Transactions** page when the pledge is a basket of shares), runs
the Monte-Carlo **Calculations**, and receives the **Print Report & Results**
("Share Cover Risk Report"): PD, risk grade, downturn LGD, EL, EL grade and
RWA% for the Reference Entity (share issuer), the Client/Borrower (SPV) and
the Combined exposure — plus a CYTE-branded Excel export of the report.

The app flow follows the workbook sheet by sheet:

| Workbook sheet | App step | Notes |
|---|---|---|
| Input | 1 · Input | Same sections, same labels, same dropdowns, same show/hide rules as the sheet's ComboBox macros |
| Portfolio Transactions | 2 · Portfolio | Only when "Portfolio of Shares?" = Yes (the sheet's own instruction) |
| Calculations (+ hidden Results) | 3 · Calculate | Runs the 10,000-path simulation; shows the year-by-year table and the Results block |
| Print Report & Results | 4 · Report | The Share Cover Risk Report; print view + `.xlsx` export |

Hidden support sheets (Constants, Random Numbers, LGD Buckets, Simulation,
Volatilities & Multiples, Sheet3, Asset Priority Adjustment) become reference
data / engine internals; they are not pages.

## Goals / non-goals / anti-goals

**Goals**
- Value-for-value parity with the workbook on the single-share path: the
  Excelcior Shipping example in the file is the golden case (every Results
  / Print Report number reproduced to <= 1e-9 relative).
- Faithful capture flow: every editable Input / Portfolio cell exists as a
  field, with the workbook's conditional enabling (transaction structure,
  cover-linked rates, DCR changes, currency mismatch, dividend %).
- CYTE Risk Suite look and feel, identical shell/palette/components to the
  sibling apps (white-labelled under the CYTE brand, not Anchor Point).
- Same repo shape, run commands and persistence pattern as the siblings so
  the suite stays operable as one.

**Non-goals**
- No re-engineering of the methodology. Workbook defects are either
  replicated (where parity requires) or fixed and documented (where the
  defect makes a path unusable) — see "Workbook quirks".
- No user auth / multi-tenant (siblings don't have it either).
- No re-implementation of the hidden "Asset Priority Adjustment" sheet
  (unreferenced by any formula).

**Anti-goals** (would make it a failure even if it "works")
- Silently changing numbers: any deviation from the workbook must be in
  this doc and in the parity notes.
- A different UI vocabulary from the sheet: analysts know the Input page
  labels; keep them.

## Methodology as implemented in the workbook (engine spec)

All symbols reference the workbook's **Calculations** sheet cells.

### Inputs (Calculations column E, from Input)
- `E8/E9` start / maturity -> `E10 = YEARFRAC(start, maturity)` (30/360 US,
  Excel default basis 0).
- `E11` amortised / interest-only loan amount (0 when "Not Applicable");
  `E12` bullet loan amount (0 when N/A); `E13` bullet interest rate (0 when N/A).
- `E14` initial share value = shares x price; `E15` initial cover ratio =
  `E14 / (E11 + E12)` (the Input formula divides by whichever amounts apply).
- `E19` dividend yield; `E20` % of dividends repaid (1.0 or custom).
- `E21` share price volatility = `SQRT(s_eq^2 + s_fx^2 + 2*s_eq*s_fx*MAX(0,rho))`
  (currency mismatch inputs are 0 when "No"); portfolio mode: the portfolio's
  correlation-matrix volatility (see Portfolio).
- `E25` transaction structure in {Bullet Payment, Straight Amortisation,
  Interest Only Repayments, Straight Amortisation & Bullet}.
- `E31` risk-free rate; `E32` minimum PD = 0.0003; `E41` approach
  (1 Economic Value / 2 Orderly Liquidation / 3 Fire Sale — the
  Calculations-sheet ComboBox; default 1); `E42` LGD floor 1e-7 (unused by
  the results chain); `E43` listing; `E48` time to unwind (years, see
  Equity_Duration); `E49` discount factor `1/(1+E31)^E48`.
- Default-cover-ratio schedule (`H47:J53`): bucket lower bounds
  `0, t1+0.1, t2+0.1 ...` with DCR values `H43, I43, J43 ...`; year `y` uses the
  DCR of the last bucket whose lower bound <= `y` (Excel LOOKUP).
- Interest-rate buckets (`H38:J43`): lower bounds of cover ratio from
  Input `I55:N55`, rates from Input `I57:N57` (see deviation D2).
- Issuer default-rate table (Random Numbers `P2:U26`): per risk grade
  SB01...SB25, columns pd1...pd5; year `y` uses column `MIN(y+1, 5)` i.e.
  pd1, pd2, pd3, pd4, pd4, pd4 ... (`I14:R14`).
- PD master scale (Constants `P3:S30`): grade, fitted PD, lower, upper bound.
  Grade lookup = Excel `LOOKUP(value, lower_bounds, grades)` (largest lower
  bound <= value; values >= 0.99999... map to the D rows).

### Simulation grid (10,000 paths x up to 10 years)
Year columns `I6:R6` = `MIN(k, E10)` for k = 1...10; time steps `dt_k = year_k -
year_{k-1}` (0 once maturity is passed). Uniform draws come from the
**Random Numbers** sheet (`A1:J10000`, static values) — path p, year k uses
`RN[p][k]`.

Year 1 (block X...AL), per path:
```
X  = NORMSINV(u) * sqrt(dt) * E21 + (E31 - 0.5*E21^2) * dt
Y  = E14 * exp(X)                               (stock pre-divs)
Z  = rate_lookup(E15)                           (rate for amortised loan)
AA = E11 * (1+Z)^dt                             (amortised loan post interest)
AB = structure rule (below) using divs = E14*E19*E20
AC = E12 * (1+E13)^dt                           (bullet loan post interest)
AD = AC + AB                                    (total loan post divs)
AE = MAX(Y - (AA - AB), 0)                      (stock post divs)   [quirk Q1 on row 7]
AF = AE>0 ? (dt==1 ? AE/AD : Y/(AA+AC)) : 0 ; division error -> 1000
AG = AF > DCR_1 ? 1 : 0                          (survival of covenant)  [quirk Q2 on row 14]
AH = Y > AC ? 1 : 0                              (survival of SPV)
AI = AG==1 ? "" : (AH==0 ? 3 : E41)              (LGD approach)
AJ = exp(-s_eq_input * sqrt(E48)) * AE * E49     (stock value after unwind, discounted; s_eq_input = Input!H66, NOT E21)
AK = MAX((AD - AJ)/AD, 0)
AL = AI=="" ? 0 : MAX(LGD_Estimation(AI, AD, AJ, FSH), 0)
```
Structure rule for `AB` (and `AQ` in later years):
- Straight Amortisation / Straight Amortisation & Bullet:
  `MAX(stock>0 ? loan_post_int - divs : 0, 0)`
- Interest Only Repayments: `MAX(stock>0 ? loan_post_int - divs : 0, E11, 0)`
- Bullet Payment: `0`

`FSH` (fire-sale haircut, `AL4`) = 30% if Listed else 50%.
`LGD_Estimation(approach, EAD, NMC, FSH)`: approach 1 -> `(EAD-NMC)/EAD`;
approach 3 -> `(EAD - NMC*(1-FSH))/EAD`; approach 2 -> 0 (VBA has no branch).

Year k >= 2 (blocks AM...BA etc.), with `prev` = previous year's values:
```
AM = prev.AH==1 ? NORMSINV(u_k)*sqrt(dt)*E21 + (E31-0.5*E21^2)*dt : 0
AN = prev.AH==1 ? prev.AE * exp(AM) : 0
AO = rate_lookup(prev.AF)
AP = prev.AB * (1+AO)^dt
AQ = structure rule with divs = prev.AE*E19*E20, stock = AN, loan_post_int = AP
AR = prev.AC * (1+E13)^dt
AS = AR + AQ
AT = MAX(AN - (AP - AQ), 0)
AU = AT>0 ? (dt==1 ? AT/AS : AN/(AP+AR)) : 0 ; error -> 1000
AV = AU > DCR_k ; AW = AN > AR ; AX = AV ? "" : (AW==0 ? 3 : E41)
AY = exp(-s_eq_input*sqrt(E48)) * AT * E49 ; AZ = MAX((AS-AY)/AS, 0)
BA = (AM==0 || AX=="") ? 0 : MAX(LGD_Estimation(AX, AS, AY, FSH), 0)
```

### Per-year aggregates (Calculations rows 9-17, `I...R`)
- `I9` avg loan = mean of total-loan column over paths where > 0 (0 if dt=0).
- `I10` avg share value = mean of stock-post-divs over paths where > 0.
- Cumulative covenant breach `cov_k = 1 - mean(survival_covenant_k)`;
  `I11` = `cov_1`, `J11` = `cov_2 - cov_1`, ... (annual SPV PD, covenant breach).
- Cumulative SPV default `spv_k = 1 - mean(survival_spv_k)`;
  `I13` = `MAX(spv_1, E32)`, `J13` = `MAX(spv_2 - spv_1 - J14, E32)` ... (display only).
- `I14` issuer default rate (table above).
- `I15` issuer LGD = `MAX((I9 - 0.1*I10)/I9, 0)` (0 if I9 = 0).
- `I16` SPV LGD = `LGD_Average_Conditional(prev_survival, survival_k, LGD_k)`
  = mean of LGD over paths with `prev_survival=1 and survival_k=0 and LGD>0`
  (year 1: prev_survival == 1, the `V` column).
- `I17` covenant effectiveness = `Covenant_Loss(prev_survival, survival_k,
  LGD_estimation_k)` = #(triggered and AK>0) / #(triggered); 0 when dt=0 (k>=2).
- `I12` SPV annual PD = `MAX(I11*I17 - I14, E32)`.

### Results block (rows 21-33)
`Conditional_Average(P, years, v)` = mean of `v_i` for i = 1...floor(P) (VBA
`For i = 1 To P` with double P) where `years_i < P + 0.75`.
`Weighted_Average(P, years, n1,n2,n3, d1,d2,d3)` = sum n1*n2*n3 / sum d1*d2*d3
over the same i.
```
J21 PD client avg      = CondAvg(I12:R12)
J22 PD client weighted = sum I9*I12 / sum I9
J23 PD issuer avg      = CondAvg(I14:R14)
J24 PD issuer weighted = sum I9*I14 / sum I9
J25 PD total           = J22 + J24
J26 LGD client avg     = CondAvg(I16:R16)
J27 LGD client weighted= sum I9*I11*I16 / sum I9*I11
J28 LGD issuer avg     = CondAvg(I15:R15)
J29 LGD issuer weighted= sum I9*I14*I15 / sum I9*I14
J30 LGD total          = J22/J25*J27 + J24/J25*J29
J31 EL                 = J30 * J25
I32 risk grade         = grade_lookup(J25)
J33 RWA%               = Basel_II_Cap_Corp(J25, J30, MIN(E10, 5), 0.99)
```
Rows 55-61 (display): SPV default `=I12`, issuer default `=I14`, combined
`= sum`, SPV LGD `=I16`, issuer LGD `=I15`, combined LGD
`= I16/combined*I12 + I15/combined*I14`.

`Basel_II_Cap_Corp(PD, LGD, M, alpha)`:
```
R = 0.12*(1-exp(-50PD))/(1-exp(-50)) + 0.24*(1 - (1-exp(-50PD))/(1-exp(-50)))
b = (0.11852 - 0.05478*ln PD)^2
K = (LGD*Phi((1-R)^-0.5*PhiInv(PD) + sqrt(R/(1-R))*PhiInv(alpha)) - PD*LGD) * (1-1.5b)^-1 * (1+(M-2.5)b)
RWA% = 12.5*K
```

### Print Report & Results (rows 37-43)
| | Reference Entity | Client/Borrower | Combined |
|---|---|---|---|
| PD | `D38 = J24` | `G38 = J22` | `J38 = MIN(D38+G38, 1)` |
| Risk Grade | lookup(D38) | lookup(G38) | lookup(J38) |
| Downturn LGD | `D40 = J29` | `G40 = J27` | `J40 = (D38*D40 + G38*G40)/(D38+G38)` |
| EL | D40*D38 | G40*G38 | J38*J40 |
| EL Grade | lookup(EL) | lookup(EL) | lookup(EL) |
| RWA% | Listed: `MAX(Basel(D38,D40,years,0.99), 2)`; Unlisted: `MAX(..., 3)` | `Basel(G38,G40,years,0.99)` (0 on error) | `Basel(J38,J40,MIN(years,5),0.99)` |

Note the Reference-Entity and Client RWA use the full `years` as maturity
(not capped at 5); Combined caps at 5. Replicated.

Transaction-detail block of the report: client name, CIF, date (today),
reference share, reference CIF, start, maturity, years, amortised/IO amount,
bullet amount, bullet rate, number of shares, share price, initial share
value, initial cover ratio, initial DCR, PD of reference entity (fitted PD of
the grade), dividend yield, % dividends repaid, share price volatility,
liabilities ranking ahead / pari-passu / subordinate, transaction structure.

### Other derived Input quantities
- `Equity_Duration(N, V, 25%)`: `n = CInt((N/V)/0.25)` (VBA Integer coercion:
  round-half-to-even), unwind years = `((n+1)/2) / 251`; days = years x 251.
  (`E48`; shown on Input as H84/H87.)
- Liquidity flag `E44`: Unlisted -> ""; else `N/40 > 0.25*V` -> "Illiquid"
  else "Liquid". Display only.
- Reference entity fitted PD `E18` = master-scale fitted PD of the grade.
- Risk-free rate default = Constants country table col D for the reference
  entity's country; Input H112 overrides (the file carries 6% vs table 7%).

### Portfolio Transactions (up to 10 stocks)
Per stock: name, number of shares, share price, stock volatility, dividend
yield, average daily traded volume, country of risk, risk grade, revenue
size, corporate sector, EBITDA, total stock market capitalisation, total
liabilities, time to unwind (years), unlisted haircut, illiquid haircut,
currency pair, currency-pair volatility; a 10x10 equity correlation matrix,
10x10 currency-pair correlation matrix and 10x10 currency x equity matrix
(upper-triangle inputs mirrored).

Combined outputs (`E84:E93`): shares `sum N_i`; price `sum V_i / sum N_i`;
volatility `sqrt(w*C*w^T)` where `w_i = value_i/sum(value) * sigma_i` over the
20-vector [equity weights, currency weights] and the 20x20 block matrix
[[C_eq, C_fx,eq^T],[C_fx,eq, C_fx]] (`D159:W180`; currency x equity block
floored at 0); value-weighted dividend yield, ADTV, time to unwind, unlisted
haircut, illiquid haircut, risk-free rate (country table), equity LGD
(see Corporate LGD).

In portfolio mode the engine takes: share value, volatility, dividend yield,
time to unwind and the report's share count / price / yield / volatility from
the portfolio combined outputs (see Deviation D1).

### Corporate (Equity) LGD per stock — optional module
VBA `Corporate_LGD_Final_Collateral_Metric("Unsecured_LGD", ...)` fed by the
per-stock PD (grade fitted PD x 100), insolvency regime score and recovery
costs (Constants country table cols B, C), EBITDA, earnings multiple and
asset volatility (Volatilities & Multiples by sector + revenue size),
Africa adjust (country col E), the **Simulation** sheet's 10,000-value LGD
distribution (`A2:A10001`) and performing-book percentile table
(`C2:D1127`). Output "Equity LGD" per stock (`D47:M47`) and value-weighted
`E93`, which flows to Calculations `E47` and is used **only** as the
`IFERROR` fallback of the Combined downturn LGD on the report.
On the single-share Input page this block (H125:K184) is `#REF!`-broken in
the prototype and cannot produce a value. Builder: port it last; if parity
on the four cached portfolio values (0.3045, 0.9508, 0.7121, 0.9508) is not
reached in reasonable time, ship the app with Equity LGD = null and say so.

## Workbook quirks (preserved for parity) and deviations (my calls)

**Preserved — only active when the workbook's own random draw set is used
(default). A user-supplied seed uses the clean formulas.**
- Q1 Row 7 (path 1, year 1): stock post-divs is `Y*(1-E19)` instead of
  `Y - (AA - AB)`.
- Q2 Row 14 (path 8, year 1): survival-of-covenant hard-coded to 0.

**Preserved always**
- LGD_Estimation returns 0 for approach 2 (Orderly Liquidation): the VBA has
  no branch for it. Surface a warning in the result when approach = 2.
- `AJ` uses the raw equity volatility (Input H66), not the currency-adjusted
  `E21`.
- Reference-entity / client RWA% use uncapped years as maturity.
- Issuer default rate column pattern pd1, pd2, pd3, pd4, pd4 ...
- Row 13 "SPV annual PD [No Covenant]" uses the LGD floor (`E42`) instead
  of min PD for year 4 (`L13`) — display row only; replicate.

**Deviations**
- D1 Portfolio mode consistency: the workbook feeds the engine with
  Input!H33 (shares x price typed on the Input page) and Input!H62 (yield)
  even when "Portfolio of Shares? = Yes", while the report shows the
  portfolio totals. The app uses the portfolio combined values for both
  engine and report in portfolio mode (the sheet's evident intent). The
  Input page's shares / price / yield / volatility fields are read-only
  mirrors of the portfolio totals in that mode.
- D2 Amortised-loan interest: the prototype's first rate bucket (`J38`)
  points at the **bullet** rate cell `E13`, which is "Not Applicable" (-> 0)
  for amortised / interest-only structures, so those loans accrue no
  interest. The app uses Input `I57` ("Current Interest Rate Charged") as the
  first bucket's rate. Bullet structures are unaffected (parity holds).
- D3 Vestigial inputs kept visible but marked "not used by the engine":
  Time to unwind (H68, replaced by the computed Equity_Duration), unlisted /
  illiquid haircuts (H108/H110 -> E45/E46 unreferenced), other collateral /
  pari-passu collateral fields (H77-H81), liquidity flag.
- D4 Report date = calculation date (the sheet's `TODAY()`).

## Architecture (mirrors the sibling suite apps)

- **Backend** `backend/app/` — FastAPI, Python 3.12, pure-Python engine (no
  numpy/pandas): `domain/{models,reference,mathx,duration,simulation,
  aggregate,report,basel,portfolio,corporate_lgd}.py`. `NormalDist` /
  Acklam `norm_ppf` as in siblings (parity shown with
  `statistics.NormalDist.inv_cdf`).
- **Reference data** `backend/app/data/reference/*.json`, generated by
  `scripts/export_reference.py` from the workbook (never hand-edited):
  `pd_masterscale.json` (P3:S30), `issuer_default_rates.json` (RN P2:U26),
  `countries.json` (A3:E181: insolvency score, recovery cost, risk-free
  rate, Africa flag), `sectors.json`, `volatilities_multiples.json`
  (sector+size -> asset vol, earnings multiple), `sector_correlations.json`
  (Sheet3 B3:Q18), `lgd_buckets.json`, `random_numbers.json` (10,000x10
  uniforms, ~1.9 MB, loaded once), `simulation.json` (Simulation A/C/D).
- **Persistence**: `MemoryStore` (JSON dev store, default) / `SupabaseStore`
  (payload-jsonb tables `batches`, `transactions`, `runs`), selected by
  env, same code shape as the siblings; migration under `supabase/`.
  Supabase project creation is left to the owner (needs credentials).
- **API** (`/api`): `health`, `reference/capture-config` (dropdown lists,
  defaults, country table, grades, sectors), `batches` CRUD,
  `batches/{id}/transactions` CRUD, `transactions/{id}/calculate` -> run,
  `runs/{id}`, `runs/{id}/export.xlsx`. Runs are immutable snapshots of
  inputs + results.
- **Frontend** `frontend/` — React 19 + Vite + Tailwind + react-router,
  CYTE palette (`#001080` navy, panel `#DBE3F1`, RAG colours), same
  `AppShell`, `.card / .section-header / .field-label / .field-input /
  .btn-primary` component classes. Routes: `/` suite landing, `/batches`,
  `/batches/:id`, `/batches/:id/transactions/new`, `/transactions/:id`
  (wizard with tabs 1 · Input, 2 · Portfolio, 3 · Calculate, 4 · Report).
  Report tab has a print stylesheet and the xlsx download.
- **Ports** 8003 / 5176 (8000-8002 and 5173-5175 are taken by siblings).
- **Tests** `backend/tests/`: golden parity on the Excelcior case (every
  Calculations I9:R17 value, J21-J33, the full Print Report block, Input
  H84/H87), unit tests for Equity_Duration rounding, grade lookup, Basel
  formula, DCR schedule, structure rules, portfolio volatility (cached
  0.36840968...), API flow test (create -> calculate -> export).

## Build order (for the plan)
1. Reference export script + JSON assets + engine (`domain/`) with the
   golden parity test first (TDD against cached workbook values).
2. API + stores + schemas; API flow test.
3. Frontend shell + Input page (with all conditional rules) + Portfolio
   page + Calculate page + Report page; xlsx export.
4. README (quick start identical in shape to siblings), parity notes doc.
5. Corporate LGD module (optional, last).

## Left to the builder
- Exact field grouping/ordering inside the four pages beyond "follow the
  sheet's sections".
- Validation messages; how "Not Applicable" is represented (null) in JSON.
- Chart or no chart on the Calculate page (a per-year PD/LGD bar chart is
  welcome but not required).

# Securities Lending (Share Cover) Model

Share-backed lending **PD, LGD, EL & RWA application** — CYTE Risk Suite sibling of
[`../global-finance-model`](../global-finance-model),
[`../global-banking-model`](../global-banking-model) and
[`../global-insurance-model`](../global-insurance-model). It reproduces the
"Stock Lending Model" workbook (`Equity Finance Model Final V1.5 (Henry
Adjusted)v1.2.xlsm`, repo root) as a web app: a 10,000-path simulation of the
pledged share price against the default-cover-ratio covenant, combined with the
share issuer's own default risk, producing the **Share Cover Risk Report** —
PD, risk grade, downturn LGD, EL, EL grade and RWA% for the Reference Entity,
the Client/Borrower and the Combined exposure.

## Quick start (no credentials needed)

Backend (Python 3.12):

```bash
cd backend
py -3.12 -m venv .venv
.venv\Scripts\pip install -e .[dev]
.venv\Scripts\python -m uvicorn app.main:app --port 8003
```

Frontend:

```bash
npm run install-frontend
npm run dev          # http://localhost:5176 (proxies /api to 8003)
```

With `SUPABASE_URL` + `SUPABASE_SERVICE_ROLE_KEY` set (see `.env.example`) the
backend persists to Supabase (apply `supabase/migrations/0001_init.sql`);
without credentials it falls back to a local JSON dev store
(`backend/dev_store.json`). Ports 8003/5176 leave 8000–8002 / 5173–5175 free
for the sibling suite apps.

## Flow (mirrors the workbook sheet by sheet)

| Workbook sheet | App step |
|---|---|
| Input | **1 · Input** — same sections, labels and show/hide rules as the sheet's ComboBox macros (transaction structure, cover-linked rates, DCR changes, currency mismatch, dividend %) |
| Portfolio Transactions | **2 · Portfolio Transactions** — up to 10 stocks, equity / currency / currency×equity correlation matrices, live "Outputs (Combined)" block (only when "Portfolio of Shares? = Yes") |
| Calculations (+ hidden Results) | **3 · Calculations** — year-by-year table (rows 9–17, 55–61) and the Results block (J21–J33) |
| Print Report & Results | **4 · Print Report & Results** — the Share Cover Risk Report with print view and CYTE-branded `export.xlsx` |

Batch → transaction → **calculate** → run (immutable snapshot of inputs +
results) → report / export.

## Engine parity

The pure-Python engine (`backend/app/domain/`) is locked value-for-value
(rel 1e-9) to the workbook's cached Excelcior Shipping example: every
Calculations year-series cell (I6:R17, I57:R61), the Results block
(J21–J33), the full Print Report block (D38:J43), the Input page's unwind
term (H84/H87), three sampled simulation rows, the Portfolio sheet's combined
outputs (E84:E93) and the per-stock Equity LGD (D47:G47, the VBA
`Corporate_LGD_Final_Collateral_Metric` port):

```bash
cd backend && .venv\Scripts\python -m pytest tests -q
```

Fixtures: `scripts/export_golden.py` regenerates
`backend/tests/fixtures/golden_excelcior.json` from the workbook's cached
values; `scripts/export_reference.py` regenerates
`backend/app/data/reference/*.json` (master scale, issuer default rates,
country table, sectors, volatilities & multiples, the 10,000×10 random draw
set, the Simulation distribution) — never hand-edit either. See
`docs/specs/2026-10-20-parity-notes.md` for the preserved workbook quirks,
the documented deviations and how a custom `random_seed` switches to clean
formulas.

## Repo map

```
backend/app/domain/      pure-Python engine (parity-locked, no numpy/pandas)
backend/app/data/        reference JSON (generated - do not hand-edit)
backend/app/services/    calc_service (Input page -> engine inputs), export_xlsx
backend/tests/           golden parity + engine rules + API flow + export
frontend/                React 19 + Vite + Tailwind (CYTE Risk Suite UI)
scripts/                 export_reference / export_golden
supabase/                migration (batches / transactions / runs, RLS on)
docs/specs/              design spec + parity notes
docs/superpowers/plans/  implementation plan
```

## Not done yet (deliberate)

- **Supabase project**: the store and migration are in place but no project
  has been created or linked (needs owner credentials); the JSON dev store is
  the default.
- **Extra Excel-recalculated fixtures**: only the Excelcior case carries
  cached outputs, so amortising structures, DCR schedules, cover-linked
  rates, currency mismatch, unlisted shares, fractional maturities and
  portfolio-mode runs are covered by hand-derived unit tests rather than
  workbook parity. Recalculating copies of the workbook in Excel and rerunning
  `scripts/export_golden.py` would extend the parity claim.
- **Calculations-sheet recovery policy**: exposed as "Recovery Policy" under
  Calculation Settings; approach 2 (Orderly Liquidation) yields LGD = 0 in the
  source VBA and the app warns when it is selected.

# Securities Lending Model — parity notes

Companion to `2026-10-20-securities-lending-model-design.md`. Records what the
engine reproduces from the workbook exactly, which workbook defects are
preserved on purpose, and where the app deliberately deviates.

## Golden case and tolerance

- Source: `Equity Finance Model Final V1.5 (Henry Adjusted)v1.2.xlsm`, cached
  values of the Excelcior Shipping example (bullet R75m loan, 428.6m shares
  at R0.40, 10 years, DCR 1.75, SB11 reference entity, listed, approach 1,
  workbook random draws). Exported by `scripts/export_golden.py` into
  `backend/tests/fixtures/golden_excelcior.json`.
- Tolerance: `rel=1e-9` (`abs=1e-12` for zeros). Achieved:
  Calculations I6:R17 and I57:R61 (14 series x 10 years), Results J21–J33
  and I32, Print Report D38:J43, Input H84/H87, simulation rows 7–9,
  Portfolio E84:E93 and D47:G47 (`rel=1e-6` on the Equity LGD, which goes
  through a 601-step numerical integration).
- The engine runs the 10,000 x 10 grid in ~0.25 s (pure Python 3.12).

## Preserved workbook quirks

Active only with the workbook draw set (`random_seed = null`, the default);
a user seed uses the clean formulas:

- **Q1** Calculations `AE7` (path 1, year 1) is `MAX(Y7*(1-E19),0)` instead of
  the `MAX(Y-(AA-AB),0)` used by every other row.
- **Q2** Calculations `AG14` (path 8, year 1) is a hard-coded `0` instead of
  the covenant test. Without it the year-1 breach rate is 0.1886, not the
  workbook's 0.1887.

Always preserved:

- VBA `LGD_Estimation` has no branch for approach 2 (Orderly Liquidation) and
  returns 0; the app adds a warning when approach 2 is selected. Paths where
  the SPV itself defaults still use approach 3 (fire sale) whatever the
  policy, as in the sheet (`AI = IF(AH=0, 3, E41)`).
- The unwind term `AJ` discounts with the raw equity volatility (Input H66),
  not the currency-adjusted `E21`.
- Reference-entity and client RWA% use the full term as Basel maturity;
  only the Combined column caps at 5 years. Reference RWA is floored at 2
  (Listed) / 3 (Unlisted).
- Issuer default rates follow the column pattern pd1, pd2, pd3, pd4, pd4,
  pd4 … (`MIN(year+1, 5)` into P:U).
- Row 13 "SPV annual PD [No Covenant]" uses the LGD floor (1e-7) instead of
  the minimum PD for year 4 (`L13` references `E42`). Display row only.
- `Conditional_Average` / `Weighted_Average` loop `For i = 1 To Period` with
  an Integer counter: the bound is `CInt(Period)` (round-half-even), so a
  2.6-year deal averages years 1–3 and a 2.4-year deal years 1–2.
- "Africa Adjust" (Input K177, Portfolio row 151) reads country-table column
  4, which is the risk-free rate rather than the Africa flag in column 5; the
  Equity LGD port replicates it, so the 15% insolvency-haircut branch never
  fires.
- The Equity LGD per stock passes `Approach` from a cell holding 0.02; the
  VBA overrides it to 2 anyway.

## Deviations (documented decisions)

- **D1 Portfolio mode consistency.** The sheet feeds the engine from the
  Input page's typed shares x price (H33) and yield (H62) even when
  "Portfolio of Shares? = Yes", while the report shows portfolio totals. The
  app uses the portfolio combined values (value, volatility incl. FX,
  yield, unwind period) for both engine and report; the Input page mirrors
  them read-only. The reference-entity leg (issuer default rates, listing,
  country) stays workbook-literal from the Input page's single Reference
  Share block.
- **D2 Amortised-loan interest.** `Calculations!J38` points the first
  rate bucket at the bullet rate `E13`, which is "Not Applicable" (0) for
  amortised / interest-only structures. The app uses the Input page's
  "Current Interest Rate Charged" (`I57`) as the first bucket. Bullet
  structures are unaffected.
- **D3 Vestigial inputs** kept visible and marked "report only": time to
  unwind (H68; the engine uses the computed Equity_Duration), unlisted /
  illiquid haircuts (H108/H110 → `E45/E46`, unreferenced), the three
  collateral fields (H77–H81), the liquidity flag.
- **D4** Report date = calculation date (`TODAY()`).
- **D5** Maturities beyond 10 years are rejected (the grid stops at year 10).
- **D6** Grade labels stay SB01–SB25 with the workbook's exact bounds; D1–D3
  share one lower bound and `LOOKUP` returns the last of them.
- **Zero covenant triggers.** When no path breaches in a year the VBA
  `Covenant_Loss` / `LGD_Average_Conditional` divide by zero (`#VALUE!`
  through the Results block). The app returns 0 for that year's covenant
  effectiveness and SPV LGD (and 0 for a zero-denominator weighted average)
  and adds a warning naming the year.
- **Export layout.** Row 1 of every exported sheet is the CYTE brand band;
  the sheet title sits on row 2.

## What is NOT parity-tested

Only the Excelcior case has cached outputs. Amortising / interest-only /
SA+bullet structures, DCR change schedules, cover-linked rate buckets,
currency mismatch, unlisted shares, fractional-year maturities, recovery
approaches 2–3 and full portfolio-mode runs are covered by hand-derived unit
tests (`backend/tests/domain/test_engine_rules.py`) that pin the formulas
above, not by a workbook recalculation. Recalculate copies of the workbook
in Excel and rerun `scripts/export_golden.py` to extend the claim.

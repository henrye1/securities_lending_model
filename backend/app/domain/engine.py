"""run_engine: EngineInputs -> EngineResult (the Calculations + Print Report
sheets for one transaction)."""
from __future__ import annotations

from app.domain import grades, reference
from app.domain.aggregate import results_block, year_rows
from app.domain.models import EngineInputs, EngineResult
from app.domain.report import print_report
from app.domain.simulation import simulate

APPROACH_2_WARNING = (
    "Recovery approach 2 (Orderly Liquidation) yields LGD = 0 in the source model's "
    "LGD_Estimation; results reflect that."
)


def run_engine(inp: EngineInputs, equity_lgd_fallback: float | None = None) -> EngineResult:
    warnings: list[str] = []
    if inp.draws is None:
        draws = reference.random_numbers()
        apply_quirks = inp.apply_quirks
    else:
        draws = inp.draws
        apply_quirks = False
    if inp.approach == 2:
        warnings.append(APPROACH_2_WARNING)

    sim = simulate(inp, draws, apply_quirks)
    rows = year_rows(sim, inp, warnings)
    results = results_block(rows, inp)
    report = print_report(results, inp, equity_lgd_fallback)

    loan_total = inp.amortised_amount + inp.bullet_amount
    derived = {
        "years_total": inp.years_total,
        "initial_cover_ratio": inp.share_value / loan_total if loan_total else 0.0,
        "initial_dcr": sim.dcr[0],
        "dcr_by_year": sim.dcr,
        "discount_factor": 1.0 / (1.0 + inp.risk_free_rate) ** inp.unwind_years,
        "unwind_years": inp.unwind_years,
        "fsh": 0.30 if inp.listing == "Listed" else 0.50,
        "reference_pd": grades.fitted_pd(inp.reference_grade),
        "volatility": inp.volatility,
        "n_paths": sim.n_paths,
        "workbook_draws": inp.draws is None,
        "quirks_applied": apply_quirks,
        "path_samples": {
            p: {
                "stock_y1": sim.stock[0][p], "cover_y1": sim.cover[0][p],
                "survival_covenant_y1": sim.survival_covenant[0][p], "lgd_y1": sim.lgd[0][p],
                "stock_y2": sim.stock[1][p], "lgd_y2": sim.lgd[1][p],
            }
            for p in range(min(3, sim.n_paths))
        },
    }
    return EngineResult(years=rows, results=results, report=report, derived=derived, warnings=warnings)

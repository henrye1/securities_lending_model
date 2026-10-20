"""Print Report & Results rows 37-43: Reference Entity / Client-Borrower /
Combined x PD, Risk Grade, Downturn LGD, EL, EL Grade, RWA%."""
from __future__ import annotations

from app.domain import grades
from app.domain.basel import basel_ii_cap_corp
from app.domain.models import EngineInputs, ReportColumn, ResultsBlock


def _column(pd: float, lgd: float, rwa: float) -> ReportColumn:
    el = pd * lgd
    return ReportColumn(
        pd=pd, grade=grades.grade_for(pd), lgd=lgd, el=el,
        el_grade=grades.grade_for(el), rwa_pct=rwa,
    )


def _basel_or(pd: float, lgd: float, maturity: float, default: float) -> float:
    try:
        return basel_ii_cap_corp(pd, lgd, maturity)
    except ValueError:
        return default


def print_report(
    results: ResultsBlock, inp: EngineInputs, equity_lgd_fallback: float | None = None
) -> dict[str, ReportColumn]:
    years = inp.years_total
    d38, g38 = results.pd_issuer_weighted, results.pd_client_weighted
    d40, g40 = results.lgd_issuer_weighted, results.lgd_client_weighted
    j38 = min(d38 + g38, 1.0)
    denominator = d38 + g38
    if denominator:
        j40 = (d38 * d40 + g38 * g40) / denominator
    else:  # IFERROR(..., Calculations!E47) - the portfolio equity LGD
        j40 = equity_lgd_fallback if equity_lgd_fallback is not None else 0.0

    floor = 2.0 if inp.listing == "Listed" else 3.0                     # D43
    reference = _column(d38, d40, max(_basel_or(d38, d40, years, 0.0), floor))
    client = _column(g38, g40, _basel_or(g38, g40, years, 0.0))         # G43 IFERROR -> 0
    combined = _column(j38, j40, _basel_or(j38, j40, min(years, 5.0), 0.0))  # J43
    return {"reference": reference, "client": client, "combined": combined}

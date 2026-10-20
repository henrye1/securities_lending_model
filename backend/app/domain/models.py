"""Engine input / output models (plain dataclasses) and the two lookup
schedules the Calculations sheet builds from the Input page:

- default-cover-ratio by year  (Calculations H47:J53)
- interest rate by cover ratio (Calculations H38:J43)
"""
from __future__ import annotations

from dataclasses import dataclass, field

from app.domain.mathx import excel_lookup

Schedule = list[tuple[float, float]]  # (lower bound, value)


def build_dcr_schedule(initial_dcr: float, changes: list[tuple[float, float]]) -> Schedule:
    """[(0, initial)] + [(t + 0.1, dcr) for each change with t > 0]: a change
    at time t applies from the first whole year strictly after t."""
    sched: Schedule = [(0.0, float(initial_dcr))]
    for t, dcr in changes:
        if t and t > 0:
            sched.append((float(t) + 0.1, float(dcr)))
    return sched


def dcr_for_year(schedule: Schedule, year: float) -> float:
    return excel_lookup(year, [b for b, _ in schedule], [v for _, v in schedule])


def rate_for_cover(schedule: Schedule, cover: float) -> float:
    return excel_lookup(cover, [b for b, _ in schedule], [v for _, v in schedule])


@dataclass
class EngineInputs:
    years_total: float                       # E10
    amortised_amount: float                  # E11 (0 if N/A)
    bullet_amount: float                     # E12 (0 if N/A)
    bullet_rate: float                       # E13 (0 if N/A)
    share_value: float                       # E14
    dividend_yield: float                    # E19
    dividends_repaid: float                  # E20
    volatility: float                        # E21 (currency-adjusted or portfolio)
    equity_volatility: float                 # Input!H66 raw (used in AJ)
    structure: str                           # E25
    risk_free_rate: float                    # E31
    dcr_schedule: Schedule                   # H47:J53
    rate_schedule: Schedule                  # H38:J43
    reference_grade: str = "SB11"            # Input!H97
    min_pd: float = 0.0003                   # E32
    approach: int = 1                        # E41
    listing: str = "Listed"                  # E43
    unwind_years: float = 0.0                # E48
    lgd_floor: float = 1e-7                  # E42 (row-13 quirk only)
    draws: list[list[float]] | None = None   # None -> workbook draws (+ quirks)
    apply_quirks: bool = True


@dataclass
class YearRow:
    year: float
    dt: float
    dcr: float
    avg_loan: float
    avg_share_value: float
    spv_pd_covenant: float
    spv_pd: float
    spv_pd_no_covenant: float
    issuer_default_rate: float
    issuer_lgd: float
    spv_lgd: float
    covenant_effectiveness: float
    combined_pd: float
    combined_lgd: float


@dataclass
class ResultsBlock:
    pd_client_avg: float
    pd_client_weighted: float
    pd_client_grade: str
    pd_issuer_avg: float
    pd_issuer_weighted: float
    pd_issuer_grade: str
    pd_total: float
    lgd_client_avg: float
    lgd_client_weighted: float
    lgd_issuer_avg: float
    lgd_issuer_weighted: float
    lgd_total: float
    el: float
    risk_grade: str
    rwa_pct: float


@dataclass
class ReportColumn:
    pd: float
    grade: str
    lgd: float
    el: float
    el_grade: str
    rwa_pct: float


@dataclass
class EngineResult:
    years: list[YearRow]
    results: ResultsBlock
    report: dict[str, ReportColumn]          # reference / client / combined
    derived: dict = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)

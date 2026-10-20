"""Path simulation - the Calculations sheet's 10,000-row x 10-year grid
(columns V..FQ). One python loop per path, years inside; the per-year
per-path columns the aggregation needs are kept as lists.

Cell references in comments are the YEAR-1 block (X..AL); later years use the
same formulas with the previous year's values (AM..BA etc.)."""
from __future__ import annotations

import math
from dataclasses import dataclass, field

from app.domain.mathx import norm_ppf
from app.domain.models import EngineInputs, dcr_for_year, rate_for_cover

N_YEARS = 10

AMORTISING = ("Straight Amortisation", "Straight Amortisation & Bullet")
INTEREST_ONLY = "Interest Only Repayments"


def lgd_estimation(approach: int, ead: float, stock_unwind_nmc: float, fsh: float) -> float:
    """VBA LGD_Estimation: approach 1 -> (EAD-NMC)/EAD; 3 -> (EAD-NMC*(1-FSH))/EAD;
    approach 2 has no branch in the VBA and returns 0."""
    if ead == 0:
        return 0.0
    if approach == 1:
        return (ead - stock_unwind_nmc) / ead
    if approach == 3:
        return (ead - stock_unwind_nmc * (1 - fsh)) / ead
    return 0.0


@dataclass
class SimPaths:
    years: list[float]
    dt: list[float]
    dcr: list[float]
    n_paths: int
    # per year (index 0..9) -> per path lists
    loan: list[list[float]] = field(default_factory=list)              # AD / AS  total loan post divs
    stock: list[list[float]] = field(default_factory=list)             # AE / AT  stock post divs
    cover: list[list[float]] = field(default_factory=list)             # AF / AU
    survival_covenant: list[list[int]] = field(default_factory=list)   # AG / AV
    survival_spv: list[list[int]] = field(default_factory=list)        # AH / AW
    lgd: list[list[float]] = field(default_factory=list)               # AL / BA  LGD (modelled)
    lgd_estimation: list[list[float]] = field(default_factory=list)    # AK / AZ
    change: list[list[float]] = field(default_factory=list)            # X / AM


def year_grid(years_total: float) -> tuple[list[float], list[float]]:
    """I6:R6 = MIN(k, E10); I7:R7 = differences."""
    years = [min(float(k), years_total) for k in range(1, N_YEARS + 1)]
    dt = [years[0]] + [years[k] - years[k - 1] for k in range(1, N_YEARS)]
    return years, dt


def _loan_post_divs(structure: str, stock: float, loan_post_int: float, divs: float, amortised_amount: float) -> float:
    """AB / AQ: the transaction-structure rule."""
    if structure in AMORTISING:
        return max((loan_post_int - divs) if stock > 0 else 0.0, 0.0)
    if structure == INTEREST_ONLY:
        return max((loan_post_int - divs) if stock > 0 else 0.0, amortised_amount, 0.0)
    return 0.0  # Bullet Payment


def simulate(inp: EngineInputs, draws: list[list[float]], apply_quirks: bool) -> SimPaths:
    years, dt = year_grid(inp.years_total)
    dcr = [dcr_for_year(inp.dcr_schedule, y) for y in years]
    n = len(draws)
    sim = SimPaths(years=years, dt=dt, dcr=dcr, n_paths=n)
    for _ in range(N_YEARS):
        for coll in (sim.loan, sim.stock, sim.cover, sim.survival_covenant, sim.survival_spv,
                     sim.lgd, sim.lgd_estimation, sim.change):
            coll.append([0.0] * n)

    e14, e11, e12, e13 = inp.share_value, inp.amortised_amount, inp.bullet_amount, inp.bullet_rate
    e19, e20, e21, e31 = inp.dividend_yield, inp.dividends_repaid, inp.volatility, inp.risk_free_rate
    drift = e31 - 0.5 * e21 * e21
    fsh = 0.30 if inp.listing == "Listed" else 0.50                       # AL4
    discount = 1.0 / (1.0 + e31) ** inp.unwind_years                      # E49
    unwind_factor = math.exp(-inp.equity_volatility * math.sqrt(inp.unwind_years)) * discount  # AJ multiplier
    initial_cover = e14 / (e11 + e12) if (e11 + e12) else 0.0             # E15

    for p in range(n):
        u = draws[p]
        prev_stock = prev_cover = 0.0
        prev_amort = prev_bullet = 0.0
        prev_surv_spv = 1
        for k in range(N_YEARS):
            d = dt[k]
            if k == 0:
                x = norm_ppf(u[0]) * math.sqrt(d) * e21 + drift * d                 # X
                y = e14 * math.exp(x)                                               # Y
                rate = rate_for_cover(inp.rate_schedule, initial_cover)             # Z
                amort_post_int = e11 * (1 + rate) ** d                              # AA
                divs = e14 * e19 * e20
                bullet_post_int = e12 * (1 + e13) ** d                              # AC
            else:
                if prev_surv_spv == 1:
                    x = norm_ppf(u[k]) * math.sqrt(d) * e21 + drift * d             # AM
                    y = prev_stock * math.exp(x)                                    # AN
                else:
                    x, y = 0.0, 0.0
                rate = rate_for_cover(inp.rate_schedule, prev_cover)                # AO
                amort_post_int = prev_amort * (1 + rate) ** d                       # AP
                divs = prev_stock * e19 * e20
                bullet_post_int = prev_bullet * (1 + e13) ** d                      # AR
            amort = _loan_post_divs(inp.structure, y, amort_post_int, divs, e11)    # AB / AQ
            loan = bullet_post_int + amort                                          # AD / AS
            if apply_quirks and k == 0 and p == 0:
                stock = max(y * (1 - e19), 0.0)                                     # Q1: row 7
            else:
                stock = max(y - (amort_post_int - amort), 0.0)                      # AE / AT
            # AF / AU
            if stock > 0:
                try:
                    cover = stock / loan if d == 1 else y / (amort_post_int + bullet_post_int)
                except ZeroDivisionError:
                    cover = 1000.0
            else:
                cover = 0.0
            surv_cov = 1 if cover > dcr[k] else 0                                   # AG / AV
            if apply_quirks and k == 0 and p == 7:
                surv_cov = 0                                                        # Q2: row 14
            surv_spv = 1 if y > bullet_post_int else 0                              # AH / AW
            approach = None if surv_cov == 1 else (3 if surv_spv == 0 else inp.approach)  # AI / AX
            nmc = unwind_factor * stock                                             # AJ / AY
            lgd_est = max((loan - nmc) / loan, 0.0) if loan else 0.0               # AK / AZ
            if approach is None or (k > 0 and x == 0.0):
                lgd = 0.0
            else:
                lgd = max(lgd_estimation(approach, loan, nmc, fsh), 0.0)            # AL / BA

            sim.loan[k][p] = loan
            sim.stock[k][p] = stock
            sim.cover[k][p] = cover
            sim.survival_covenant[k][p] = surv_cov
            sim.survival_spv[k][p] = surv_spv
            sim.lgd[k][p] = lgd
            sim.lgd_estimation[k][p] = lgd_est
            sim.change[k][p] = x

            prev_stock, prev_cover, prev_amort, prev_bullet, prev_surv_spv = (
                stock, cover, amort, bullet_post_int, surv_spv,
            )
    return sim

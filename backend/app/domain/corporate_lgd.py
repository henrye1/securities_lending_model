"""Line-by-line port of the workbook's VBA Corporate_LGD_Final_Collateral_Metric
(Module3) - the per-stock "Equity LGD" of the Portfolio Transactions sheet
(rows 101-157), using the Simulation sheet's LGD distribution and
performing-book percentile table.

Only the inputs the sheet actually wires are non-zero (see
equity_lgd_for_stock); the VBA forces Approach = 2 and Adjustment = 2.
"""
from __future__ import annotations

import math
from statistics import NormalDist

from app.domain import grades, reference
from app.domain.mathx import excel_lookup
from app.domain.portfolio import StockInput


def _cdf(x: float, mean: float, sd: float) -> float:  # Excel NORMDIST(x, mean, sd, TRUE)
    return NormalDist(mean, sd).cdf(x)


def _inv(p: float, mean: float, sd: float) -> float:  # Excel NORMINV
    return NormalDist(mean, sd).inv_cdf(p)


def excel_percentile_inc(values: list[float], k: float) -> float:
    """Excel PERCENTILE / PERCENTILE.INC."""
    v = sorted(values)
    n = len(v)
    if n == 0:
        raise ValueError("empty array")
    if not 0.0 <= k <= 1.0:
        raise ValueError("k must be in [0, 1]")
    rank = k * (n - 1)
    lo = int(math.floor(rank))
    frac = rank - lo
    if lo + 1 >= n:
        return v[-1]
    return v[lo] + frac * (v[lo + 1] - v[lo])


def _frange(start: float, stop: float, step: float):
    i = 0
    while True:
        x = start + i * step
        if x > stop + 1e-12:
            return
        yield x
        i += 1


def corporate_lgd_final_collateral_metric(
    metric: str,
    pd_pct: float,
    insolv_regime: float,
    earnings: float,
    tot_liab: float,
    facility: float,
    senior: float,
    subordinate: float,
    rec_enh: float,
    coll_1: float,
    coll_2: float,
    fac_col: float,
    rec_costs: float,
    ear_mult: float,
    ear_vol: float,
    africa_adjust: float,
    coll_3rd: float,
    unsecured_floor: float,
    distribution: list[float],
    performing_book: list[list[float]],
) -> float:
    del rec_enh  # unused in the VBA too
    tot_liab = max(tot_liab, facility + coll_2)
    adjustment = 2.0

    economic_value_t = earnings * ear_mult
    economic_vol_t = economic_value_t * ear_vol
    if economic_vol_t <= 0:
        raise ValueError("Earnings x multiple x volatility must be positive")
    economic_value_d = _inv(pd_pct / 100, economic_value_t, economic_vol_t)

    max_fac_lgd = 1 + adjustment
    max_fac_lgd1 = 1.0
    debt_parri_passu = 1.0
    debt_parri_passu1 = 1.0
    dpp_costs = tot_liab * debt_parri_passu * (1 + rec_costs)
    dpp_costs1 = tot_liab * debt_parri_passu1
    dp_senior = dpp_costs          # DAP_Costs = 0 (Debt_Senior = 0)
    dp_senior1 = dpp_costs1

    # Approach is forced to 2 (orderly wind-up) in the VBA
    economic_value_final = dp_senior / (1 + max(0.0 * ear_vol, -0.99))
    economic_value_final1 = dp_senior1

    haircut = (0.15 if africa_adjust > 0.5 else 0.1) * (insolv_regime - 1)
    final_asset_value = economic_value_final / (1 - haircut)
    final_asset_value1 = economic_value_final1 / (1 - haircut)
    multiplier = final_asset_value / (max_fac_lgd * dp_senior) * (debt_parri_passu * tot_liab)
    multiplier1 = final_asset_value1 / dp_senior1 * (tot_liab * debt_parri_passu1)

    # --- LGD incorporating capital structure and recovery costs ---------------
    first_pd_point = pd_pct / 100
    length3 = max(first_pd_point - _cdf(final_asset_value, economic_value_t, economic_vol_t), 0.0)
    s = 0.0
    s2 = length3
    length = 0.0
    for i in _frange(0.0, 300.0, 0.5):
        ind = 1 if max(final_asset_value - i / 100 * multiplier, 0.0) < economic_value_d else 0
        pd_point_t = _cdf(max(final_asset_value - multiplier * i / 100, 0.0), economic_value_t, economic_vol_t)
        pd_point_t1 = _cdf(max(final_asset_value - multiplier * (i + 0.005) / 100, 0.0), economic_value_t, economic_vol_t)
        length = pd_point_t - pd_point_t1
        s += length * min(i / 100, max_fac_lgd) * ind
        s2 += length * ind
    if max(final_asset_value - multiplier, 0.0) > economic_value_d:
        s += length * min(300.005 / 100, max_fac_lgd)
        s2 += length
    corporate_lgd1 = 0.0 if (s < 0 or s2 == 0) else s / s2
    k = excel_lookup(corporate_lgd1, [row[0] for row in performing_book], [row[1] for row in performing_book])
    corporate_lgd1 = excel_percentile_inc(distribution, k)

    # --- LGD without recovery costs / capital structure --------------------------
    s3 = s4 = 0.0
    for i in _frange(0.0, 120.0, 0.25):
        if max(final_asset_value1 - i / 100 * multiplier1, 0.0) < economic_value_d:
            t2 = _cdf(final_asset_value1 - multiplier1 * i / 100, economic_value_t, economic_vol_t)
            t3 = _cdf(final_asset_value1 - multiplier1 * (i + 0.25) / 100, economic_value_t, economic_vol_t)
            length1 = t2 - t3
            s3 += length1 * min((i + 0.25) / 100, max_fac_lgd1)
            s4 += length1
    pd_scaler1 = pd_pct - _cdf(final_asset_value1, economic_value_t, economic_vol_t)  # VBA uses PD in %
    if pd_scaler1 > 0:
        corporate_lgd2 = s3 / (s4 + pd_scaler1)
    else:
        if s4 == 0:
            raise ValueError("No default region in the unsecured LGD integration")
        corporate_lgd2 = s3 / s4 - 0.0025
    del corporate_lgd2  # feeds AVL_Default_Region / K_Ratio, which the VBA never uses

    # --- Collateral and seniority ------------------------------------------------
    avl_fac, avl_other = fac_col, coll_1
    pari_passu_amount = tot_liab - senior - subordinate
    assets_for_dist1 = (1 - corporate_lgd1) * tot_liab + tot_liab * rec_costs
    assets_for_dist = max(assets_for_dist1 - senior * (1 + rec_costs), 0.0)
    dist_fac, dist_other = avl_fac, avl_other
    sbg_facility = facility
    coll_debt_other = coll_2
    uncol_debt_other = pari_passu_amount - facility - coll_2
    costs = pari_passu_amount * rec_costs

    total_coll = dist_fac + dist_other
    if total_coll > assets_for_dist:
        fac_coll_check = dist_fac * assets_for_dist / total_coll
        other_coll_check = dist_other * assets_for_dist / total_coll
    else:
        fac_coll_check, other_coll_check = dist_fac, dist_other

    dist_sbg = min(min(dist_fac, fac_coll_check), sbg_facility)
    dist_coll_other = min(min(dist_other, other_coll_check), coll_debt_other)
    dist_bal_remaining = assets_for_dist - dist_sbg - dist_coll_other

    bal_sbg = sbg_facility - dist_sbg
    bal_coll_other = coll_debt_other - dist_coll_other
    bal_rem_post = uncol_debt_other
    bal_sum = bal_sbg + bal_coll_other + bal_rem_post
    total_post = bal_sum + costs
    if total_post == 0 or bal_sum == 0:
        raise ValueError("Zero post-collateral debt in the VBA cost allocation (division by zero)")

    sbg_costs = (bal_sbg * costs * dist_bal_remaining) / (total_post * bal_sum)
    coll_other_costs = (bal_coll_other * costs * dist_bal_remaining) / (total_post * bal_sum)
    uncol_costs = (bal_rem_post * costs * dist_bal_remaining) / (total_post * bal_sum)

    uns_sbg = min(dist_bal_remaining / total_post * bal_sbg, bal_sbg) + sbg_costs
    uns_coll_other = min(dist_bal_remaining / total_post * bal_coll_other, bal_coll_other) + coll_other_costs
    uns_uncol = min(dist_bal_remaining / total_post * bal_rem_post, bal_rem_post) + uncol_costs
    bal_rem = dist_bal_remaining - uns_sbg - uns_coll_other - uns_uncol

    fac_add = bal_sbg * costs / bal_sum
    coll_other_add = bal_coll_other * costs / bal_sum
    uncol_add = bal_rem_post * costs / bal_sum

    loss_sbg = min(bal_sbg - uns_sbg + fac_add, sbg_facility)
    loss_coll_other = bal_coll_other - uns_coll_other + coll_other_add
    loss_uncol = bal_rem_post - uns_uncol + uncol_add
    total1 = loss_sbg + loss_coll_other + loss_uncol

    fac_gets = min(loss_sbg / total1 * bal_rem, loss_sbg) if total1 > 0 else 0.0
    facility_debt_outstanding = loss_sbg - fac_gets

    lgd_sbg = max((facility_debt_outstanding - coll_3rd) / facility, 0.0)
    conditional_unsec_lgd = facility_debt_outstanding / (facility - fac_coll_check)

    if fac_col > 0 or subordinate > 0:
        floored_lgd = lgd_sbg
    else:
        floored_lgd = max(lgd_sbg, unsecured_floor)
    floored_con_unsec = min(max(conditional_unsec_lgd, unsecured_floor), 1.02)

    if metric == "Facility_LGD":
        return floored_lgd
    if metric == "Unsecured_LGD":
        return floored_con_unsec
    raise ValueError(f"Unknown metric '{metric}'")


def equity_lgd_for_stock(s: StockInput) -> float | None:
    """Portfolio Transactions D156 ('Unsecured_LGD') for one stock, or None when
    the sheet would show #VALUE! / blank (missing financials or reference data)."""
    country = reference.country(s.country) if s.country else None
    vm = reference.volatilities_multiples().get(f"{s.sector.strip()} {s.revenue_size}")
    if country is None or vm is None or s.ebitda <= 0 or s.market_cap <= 0 or not s.risk_grade:
        return None
    try:
        pd_pct = grades.fitted_pd(s.risk_grade) * 100
    except ValueError:
        return None
    rec_costs = float(country["recovery_cost"] or 0.0)
    sim = reference.simulation()
    try:
        return corporate_lgd_final_collateral_metric(
            metric="Unsecured_LGD",
            pd_pct=pd_pct,
            insolv_regime=float(country["insolvency_score"]),
            earnings=s.ebitda,
            tot_liab=s.total_liabilities + s.market_cap,   # D121 = D41 + D40
            facility=s.market_cap,                           # D123 = D40
            senior=s.total_liabilities,                      # D124 = D41
            subordinate=0.0,
            rec_enh=0.0,
            coll_1=0.0,
            coll_2=0.0,
            fac_col=0.0,
            rec_costs=rec_costs,                             # D137 (COMI share = 1)
            ear_mult=float(vm["earnings_multiple"]),
            ear_vol=float(vm["asset_vol"]),
            # Workbook quirk: D151 "Africa Adjust" = VLOOKUP(country, Constants!A:E, 4) - column 4
            # is the risk-free rate, not the Africa flag in column 5. Replicated for parity.
            africa_adjust=float(country["risk_free_rate"] or 0.0),
            coll_3rd=0.0,
            unsecured_floor=0.3 if rec_costs == 0.055 else 0.1,
            distribution=sim["distribution"],
            performing_book=sim["performing_book"],
        )
    except (ValueError, ZeroDivisionError):
        return None

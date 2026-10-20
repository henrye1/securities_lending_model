"""Calculations sheet rows 9-17 (per-year aggregates), the Results block
(rows 21-33) and the combined-risk rows 55-61."""
from __future__ import annotations

from app.domain import grades
from app.domain.basel import basel_ii_cap_corp
from app.domain.mathx import vba_cint
from app.domain.models import EngineInputs, ResultsBlock, YearRow
from app.domain.simulation import SimPaths

ZERO_TRIGGER_WARNING = (
    "Year {year}: no covenant breaches in {n} paths - covenant effectiveness and SPV LGD set "
    "to 0 (the workbook's Covenant_Loss / LGD_Average_Conditional would return #VALUE!)."
)


def _positive_mean(values: list[float]) -> float:
    pos = [v for v in values if v > 0]
    return sum(pos) / len(pos) if pos else 0.0


def covenant_loss(prev_surv: list[int], surv: list[int], lgd_estimation: list[float]) -> float | None:
    """VBA Covenant_Loss: #(1->0 transitions with LGD estimation > 0) / #(1->0).
    None when there are no transitions (the VBA raises)."""
    trig = loss = 0
    for a, b, lg in zip(prev_surv, surv, lgd_estimation):
        if a == 1 and b == 0:
            trig += 1
            if lg > 0:
                loss += 1
    return loss / trig if trig else None


def lgd_average_conditional(prev_surv: list[int], surv: list[int], lgd: list[float]) -> float | None:
    """VBA LGD_Average_Conditional: mean LGD over 1->0 transitions with LGD > 0."""
    vals = [lg for a, b, lg in zip(prev_surv, surv, lgd) if a == 1 and b == 0 and lg > 0]
    return sum(vals) / len(vals) if vals else None


def _loop_indices(period: float, years: list[float]) -> list[int]:
    """VBA `For i = 1 To Period` with an Integer counter (CInt bound), keeping
    years_i < Period + 0.75."""
    upper = min(vba_cint(period), len(years))
    return [i for i in range(upper) if years[i] < period + 0.75]


def conditional_average(period: float, years: list[float], values: list[float]) -> float:
    idx = _loop_indices(period, years)
    return sum(values[i] for i in idx) / len(idx) if idx else 0.0


def weighted_average(
    period: float, years: list[float],
    n1: list[float], n2: list[float], n3: list[float],
    d1: list[float], d2: list[float], d3: list[float],
) -> float:
    idx = _loop_indices(period, years)
    num = sum(n1[i] * n2[i] * n3[i] for i in idx)
    den = sum(d1[i] * d2[i] * d3[i] for i in idx)
    return num / den if den else 0.0


def year_rows(sim: SimPaths, inp: EngineInputs, warnings: list[str]) -> list[YearRow]:
    n = sim.n_paths
    ones = [1] * n
    cum_cov = [1 - sum(s) / n for s in sim.survival_covenant]
    cum_spv = [1 - sum(s) / n for s in sim.survival_spv]
    rows: list[YearRow] = []
    for k in range(len(sim.years)):
        year, d = sim.years[k], sim.dt[k]
        avg_loan = _positive_mean(sim.loan[k]) if d > 0 else 0.0                       # I9
        avg_share = _positive_mean(sim.stock[k]) if d > 0 else 0.0                     # I10
        pd_cov = cum_cov[k] if k == 0 else cum_cov[k] - cum_cov[k - 1]                # I11
        issuer_rate = grades.issuer_default_rate(inp.reference_grade, year)            # I14
        prev = ones if k == 0 else sim.survival_covenant[k - 1]
        if k == 0 or d > 0:
            eff = covenant_loss(prev, sim.survival_covenant[k], sim.lgd_estimation[k])  # I17
        else:
            eff = 0.0
        spv_lgd = lgd_average_conditional(prev, sim.survival_covenant[k], sim.lgd[k])  # I16
        if eff is None or spv_lgd is None:
            if d > 0:
                warnings.append(ZERO_TRIGGER_WARNING.format(year=k + 1, n=n))
            eff = 0.0 if eff is None else eff
            spv_lgd = 0.0 if spv_lgd is None else spv_lgd
        spv_pd = max(pd_cov * eff - issuer_rate, inp.min_pd)                           # I12
        floor = inp.lgd_floor if k == 3 else inp.min_pd                                 # L13 uses E42
        if k == 0:
            spv_pd_no_cov = max(cum_spv[0], inp.min_pd)                                # I13
        else:
            spv_pd_no_cov = max(cum_spv[k] - cum_spv[k - 1] - issuer_rate, floor)
        issuer_lgd = max((avg_loan - avg_share * 0.1) / avg_loan, 0.0) if avg_loan else 0.0  # I15
        combined_pd = spv_pd + issuer_rate                                             # I57
        combined_lgd = (
            spv_lgd / combined_pd * spv_pd + issuer_lgd / combined_pd * issuer_rate     # I61
            if combined_pd else 0.0
        )
        rows.append(YearRow(
            year=year, dt=d, dcr=sim.dcr[k], avg_loan=avg_loan, avg_share_value=avg_share,
            spv_pd_covenant=pd_cov, spv_pd=spv_pd, spv_pd_no_covenant=spv_pd_no_cov,
            issuer_default_rate=issuer_rate, issuer_lgd=issuer_lgd, spv_lgd=spv_lgd,
            covenant_effectiveness=eff, combined_pd=combined_pd, combined_lgd=combined_lgd,
        ))
    return rows


def results_block(rows: list[YearRow], inp: EngineInputs) -> ResultsBlock:
    p = inp.years_total
    years = [r.year for r in rows]
    loan = [r.avg_loan for r in rows]
    spv_pd = [r.spv_pd for r in rows]
    pd_cov = [r.spv_pd_covenant for r in rows]
    issuer_pd = [r.issuer_default_rate for r in rows]
    spv_lgd = [r.spv_lgd for r in rows]
    issuer_lgd = [r.issuer_lgd for r in rows]
    one = [1.0] * len(rows)

    pd_client_avg = conditional_average(p, years, spv_pd)                                   # J21
    pd_client_w = weighted_average(p, years, loan, spv_pd, one, loan, one, one)             # J22
    pd_issuer_avg = conditional_average(p, years, issuer_pd)                                # J23
    pd_issuer_w = weighted_average(p, years, loan, issuer_pd, one, loan, one, one)          # J24
    pd_total = pd_client_w + pd_issuer_w                                                    # J25
    lgd_client_avg = conditional_average(p, years, spv_lgd)                                 # J26
    lgd_client_w = weighted_average(p, years, loan, pd_cov, spv_lgd, loan, pd_cov, one)     # J27
    lgd_issuer_avg = conditional_average(p, years, issuer_lgd)                              # J28
    lgd_issuer_w = weighted_average(p, years, loan, issuer_pd, issuer_lgd, loan, issuer_pd, one)  # J29
    lgd_total = (pd_client_w / pd_total * lgd_client_w + pd_issuer_w / pd_total * lgd_issuer_w
                 if pd_total else 0.0)                                                       # J30
    el = lgd_total * pd_total                                                               # J31
    try:
        rwa = basel_ii_cap_corp(pd_total, lgd_total, min(p, 5.0))                          # J33
    except ValueError:
        rwa = 0.0
    return ResultsBlock(
        pd_client_avg=pd_client_avg, pd_client_weighted=pd_client_w,
        pd_client_grade=grades.grade_for(pd_client_w),
        pd_issuer_avg=pd_issuer_avg, pd_issuer_weighted=pd_issuer_w,
        pd_issuer_grade=grades.grade_for(pd_issuer_w),
        pd_total=pd_total, lgd_client_avg=lgd_client_avg, lgd_client_weighted=lgd_client_w,
        lgd_issuer_avg=lgd_issuer_avg, lgd_issuer_weighted=lgd_issuer_w, lgd_total=lgd_total,
        el=el, risk_grade=grades.grade_for(pd_total), rwa_pct=rwa,
    )

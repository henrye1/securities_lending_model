"""Engine behaviour the golden case cannot discriminate: short maturities,
amortising structures, custom draws (no quirks), approach-2 warning and the
zero-covenant-trigger ruling."""
from __future__ import annotations

import math
import random
from dataclasses import replace

import pytest

from app.domain.aggregate import conditional_average, weighted_average
from app.domain.engine import APPROACH_2_WARNING, run_engine
from app.domain.simulation import lgd_estimation, simulate, year_grid
from tests.domain.test_engine_parity import excelcior_inputs


def _draws(seed: int, n: int = 10000) -> list[list[float]]:
    rng = random.Random(seed)
    return [[rng.random() for _ in range(10)] for _ in range(n)]


def test_short_maturity_years():
    inp = replace(excelcior_inputs(), years_total=2.5)
    years, dt = year_grid(2.5)
    assert years == [1, 2, 2.5, 2.5, 2.5, 2.5, 2.5, 2.5, 2.5, 2.5]
    assert dt == [1, 1, 0.5, 0, 0, 0, 0, 0, 0, 0]
    res = run_engine(inp)
    assert all(r.avg_loan == 0 for r in res.years[3:])
    assert all(r.covenant_effectiveness == 0 for r in res.years[3:])
    # CInt(2.5) = 2 -> the Results block averages years 1..2 only
    assert res.results.pd_client_avg == pytest.approx(
        (res.years[0].spv_pd + res.years[1].spv_pd) / 2
    )


def test_conditional_average_uses_vba_integer_bound():
    years = [1, 2, 2.6, 2.6, 2.6, 2.6, 2.6, 2.6, 2.6, 2.6]
    values = [10, 20, 30, 40, 50, 60, 70, 80, 90, 100]
    assert conditional_average(2.6, years, values) == pytest.approx(20)      # CInt(2.6) = 3
    assert conditional_average(2.4, years, values) == pytest.approx(15)      # CInt(2.4) = 2
    one = [1.0] * 10
    assert weighted_average(2.6, years, values, one, one, one, one, one) == pytest.approx(60 / 3)
    assert weighted_average(2.6, years, values, one, one, [0.0] * 10, one, one) == 0.0


def test_structure_rules():
    base = excelcior_inputs()
    inp = replace(
        base, structure="Straight Amortisation", amortised_amount=50_000_000.0,
        bullet_amount=0.0, bullet_rate=0.0, rate_schedule=[(0.0, 0.10)],
        draws=_draws(1, n=50),
    )
    sim = simulate(inp, inp.draws, apply_quirks=False)
    divs = base.share_value * base.dividend_yield * base.dividends_repaid
    for p in range(50):
        if sim.stock[0][p] > 0:
            assert sim.loan[0][p] == pytest.approx(max(50_000_000 * 1.10 - divs, 0))
            break
    else:
        pytest.fail("no positive stock path")
    io = replace(inp, structure="Interest Only Repayments")
    sim_io = simulate(io, io.draws, apply_quirks=False)
    assert all(v >= 50_000_000 for v in sim_io.loan[0])
    bullet = replace(inp, structure="Bullet Payment", bullet_amount=50_000_000.0, bullet_rate=0.10,
                     amortised_amount=0.0)
    sim_b = simulate(bullet, bullet.draws, apply_quirks=False)
    assert all(v == pytest.approx(55_000_000) for v in sim_b.loan[0])


def test_custom_seed_disables_quirks():
    inp = replace(excelcior_inputs(), draws=_draws(7, n=200))
    res = run_engine(inp)
    assert res.derived["workbook_draws"] is False and res.derived["quirks_applied"] is False
    sim = simulate(inp, inp.draws, apply_quirks=False)
    # path 0 year 1: clean formula (bullet -> stock post divs == stock pre divs)
    assert sim.stock[0][0] == pytest.approx(inp.share_value * math.exp(sim.change[0][0]))
    assert sim.survival_covenant[0][7] == (1 if sim.cover[0][7] > 1.75 else 0)


def test_workbook_draws_apply_quirks():
    res = run_engine(excelcior_inputs())
    assert res.derived["quirks_applied"] is True
    # Q2 (row 14 forced breach) lifts the year-1 breach rate from 0.1886 to 0.1887
    assert res.years[0].spv_pd_covenant == pytest.approx(0.1887)


def test_approach_2_warning():
    res = run_engine(replace(excelcior_inputs(), approach=2, draws=_draws(3, n=100)))
    assert APPROACH_2_WARNING in res.warnings
    # covenant-breach paths get approach 2 -> 0; SPV-default paths still use approach 3
    assert lgd_estimation(2, 100.0, 50.0, 0.3) == 0.0
    assert lgd_estimation(3, 100.0, 50.0, 0.3) == pytest.approx(0.65)
    assert lgd_estimation(1, 100.0, 50.0, 0.3) == pytest.approx(0.5)


def test_zero_covenant_triggers_warn_instead_of_error():
    # 10x cover, DCR 1.1 -> no path breaches in year 1
    inp = replace(excelcior_inputs(), share_value=750_000_000.0, dcr_schedule=[(0.0, 1.1)],
                  draws=_draws(5, n=500))
    res = run_engine(inp)
    assert any("Year 1: no covenant breaches" in w for w in res.warnings)
    assert res.years[0].covenant_effectiveness == 0 and res.years[0].spv_lgd == 0
    assert res.years[0].spv_pd == inp.min_pd

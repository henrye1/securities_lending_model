import pytest

from app.domain import reference


def test_masterscale_and_rates():
    ms = reference.pd_masterscale()
    assert ms[0] == {"grade": "SB01", "fitted_pd": 0.0001, "lower": 0, "upper": 0.00012}
    assert ms[10]["grade"] == "SB11" and ms[10]["fitted_pd"] == 0.0032
    assert len(ms) == 28
    assert reference.issuer_default_rates()["SB11"] == [0.003201, 0.003594, 0.004014, 0.004449, 0.004888]


def test_countries_and_sectors():
    sa = reference.country("South Africa")
    assert sa["insolvency_score"] == pytest.approx(1.843243243243243)
    assert sa["recovery_cost"] == 0.02 and sa["risk_free_rate"] == 0.07
    assert len(reference.countries()) == 179
    assert reference.sectors()[14] == "RETAIL_AND_CONSUMER"
    assert reference.revenue_sizes() == ["Revenue <= R500m", "Revenue > R500m"]
    vm = reference.volatilities_multiples()["RETAIL_AND_CONSUMER Revenue > R500m"]
    assert vm["earnings_multiple"] == pytest.approx(10.148333)


def test_random_numbers_and_simulation():
    rn = reference.random_numbers()
    assert len(rn) == 10000 and len(rn[0]) == 10
    assert rn[0][0] == pytest.approx(0.416181313970851)
    sim = reference.simulation()
    assert len(sim["distribution"]) == 10000 and len(sim["performing_book"]) == 1126


def test_capture_lists():
    lists = reference.capture_lists()
    assert lists["structures"][0] == "Bullet Payment" and len(lists["grades"]) == 25
    assert lists["recovery_policies"][1] == "Orderly Liquidation (Wind-up)"
    assert lists["min_pd"] == 0.0003 and lists["trading_days"] == 251

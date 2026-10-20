import json
from pathlib import Path

import pytest

from app.domain.portfolio import PortfolioInput, StockInput, combine

FIXTURE = json.loads(
    (Path(__file__).resolve().parents[1] / "fixtures" / "golden_excelcior.json").read_text(encoding="utf-8")
)


def _identity(n: int = 10):
    return [[1.0 if i == j else 0.0 for j in range(n)] for i in range(n)]


def _zeros(n: int = 10):
    return [[0.0] * n for _ in range(n)]


def test_portfolio_four_stocks_matches_workbook():
    sheet = FIXTURE["portfolio_sheet"]
    stocks = [StockInput(**s) for s in sheet["stocks"]]
    p = PortfolioInput(
        stocks=stocks,
        equity_correlation=sheet["equity_correlation"],
        currency_correlation=_identity(),
        currency_equity_correlation=_zeros(),
    )
    c = combine(p)
    exp = sheet["combined"]
    for key in (
        "number_of_shares", "share_price", "stock_volatility", "dividend_yield",
        "average_daily_volume", "time_to_unwind", "unlisted_haircut", "illiquid_haircut",
        "risk_free_rate",
    ):
        assert getattr(c, key) == pytest.approx(exp[key], rel=1e-9), key
    assert c.equity_lgd is None
    assert len(c.stock_values) == 10 and c.stock_values[0] == pytest.approx(13910060 * 85)


def test_single_stock_volatility_is_its_own():
    p = PortfolioInput(
        stocks=[StockInput(name="A", number_of_shares=100, share_price=2, volatility=0.3)],
        equity_correlation=_identity(),
        currency_correlation=_identity(),
        currency_equity_correlation=_zeros(),
    )
    c = combine(p)
    assert c.stock_volatility == pytest.approx(0.3) and c.share_price == 2 and c.number_of_shares == 100


def test_empty_portfolio_is_all_zero():
    c = combine(PortfolioInput(stocks=[], equity_correlation=_identity(),
                               currency_correlation=_identity(), currency_equity_correlation=_zeros()))
    assert c.number_of_shares == 0 and c.share_price == 0 and c.stock_volatility == 0

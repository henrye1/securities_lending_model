"""Parity of the VBA Corporate_LGD_Final_Collateral_Metric port on the four
stocks cached in the workbook's Portfolio Transactions sheet (D47:G47, E93)."""
import json
from pathlib import Path

import pytest

from app.domain.corporate_lgd import equity_lgd_for_stock, excel_percentile_inc
from app.domain.portfolio import PortfolioInput, StockInput, combine

FIXTURE = json.loads(
    (Path(__file__).resolve().parents[1] / "fixtures" / "golden_excelcior.json").read_text(encoding="utf-8")
)


def test_excel_percentile_inc():
    assert excel_percentile_inc([1, 2, 3, 4], 0.5) == 2.5
    assert excel_percentile_inc([3, 1, 2], 0.0) == 1 and excel_percentile_inc([3, 1, 2], 1.0) == 3


def test_equity_lgd_per_stock_matches_workbook():
    sheet = FIXTURE["portfolio_sheet"]
    got = [equity_lgd_for_stock(StockInput(**s)) for s in sheet["stocks"]]
    assert got == pytest.approx(sheet["equity_lgd_per_stock"], rel=1e-6)


def test_combined_equity_lgd_matches_workbook():
    sheet = FIXTURE["portfolio_sheet"]
    p = PortfolioInput(stocks=[StockInput(**s) for s in sheet["stocks"]],
                       equity_correlation=sheet["equity_correlation"])
    assert combine(p).equity_lgd == pytest.approx(sheet["combined"]["equity_lgd"], rel=1e-6)


def test_equity_lgd_is_none_without_financials():
    assert equity_lgd_for_stock(StockInput(name="x", risk_grade="SB10", country="South Africa")) is None

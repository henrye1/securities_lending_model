"""Portfolio Transactions sheet: per-stock inputs (D9:M51) and the combined
outputs block (E84:E93) that feeds the engine in portfolio mode."""
from __future__ import annotations

import math
from dataclasses import dataclass, field

from app.domain import reference

MAX_STOCKS = 10


@dataclass
class StockInput:
    name: str = ""
    number_of_shares: float = 0.0
    share_price: float = 0.0
    volatility: float = 0.0
    dividend_yield: float = 0.0
    average_daily_volume: float = 0.0
    country: str = ""
    risk_grade: str = ""
    revenue_size: str = ""
    sector: str = ""
    ebitda: float = 0.0
    market_cap: float = 0.0
    total_liabilities: float = 0.0
    time_to_unwind: float = 0.0
    unlisted_haircut: float = 0.0
    illiquid_haircut: float = 0.0
    currency_pair: str = ""
    currency_volatility: float = 0.0


def identity(n: int = MAX_STOCKS) -> list[list[float]]:
    return [[1.0 if i == j else 0.0 for j in range(n)] for i in range(n)]


def zeros(n: int = MAX_STOCKS) -> list[list[float]]:
    return [[0.0] * n for _ in range(n)]


@dataclass
class PortfolioInput:
    stocks: list[StockInput] = field(default_factory=list)
    equity_correlation: list[list[float]] = field(default_factory=identity)       # D20:M29
    currency_correlation: list[list[float]] = field(default_factory=identity)     # D56:M65
    currency_equity_correlation: list[list[float]] = field(default_factory=zeros)  # D69:M78 (pair x stock)


@dataclass
class PortfolioCombined:
    number_of_shares: float
    share_price: float
    stock_volatility: float
    dividend_yield: float
    average_daily_volume: float
    time_to_unwind: float
    unlisted_haircut: float
    illiquid_haircut: float
    risk_free_rate: float
    equity_lgd: float | None
    stock_values: list[float]
    weights: list[float]


def _pad(stocks: list[StockInput]) -> list[StockInput]:
    if len(stocks) > MAX_STOCKS:
        raise ValueError(f"At most {MAX_STOCKS} stocks are supported")
    return list(stocks) + [StockInput() for _ in range(MAX_STOCKS - len(stocks))]


def _cell(m: list[list[float]], i: int, j: int) -> float:
    try:
        v = m[i][j]
    except IndexError:
        return 0.0
    return 0.0 if v is None else float(v)


def combine(p: PortfolioInput) -> PortfolioCombined:
    stocks = _pad(p.stocks)
    values = [s.number_of_shares * s.share_price for s in stocks]          # row 12
    total = sum(values)
    shares = sum(s.number_of_shares for s in stocks)                         # E84

    def weighted(attr: str) -> float:  # SUMPRODUCT(row, values) / SUM(values)
        return sum(getattr(s, attr) * v for s, v in zip(stocks, values)) / total if total else 0.0

    # Row 14 / row 52: value weight x volatility, for equities then currency pairs
    w_eq = [(v / total) * s.volatility if total else 0.0 for s, v in zip(stocks, values)]
    w_fx = [(v / total) * s.currency_volatility if total else 0.0 for s, v in zip(stocks, values)]
    w = w_eq + w_fx

    # 20x20 block matrix D161:W180 - [[C_eq, C_fxeq^T], [C_fxeq, C_fx]] with the
    # currency x equity block floored at 0 (rows 171-180 use MAX(0, .)).
    n = MAX_STOCKS
    big = [[0.0] * (2 * n) for _ in range(2 * n)]
    for i in range(n):
        for j in range(n):
            big[i][j] = _cell(p.equity_correlation, i, j)
            big[n + i][n + j] = _cell(p.currency_correlation, i, j)
            fx_eq = max(0.0, _cell(p.currency_equity_correlation, i, j))  # pair i x stock j
            big[n + i][j] = fx_eq
            big[j][n + i] = fx_eq
    var = sum(w[i] * big[i][j] * w[j] for i in range(2 * n) for j in range(2 * n))
    vol = math.sqrt(var) if var > 0 else 0.0

    def rf(s: StockInput) -> float:  # IFERROR(VLOOKUP(country, table_1, 4), "") -> 0 in SUMPRODUCT
        c = reference.country(s.country) if s.country else None
        return float(c["risk_free_rate"]) if c and c.get("risk_free_rate") is not None else 0.0

    # E93 = SUMPRODUCT(D47:M47, values) / SUM(values); a blank (errored) D47 counts as 0.
    from app.domain.corporate_lgd import equity_lgd_for_stock  # local import: avoids a cycle

    per_stock = [equity_lgd_for_stock(s) if v > 0 else None for s, v in zip(stocks, values)]
    equity_lgd = (
        sum((lgd or 0.0) * v for lgd, v in zip(per_stock, values)) / total
        if total and any(lgd is not None for lgd in per_stock)
        else None
    )

    return PortfolioCombined(
        number_of_shares=shares,
        share_price=total / shares if shares else 0.0,
        stock_volatility=vol,
        dividend_yield=weighted("dividend_yield"),
        average_daily_volume=weighted("average_daily_volume"),
        time_to_unwind=weighted("time_to_unwind"),
        unlisted_haircut=weighted("unlisted_haircut"),
        illiquid_haircut=weighted("illiquid_haircut"),
        risk_free_rate=sum(rf(s) * v for s, v in zip(stocks, values)) / total if total else 0.0,
        equity_lgd=equity_lgd,
        stock_values=values,
        weights=[v / total if total else 0.0 for v in values],
    )

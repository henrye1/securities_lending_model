"""VBA Equity_Duration and the Calculations!E44 liquidity flag."""
from __future__ import annotations

from app.domain.mathx import vba_cint


def equity_duration(
    number_of_shares: float,
    average_daily_volume: float,
    pct: float = 0.25,
    trading_days: int = 251,
) -> float:
    """Years to sell all shares at `pct` of average daily volume, assuming
    equal daily sales: the VBA loop's volume-weighted mean day index / 251.
    The loop bound (shares / volume / pct) is coerced to Integer (CInt)."""
    if number_of_shares <= 0 or average_daily_volume <= 0 or pct <= 0:
        return 0.0
    n = vba_cint((number_of_shares / average_daily_volume) / pct)
    if n <= 0:
        return 0.0
    return ((n + 1) / 2) / trading_days


def liquidity_flag(listing: str, number_of_shares: float, average_daily_volume: float) -> str:
    """Calculations!E44: blank for Unlisted; Illiquid if shares/40 > 25% of ADTV."""
    if listing == "Unlisted":
        return ""
    return "Illiquid" if number_of_shares / 40 > average_daily_volume * 0.25 else "Liquid"

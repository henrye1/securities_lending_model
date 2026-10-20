"""Excel/VBA-compatible numeric helpers shared by the engine. Pure stdlib."""
from __future__ import annotations

from datetime import date
from statistics import NormalDist
from typing import Sequence, TypeVar

T = TypeVar("T")
_N = NormalDist()


def norm_ppf(p: float) -> float:
    """Inverse standard normal CDF (Excel NORMSINV) for 0 < p < 1."""
    if not 0.0 < p < 1.0:
        raise ValueError(f"norm_ppf requires 0 < p < 1, got {p}")
    return _N.inv_cdf(p)


def norm_cdf(x: float) -> float:
    """Standard normal CDF (Excel NORMSDIST)."""
    return _N.cdf(x)


def yearfrac_30_360_us(start: date, end: date) -> float:
    """Excel YEARFRAC(start, end, 0): US (NASD) 30/360 day count."""
    d1, d2 = start.day, end.day
    if d1 == 31:
        d1 = 30
    if d2 == 31 and d1 >= 30:
        d2 = 30
    days = (end.year - start.year) * 360 + (end.month - start.month) * 30 + (d2 - d1)
    return days / 360


def excel_lookup(value: float, bounds: Sequence[float], results: Sequence[T]) -> T:
    """Excel LOOKUP(value, bounds, results): result of the largest bound <= value.

    Leniency: a value below the first bound returns results[0] (Excel would
    return #N/A); the engine never relies on that error.
    """
    chosen = 0
    for i, b in enumerate(bounds):
        if b <= value:
            chosen = i
        else:
            break
    return results[chosen]


def vba_cint(x: float) -> int:
    """VBA CInt / Integer coercion: round half to even."""
    return int(round(x))


def safe_divide(num: float, denom: float, default: float = 0.0) -> float:
    return num / denom if denom else default

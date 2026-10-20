"""PD master scale lookups (Constants P3:S30) and the issuer default-rate
table (Random Numbers P2:U26)."""
from __future__ import annotations

from app.domain import reference
from app.domain.mathx import excel_lookup


def grade_for(pd: float) -> str:
    """Excel LOOKUP(pd, Constants!R3:S30, Constants!P3:P30)."""
    scale = reference.pd_masterscale()
    return excel_lookup(pd, [r["lower"] for r in scale], [r["grade"] for r in scale])


def fitted_pd(grade: str) -> float:
    """VLOOKUP(grade, Constants!P3:Q30, 2, FALSE)."""
    for r in reference.pd_masterscale():
        if r["grade"] == grade:
            return float(r["fitted_pd"])
    raise ValueError(f"Unknown risk grade '{grade}'")


def issuer_default_rate(grade: str, year: float) -> float:
    """VLOOKUP(grade, 'Random Numbers'!P2:U26, MIN(year+1, 5), FALSE): the
    workbook's column pattern is pd1, pd2, pd3, pd4, pd4, pd4 ..."""
    rates = reference.issuer_default_rates().get(grade)
    if rates is None:
        raise ValueError(f"Unknown risk grade '{grade}'")
    col = min(int(year) + 1, 5)  # 1-based column within P:U, column 2 = pd1
    return float(rates[col - 2])

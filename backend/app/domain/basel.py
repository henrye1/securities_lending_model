"""VBA Basel_II_Cap_Corp - Basel II corporate IRB capital requirement x 12.5."""
from __future__ import annotations

import math

from app.domain.mathx import norm_cdf, norm_ppf


def basel_ii_cap_corp(pd: float, lgd: float, maturity: float, alpha: float = 0.99) -> float:
    if not 0.0 < pd < 1.0:
        raise ValueError(f"PD must be in (0, 1) for the Basel formula, got {pd}")
    w = (1 - math.exp(-50 * pd)) / (1 - math.exp(-50))
    correlation = 0.12 * w + 0.24 * (1 - w)
    b = (0.11852 - 0.05478 * math.log(pd)) ** 2
    z = norm_cdf(
        (1 - correlation) ** -0.5 * norm_ppf(pd)
        + (correlation / (1 - correlation)) ** 0.5 * norm_ppf(alpha)
    )
    k = (lgd * z - pd * lgd) * (1 - 1.5 * b) ** -1 * (1 + (maturity - 2.5) * b)
    return k * 12.5

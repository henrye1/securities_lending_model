from datetime import date

import pytest

from app.domain.mathx import excel_lookup, norm_cdf, norm_ppf, safe_divide, vba_cint, yearfrac_30_360_us


def test_yearfrac_excelcior():
    assert yearfrac_30_360_us(date(2015, 5, 31), date(2025, 5, 31)) == 10.0


def test_yearfrac_partial():
    assert yearfrac_30_360_us(date(2024, 1, 15), date(2026, 7, 15)) == pytest.approx(2.5)


def test_yearfrac_month_end_rule():
    # US (NASD) 30/360: 31st start -> 30th; end 31st -> 30th only if start >= 30th
    assert yearfrac_30_360_us(date(2024, 1, 31), date(2024, 3, 31)) == pytest.approx(60 / 360)
    assert yearfrac_30_360_us(date(2024, 1, 30), date(2024, 2, 29)) == pytest.approx(29 / 360)


def test_norm_ppf_matches_excel():
    assert norm_ppf(0.416181313970851) == pytest.approx(-0.21168, abs=1e-4)
    assert norm_cdf(norm_ppf(0.3)) == pytest.approx(0.3, rel=1e-12)


def test_excel_lookup():
    assert excel_lookup(2.0, [0, 1.5, 3], ["a", "b", "c"]) == "b"
    assert excel_lookup(3.0, [0, 1.5, 3], ["a", "b", "c"]) == "c"


def test_excel_lookup_below_first_bound():
    assert excel_lookup(-1, [0, 1], ["a", "b"]) == "a"


def test_vba_cint():
    assert vba_cint(2285.71) == 2286
    assert vba_cint(2.5) == 2
    assert vba_cint(3.5) == 4


def test_safe_divide():
    assert safe_divide(1, 0) == 0.0 and safe_divide(1, 4) == 0.25

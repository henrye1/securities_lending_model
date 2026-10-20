import pytest

from app.domain.duration import equity_duration, liquidity_flag


def test_equity_duration_excelcior():
    assert equity_duration(428571428.5714286, 750000) == pytest.approx(4.555776892430279, rel=1e-12)


def test_equity_duration_zero_volume():
    assert equity_duration(100, 0) == 0.0
    assert equity_duration(0, 100) == 0.0


def test_liquidity():
    assert liquidity_flag("Listed", 428571428.57, 750000) == "Illiquid"
    assert liquidity_flag("Listed", 1000, 750000) == "Liquid"
    assert liquidity_flag("Unlisted", 1, 1) == ""

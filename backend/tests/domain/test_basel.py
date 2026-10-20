import pytest

from app.domain.basel import basel_ii_cap_corp


def test_basel_combined():
    assert basel_ii_cap_corp(0.052780683384851604, 0.3609173067445691, 5) == pytest.approx(
        0.9020337553547401, rel=1e-9
    )


def test_basel_client_uncapped_maturity():
    assert basel_ii_cap_corp(0.048518112156255844, 0.325886659717944, 10) == pytest.approx(
        1.0531192083116148, rel=1e-9
    )


def test_basel_rejects_degenerate_pd():
    with pytest.raises(ValueError):
        basel_ii_cap_corp(0.0, 0.5, 5)

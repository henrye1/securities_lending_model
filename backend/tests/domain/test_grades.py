import pytest

from app.domain.grades import fitted_pd, grade_for, issuer_default_rate


def test_grade_lookup():
    assert grade_for(0.052780683384851604) == "SB19"
    assert grade_for(0.004262571228595757) == "SB12"
    assert grade_for(0.0) == "SB01"
    assert grade_for(0.00012) == "SB02"
    assert grade_for(0.9999999999) == "D1"


def test_fitted_pd():
    assert fitted_pd("SB11") == 0.0032


def test_fitted_pd_unknown_grade():
    with pytest.raises(ValueError):
        fitted_pd("SB99")


def test_issuer_default_rate_columns():
    assert [issuer_default_rate("SB11", y) for y in (1, 2, 3, 4, 5, 10)] == [
        0.003201, 0.003594, 0.004014, 0.004449, 0.004449, 0.004449,
    ]

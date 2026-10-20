"""Second golden case: the TADVEST transaction (9-year bullet, DCR 1.0, no
dividends, 1.2x cover, Mauritius). Fixture generated from the workbook after a
full Excel recalculation (the file as supplied was saved in manual calculation
mode with a stale #VALUE! in Calculations!BA5532)."""
from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path

import pytest

from app.domain.engine import run_engine
from app.schemas.models import TransactionCreate
from app.services.calc_service import to_engine_inputs

FIXTURE = json.loads(
    (Path(__file__).resolve().parents[1] / "fixtures" / "golden_tadvest.json").read_text(encoding="utf-8")
)
REL, ABS = 1e-9, 1e-12


@pytest.fixture(scope="module")
def result():
    inp, derived, _ = to_engine_inputs(TransactionCreate(**FIXTURE["inputs"]))
    assert derived["unwind_years"] == pytest.approx(FIXTURE["input_derived"]["unwind_years"], rel=1e-12)
    return run_engine(inp)


@pytest.mark.parametrize("name", [
    "years", "dt", "dcr", "avg_loan", "avg_share_value", "spv_pd_covenant", "spv_pd",
    "spv_pd_no_covenant", "issuer_default_rate", "issuer_lgd", "spv_lgd",
    "covenant_effectiveness", "combined_pd", "combined_lgd",
])
def test_year_series_match_workbook(result, name):
    key = "year" if name == "years" else name
    got = [getattr(r, key) for r in result.years]
    for g, expected in zip(got, FIXTURE["calculations"][name]):
        if isinstance(expected, str):
            # Workbook #VALUE! (VBA divides by zero when a year has no covenant
            # transitions, e.g. after maturity); the app's ruling returns 0.
            assert g == 0.0, name
        else:
            assert g == pytest.approx(expected, rel=REL, abs=ABS), name


def test_results_and_report_match_workbook(result):
    for key, value in FIXTURE["calculations"]["results"].items():
        got = asdict(result.results)[key]
        assert got == value if isinstance(value, str) else got == pytest.approx(value, rel=REL), key
    for column in ("reference", "client", "combined"):
        for key, value in FIXTURE["report"][column].items():
            got = asdict(result.report[column])[key]
            assert got == value if isinstance(value, str) else got == pytest.approx(value, rel=REL), (column, key)

"""Export the workbook's hidden reference sheets to backend/app/data/reference/*.json.

Usage: python scripts/export_reference.py ["<path to .xlsm>"]
Never hand-edit the generated files - rerun this script instead.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import openpyxl

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_XLSM = ROOT / "Equity Finance Model Final V1.5 (Henry Adjusted)v1.2.xlsm"
OUT = ROOT / "backend" / "app" / "data" / "reference"

CAPTURE_LISTS = {
    "structures": [
        "Bullet Payment",
        "Straight Amortisation",
        "Interest Only Repayments",
        "Straight Amortisation & Bullet",
    ],
    "yes_no": ["Yes", "No"],
    "listings": ["Listed", "Unlisted"],
    "dividend_options": ["100%", "Custom"],
    "recovery_policies": [
        "Economic Value (Going Concern)",
        "Orderly Liquidation (Wind-up)",
        "Distressed Liquidation (Fire Sale)",
    ],
    "grades": [f"SB{i:02d}" for i in range(1, 26)],
    "revenue_sizes": ["Revenue <= R500m", "Revenue > R500m"],
    "min_pd": 0.0003,
    "lgd_floor": 1e-7,
    "trading_days": 251,
    "unwind_pct": 0.25,
}


def dump(name: str, data) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / f"{name}.json").write_text(json.dumps(data, indent=None if name in ("random_numbers", "simulation") else 1), encoding="utf-8")
    print(f"wrote {name}.json")


def main(path: Path) -> None:
    wb = openpyxl.load_workbook(path, data_only=True, read_only=True)
    const = wb["Constants"]
    rn = wb["Random Numbers"]
    sim = wb["Simulation"]
    sheet3 = wb["Sheet3"]
    buckets = wb["LGD Buckets"]

    # PD master scale P3:S30
    ms = []
    for row in const.iter_rows(min_row=3, max_row=30, min_col=16, max_col=19, values_only=True):
        if row[0] is None:
            continue
        ms.append({"grade": row[0], "fitted_pd": row[1], "lower": row[2], "upper": row[3]})
    dump("pd_masterscale", ms)

    # Issuer default rates (Random Numbers P2:U26)
    rates = {}
    for row in rn.iter_rows(min_row=2, max_row=26, min_col=16, max_col=21, values_only=True):
        if row[0]:
            rates[row[0]] = list(row[1:6])
    dump("issuer_default_rates", rates)

    # Countries A3:E181
    countries = []
    for row in const.iter_rows(min_row=3, max_row=181, min_col=1, max_col=5, values_only=True):
        if row[0] is None:
            continue
        countries.append(
            {
                "name": row[0],
                "insolvency_score": row[1],
                "recovery_cost": row[2],
                "risk_free_rate": row[3],
                "africa_adjust": row[4],
            }
        )
    dump("countries", countries)

    # Sectors U2:U17 (trailing whitespace stripped)
    sectors = [r[0].strip() for r in const.iter_rows(min_row=2, max_row=17, min_col=21, max_col=21, values_only=True) if r[0]]
    dump("sectors", sectors)

    # Volatilities & multiples AT2:AV33 - keys kept EXACTLY as in the sheet
    vm = {}
    for row in const.iter_rows(min_row=2, max_row=40, min_col=46, max_col=48, values_only=True):
        if row[0] and row[1] is not None:
            vm[row[0]] = {"asset_vol": row[1], "earnings_multiple": row[2]}
    dump("volatilities_multiples", vm)

    # Sector correlations Sheet3 A3:Q18
    names, matrix = [], []
    for row in sheet3.iter_rows(min_row=3, max_row=18, min_col=1, max_col=17, values_only=True):
        if row[0] is None:
            continue
        names.append(row[0].strip())
        matrix.append(list(row[1:17]))
    dump("sector_correlations", {"names": names, "matrix": matrix})

    # LGD buckets B4:F12
    lb = []
    for row in buckets.iter_rows(min_row=4, max_row=12, min_col=2, max_col=6, values_only=True):
        lb.append({"bucket": row[0], "lower": row[1], "upper": row[2], "label": row[3], "fitted": row[4]})
    dump("lgd_buckets", lb)

    # Random numbers A1:J10000
    draws = [list(r) for r in rn.iter_rows(min_row=1, max_row=10000, min_col=1, max_col=10, values_only=True)]
    assert all(v is not None for r in draws for v in r), "blank random draw"
    dump("random_numbers", draws)

    # Simulation A2:A10001 and C2:D1127
    dist = [r[0] for r in sim.iter_rows(min_row=2, max_row=10001, min_col=1, max_col=1, values_only=True)]
    pb = [list(r) for r in sim.iter_rows(min_row=2, max_row=1127, min_col=3, max_col=4, values_only=True)]
    dump("simulation", {"distribution": dist, "performing_book": pb})

    dump("capture_lists", CAPTURE_LISTS)


if __name__ == "__main__":
    main(Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_XLSM)

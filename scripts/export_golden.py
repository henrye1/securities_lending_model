"""Export the workbook's cached (Excel-calculated) values for the Excelcior
Shipping example into backend/tests/fixtures/golden_excelcior.json.

Usage: python scripts/export_golden.py ["<path to .xlsm>" ["<output .json>"]]
The fixture is the parity oracle for the engine tests - never hand-edit.
"""
from __future__ import annotations

import json
import sys
from datetime import date, datetime
from pathlib import Path

import openpyxl

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_XLSM = ROOT / "Equity Finance Model Final V1.5 (Henry Adjusted)v1.2.xlsm"
OUT = ROOT / "backend" / "tests" / "fixtures" / "golden_excelcior.json"

YEAR_COLS = "IJKLMNOPQR"


def _row(ws, r: int) -> list:
    return [ws[f"{c}{r}"].value for c in YEAR_COLS]


def _d(v) -> str:
    if isinstance(v, datetime):
        return v.date().isoformat()
    if isinstance(v, date):
        return v.isoformat()
    return v


def _na(v):
    return None if v == "Not Applicable" else v


def main(path: Path, out: Path = OUT) -> None:
    wb = openpyxl.load_workbook(path, data_only=True)
    inp = wb["Input"]
    calc = wb["Calculations"]
    prt = wb["Print Report & Results"]
    pt = wb["Portfolio Transactions"]

    inputs = {
        "client_cif": str(inp["H10"].value),
        "client_name": inp["H12"].value,
        "client_country": inp["H14"].value,
        "portfolio_of_shares": inp["H16"].value == "Yes",
        "start_date": _d(inp["H19"].value),
        "maturity_date": _d(inp["H21"].value),
        "structure": inp["H23"].value,
        "amortised_loan_amount": _na(inp["H25"].value),
        "bullet_loan_amount": _na(inp["H27"].value),
        "number_of_shares": inp["H29"].value,
        "share_price": inp["H31"].value,
        "average_daily_volume": inp["H37"].value,
        "dcr_changes": inp["H39"].value == "Yes",
        "default_cover_ratio": inp["H43"].value,
        "dcr_schedule": [],
        "bullet_interest_rate": _na(inp["H48"].value),
        "rate_linked_to_cover": inp["H53"].value == "Yes",
        "amortised_interest_rate": None,
        "rate_schedule": [],
        "dividend_yield": inp["H62"].value,
        "dividends_repaid": inp["L64"].value,
        "stock_volatility": inp["H66"].value,
        "liabilities_ahead": inp["H71"].value,
        "liabilities_pari_passu": inp["H73"].value,
        "liabilities_subordinate": inp["H75"].value,
        "other_collateral": inp["H77"].value,
        "collateral_pari_passu": inp["H79"].value,
        "other_pari_passu_liabilities": inp["H81"].value,
        "reference_cif": "" if inp["H89"].value is None else str(inp["H89"].value),
        "reference_name": inp["H91"].value,
        "reference_country": inp["H93"].value,
        "listing": inp["H95"].value,
        "risk_grade": inp["H97"].value,
        "revenue_size": inp["H99"].value,
        "sectors": [{"sector": inp["H101"].value.strip(), "weight": 1.0}],
        "unlisted_haircut": inp["H108"].value,
        "illiquid_haircut": inp["H110"].value,
        "risk_free_rate": inp["H112"].value,
        "currency_mismatch": inp["H116"].value == "Yes",
        "currency_volatility": inp["H118"].value or 0,
        "currency_correlation": inp["H120"].value or 0,
        "recovery_approach": calc["E41"].value,
        "random_seed": None,
        "portfolio": None,
    }

    sample_cols = ("X", "Y", "AE", "AF", "AG", "AH", "AL", "AM", "AN", "AU", "AV", "BA")

    def samples(r: int) -> dict:
        return {c: calc[f"{c}{r}"].value for c in sample_cols}

    calculations = {
        "years": _row(calc, 6),
        "dt": _row(calc, 7),
        "dcr": _row(calc, 8),
        "avg_loan": _row(calc, 9),
        "avg_share_value": _row(calc, 10),
        "spv_pd_covenant": _row(calc, 11),
        "spv_pd": _row(calc, 12),
        "spv_pd_no_covenant": _row(calc, 13),
        "issuer_default_rate": _row(calc, 14),
        "issuer_lgd": _row(calc, 15),
        "spv_lgd": _row(calc, 16),
        "covenant_effectiveness": _row(calc, 17),
        "combined_pd": _row(calc, 57),
        "combined_lgd": _row(calc, 61),
        "results": {
            "pd_client_avg": calc["J21"].value,
            "pd_client_weighted": calc["J22"].value,
            "pd_issuer_avg": calc["J23"].value,
            "pd_issuer_weighted": calc["J24"].value,
            "pd_total": calc["J25"].value,
            "lgd_client_avg": calc["J26"].value,
            "lgd_client_weighted": calc["J27"].value,
            "lgd_issuer_avg": calc["J28"].value,
            "lgd_issuer_weighted": calc["J29"].value,
            "lgd_total": calc["J30"].value,
            "el": calc["J31"].value,
            "risk_grade": calc["I32"].value,
            "rwa_pct": calc["J33"].value,
        },
        "e21_volatility": calc["E21"].value,
        "e44_liquidity": calc["E44"].value,
        "e49_discount_factor": calc["E49"].value,
        "fsh": calc["AL4"].value,
        "path_samples": {"7": samples(7), "8": samples(8), "9": samples(9)},
    }

    def rep(col: str) -> dict:
        return {
            "pd": prt[f"{col}38"].value,
            "grade": prt[f"{col}39"].value,
            "lgd": prt[f"{col}40"].value,
            "el": prt[f"{col}41"].value,
            "el_grade": prt[f"{col}42"].value,
            "rwa_pct": prt[f"{col}43"].value,
        }

    report = {"reference": rep("D"), "client": rep("G"), "combined": rep("J")}

    stock_cols = "DEFGHIJKLM"
    stocks = []
    for c in stock_cols:
        if pt[f"{c}9"].value is None:
            continue
        stocks.append(
            {
                "name": pt[f"{c}9"].value,
                "number_of_shares": pt[f"{c}10"].value,
                "share_price": pt[f"{c}11"].value,
                "volatility": pt[f"{c}13"].value,
                "dividend_yield": pt[f"{c}15"].value,
                "average_daily_volume": pt[f"{c}16"].value or 0,
                "country": pt[f"{c}35"].value,
                "risk_grade": pt[f"{c}36"].value,
                "revenue_size": pt[f"{c}37"].value,
                "sector": pt[f"{c}38"].value.strip(),
                "ebitda": pt[f"{c}39"].value,
                "market_cap": pt[f"{c}40"].value,
                "total_liabilities": pt[f"{c}41"].value,
                "time_to_unwind": pt[f"{c}42"].value,
                "unlisted_haircut": pt[f"{c}43"].value,
                "illiquid_haircut": pt[f"{c}44"].value,
                "currency_pair": pt[f"{c}50"].value,
                "currency_volatility": pt[f"{c}51"].value or 0,
            }
        )
    eq_corr = [[pt[f"{c}{r}"].value for c in stock_cols] for r in range(20, 30)]
    portfolio_sheet = {
        "stocks": stocks,
        "equity_correlation": eq_corr,
        "combined": {
            "number_of_shares": pt["E84"].value,
            "share_price": pt["E85"].value,
            "stock_volatility": pt["E86"].value,
            "dividend_yield": pt["E87"].value,
            "average_daily_volume": pt["E88"].value,
            "time_to_unwind": pt["E89"].value,
            "unlisted_haircut": pt["E90"].value,
            "illiquid_haircut": pt["E91"].value,
            "risk_free_rate": pt["E92"].value,
            "equity_lgd": pt["E93"].value,
        },
        "equity_lgd_per_stock": [pt[f"{c}47"].value for c in stock_cols[: len(stocks)]],
    }

    fixture = {
        "name": inp["H12"].value,
        "inputs": inputs,
        "input_derived": {
            "unwind_years": inp["H84"].value,
            "unwind_days": inp["H87"].value,
            "share_value": inp["H33"].value,
            "initial_cover_ratio": inp["H35"].value,
        },
        "calculations": calculations,
        "report": report,
        "portfolio_sheet": portfolio_sheet,
    }
    fixture["source"] = path.name
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(fixture, indent=1), encoding="utf-8")
    print("wrote", out)
    print(
        "pd_total", calculations["results"]["pd_total"],
        "combined rwa", report["combined"]["rwa_pct"],
        "portfolio vol", portfolio_sheet["combined"]["stock_volatility"],
    )


if __name__ == "__main__":
    main(Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_XLSM,
         Path(sys.argv[2]) if len(sys.argv) > 2 else OUT)

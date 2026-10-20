"""Transaction payload (the Input / Portfolio pages) -> EngineInputs (the
Calculations sheet's column E) -> Run."""
from __future__ import annotations

import math
import random
from dataclasses import asdict

from app.domain import grades, reference
from app.domain.duration import equity_duration, liquidity_flag
from app.domain.engine import run_engine
from app.domain.models import EngineInputs, build_dcr_schedule
from app.domain.portfolio import PortfolioCombined, PortfolioInput, StockInput, combine
from app.repositories.store import Store, new_id, now
from app.schemas.models import Run, Transaction, TransactionCreate

N_PATHS = 10000
MAX_YEARS = 10.0
POLICY_BY_APPROACH = {
    1: "Economic Value (Going Concern)",
    2: "Orderly Liquidation (Wind-up)",
    3: "Distressed Liquidation (Fire Sale)",
}


def _yearfrac(tx: TransactionCreate) -> float:
    from app.domain.mathx import yearfrac_30_360_us

    return yearfrac_30_360_us(tx.start_date, tx.maturity_date)


def validation_errors(tx: TransactionCreate) -> list[str]:
    errors: list[str] = []
    if tx.maturity_date <= tx.start_date:
        errors.append("Maturity date must be after the start date")
    elif _yearfrac(tx) > MAX_YEARS:
        errors.append("Maturity must be within 10 years of the start date (the model's horizon)")
    amort = tx.amortised_loan_amount or 0.0
    bullet = tx.bullet_loan_amount or 0.0
    if tx.structure == "Bullet Payment" and bullet <= 0:
        errors.append("Bullet Loan Amount is required for a Bullet Payment structure")
    if tx.structure in ("Straight Amortisation", "Interest Only Repayments") and amort <= 0:
        errors.append("Amortised / Interest Only Loan Amount is required for this structure")
    if tx.structure == "Straight Amortisation & Bullet" and (amort <= 0 or bullet <= 0):
        errors.append("Both the amortised and the bullet loan amounts are required")
    if tx.portfolio_of_shares:
        if not tx.portfolio or not tx.portfolio.stocks:
            errors.append("Portfolio of Shares is Yes but no stocks were captured")
    else:
        if tx.number_of_shares <= 0 or tx.share_price <= 0:
            errors.append("Number of Shares and Share Price must be positive")
    if tx.risk_grade not in reference.issuer_default_rates():
        errors.append(f"Unknown risk grade '{tx.risk_grade}'")
    if reference.country(tx.reference_country) is None:
        errors.append(f"Unknown reference entity country '{tx.reference_country}'")
    if tx.default_cover_ratio <= 0:
        errors.append("Default Cover Ratio must be positive")
    if tx.stock_volatility <= 0 and not tx.portfolio_of_shares:
        errors.append("Stock Volatility must be positive")
    return errors


def _portfolio(tx: TransactionCreate) -> PortfolioCombined | None:
    if not (tx.portfolio_of_shares and tx.portfolio):
        return None
    p = PortfolioInput(
        stocks=[StockInput(**s.model_dump()) for s in tx.portfolio.stocks],
        equity_correlation=tx.portfolio.equity_correlation,
        currency_correlation=tx.portfolio.currency_correlation,
        currency_equity_correlation=tx.portfolio.currency_equity_correlation,
    )
    return combine(p)


def to_engine_inputs(tx: TransactionCreate) -> tuple[EngineInputs, dict, PortfolioCombined | None]:
    errors = validation_errors(tx)
    if errors:
        raise ValueError("; ".join(errors))

    years = _yearfrac(tx)                                                     # E10
    bullet_types = ("Bullet Payment", "Straight Amortisation & Bullet")
    amort = (tx.amortised_loan_amount or 0.0) if tx.structure != "Bullet Payment" else 0.0  # E11
    bullet = (tx.bullet_loan_amount or 0.0) if tx.structure in bullet_types else 0.0      # E12
    bullet_rate = (tx.bullet_interest_rate or 0.0) if tx.structure in bullet_types else 0.0  # E13

    port = _portfolio(tx)
    if port:  # Deviation D1: portfolio totals feed the engine
        shares, price = port.number_of_shares, port.share_price
        dividend_yield = port.dividend_yield
        equity_vol = port.stock_volatility
        volatility = port.stock_volatility                                    # E21 (portfolio)
        unwind_years = port.time_to_unwind                                    # E48
        adtv = port.average_daily_volume
    else:
        shares, price = tx.number_of_shares, tx.share_price
        dividend_yield = tx.dividend_yield
        equity_vol = tx.stock_volatility
        fx_vol = tx.currency_volatility if tx.currency_mismatch else 0.0
        fx_corr = tx.currency_correlation if tx.currency_mismatch else 0.0
        volatility = math.sqrt(
            equity_vol ** 2 + fx_vol ** 2 + 2 * equity_vol * fx_vol * max(0.0, fx_corr)
        )                                                                     # E21
        unwind_years = equity_duration(shares, tx.average_daily_volume)       # E48 (Input H84)
        adtv = tx.average_daily_volume
    share_value = shares * price                                              # E14

    country = reference.country(tx.reference_country) or {}
    rf = tx.risk_free_rate if tx.risk_free_rate is not None else float(country.get("risk_free_rate") or 0.0)

    changes = [(c.time, c.dcr) for c in tx.dcr_schedule] if tx.dcr_changes else []
    dcr_schedule = build_dcr_schedule(tx.default_cover_ratio, changes)
    base_rate = tx.amortised_interest_rate or 0.0                             # Deviation D2
    rate_schedule = [(0.0, base_rate)]
    if tx.rate_linked_to_cover:
        rate_schedule += sorted((b.lower_bound, b.rate) for b in tx.rate_schedule if b.lower_bound > 0)

    draws = None
    if tx.random_seed is not None:
        rng = random.Random(tx.random_seed)
        draws = [[rng.random() for _ in range(10)] for _ in range(N_PATHS)]

    inp = EngineInputs(
        years_total=years,
        amortised_amount=amort,
        bullet_amount=bullet,
        bullet_rate=bullet_rate,
        share_value=share_value,
        dividend_yield=dividend_yield,
        dividends_repaid=tx.dividends_repaid,
        volatility=volatility,
        equity_volatility=equity_vol,
        structure=tx.structure,
        risk_free_rate=rf,
        dcr_schedule=dcr_schedule,
        rate_schedule=rate_schedule,
        reference_grade=tx.risk_grade,
        approach=tx.recovery_approach,
        listing=tx.listing,
        unwind_years=unwind_years,
        draws=draws,
    )
    loan_total = amort + bullet
    derived = {
        "share_value": share_value,
        "number_of_shares": shares,
        "share_price": price,
        "initial_cover_ratio": share_value / loan_total if loan_total else 0.0,   # Input H35
        "unwind_years": unwind_years,
        "unwind_days": unwind_years * 251,                                       # Input H87
        "liquidity": liquidity_flag(tx.listing, shares, adtv),                   # E44
        "volatility": volatility,
        "dividend_yield": dividend_yield,
        "risk_free_rate": rf,
        "recovery_policy": POLICY_BY_APPROACH[tx.recovery_approach],
        "amortised_amount": amort,
        "bullet_amount": bullet,
        "bullet_rate": bullet_rate,
        "reference_pd": grades.fitted_pd(tx.risk_grade),                         # E18
    }
    return inp, derived, port


def calculate(store: Store, tx: Transaction) -> Run:
    inp, derived, port = to_engine_inputs(tx)
    result = run_engine(inp, equity_lgd_fallback=port.equity_lgd if port else None)
    payload = {
        "years": [asdict(r) for r in result.years],
        "results": asdict(result.results),
        "report": {k: asdict(v) for k, v in result.report.items()},
        "derived": {**result.derived, **derived},
        "portfolio": asdict(port) if port else None,
        "warnings": result.warnings,
        "report_date": now().date().isoformat(),
    }
    run = Run(
        id=new_id(),
        transaction_id=tx.id,
        created_at=now(),
        inputs=tx.model_dump(mode="json"),
        result=payload,
        pd_total=result.results.pd_total,
        risk_grade=result.results.risk_grade,
        lgd_total=result.results.lgd_total,
        el=result.results.el,
        rwa_pct=result.results.rwa_pct,
    )
    store.save_run(run)
    store.update_transaction(
        tx.model_copy(
            update={
                "latest_run_id": run.id,
                "latest_pd": run.pd_total,
                "latest_risk_grade": run.risk_grade,
                "latest_lgd": run.lgd_total,
                "latest_el": run.el,
                "status": "calculated",
                "updated_at": now(),
            }
        )
    )
    return run

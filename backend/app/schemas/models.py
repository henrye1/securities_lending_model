"""Pydantic API models. A transaction payload is the workbook's Input page
(plus the Portfolio Transactions page); 'Not Applicable' cells are null."""
from __future__ import annotations

from datetime import date, datetime
from typing import Any, Literal, Optional

from pydantic import BaseModel, Field

Structure = Literal[
    "Bullet Payment",
    "Straight Amortisation",
    "Interest Only Repayments",
    "Straight Amortisation & Bullet",
]
Listing = Literal["Listed", "Unlisted"]


class DcrChange(BaseModel):
    time: float  # years after start at which the DCR changes (Input I41:N41)
    dcr: float   # the new default cover ratio (Input I43:N43)


class RateBucket(BaseModel):
    lower_bound: float  # cover ratio lower boundary (Input J55:N55)
    rate: float         # interest rate for that cover interval (Input J57:N57)


class SectorWeight(BaseModel):
    sector: str
    weight: float = 1.0  # fraction (Input M101:M105)


class StockPayload(BaseModel):
    name: str = ""
    number_of_shares: float = 0.0
    share_price: float = 0.0
    volatility: float = 0.0
    dividend_yield: float = 0.0
    average_daily_volume: float = 0.0
    country: str = ""
    risk_grade: str = ""
    revenue_size: str = ""
    sector: str = ""
    ebitda: float = 0.0
    market_cap: float = 0.0
    total_liabilities: float = 0.0
    time_to_unwind: float = 0.0
    unlisted_haircut: float = 0.0
    illiquid_haircut: float = 0.0
    currency_pair: str = ""
    currency_volatility: float = 0.0


def _identity() -> list[list[float]]:
    return [[1.0 if i == j else 0.0 for j in range(10)] for i in range(10)]


def _zeros() -> list[list[float]]:
    return [[0.0] * 10 for _ in range(10)]


class PortfolioPayload(BaseModel):
    stocks: list[StockPayload] = Field(default_factory=list, max_length=10)
    equity_correlation: list[list[float]] = Field(default_factory=_identity)
    currency_correlation: list[list[float]] = Field(default_factory=_identity)
    currency_equity_correlation: list[list[float]] = Field(default_factory=_zeros)


class TransactionCreate(BaseModel):
    # Client / Borrower Details
    client_cif: str = ""
    client_name: str
    client_country: str = "South Africa"
    portfolio_of_shares: bool = False
    # Transaction Details
    start_date: date
    maturity_date: date
    structure: Structure = "Bullet Payment"
    amortised_loan_amount: Optional[float] = None   # null = Not Applicable
    bullet_loan_amount: Optional[float] = None      # null = Not Applicable
    number_of_shares: float = 0.0
    share_price: float = 0.0
    average_daily_volume: float = 0.0
    dcr_changes: bool = False
    default_cover_ratio: float = 1.75
    dcr_schedule: list[DcrChange] = Field(default_factory=list, max_length=6)
    # Interest
    bullet_interest_rate: Optional[float] = None    # null = Not Applicable
    rate_linked_to_cover: bool = False
    amortised_interest_rate: Optional[float] = None
    rate_schedule: list[RateBucket] = Field(default_factory=list, max_length=5)
    # Stock Details
    dividend_yield: float = 0.0
    dividends_repaid: float = 1.0
    stock_volatility: float = 0.0
    # Other Liabilities and Collateral (report only)
    liabilities_ahead: Optional[float] = None
    liabilities_pari_passu: Optional[float] = None
    liabilities_subordinate: Optional[float] = None
    other_collateral: Optional[float] = None
    collateral_pari_passu: Optional[float] = None
    other_pari_passu_liabilities: Optional[float] = None
    # Reference Share Details
    reference_cif: str = ""
    reference_name: str = ""
    reference_country: str = "South Africa"
    listing: Listing = "Listed"
    risk_grade: str = "SB11"
    revenue_size: str = "Revenue > R500m"
    sectors: list[SectorWeight] = Field(default_factory=list, max_length=3)
    unlisted_haircut: float = 0.5
    illiquid_haircut: float = 0.3
    risk_free_rate: Optional[float] = None          # null -> country table
    # Currency Risk
    currency_mismatch: bool = False
    currency_volatility: float = 0.0
    currency_correlation: float = 0.0
    # Calculation settings (Calculations sheet ComboBox / draws)
    recovery_approach: int = Field(default=1, ge=1, le=3)
    random_seed: Optional[int] = None               # null -> workbook draw set
    portfolio: Optional[PortfolioPayload] = None


class Transaction(TransactionCreate):
    id: str
    batch_id: str
    created_at: datetime
    updated_at: datetime
    latest_run_id: str | None = None
    latest_pd: float | None = None
    latest_risk_grade: str | None = None
    latest_lgd: float | None = None
    latest_el: float | None = None
    status: str = "draft"  # draft | calculated


class Batch(BaseModel):
    id: str
    name: str
    created_at: datetime
    transaction_count: int = 0


class Run(BaseModel):
    id: str
    transaction_id: str
    created_at: datetime
    inputs: dict[str, Any] = Field(default_factory=dict)
    result: dict[str, Any] = Field(default_factory=dict)
    pd_total: float = 0.0
    risk_grade: str = ""
    lgd_total: float = 0.0
    el: float = 0.0
    rwa_pct: float = 0.0

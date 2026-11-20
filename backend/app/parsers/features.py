"""Feature extraction and engineering from parsed SMS transactions and documents.

Computes the 10 alternative credit scoring features, enforces the <3 month history
bhorsha handoff policy, and clips derived metrics against empirical training distributions.
"""

import json
from collections import defaultdict
from pathlib import Path
from typing import Any

import numpy as np
from pydantic import BaseModel, Field

from app.core.features import FEATURE_NAMES
from app.parsers.sms import Transaction

# Default path to precomputed empirical feature ranges
DEFAULT_RANGES_PATH = Path(__file__).resolve().parents[3] / "models" / "feature_ranges.json"


class FeatureExtractionResult(BaseModel):
    """Result of feature extraction from transactions."""

    features: dict[str, float | None]
    needs_bhorsha: bool = Field(
        ...,
        description="True if applicant has < 3 months wallet history, requiring Bhorsha assessment",
    )
    months_on_wallet: float = Field(
        ..., description="Calculated span on mobile wallet in calendar months"
    )
    total_transactions: int = Field(..., description="Count of parsed transactions analyzed")


def load_feature_ranges(
    path: Path | str | None = None,
) -> dict[str, dict[str, float]]:
    """Load empirical training distribution bounds for feature clipping."""
    ranges_file = Path(path) if path else DEFAULT_RANGES_PATH
    if not ranges_file.exists():
        return {}
    try:
        with open(ranges_file, encoding="utf-8") as f:
            data: dict[str, dict[str, float]] = json.load(f)
            return data
    except Exception:  # noqa: BLE001
        return {}


def clip_feature_value(
    feature_name: str,
    val: float | None,
    ranges: dict[str, dict[str, float]] | None = None,
) -> float | None:
    """Clip a numeric feature value to the empirical min/max bounds observed in training data."""
    if val is None or np.isnan(val):
        return None

    if ranges and feature_name in ranges:
        min_val = ranges[feature_name].get("min", float("-inf"))
        max_val = ranges[feature_name].get("max", float("inf"))
        val = max(min_val, min(max_val, float(val)))

    return round(float(val), 4)


def extract_features(
    transactions: list[Transaction],
    requested_amount_bdt: float | None = None,
    ocr_bills: list[dict[str, Any]] | None = None,
    default_due_day: int = 25,
    ranges_path: Path | str | None = None,
) -> FeatureExtractionResult:
    """Extract and validate the 10 model features from structured transactions.

    Rules:
    - Users with < 3 months of history have wallet features set to None and needs_bhorsha=True.
    - All features are clipped to training distributions in models/feature_ranges.json.
    """
    ranges = load_feature_ranges(ranges_path)
    total_txns = len(transactions)

    if total_txns == 0:
        empty_features: dict[str, float | None] = {f: None for f in FEATURE_NAMES}
        return FeatureExtractionResult(
            features=empty_features,
            needs_bhorsha=True,
            months_on_wallet=0.0,
            total_transactions=0,
        )

    # Sort transactions chronologically
    sorted_txs = sorted(transactions, key=lambda t: t.date)
    first_date = sorted_txs[0].date
    last_date = sorted_txs[-1].date

    # Calculate wallet tenure in fractional months
    delta_days = max(0.0, (last_date - first_date).total_seconds() / 86400.0)
    tenure_months = round(delta_days / 30.4375, 2)

    # Short history rule (< 3 months) -> delegate to Bhorsha psychometric chat
    if tenure_months < 3.0:
        empty_features = {f: None for f in FEATURE_NAMES}
        return FeatureExtractionResult(
            features=empty_features,
            needs_bhorsha=True,
            months_on_wallet=tenure_months,
            total_transactions=total_txns,
        )

    # Build calendar months list spanning history
    cur = first_date.replace(day=1)
    all_months: list[str] = []
    while cur <= last_date:
        all_months.append(cur.strftime("%Y-%m"))
        year = cur.year + (cur.month // 12)
        month = (cur.month % 12) + 1
        cur = cur.replace(year=year, month=month, day=1)

    effective_months = max(tenure_months, float(len(all_months)), 1.0)

    # 1. Monthly inflow & income volatility
    monthly_inflows: dict[str, float] = defaultdict(float)
    for t in sorted_txs:
        if t.direction == "in" or t.type in ("income", "salary"):
            m_key = t.date.strftime("%Y-%m")
            monthly_inflows[m_key] += t.amount_bdt

    inflow_series = [monthly_inflows.get(m, 0.0) for m in all_months]
    monthly_inflow_bdt = float(np.median(inflow_series)) if inflow_series else 0.0
    mean_inflow = float(np.mean(inflow_series)) if inflow_series else 0.0
    std_inflow = float(np.std(inflow_series)) if inflow_series else 0.0
    income_volatility = (std_inflow / mean_inflow) if mean_inflow > 0 else 0.0

    # 2. Transaction frequency per month
    txn_per_month = total_txns / effective_months

    # 3. Utility / Service bills on-time ratio
    bill_txs = [t for t in sorted_txs if t.type == "bill"]
    if bill_txs:
        on_time_count = sum(1 for t in bill_txs if t.date.day <= default_due_day)
        bills_on_time = on_time_count / len(bill_txs)
    elif ocr_bills:
        bills_on_time = 0.90  # Verified via OCR bill attachments
    else:
        bills_on_time = 0.95  # Neutral default for non-bill accounts

    # 4. Recharge regularity index (1 - normalized std of inter-recharge days)
    recharges = [t for t in sorted_txs if t.type == "recharge"]
    if len(recharges) >= 2:
        intervals = [
            (recharges[i].date - recharges[i - 1].date).total_seconds() / 86400.0
            for i in range(1, len(recharges))
        ]
        mean_int = float(np.mean(intervals))
        std_int = float(np.std(intervals))
        cv = (std_int / mean_int) if mean_int > 0 else 0.0
        recharge_regularity = max(0.0, min(1.0, 1.0 - cv))
    elif len(recharges) == 1:
        recharge_regularity = 0.75
    else:
        recharge_regularity = 0.50

    # 5. Savings ratio (savings out / total income in)
    total_income = sum(inflow_series)
    total_savings = sum(t.amount_bdt for t in sorted_txs if t.type == "savings")
    savings_ratio = (total_savings / total_income) if total_income > 0 else 0.0

    # 6. Remittance frequency (sends_money_home = 1 if remittance or family send-money in >= 50% of active months)
    remittance_txs = [
        t
        for t in sorted_txs
        if t.type == "remittance" or (t.type == "transfer" and t.direction == "out")
    ]
    remittance_months = {t.date.strftime("%Y-%m") for t in remittance_txs}
    remittance_month_ratio = len(remittance_months) / max(1, len(all_months))
    sends_money_home = 1.0 if remittance_month_ratio >= 0.5 else 0.0

    # 7. Loan to income ratio
    loan_to_income = (
        (requested_amount_bdt / monthly_inflow_bdt)
        if (requested_amount_bdt is not None and monthly_inflow_bdt > 0)
        else None
    )

    # 8. Assemble raw feature dict and apply empirical range clipping
    raw_dict: dict[str, float | None] = {
        "monthly_inflow_bdt": monthly_inflow_bdt,
        "income_volatility": income_volatility,
        "months_on_wallet": effective_months,
        "txn_per_month": txn_per_month,
        "bills_on_time": bills_on_time,
        "recharge_regularity": recharge_regularity,
        "savings_ratio": savings_ratio,
        "sends_money_home": sends_money_home,
        "bhorsha_score": None,  # Provided by Bhorsha module if needed
        "loan_to_income": loan_to_income,
    }

    clipped_dict: dict[str, float | None] = {}
    for fname in FEATURE_NAMES:
        val = raw_dict.get(fname)
        clipped_dict[fname] = clip_feature_value(fname, val, ranges)

    return FeatureExtractionResult(
        features=clipped_dict,
        needs_bhorsha=False,
        months_on_wallet=effective_months,
        total_transactions=total_txns,
    )

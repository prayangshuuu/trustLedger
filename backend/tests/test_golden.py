"""Golden benchmark test matching notebook evaluation on the Shathi persona."""

import numpy as np
from app.core.decision import score_applicant


def test_shathi_golden_benchmark() -> None:
    """Reproduce the notebook's Shathi benchmark metrics within ±0.01 tolerance."""
    shathi_features = {
        "monthly_inflow_bdt": 14000.0,
        "income_volatility": 0.10,
        "months_on_wallet": 30.0,
        "txn_per_month": 18.0,
        "bills_on_time": 0.97,
        "recharge_regularity": 0.90,
        "savings_ratio": 0.04,
        "sends_money_home": 1.0,
        "bhorsha_score": np.nan,
        "loan_to_income": 4.0,
    }

    decision = score_applicant(shathi_features, group="F_urban")

    # 1. P(repay) reproduction within ±0.01 of notebook's 0.933661 (~0.934)
    assert abs(decision.p_repay - 0.933661) <= 0.01
    assert abs(decision.p_repay - 0.934) <= 0.01
    assert round(decision.p_repay, 3) == 0.934

    # 2. Credit score matches 691 exactly
    assert decision.score == 691

    # 3. Risk band is Good (650-749)
    assert decision.band == "Good"

    # 4. Approval status is True
    assert decision.approved is True

    # 5. Calibrated threshold within ±0.01 of 0.717315 for F_urban
    assert abs(decision.threshold_used - 0.717315) <= 0.01
    assert decision.evaluated_group == "F_urban"
    assert decision.timestamp is not None

    # 6. SHAP Bangla reasons match notebook exactly
    assert decision.good == [
        "বিল সময়মতো পরিশোধ",
        "নিয়মিত মোবাইল রিচার্জ",
    ]
    assert decision.bad == [
        "সঞ্চয় কম",
    ]

    # 7. Actionable tips match notebook exactly
    assert decision.tips == [
        "প্রতি মাসে আয়ের অন্তত ৫% সঞ্চয় করুন।",
    ]

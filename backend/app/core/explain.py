"""SHAP explainability engine for TrustLedger credit scoring.

Generates local feature attributions using TreeExplainer, identifies top positive/negative
drivers, and translates them into borrower-facing Bangla explanations and actionable tips.
"""

from functools import lru_cache
from typing import Any, Literal

import numpy as np
import pandas as pd
import shap
from pydantic import BaseModel

from app.core.features import FeatureVector, get_feature_order, to_dataframe
from app.core.model import load_meta, load_model

ENGLISH_FEATURE_LABELS: dict[str, str] = {
    "monthly_inflow_bdt": "Monthly inflow (BDT)",
    "income_volatility": "Income volatility",
    "months_on_wallet": "Months on wallet",
    "txn_per_month": "Transactions per month",
    "bills_on_time": "Bills paid on time",
    "recharge_regularity": "Mobile recharge regularity",
    "savings_ratio": "Savings ratio",
    "sends_money_home": "Sends money home",
    "bhorsha_score": "Bhorsha score",
    "loan_to_income": "Loan to income ratio",
}


class Reason(BaseModel):
    """Individual feature contribution reason."""

    feature: str
    label: str
    text: str
    impact: float
    kind: Literal["good", "bad"]

    def __eq__(self, other: object) -> bool:
        if isinstance(other, str):
            return other in (self.text, self.feature, self.label)
        return super().__eq__(other)

    def __str__(self) -> str:
        return self.text


class Explanation(BaseModel):
    """Comprehensive explainability bundle with Bangla strings, tips, and structured reasons."""

    good: list[str]
    bad: list[str]
    tips: list[str]
    reasons: list[Reason]

    @property
    def good_reasons(self) -> list[str]:
        """Return Bangla good reason strings."""
        return self.good

    @property
    def bad_reasons(self) -> list[str]:
        """Return Bangla bad reason strings."""
        return self.bad

    def __getitem__(self, item: str) -> Any:
        return getattr(self, item)


@lru_cache(maxsize=1)
def get_explainer() -> shap.TreeExplainer:
    """Instantiate and cache a SHAP TreeExplainer for the production XGBoost model."""
    model = load_model()
    return shap.TreeExplainer(model)


def clear_explainer_cache() -> None:
    """Clear cached TreeExplainer instance."""
    get_explainer.cache_clear()


def explain(
    features: FeatureVector | dict[str, Any] | pd.DataFrame,
    k: int = 2,
    min_impact: float = 0.02,
) -> Explanation:
    """Compute top positive and negative reasons for an applicant's score.

    Filters out missing/NaN features and impacts strictly smaller than `min_impact`.

    Args:
        features: FeatureVector, feature dict, or 1-row DataFrame.
        k: Maximum number of good and bad reasons to report (default: 2).
        min_impact: Absolute SHAP value threshold below which features are ignored (default: 0.02).

    Returns:
        Explanation containing Bangla good/bad strings, actionable tips, and Reason objects.
    """
    if isinstance(features, pd.DataFrame):
        expected_cols = get_feature_order()
        if list(features.columns) != expected_cols:
            features = features[expected_cols]
        df = features
    else:
        df = to_dataframe(features)

    feature_names = get_feature_order()
    explainer = get_explainer()
    raw_sv = explainer.shap_values(df)

    if isinstance(raw_sv, list):
        sv_row = np.asarray(raw_sv[1][0] if len(raw_sv) > 1 else raw_sv[0][0])
    elif isinstance(raw_sv, np.ndarray) and raw_sv.ndim == 3:
        sv_row = np.asarray(raw_sv[0, :, 1])
    else:
        sv_row = np.asarray(raw_sv[0])

    meta = load_meta()
    reasons_meta: dict[str, list[str]] = meta.get("reasons", {})
    tips_meta: dict[str, str] = meta.get("tips", {})

    usable_indices: list[int] = []
    for i in range(len(feature_names)):
        val = df.iloc[0, i]
        impact = float(sv_row[i])
        if not pd.isna(val) and abs(impact) >= min_impact:
            usable_indices.append(i)

    good_indices = sorted(
        [i for i in usable_indices if float(sv_row[i]) > 0],
        key=lambda i: -float(sv_row[i]),
    )[:k]

    bad_indices = sorted(
        [i for i in usable_indices if float(sv_row[i]) < 0],
        key=lambda i: float(sv_row[i]),
    )[:k]

    good_bangla: list[str] = []
    good_reasons: list[Reason] = []
    for i in good_indices:
        fname = feature_names[i]
        bangla_text = reasons_meta.get(fname, [fname, fname])[0]
        good_bangla.append(bangla_text)
        good_reasons.append(
            Reason(
                feature=fname,
                label=ENGLISH_FEATURE_LABELS.get(fname, fname),
                text=bangla_text,
                impact=float(sv_row[i]),
                kind="good",
            )
        )

    bad_bangla: list[str] = []
    bad_reasons: list[Reason] = []
    tips_list: list[str] = []
    for i in bad_indices:
        fname = feature_names[i]
        bangla_text = reasons_meta.get(fname, [fname, fname])[1]
        bad_bangla.append(bangla_text)
        bad_reasons.append(
            Reason(
                feature=fname,
                label=ENGLISH_FEATURE_LABELS.get(fname, fname),
                text=bangla_text,
                impact=float(sv_row[i]),
                kind="bad",
            )
        )
        if fname in tips_meta:
            tips_list.append(tips_meta[fname])

    all_reasons = good_reasons + bad_reasons

    return Explanation(
        good=good_bangla,
        bad=bad_bangla,
        tips=tips_list,
        reasons=all_reasons,
    )

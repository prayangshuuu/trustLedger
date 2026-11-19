"""Scoring functions for TrustLedger.

Transforms applicant features into repayment probabilities, credit scores (300-900),
and risk tier bands per the TrustLedger specification.
"""

import math
from typing import Any, overload

import numpy as np
import pandas as pd

from app.core.features import (
    AllFeaturesMissingError,
    FeatureVector,
    get_feature_order,
    to_dataframe,
)
from app.core.model import load_meta, load_model


def predict(features: FeatureVector | dict[str, Any] | pd.DataFrame) -> float:
    """Predict repayment probability P(repay) for an applicant.

    Args:
        features: FeatureVector, feature dictionary, or 1-row DataFrame.

    Returns:
        float: Estimated probability of full repayment within [0.0, 1.0].

    Raises:
        AllFeaturesMissingError: If all features are missing/NaN.
        ValueError: If input DataFrame is empty.
        TypeError: If features is not a FeatureVector, dict, or DataFrame.
    """
    if isinstance(features, pd.DataFrame):
        if features.empty:
            raise ValueError("Input DataFrame is empty; cannot predict.")
        expected_cols = get_feature_order()
        if list(features.columns) != expected_cols:
            features = features.reindex(columns=expected_cols)
        if features.isna().all(axis=1).iloc[0]:
            raise AllFeaturesMissingError("All features are NaN; cannot predict.")
        df = features
    elif isinstance(features, (FeatureVector, dict)):
        df = to_dataframe(features)
    else:
        raise TypeError(
            f"Expected FeatureVector, dict, or DataFrame, got {type(features).__name__}"
        )

    model = load_model()
    probs = model.predict_proba(df)
    p_repay = float(probs[0, 1])
    return float(np.clip(p_repay, 0.0, 1.0))


@overload
def to_score(p: float) -> int: ...


@overload
def to_score(p: np.ndarray) -> np.ndarray: ...


def to_score(p: float | np.ndarray) -> int | np.ndarray:
    """Convert repayment probability to a credit score in [300, 900].

    Formula:
        score = 600 + (50 / ln(2)) * ln((p / (1 - p)) / 4), clipped to [300, 900].
    Parameters are dynamically loaded from metadata if available.

    Args:
        p: Float probability in [0.0, 1.0] or numpy ndarray of probabilities.

    Returns:
        int or np.ndarray: Credit score(s) clipped to [300, 900].

    Raises:
        ValueError: If p contains values outside [0.0, 1.0] or NaN.
    """
    try:
        meta = load_meta()
        scale = meta.get("score_scale", {})
        base_points = float(scale.get("points_at_4_to_1", 600))
        pdo = float(scale.get("points_to_double_odds", 50))
        score_range = scale.get("range", [300, 900])
        min_score = int(score_range[0])
        max_score = int(score_range[1])
    except Exception:  # noqa: BLE001
        base_points = 600.0
        pdo = 50.0
        min_score = 300
        max_score = 900

    factor = pdo / math.log(2.0)

    if isinstance(p, (float, int)) and not isinstance(p, bool):
        p_val = float(p)
        if math.isnan(p_val) or p_val < 0.0 or p_val > 1.0:
            raise ValueError(f"Invalid repayment probability p={p_val}: must be within [0.0, 1.0]")
        p_clipped = max(1e-4, min(1.0 - 1e-4, p_val))
        odds = (p_clipped / (1.0 - p_clipped)) / 4.0
        raw_score = base_points + factor * math.log(odds)
        clipped_score = max(float(min_score), min(float(max_score), raw_score))
        return round(clipped_score)

    p_arr = np.asarray(p, dtype=float)
    if np.isnan(p_arr).any() or (p_arr < 0.0).any() or (p_arr > 1.0).any():
        raise ValueError("All repayment probabilities must be within [0.0, 1.0] and non-NaN")

    if p_arr.size == 0:
        return np.asarray([], dtype=int)

    p_clipped_arr = np.clip(p_arr, 1e-4, 1.0 - 1e-4)
    odds_arr = (p_clipped_arr / (1.0 - p_clipped_arr)) / 4.0
    raw_arr = base_points + (pdo / np.log(2.0)) * np.log(odds_arr)
    clipped_arr = np.clip(np.round(raw_arr), min_score, max_score)
    res: np.ndarray = np.asarray(clipped_arr, dtype=int)
    return res


def band(score: int) -> str:
    """Map credit score to risk tier band.

    Bands:
        >= 750: Excellent
        >= 650: Good
        >= 550: Fair
        < 550:  Building
    """
    if score >= 750:
        return "Excellent"
    if score >= 650:
        return "Good"
    if score >= 550:
        return "Fair"
    return "Building"

"""Unit tests for probability prediction, score scaling, and risk bands."""

from typing import Any, cast

import numpy as np
import pandas as pd
import pytest
from app.core.features import AllFeaturesMissingError, FeatureVector, get_feature_order
from app.core.score import band, predict, to_score


def test_predict_feature_vector() -> None:
    """Verify predict returns a valid float probability in [0, 1]."""
    fv = FeatureVector(
        monthly_inflow_bdt=14000.0,
        income_volatility=0.10,
        months_on_wallet=30.0,
        txn_per_month=18.0,
        bills_on_time=0.97,
        recharge_regularity=0.90,
        savings_ratio=0.04,
        sends_money_home=1.0,
        loan_to_income=4.0,
    )
    p = predict(fv)
    assert isinstance(p, float)
    assert 0.0 <= p <= 1.0


def test_predict_dict() -> None:
    """Verify predict accepts a raw feature dictionary."""
    data = {
        "monthly_inflow_bdt": 20000.0,
        "income_volatility": 0.05,
        "months_on_wallet": 24.0,
        "txn_per_month": 15.0,
        "bills_on_time": 0.95,
        "recharge_regularity": 0.85,
        "savings_ratio": 0.10,
        "sends_money_home": 1.0,
        "bhorsha_score": 75.0,
        "loan_to_income": 2.5,
    }
    p = predict(data)
    assert isinstance(p, float)
    assert 0.0 <= p <= 1.0


def test_predict_dataframe() -> None:
    """Verify predict accepts a pandas DataFrame with arbitrary column order."""
    cols = list(reversed(get_feature_order()))
    row = {c: 0.5 for c in cols}
    row["monthly_inflow_bdt"] = 15000.0
    df = pd.DataFrame([row], columns=cols)

    p = predict(df)
    assert isinstance(p, float)
    assert 0.0 <= p <= 1.0


def test_predict_dataframe_subset_columns() -> None:
    """Verify predict handles DataFrame with subset of columns by reindexing."""
    df = pd.DataFrame([{"monthly_inflow_bdt": 12000.0, "bhorsha_score": 80.0}])
    p = predict(df)
    assert isinstance(p, float)
    assert 0.0 <= p <= 1.0


def test_predict_empty_dataframe_raises() -> None:
    """Verify predict raises ValueError when passed an empty DataFrame."""
    df = pd.DataFrame()
    with pytest.raises(ValueError, match="Input DataFrame is empty"):
        predict(df)


def test_predict_invalid_type_raises() -> None:
    """Verify predict raises TypeError for unsupported argument types."""
    with pytest.raises(TypeError, match="Expected FeatureVector, dict, or DataFrame"):
        predict(cast(Any, ["monthly_inflow_bdt", 10000.0]))


def test_predict_all_nan_dataframe_raises() -> None:
    """Verify predict raises AllFeaturesMissingError when all DataFrame entries are NaN."""
    cols = get_feature_order()
    df = pd.DataFrame([{c: np.nan for c in cols}], columns=cols)
    with pytest.raises(AllFeaturesMissingError, match="All features are NaN"):
        predict(df)


def test_to_score_exact_formula() -> None:
    """Verify standard formula points: 4:1 odds = 600, double odds (8:1) = 650, half odds (2:1) = 550."""
    # 4:1 odds -> p = 4/5 = 0.80
    assert to_score(0.80) == 600
    # 8:1 odds -> p = 8/9 ≈ 0.8888888888888888
    assert to_score(8.0 / 9.0) == 650
    # 2:1 odds -> p = 2/3 ≈ 0.6666666666666666
    assert to_score(2.0 / 3.0) == 550


def test_to_score_monotonicity() -> None:
    """Verify score is monotonic non-decreasing in repayment probability p."""
    p_values = np.linspace(0.001, 0.999, 500)
    scores = [to_score(p) for p in p_values]

    for i in range(len(scores) - 1):
        assert scores[i] <= scores[i + 1], f"Score violated monotonicity at p={p_values[i]}"


def test_to_score_bounds_and_array() -> None:
    """Verify clipping at 300 and 900, as well as vectorized ndarray execution."""
    assert to_score(0.0) == 300
    assert to_score(1e-6) == 300
    assert to_score(0.99999) == 900
    assert to_score(1.0) == 900
    assert to_score(0) == 300
    assert to_score(1) == 900

    arr = np.array([0.0, 0.5, 1.0])
    scores = to_score(arr)
    assert isinstance(scores, np.ndarray)
    assert len(scores) == 3
    assert scores[0] == 300
    assert scores[2] == 900

    empty_scores = to_score(np.array([]))
    assert isinstance(empty_scores, np.ndarray)
    assert len(empty_scores) == 0


def test_to_score_invalid_probability_raises() -> None:
    """Verify invalid probabilities (<0, >1, NaN) raise ValueError."""
    with pytest.raises(ValueError, match="Invalid repayment probability"):
        to_score(-0.05)
    with pytest.raises(ValueError, match="Invalid repayment probability"):
        to_score(1.05)
    with pytest.raises(ValueError, match="Invalid repayment probability"):
        to_score(float("nan"))

    with pytest.raises(ValueError, match="All repayment probabilities must be within"):
        to_score(np.array([0.5, -0.1, 0.9]))
    with pytest.raises(ValueError, match="All repayment probabilities must be within"):
        to_score(np.array([0.5, 1.2]))
    with pytest.raises(ValueError, match="All repayment probabilities must be within"):
        to_score(np.array([0.5, np.nan]))


def test_to_score_custom_scale_from_meta(monkeypatch: pytest.MonkeyPatch) -> None:
    """Verify to_score dynamically respects custom scale parameters in metadata."""
    custom_meta = {
        "score_scale": {
            "points_at_4_to_1": 500,
            "points_to_double_odds": 40,
            "range": [200, 800],
        }
    }
    monkeypatch.setattr("app.core.score.load_meta", lambda *args, **kwargs: custom_meta)
    # At p=0.8 (4:1 odds), base points should now be 500
    assert to_score(0.80) == 500
    # Clamping should respect [200, 800]
    assert to_score(0.0) == 200
    assert to_score(1.0) == 800


def test_band_classification() -> None:
    """Verify band classification according to PLAN_CONTEXT.md §2."""
    assert band(900) == "Excellent"
    assert band(750) == "Excellent"
    assert band(749) == "Good"
    assert band(650) == "Good"
    assert band(649) == "Fair"
    assert band(550) == "Fair"
    assert band(549) == "Building"
    assert band(300) == "Building"
    assert band(250) == "Building"
    assert band(950) == "Excellent"


def test_to_score_fallback(monkeypatch: pytest.MonkeyPatch) -> None:
    """Verify to_score falls back to default scaling if metadata loading fails."""

    def raise_meta(*args: object, **kwargs: object) -> dict[str, object]:
        raise RuntimeError("error")

    monkeypatch.setattr("app.core.score.load_meta", raise_meta)
    score = to_score(0.933661)
    assert score == 691

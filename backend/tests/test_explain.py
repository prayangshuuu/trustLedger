"""Unit tests for SHAP feature attribution and explanation generation."""

import numpy as np
import pandas as pd
import pytest
from app.core.explain import (
    Reason,
    clear_explainer_cache,
    explain,
    get_explainer,
)
from app.core.features import FeatureVector, get_feature_order


def test_explain_shathi() -> None:
    """Verify SHAP explanation generation for the Shathi benchmark profile."""
    shathi_fv = FeatureVector(
        monthly_inflow_bdt=14000.0,
        income_volatility=0.10,
        months_on_wallet=30.0,
        txn_per_month=18.0,
        bills_on_time=0.97,
        recharge_regularity=0.90,
        savings_ratio=0.04,
        sends_money_home=1.0,
        bhorsha_score=None,
        loan_to_income=4.0,
    )
    exp = explain(shathi_fv)

    # Top-2 positive drivers
    assert "বিল সময়মতো পরিশোধ" in exp.good
    assert "নিয়মিত মোবাইল রিচার্জ" in exp.good
    assert len(exp.good) <= 2

    # Negative drivers
    assert "সঞ্চয় কম" in exp.bad
    assert len(exp.bad) <= 2

    # Actionable tips
    assert "প্রতি মাসে আয়ের অন্তত ৫% সঞ্চয় করুন।" in exp.tips

    # Structured Reason objects
    assert len(exp.reasons) == len(exp.good) + len(exp.bad)
    for r in exp.reasons:
        assert isinstance(r, Reason)
        assert r.feature in get_feature_order()
        assert len(r.label) > 0  # English label exists
        assert len(r.text) > 0  # Bangla text exists
        assert r.kind in ("good", "bad")
        assert abs(r.impact) >= 0.02

    # Verify Reason string equality and representation
    top_good = exp.reasons[0]
    assert top_good == top_good.text
    assert top_good == top_good.feature
    assert top_good == top_good.label
    assert top_good != 123  # non-string equality fallback
    assert str(top_good) == top_good.text

    # Dict-like indexing and property aliases
    assert exp["good"] == exp.good
    assert exp["bad"] == exp.bad
    assert exp["tips"] == exp.tips
    assert exp.good_reasons == exp.good
    assert exp.bad_reasons == exp.bad


def test_explain_shap_output_formats(monkeypatch: pytest.MonkeyPatch) -> None:
    """Verify explain handles list-of-arrays and 3D numpy arrays from shap."""
    fv = FeatureVector(monthly_inflow_bdt=15000.0)

    # 1. Test list of arrays format
    class MockListExplainer:
        def shap_values(self, df: pd.DataFrame) -> list[np.ndarray]:
            arr0 = np.zeros((1, 10))
            arr1 = np.zeros((1, 10))
            arr1[0, 0] = 0.5
            return [arr0, arr1]

    monkeypatch.setattr("app.core.explain.get_explainer", lambda: MockListExplainer())
    exp_list = explain(fv)
    assert len(exp_list.good) >= 1

    # 2. Test 3D array format
    class Mock3DExplainer:
        def shap_values(self, df: pd.DataFrame) -> np.ndarray:
            arr = np.zeros((1, 10, 2))
            arr[0, 0, 1] = 0.5
            return arr

    monkeypatch.setattr("app.core.explain.get_explainer", lambda: Mock3DExplainer())
    exp_3d = explain(fv)
    assert len(exp_3d.good) >= 1


def test_explain_skips_missing_and_low_impact() -> None:
    """Verify missing features and features with |SHAP| < 0.02 are ignored."""
    fv = FeatureVector(
        monthly_inflow_bdt=15000.0,
        bhorsha_score=75.0,
    )
    exp = explain(fv)

    # Neither bills_on_time nor recharge_regularity should be mentioned because they are missing
    mentioned_features = [r.feature for r in exp.reasons]
    assert "bills_on_time" not in mentioned_features
    assert "recharge_regularity" not in mentioned_features


def test_explainer_caching() -> None:
    """Verify TreeExplainer caching and cache clearing."""
    clear_explainer_cache()
    exp1 = get_explainer()
    exp2 = get_explainer()
    assert exp1 is exp2

    clear_explainer_cache()
    exp3 = get_explainer()
    assert exp3 is not exp1


def test_explain_dataframe_reordering() -> None:
    """Verify explain handles DataFrame with inverted column ordering."""
    cols = list(reversed(get_feature_order()))
    row = {c: 0.5 for c in cols}
    row["bhorsha_score"] = 85.0
    df = pd.DataFrame([row], columns=cols)

    exp = explain(df)
    assert len(exp.good) > 0 or len(exp.bad) > 0


def test_explain_dict_input_and_k_parameter() -> None:
    """Verify explain works with raw dictionary and respects custom k and min_impact."""
    features_dict = {
        "monthly_inflow_bdt": 18000.0,
        "income_volatility": 0.08,
        "months_on_wallet": 24.0,
        "txn_per_month": 25.0,
        "bills_on_time": 1.0,
        "recharge_regularity": 0.95,
        "savings_ratio": 0.15,
        "sends_money_home": 1.0,
        "bhorsha_score": None,
        "loan_to_income": 2.5,
    }

    # k=1 should limit good and bad to at most 1 item
    exp_k1 = explain(features_dict, k=1)
    assert len(exp_k1.good) <= 1
    assert len(exp_k1.bad) <= 1

    # High min_impact should filter out signals below that threshold
    exp_strict = explain(features_dict, min_impact=5.0)
    assert len(exp_strict.reasons) == 0


def test_explain_zero_network_db(monkeypatch: pytest.MonkeyPatch) -> None:
    """Verify explain makes zero network, database, or external API calls."""
    import socket

    def guarded_connect(*_args: object, **_kwargs: object) -> None:
        raise RuntimeError("Network call attempted in explain core logic!")

    monkeypatch.setattr(socket.socket, "connect", guarded_connect)
    monkeypatch.setattr(socket, "getaddrinfo", guarded_connect)

    fv = FeatureVector(
        monthly_inflow_bdt=14000.0,
        income_volatility=0.10,
        months_on_wallet=30.0,
        bills_on_time=0.97,
    )
    exp = explain(fv)
    assert len(exp.good) > 0

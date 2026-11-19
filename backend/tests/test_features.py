"""Unit tests for FeatureVector and feature transformation."""

import numpy as np
import pandas as pd
import pytest
from app.core.features import (
    FEATURE_NAMES,
    AllFeaturesMissingError,
    FeatureVector,
    get_feature_order,
    to_dataframe,
)
from app.core.model import load_meta
from pydantic import ValidationError

EXPECTED_10_FEATURES = (
    "monthly_inflow_bdt",
    "income_volatility",
    "months_on_wallet",
    "txn_per_month",
    "bills_on_time",
    "recharge_regularity",
    "savings_ratio",
    "sends_money_home",
    "bhorsha_score",
    "loan_to_income",
)


def test_feature_names_match_plan_context() -> None:
    """Verify FEATURE_NAMES contains all 10 features from PLAN_CONTEXT.md §2 in order."""
    assert FEATURE_NAMES == EXPECTED_10_FEATURES
    # Also verify match with trustledger_meta.json
    meta = load_meta()
    assert tuple(meta["features"]) == EXPECTED_10_FEATURES


def test_feature_vector_valid() -> None:
    """Verify FeatureVector instantiation with typical inputs."""
    fv = FeatureVector(
        monthly_inflow_bdt=15000.0,
        income_volatility=0.15,
        months_on_wallet=24.0,
        txn_per_month=12.0,
        bills_on_time=0.95,
        recharge_regularity=0.88,
        savings_ratio=0.08,
        sends_money_home=1.0,
        bhorsha_score=80.0,
        loan_to_income=3.5,
    )
    assert fv.monthly_inflow_bdt == 15000.0
    assert fv.income_volatility == 0.15
    assert fv.months_on_wallet == 24.0
    assert fv.txn_per_month == 12.0
    assert fv.bills_on_time == 0.95
    assert fv.recharge_regularity == 0.88
    assert fv.savings_ratio == 0.08
    assert fv.sends_money_home == 1.0
    assert fv.bhorsha_score == 80.0
    assert fv.loan_to_income == 3.5
    assert not fv.is_empty()


def test_feature_vector_boundary_values() -> None:
    """Verify minimum and maximum boundary values for all features."""
    # Test valid boundary lower limits (0.0 for all features)
    zero_fv = FeatureVector(
        monthly_inflow_bdt=0.0,
        income_volatility=0.0,
        months_on_wallet=0.0,
        txn_per_month=0.0,
        bills_on_time=0.0,
        recharge_regularity=0.0,
        savings_ratio=0.0,
        sends_money_home=0.0,
        bhorsha_score=0.0,
        loan_to_income=0.0,
    )
    assert not zero_fv.is_empty()
    assert zero_fv.monthly_inflow_bdt == 0.0

    # Test valid boundary upper limits (1.0 for ratios, 100.0 for bhorsha_score)
    max_fv = FeatureVector(
        bills_on_time=1.0,
        recharge_regularity=1.0,
        savings_ratio=1.0,
        sends_money_home=1.0,
        bhorsha_score=100.0,
    )
    assert max_fv.bills_on_time == 1.0
    assert max_fv.bhorsha_score == 100.0


def test_feature_vector_optional_fields() -> None:
    """Verify all 10 features default to None and are optional."""
    empty_fv = FeatureVector()
    for field_name in EXPECTED_10_FEATURES:
        assert getattr(empty_fv, field_name) is None
    assert empty_fv.is_empty()

    # Zero-history user: only bhorsha_score provided
    zero_hist = FeatureVector(bhorsha_score=75.0)
    assert zero_hist.bhorsha_score == 75.0
    assert zero_hist.monthly_inflow_bdt is None
    assert not zero_hist.is_empty()


@pytest.mark.parametrize(
    ("field", "bad_value"),
    [
        ("monthly_inflow_bdt", -0.01),
        ("monthly_inflow_bdt", -100.0),
        ("income_volatility", -0.01),
        ("months_on_wallet", -1.0),
        ("txn_per_month", -0.5),
        ("bills_on_time", -0.01),
        ("bills_on_time", 1.01),
        ("bills_on_time", 2.0),
        ("recharge_regularity", -0.01),
        ("recharge_regularity", 1.01),
        ("savings_ratio", -0.01),
        ("savings_ratio", 1.01),
        ("sends_money_home", -0.01),
        ("sends_money_home", 1.01),
        ("bhorsha_score", -0.01),
        ("bhorsha_score", 100.01),
        ("bhorsha_score", 150.0),
        ("loan_to_income", -0.01),
    ],
)
def test_feature_vector_out_of_bounds(field: str, bad_value: float) -> None:
    """Verify out-of-bounds values raise ValidationError for each feature."""
    with pytest.raises(ValidationError):
        FeatureVector(**{field: bad_value})


def test_feature_vector_extra_fields_forbidden() -> None:
    """Verify extra attributes are strictly forbidden."""
    with pytest.raises(ValidationError):
        FeatureVector(extra_field=123)  # type: ignore[call-arg]

    with pytest.raises(ValidationError):
        FeatureVector(credit_score=700)  # type: ignore[call-arg]


def test_feature_vector_nan_sanitization() -> None:
    """Verify NaN float values (Python float, np.float64, np.float32, pd.NA) are sanitized to None."""
    data = {
        "monthly_inflow_bdt": 12000.0,
        "income_volatility": float("nan"),
        "months_on_wallet": np.nan,
        "txn_per_month": np.float32(np.nan),
        "bills_on_time": pd.NA,
        "recharge_regularity": None,
        "bhorsha_score": np.float64(np.nan),
    }
    fv = FeatureVector(**data)
    assert fv.monthly_inflow_bdt == 12000.0
    assert fv.income_volatility is None
    assert fv.months_on_wallet is None
    assert fv.txn_per_month is None
    assert fv.bills_on_time is None
    assert fv.recharge_regularity is None
    assert fv.bhorsha_score is None

    # Verify non-dict inputs are returned untouched by sanitize_nan_values
    assert FeatureVector.sanitize_nan_values("not_a_dict") == "not_a_dict"


def test_feature_vector_model_validate_passthrough() -> None:
    """Verify model_validate accepts an existing FeatureVector without re-sanitizing."""
    fv = FeatureVector(monthly_inflow_bdt=15000.0, bhorsha_score=72.0)
    validated = FeatureVector.model_validate(fv)
    assert validated.monthly_inflow_bdt == 15000.0
    assert validated.bhorsha_score == 72.0


def test_to_dataframe_exact_order() -> None:
    """Verify 1-row DataFrame output matches expected feature ordering and dtypes."""
    fv = FeatureVector(
        monthly_inflow_bdt=14000.0,
        bills_on_time=0.97,
    )
    df = to_dataframe(fv)
    assert isinstance(df, pd.DataFrame)
    assert df.shape == (1, 10)
    assert list(df.columns) == list(get_feature_order())
    assert list(df.columns) == list(EXPECTED_10_FEATURES)
    assert df["monthly_inflow_bdt"].iloc[0] == 14000.0
    assert df["bills_on_time"].iloc[0] == 0.97
    assert np.isnan(df["savings_ratio"].iloc[0])
    assert np.isnan(df["bhorsha_score"].iloc[0])
    # Check all dtypes are float
    assert all(dtype == np.float64 for dtype in df.dtypes)


def test_to_dataframe_from_dict() -> None:
    """Verify to_dataframe supports raw dictionaries and sanitizes NaNs."""
    data = {
        "monthly_inflow_bdt": 20000.0,
        "months_on_wallet": 12.0,
        "savings_ratio": np.nan,
    }
    df = to_dataframe(data)
    assert df.shape == (1, 10)
    assert df["monthly_inflow_bdt"].iloc[0] == 20000.0
    assert df["months_on_wallet"].iloc[0] == 12.0
    assert np.isnan(df["savings_ratio"].iloc[0])


def test_to_dataframe_all_missing_rejected() -> None:
    """Verify that completely empty feature vectors raise AllFeaturesMissingError."""
    empty_fv = FeatureVector()
    assert empty_fv.is_empty()

    with pytest.raises(AllFeaturesMissingError, match="All features are missing"):
        to_dataframe(empty_fv)

    with pytest.raises(AllFeaturesMissingError, match="All features are missing"):
        to_dataframe({})

    with pytest.raises(AllFeaturesMissingError, match="All features are missing"):
        to_dataframe({f: np.nan for f in FEATURE_NAMES})

    with pytest.raises(AllFeaturesMissingError, match="All features are missing"):
        to_dataframe({f: None for f in FEATURE_NAMES})

    with pytest.raises(AllFeaturesMissingError, match="All features are missing"):
        to_dataframe({f: pd.NA for f in FEATURE_NAMES})


def test_to_dataframe_type_error() -> None:
    """Verify TypeError when invalid argument type is passed."""
    with pytest.raises(TypeError, match="Expected FeatureVector or dict"):
        to_dataframe([1, 2, 3])  # type: ignore[arg-type]

    with pytest.raises(TypeError, match="Expected FeatureVector or dict"):
        to_dataframe("invalid_str")  # type: ignore[arg-type]


def test_get_feature_order_fallback(monkeypatch: pytest.MonkeyPatch) -> None:
    """Verify get_feature_order falls back to canonical names if metadata fails."""

    def raise_meta(*args: object, **kwargs: object) -> dict[str, object]:
        raise RuntimeError("simulated error")

    monkeypatch.setattr("app.core.features.load_meta", raise_meta)
    order = get_feature_order()
    assert order == list(FEATURE_NAMES)

    # Empty or non-list features in meta
    monkeypatch.setattr("app.core.features.load_meta", lambda *args, **kwargs: {"features": []})
    assert get_feature_order() == list(FEATURE_NAMES)

    monkeypatch.setattr("app.core.features.load_meta", lambda *args, **kwargs: {"features": None})
    assert get_feature_order() == list(FEATURE_NAMES)


def test_zero_network_and_db_calls(monkeypatch: pytest.MonkeyPatch) -> None:
    """Verify core/features.py makes absolute zero network, DB, or external API calls."""
    import socket

    def blocked_socket(*args: object, **kwargs: object) -> None:
        raise AssertionError("Network socket call attempted in core/features!")

    monkeypatch.setattr(socket, "socket", blocked_socket)

    # Instantiate, sanitize, and convert to dataframe
    fv = FeatureVector(
        monthly_inflow_bdt=18000.0,
        bills_on_time=0.98,
        bhorsha_score=85.0,
    )
    df = to_dataframe(fv)
    assert df.shape == (1, 10)
    assert not fv.is_empty()

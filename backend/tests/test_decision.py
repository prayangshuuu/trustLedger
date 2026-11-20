"""Unit tests for the end-to-end score_applicant decision interface."""

import numpy as np
import pytest
from app.core.decision import Decision, score_applicant
from app.core.features import AllFeaturesMissingError, FeatureVector
from app.core.model import get_model_version, load_meta


def test_score_applicant_moon() -> None:
    """Verify Moon persona produces an approved decision in Good band with Bangla reasons."""
    moon_input = {
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

    decision = score_applicant(moon_input, group="F_urban")

    assert isinstance(decision, Decision)
    assert decision.approved is True
    assert decision.band == "Good"
    assert 650 <= decision.score < 750
    assert 0.0 <= decision.p_repay <= 1.0

    # Reasons checks
    assert "বিল সময়মতো পরিশোধ" in decision.good
    assert "বিল সময়মতো পরিশোধ" in decision.good_reasons
    assert "বিল সময়মতো পরিশোধ" in decision.reasons
    assert "নিয়মিত মোবাইল রিচার্জ" in decision.good
    assert "সঞ্চয় কম" in decision.bad
    assert "সঞ্চয় কম" in decision.bad_reasons
    assert "প্রতি মাসে আয়ের অন্তত ৫% সঞ্চয় করুন।" in decision.tips

    # Metadata audit trail
    meta = load_meta()
    assert decision.threshold_used == meta["group_thresholds"]["F_urban"]
    assert decision.model_version == get_model_version()
    assert decision.group == "F_urban"
    assert decision.evaluated_group == "F_urban"
    assert decision.timestamp is not None

    # Dict-like lookup
    assert decision["score"] == decision.score
    assert decision["approved"] == decision.approved


def test_score_applicant_zero_history() -> None:
    """Verify a zero-history applicant with only bhorsha_score receives a complete Decision."""
    zero_history = FeatureVector(
        bhorsha_score=75.0,
    )

    decision = score_applicant(zero_history, group="F_rural")

    assert isinstance(decision, Decision)
    assert isinstance(decision.score, int)
    assert 300 <= decision.score <= 900
    assert decision.band in ("Excellent", "Good", "Fair", "Building")
    assert isinstance(decision.approved, bool)
    assert len(decision.reasons) >= 1
    assert "ভরসা মূল্যায়নে ভালো ফল" in decision.good

    # Missing wallet features must NOT appear in reasons
    reasons_features = [r.feature for r in decision.reasons]
    assert "monthly_inflow_bdt" not in reasons_features
    assert "bills_on_time" not in reasons_features
    assert decision.evaluated_group == "F_rural"
    assert decision.timestamp is not None


def test_score_applicant_all_missing_rejected() -> None:
    """Verify completely missing input is rejected with a clear error."""
    with pytest.raises(AllFeaturesMissingError, match="All features are missing"):
        score_applicant({}, group="F_urban")

    empty_fv = FeatureVector()
    with pytest.raises(AllFeaturesMissingError, match="All features are missing"):
        score_applicant(empty_fv, group="M_rural")


def test_score_applicant_unknown_group_rejected() -> None:
    """Verify invalid demographic group raises ValueError."""
    fv = FeatureVector(bhorsha_score=60.0)
    with pytest.raises(ValueError, match="Unknown demographic group"):
        score_applicant(fv, group="NonExistentGroup")


def test_get_core_version() -> None:
    """Verify package version helper returns a semver string."""
    from app.core import get_core_version

    version = get_core_version()
    assert version == "0.1.0"


def test_score_applicant_zero_network_db(monkeypatch: pytest.MonkeyPatch) -> None:
    """Verify that score_applicant makes zero network, DB, or external API calls."""
    import socket

    def guarded_connect(*_args: object, **_kwargs: object) -> None:
        raise RuntimeError("Network call attempted in core logic!")

    monkeypatch.setattr(socket.socket, "connect", guarded_connect)
    monkeypatch.setattr(socket, "getaddrinfo", guarded_connect)

    moon_input = {
        "monthly_inflow_bdt": 14000.0,
        "income_volatility": 0.10,
        "months_on_wallet": 30.0,
        "txn_per_month": 18.0,
        "bills_on_time": 0.97,
        "recharge_regularity": 0.90,
        "savings_ratio": 0.04,
        "sends_money_home": 1.0,
        "loan_to_income": 4.0,
    }
    decision = score_applicant(moon_input, group="F_urban")
    assert decision.approved is True
    assert decision.score == 691

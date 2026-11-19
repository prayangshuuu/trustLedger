"""Unit tests for fairness thresholds, decision gating, and disparity audits."""

import pandas as pd
import pytest
from app.core.fairness import (
    VALID_GROUPS,
    FairnessAudit,
    audit,
    decide,
    get_group_threshold,
)
from app.core.model import load_meta


def test_get_group_threshold_from_meta() -> None:
    """Verify group thresholds are read dynamically from metadata."""
    meta = load_meta()
    meta_thresholds = meta["group_thresholds"]

    for group in VALID_GROUPS:
        thr = get_group_threshold(group)
        assert thr == float(meta_thresholds[group])


def test_get_group_threshold_unknown_group() -> None:
    """Verify unknown demographic group raises ValueError."""
    with pytest.raises(ValueError, match="Unknown demographic group 'Unknown_group'"):
        get_group_threshold("Unknown_group")


def test_thresholds_not_hardcoded(monkeypatch: pytest.MonkeyPatch) -> None:
    """Verify decide uses thresholds dynamically read from metadata, not hard-coded values."""
    custom_meta = load_meta().copy()
    custom_meta["group_thresholds"] = {
        "F_urban": 0.85,
        "F_rural": 0.50,
        "M_urban": 0.85,
        "M_rural": 0.50,
    }
    monkeypatch.setattr("app.core.fairness.load_meta", lambda *args, **kwargs: custom_meta)

    # With threshold 0.85, p=0.80 should be rejected
    assert not decide(0.80, "F_urban")
    # With threshold 0.50, p=0.60 should be approved
    assert decide(0.60, "F_rural")


def test_fairness_audit_with_ground_truth() -> None:
    """Verify fairness audit computes approval rate, TPR, FPR, and gaps."""
    records = [
        # F_urban
        {"group": "F_urban", "approved": 1, "repaid": 1},
        {"group": "F_urban", "approved": 1, "repaid": 1},
        {"group": "F_urban", "approved": 0, "repaid": 0},
        {"group": "F_urban", "approved": 0, "repaid": 0},
        # F_rural
        {"group": "F_rural", "approved": 1, "repaid": 1},
        {"group": "F_rural", "approved": 1, "repaid": 1},
        {"group": "F_rural", "approved": 0, "repaid": 0},
        {"group": "F_rural", "approved": 0, "repaid": 0},
    ]

    report = audit(records)
    assert isinstance(report, FairnessAudit)
    assert report.approval_rate_gap == 0.0
    assert report.tpr_gap == 0.0
    assert report.fpr_gap == 0.0
    assert report.equalized_odds_gap == 0.0
    assert report.fairness_ok is True
    assert report["approval_rate_gap"] == 0.0


def test_fairness_audit_gap_exceeded() -> None:
    """Verify fairness_ok is False when disparity exceeds 0.05 gate."""
    records = [
        {"group": "Group_A", "approved": 1},
        {"group": "Group_A", "approved": 1},
        {"group": "Group_B", "approved": 0},
        {"group": "Group_B", "approved": 0},
    ]
    report = audit(records)
    assert report.approval_rate_gap == 1.0
    assert report.fairness_ok is False


def test_fairness_audit_empty_or_missing_columns() -> None:
    """Verify error handling on invalid audit inputs."""
    with pytest.raises(ValueError, match="Cannot perform fairness audit on empty"):
        audit([])

    with pytest.raises(ValueError, match="Cannot perform fairness audit on empty"):
        audit(pd.DataFrame())

    with pytest.raises(ValueError, match="must contain 'group' column"):
        audit([{"approved": 1}])

    with pytest.raises(ValueError, match="must contain 'approved' column"):
        audit([{"group": "F_urban"}])

    with pytest.raises(TypeError, match="Unsupported decision element type"):
        audit([123])  # type: ignore[list-item]


def test_fairness_audit_dataframe_and_alternate_columns() -> None:
    """Verify audit works with DataFrame directly and shorthand column names g, a, y."""
    df_short = pd.DataFrame(
        [
            {"g": "F_urban", "a": 1, "y": 1},
            {"g": "F_urban", "a": 0, "y": 0},
            {"g": "M_rural", "a": 1, "y": 1},
            {"g": "M_rural", "a": 0, "y": 0},
        ]
    )
    report = audit(df_short)
    assert report.approval_rate_gap == 0.0
    assert report.tpr_gap == 0.0
    assert report.equalized_odds_gap == 0.0


def test_fairness_audit_with_objects() -> None:
    """Verify audit works with objects having model_dump or __dict__."""
    from app.core.decision import Decision
    from app.core.explain import Reason

    d = Decision(
        p_repay=0.9,
        score=700,
        band="Good",
        approved=True,
        reasons=[
            Reason(
                feature="bills_on_time",
                label="Bills paid on time",
                text="বিল সময়মতো পরিশোধ",
                impact=0.5,
                kind="good",
            )
        ],
        tips=[],
        threshold_used=0.7,
        model_version="1234567890abcdef",
        group="F_urban",
    )

    class CustomRecord:
        def __init__(self, group: str, approved: int, repaid: int) -> None:
            self.group = group
            self.approved = approved
            self.repaid = repaid

    records = [
        d,
        CustomRecord("M_urban", 0, 0),
    ]
    report = audit(records)
    assert "F_urban" in report.by_group
    assert "M_urban" in report.by_group


def test_fairness_audit_all_four_groups() -> None:
    """Verify audit correctly handles all four production demographic groups."""
    records = []
    # 50 records per group, equal approval rate
    for group in VALID_GROUPS:
        for i in range(50):
            records.append(
                {
                    "group": group,
                    "approved": 1 if i < 35 else 0,  # 70% approval rate across all groups
                    "repaid": 1 if i < 35 else 0,
                }
            )

    report = audit(records)
    assert len(report.by_group) == 4
    for group in VALID_GROUPS:
        assert group in report.by_group
        assert report.by_group[group].count == 50
        assert report.by_group[group].approval_rate == pytest.approx(0.70)
    assert report.approval_rate_gap == pytest.approx(0.0)
    assert report.fairness_ok is True


def test_fairness_audit_equalized_odds_violation() -> None:
    """Verify fairness_ok is False when equalized odds gap exceeds 0.05 even if approval gap <= 0.05."""
    records = [
        # Group A: 50% approval overall. Positives: 1 approved, 0 denied (TPR=1.0). Negatives: 0 approved, 1 denied (FPR=0.0)
        {"group": "F_urban", "approved": 1, "repaid": 1},
        {"group": "F_urban", "approved": 0, "repaid": 0},
        # Group B: 50% approval overall. Positives: 0 approved, 1 denied (TPR=0.0). Negatives: 1 approved, 0 denied (FPR=1.0)
        {"group": "M_rural", "approved": 0, "repaid": 1},
        {"group": "M_rural", "approved": 1, "repaid": 0},
    ]
    report = audit(records)
    # Both groups have 50% approval rate -> approval_rate_gap = 0.0 <= 0.05
    assert report.approval_rate_gap == pytest.approx(0.0)
    # TPR gap = 1.0 - 0.0 = 1.0 > 0.05
    assert report.tpr_gap == pytest.approx(1.0)
    assert report.equalized_odds_gap == pytest.approx(1.0)
    # fairness_ok MUST fail due to equalized odds violation
    assert report.fairness_ok is False


def test_fairness_zero_network_db(monkeypatch: pytest.MonkeyPatch) -> None:
    """Verify decide and audit make zero network, database, or external API calls."""
    import socket

    def guarded_connect(*_args: object, **_kwargs: object) -> None:
        raise RuntimeError("Network call attempted in fairness core logic!")

    monkeypatch.setattr(socket.socket, "connect", guarded_connect)
    monkeypatch.setattr(socket, "getaddrinfo", guarded_connect)

    decision = decide(0.75, "F_rural")
    assert isinstance(decision, bool)

    report = audit(
        [
            {"group": "F_rural", "approved": 1},
            {"group": "M_rural", "approved": 1},
        ]
    )
    assert report.fairness_ok is True

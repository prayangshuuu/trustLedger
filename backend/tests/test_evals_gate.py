"""The eval suite's fairness gate fails when thresholds are biased (proves CI would fail)."""

from app.core.model import load_meta
from evals.run_all import model_eval


def test_fair_thresholds_pass_the_gate() -> None:
    result = model_eval()
    assert result["auc"] > 0.75
    assert result["fairness"]["gate_ok"] is True
    assert result["fairness"]["after"]["approval_rate_gap"] <= 0.05


def test_biased_threshold_fails_the_gate() -> None:
    biased = dict(load_meta()["group_thresholds"])
    biased["F_rural"] = 0.85  # deliberately demand far more from rural women
    result = model_eval(thresholds=biased)
    assert result["fairness"]["gate_ok"] is False
    assert result["fairness"]["after"]["approval_rate_gap"] > 0.05

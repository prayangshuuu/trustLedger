"""Live evaluation tests marked with @pytest.mark.live, skipped without DEEPSEEK_API_KEY."""

import os

import pytest

from evals.live.evaluate_live import evaluate_cohort


@pytest.mark.live
def test_live_pipeline_20_users_agreement():
    """Verify live evaluation meets all targets when run with live key."""
    if not os.getenv("DEEPSEEK_API_KEY"):
        pytest.skip("DEEPSEEK_API_KEY not configured")

    rep = evaluate_cohort()
    metrics = rep["metrics"]
    assert metrics["sms_parsing_f1"] >= 0.90
    assert metrics["ocr_field_f1"] >= 0.90
    assert metrics["decision_agreement"] >= 0.95
    assert metrics["explanation_guard_violations"] == 0

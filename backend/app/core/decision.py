"""Decision pipeline combining scoring, explanation, and demographic fairness.

Provides the end-to-end score_applicant interface that transforms raw alternative features
into a fully explained, fairness-evaluated lending decision.
"""

from datetime import UTC, datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.core.explain import Reason, explain
from app.core.fairness import decide, get_group_threshold
from app.core.features import FeatureVector, to_dataframe
from app.core.model import get_model_version
from app.core.score import band, predict, to_score


class Decision(BaseModel):
    """Complete credit decision for an applicant."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    p_repay: float
    score: int
    band: str
    approved: bool
    reasons: list[Reason]
    tips: list[str]
    threshold_used: float
    model_version: str
    group: str
    evaluated_group: str = ""
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))

    def model_post_init(self, context: Any) -> None:
        if not self.evaluated_group:
            self.evaluated_group = self.group

    @property
    def good(self) -> list[str]:
        """Return list of Bangla positive reason strings."""
        return [r.text for r in self.reasons if r.kind == "good"]

    @property
    def bad(self) -> list[str]:
        """Return list of Bangla negative reason strings."""
        return [r.text for r in self.reasons if r.kind == "bad"]

    @property
    def good_reasons(self) -> list[str]:
        """Alias for positive reasons."""
        return self.good

    @property
    def bad_reasons(self) -> list[str]:
        """Alias for negative reasons."""
        return self.bad

    def __getitem__(self, item: str) -> Any:
        return getattr(self, item)


def score_applicant(
    features: FeatureVector | dict[str, Any],
    group: str,
) -> Decision:
    """Score an applicant and produce a complete, explained, fairness-checked Decision.

    Args:
        features: FeatureVector instance or dictionary containing alternative features.
        group: Demographic group identifier (e.g. 'F_urban', 'F_rural', 'M_urban', 'M_rural').

    Returns:
        Decision containing p_repay, score (300-900), risk band, approval status,
        Bangla reasons/tips, calibrated threshold used, and model version hash.

    Raises:
        AllFeaturesMissingError: If all features are None or NaN.
        ValueError: If demographic group is unrecognized.
    """
    # 1. Validate demographic group and obtain calibrated threshold
    threshold_used = get_group_threshold(group)

    # 2. Convert features to 1-row DataFrame (validates against all-missing inputs)
    df = to_dataframe(features)

    # 3. Predict repayment probability P(repay)
    p_repay = predict(df)

    # 4. Convert probability to standardized credit score (300-900)
    score_val = to_score(p_repay)

    # 5. Determine risk band
    band_val = band(score_val)

    # 6. Apply fair group threshold to decide approval
    approved = decide(p_repay, group)

    # 7. Generate SHAP feature attributions and Bangla reasons/tips
    explanation = explain(df)

    # 8. Obtain model version hash for audit trail
    model_version = get_model_version()

    return Decision(
        p_repay=p_repay,
        score=score_val,
        band=band_val,
        approved=approved,
        reasons=explanation.reasons,
        tips=explanation.tips,
        threshold_used=threshold_used,
        model_version=model_version,
        group=group,
        evaluated_group=group,
        timestamp=datetime.now(UTC),
    )

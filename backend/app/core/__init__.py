"""TrustLedger core domain logic package.

Contains pure domain scoring, explanation generation, fairness metrics, and
score scaling without direct I/O or database dependencies.
"""

from app.core.decision import Decision, score_applicant
from app.core.explain import Explanation, Reason
from app.core.fairness import FairnessAudit, GroupMetrics, audit, decide, get_group_threshold
from app.core.features import AllFeaturesMissingError, FeatureVector, to_dataframe
from app.core.model import clear_cache, get_model_dir, get_model_version, load_meta, load_model
from app.core.score import band, predict, to_score

CORE_MODULE_VERSION = "0.1.0"


def get_core_version() -> str:
    """Return the core module version string."""
    return CORE_MODULE_VERSION


__all__ = [
    "CORE_MODULE_VERSION",
    "AllFeaturesMissingError",
    "Decision",
    "Explanation",
    "FairnessAudit",
    "FeatureVector",
    "GroupMetrics",
    "Reason",
    "audit",
    "band",
    "clear_cache",
    "decide",
    "get_core_version",
    "get_group_threshold",
    "get_model_dir",
    "get_model_version",
    "load_meta",
    "load_model",
    "predict",
    "score_applicant",
    "to_dataframe",
    "to_score",
]

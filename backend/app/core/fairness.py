"""Demographic parity and fairness calibration engine for TrustLedger.

Applies group-calibrated thresholds to ensure fair credit access across demographic cohorts
(gender x region), and audits decisions for demographic parity and equalized odds gaps.
"""

from collections.abc import Sequence
from typing import Any

import numpy as np
import pandas as pd
from pydantic import BaseModel

from app.core.model import load_meta

VALID_GROUPS: tuple[str, ...] = ("F_rural", "F_urban", "M_rural", "M_urban")


class GroupMetrics(BaseModel):
    """Demographic group fairness evaluation metrics."""

    group: str
    count: int
    approval_rate: float
    tpr: float | None = None
    fpr: float | None = None


class FairnessAudit(BaseModel):
    """Audit summary containing per-group metrics and inter-group disparity gaps."""

    by_group: dict[str, GroupMetrics]
    approval_rate_gap: float
    tpr_gap: float | None = None
    fpr_gap: float | None = None
    equalized_odds_gap: float | None = None
    fairness_ok: bool

    def __getitem__(self, item: str) -> Any:
        return getattr(self, item)


def get_group_threshold(group: str) -> float:
    """Retrieve calibrated decision threshold for a specific demographic group.

    Args:
        group: Demographic segment, e.g. 'F_rural', 'F_urban', 'M_rural', 'M_urban'.

    Returns:
        float: Minimum P(repay) required for approval in that group.

    Raises:
        ValueError: If group is not present in model metadata.
    """
    meta = load_meta()
    group_thresholds: dict[str, float] = meta.get("group_thresholds", {})
    if group not in group_thresholds:
        valid_keys = list(group_thresholds.keys()) if group_thresholds else list(VALID_GROUPS)
        raise ValueError(
            f"Unknown demographic group '{group}'. Expected one of: {', '.join(valid_keys)}"
        )
    return float(group_thresholds[group])


def decide(p_repay: float, group: str) -> bool:
    """Make approval decision for an applicant based on their group-calibrated threshold.

    Args:
        p_repay: Predicted repayment probability in [0.0, 1.0].
        group: Demographic group identifier.

    Returns:
        bool: True if p_repay >= group threshold, False otherwise.
    """
    threshold = get_group_threshold(group)
    return bool(p_repay >= threshold)


def audit(decisions: Sequence[Any] | pd.DataFrame) -> FairnessAudit:
    """Audit a collection of lending decisions across demographic groups.

    Evaluates approval rates, True Positive Rates (TPR), and False Positive Rates (FPR),
    and checks if demographic parity and equalized odds gaps satisfy the <= 0.05 standard.

    Args:
        decisions: Sequence of Decision objects, dictionaries, or a DataFrame with
            at least 'group' and 'approved' (and optionally 'repaid' or 'y').

    Returns:
        FairnessAudit report with per-group metrics, gaps, and pass/fail gate.

    Raises:
        ValueError: If decisions collection is empty.
    """
    if isinstance(decisions, pd.DataFrame):
        df = decisions.copy()
    else:
        if len(decisions) == 0:
            raise ValueError("Cannot perform fairness audit on empty decisions list.")
        rows: list[dict[str, Any]] = []
        for item in decisions:
            if isinstance(item, dict):
                rows.append(item)
            elif hasattr(item, "model_dump"):
                rows.append(item.model_dump())
            elif hasattr(item, "__dict__"):
                rows.append(vars(item))
            else:
                raise TypeError(f"Unsupported decision element type: {type(item).__name__}")
        df = pd.DataFrame(rows)

    if df.empty:
        raise ValueError("Cannot perform fairness audit on empty decisions table.")

    if "group" not in df.columns:
        if "g" in df.columns:
            df["group"] = df["g"]
        else:
            raise ValueError("Decisions must contain 'group' column.")

    if "approved" not in df.columns:
        if "a" in df.columns:
            df["approved"] = df["a"]
        else:
            raise ValueError("Decisions must contain 'approved' column.")

    df["approved"] = pd.to_numeric(df["approved"], errors="coerce").fillna(0).astype(int)

    has_truth = False
    if "repaid" in df.columns and not df["repaid"].isna().all():
        has_truth = True
        df["repaid"] = pd.to_numeric(df["repaid"], errors="coerce")
    elif "y" in df.columns and not df["y"].isna().all():
        has_truth = True
        df["repaid"] = pd.to_numeric(df["y"], errors="coerce")

    by_group: dict[str, GroupMetrics] = {}
    groups = df["group"].unique()

    for g in groups:
        g_str = str(g)
        gdf = df[df["group"] == g]
        count = len(gdf)
        app_rate = float(gdf["approved"].mean()) if count > 0 else 0.0

        tpr_val: float | None = None
        fpr_val: float | None = None
        if has_truth:
            pos = gdf[gdf["repaid"] == 1]
            neg = gdf[gdf["repaid"] == 0]
            if len(pos) > 0:
                tpr_val = float(pos["approved"].mean())
            if len(neg) > 0:
                fpr_val = float(neg["approved"].mean())

        by_group[g_str] = GroupMetrics(
            group=g_str,
            count=count,
            approval_rate=app_rate,
            tpr=tpr_val,
            fpr=fpr_val,
        )

    rates = [m.approval_rate for m in by_group.values()]
    approval_rate_gap = float(np.max(rates) - np.min(rates)) if rates else 0.0

    tpr_gap: float | None = None
    fpr_gap: float | None = None
    equalized_odds_gap: float | None = None

    if has_truth:
        tprs = [m.tpr for m in by_group.values() if m.tpr is not None]
        fprs = [m.fpr for m in by_group.values() if m.fpr is not None]
        if tprs and fprs:
            tpr_gap = float(np.max(tprs) - np.min(tprs))
            fpr_gap = float(np.max(fprs) - np.min(fprs))
            equalized_odds_gap = max(tpr_gap, fpr_gap)

    # Fairness rule per PLAN_CONTEXT.md: disparity gaps must be <= 0.05
    fairness_ok = approval_rate_gap <= 0.05 and (
        equalized_odds_gap is None or equalized_odds_gap <= 0.05
    )

    return FairnessAudit(
        by_group=by_group,
        approval_rate_gap=approval_rate_gap,
        tpr_gap=tpr_gap,
        fpr_gap=fpr_gap,
        equalized_odds_gap=equalized_odds_gap,
        fairness_ok=fairness_ok,
    )

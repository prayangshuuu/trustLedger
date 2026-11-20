"""Explainer: SHAP reasons + RAG-grounded Bangla tips + an LLM summary that may only mention
features present in the SHAP output (rule-checked, template fallback)."""

import logging
from typing import Any

from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.agents.prompts import load_prompt
from app.core.decision import Decision
from app.core.explain import ENGLISH_FEATURE_LABELS
from app.core.model import load_meta
from app.llm.client import get_llm_client, register_mock_task
from app.rag.tips import GroundedTip, ground_tips

logger = logging.getLogger("trustledger.explainer")


class ExplainerOutput(BaseModel):
    summary_bn: str
    summary_source: str  # "llm" | "template"
    grounded_tips: list[GroundedTip]
    mentioned_features: list[str]


class _Summary(BaseModel):
    summary_bn: str


def template_summary(decision: Decision) -> str:
    good = [r.text for r in decision.reasons if r.kind == "good"]
    bad = [r.text for r in decision.reasons if r.kind == "bad"]
    parts = [f"আপনার ট্রাস্টলেজার স্কোর {decision.score}।"]
    if good:
        parts.append("স্কোর বাড়িয়েছে: " + ", ".join(good) + "।")
    if bad:
        parts.append("উন্নতির সুযোগ: " + ", ".join(bad) + "।")
    return " ".join(parts)


def _mock_explainer(system: str, user_content: str) -> dict[str, Any]:
    return {"summary_bn": user_content.split("<template>", 1)[-1].split("</template>", 1)[0]}


register_mock_task("explainer_agent", _mock_explainer)


def feature_mentions(text: str) -> set[str]:
    """Features whose Bangla reason strings or English labels appear in text."""
    reasons: dict[str, list[str]] = load_meta().get("reasons", {})
    lowered = text.lower()
    found: set[str] = set()
    for feature, phrases in reasons.items():
        if (
            any(p and p in text for p in phrases)
            or ENGLISH_FEATURE_LABELS.get(feature, "#").lower() in lowered
        ):
            found.add(feature)
    return found


def explain_decision(db: Session | None, decision: Decision) -> ExplainerOutput:
    shap_features = {r.feature for r in decision.reasons}
    template = template_summary(decision)
    reasons_xml = "\n".join(f"- {r.feature} ({r.kind}): {r.text}" for r in decision.reasons)
    summary, source = template, "template"
    try:
        result = get_llm_client().chat(
            [
                {"role": "system", "content": load_prompt("explainer_agent")},
                {
                    "role": "user",
                    "content": f"<score>{decision.score}</score>\n<shap_reasons>\n{reasons_xml}\n"
                    f"</shap_reasons>\n<template>{template}</template>",
                },
            ],
            schema=_Summary,
            temperature=0.2,
        )
        candidate = result.summary_bn.strip()
        # Rule check: the summary may only mention SHAP features
        if candidate and feature_mentions(candidate) <= shap_features:
            summary, source = candidate, "llm"
    except Exception:  # noqa: BLE001 - template is always a valid explanation
        logger.warning("explainer LLM call failed; using template summary")

    tip_pairs = []
    tips_meta: dict[str, str] = load_meta().get("tips", {})
    for r in decision.reasons:
        if r.kind == "bad" and r.feature in tips_meta:
            tip_pairs.append((r.feature, tips_meta[r.feature]))
    return ExplainerOutput(
        summary_bn=summary,
        summary_source=source,
        grounded_tips=ground_tips(db, tip_pairs),
        mentioned_features=sorted(feature_mentions(summary)),
    )

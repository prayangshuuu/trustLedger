"""Bhorsha psychometric scoring engine with rubric evaluation and anti-gaming controls.

Assesses borrower character, financial discipline, risk tolerance, and consistency
through conversational scenarios, outputting a calibrated bhorsha_score in [0, 100].
"""

import re
from collections import defaultdict
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, Field

from app.llm.client import get_llm_client, register_mock_task
from app.privacy.redaction import redact_pii

QUESTIONS_FILE = Path(__file__).resolve().parent / "questions.yaml"
PROMPTS_DIR = Path(__file__).resolve().parent / "prompts"


class AnswerEvaluation(BaseModel):
    """Evaluation result for a single question response."""

    question_id: str
    dimension: str
    score: float = Field(..., ge=0.0, le=100.0)
    rationale: str
    anti_gaming_flags: list[str] = Field(default_factory=list)


class BhorshaScoreResult(BaseModel):
    """Aggregate outcome of the Bhorsha psychometric assessment."""

    bhorsha_score: float = Field(
        ..., ge=0.0, le=100.0, description="Overall Bhorsha credit trustworthiness score"
    )
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence in assessment validity")
    dimension_scores: dict[str, float] = Field(
        ..., description="Breakdown across psychometric dimensions"
    )
    anti_gaming_flags: list[str] = Field(
        default_factory=list, description="Triggered integrity and anti-gaming warnings"
    )
    is_consistent: bool = Field(
        ..., description="True if paired question answers align without major contradictions"
    )


def load_question_bank() -> list[dict[str, Any]]:
    """Load question bank and rubrics from questions.yaml."""
    if not QUESTIONS_FILE.exists():
        return []
    with open(QUESTIONS_FILE, encoding="utf-8") as f:
        data = yaml.safe_load(f)
        return list(data.get("questions", []))


class RubricScore(BaseModel):
    """Final JSON kept from the rubric rater (its reasoning is never stored)."""

    score: float = Field(..., ge=0.0, le=100.0)
    rationale: str = ""


def load_prompt(name: str) -> str:
    return (PROMPTS_DIR / f"{name}.md").read_text(encoding="utf-8")


def prompt_version(name: str) -> str:
    match = re.search(r'version="([^"]+)"', load_prompt(name))
    return match.group(1) if match else "unknown"


def heuristic_rubric_score(text: str) -> tuple[float, str]:
    """Deterministic keyword rubric used by the offline mock and as a live-mode fallback."""
    text = text.strip().lower()
    # Positive behavioral tokens
    positive_signals = (
        "আলাদা",
        "সঞ্চয়",
        "ডিপিএস",
        "বাজেট",
        "তালিকা",
        "পরিকল্পনা",
        "নিয়মিত",
        "ঋণ শোধ",
        "কিস্তি",
        "জরুরি",
        "ইমার্জেন্সি",
        "না করে দেব",
        "ঝুঁকি",
        "ফেরত",
        "দায়িত্ব",
        "save",
        "budget",
        "plan",
        "emergency",
        "repay",
        "refuse",
        "return",
        "responsible",
    )
    # Negative behavioral tokens
    negative_signals = (
        "খরচ করে ফেলি",
        "লটারি",
        "দ্বিগুণ",
        "দাদন",
        "বন্ধক",
        "ধার করি",
        "পরোয়া করি না",
        "ভুলে যাই",
        "লাভের আশা",
        "রেখে দেব",
        "চুপচাপ",
        "ভাগ্যের",
        "উড়িয়ে",
        "spend all",
        "lottery",
        "gamble",
        "ignore",
        "keep",
    )

    pos_count = sum(1 for token in positive_signals if token in text)
    neg_count = sum(1 for token in negative_signals if token in text)

    base_score = 65.0
    if pos_count > neg_count:
        base_score = min(100.0, 75.0 + (pos_count * 8.0))
        rationale = "Applicant demonstrates forward planning, disciplined habits, and responsible risk awareness."
    elif neg_count > pos_count:
        base_score = max(20.0, 45.0 - (neg_count * 8.0))
        rationale = "Applicant indicates impulsive spending, lack of contingency savings, or speculative risk taking."
    else:
        # Default moderate score
        base_score = 60.0
        rationale = "Applicant response reflects standard pragmatic household management."

    return base_score, rationale


def _mock_rubric(system: str, user_content: str) -> dict[str, Any]:
    answer = user_content.split("<answer>", 1)[-1].split("</answer>", 1)[0]
    score, rationale = heuristic_rubric_score(answer)
    return {"score": score, "rationale": rationale}


register_mock_task("bhorsha_rubric", _mock_rubric)


def rubric_score(question: dict[str, Any], answer_text: str) -> tuple[float, str]:
    """Score one answer against its rubric via LLMClient; falls back to the heuristic on error."""
    rubric = question.get("rubric", {})
    user = (
        f"<question>{question.get('bangla', '')} ({question.get('english', '')})</question>\n"
        f"<rubric>strong: {rubric.get('strong', '')}\nmoderate: {rubric.get('moderate', '')}\n"
        f"weak: {rubric.get('weak', '')}</rubric>\n"
        f"<answer>{redact_pii(answer_text)}</answer>"
    )
    try:
        result = get_llm_client().chat(
            [
                {"role": "system", "content": load_prompt("scorer")},
                {"role": "user", "content": user},
            ],
            schema=RubricScore,
        )
        return float(result.score), str(result.rationale)
    except Exception:  # noqa: BLE001 - never fail an interview because of the LLM
        return heuristic_rubric_score(answer_text)


def evaluate_single_answer(
    question: dict[str, Any],
    answer_text: str,
    elapsed_seconds: float = 10.0,
    previous_answers: list[str] | None = None,
) -> AnswerEvaluation:
    """Evaluate a single user answer against the dimension rubric with anti-gaming checks."""
    flags: list[str] = []
    text = answer_text.strip().lower()

    # 1. Anti-gaming check: Suspiciously fast submission (< 2 seconds)
    if elapsed_seconds < 2.0:
        flags.append("rapid_submission")

    # 2. Anti-gaming check: Repeated identical answer
    if previous_answers and any(text == prev.strip().lower() for prev in previous_answers):
        flags.append("duplicate_answer")

    # 3. Anti-gaming check: Monosyllabic / evasive non-response
    if len(text.split()) < 3 and text in ("হ্যাঁ", "না", "হুম", "yes", "no", "ok", "ভালো"):
        flags.append("minimal_response")

    # 4. Rubric score from the LLM (mock mode uses the deterministic heuristic below)
    base_score, rationale = rubric_score(question, text)

    # Apply anti-gaming penalties
    if "rapid_submission" in flags:
        base_score = max(10.0, base_score - 15.0)
    if "duplicate_answer" in flags:
        base_score = max(10.0, base_score - 25.0)
    if "minimal_response" in flags:
        base_score = max(15.0, base_score - 10.0)

    return AnswerEvaluation(
        question_id=question["id"],
        dimension=question["dimension"],
        score=round(base_score, 2),
        rationale=rationale,
        anti_gaming_flags=flags,
    )


def compute_bhorsha_score(
    evaluations: list[AnswerEvaluation],
    question_bank: list[dict[str, Any]],
) -> BhorshaScoreResult:
    """Aggregate per-question rubric scores, check consistency pairs, and compute final Bhorsha metrics."""
    if not evaluations:
        return BhorshaScoreResult(
            bhorsha_score=50.0,
            confidence=0.0,
            dimension_scores={},
            anti_gaming_flags=["empty_session"],
            is_consistent=False,
        )

    eval_map = {e.question_id: e for e in evaluations}
    q_map = {q["id"]: q for q in question_bank}

    # 1. Dimension breakdowns
    dim_scores: dict[str, list[float]] = defaultdict(list)
    all_flags: list[str] = []

    for ev in evaluations:
        dim_scores[ev.dimension].append(ev.score)
        all_flags.extend(ev.anti_gaming_flags)

    averaged_dims = {
        dim: round(float(sum(scores) / len(scores)), 2) for dim, scores in dim_scores.items()
    }

    # 2. Consistency Pair Verification
    consistency_penalties = 0.0
    contradictions = 0
    checked_pairs: set[tuple[str, str]] = set()

    for qid, ev in eval_map.items():
        q_def = q_map.get(qid)
        if not q_def:
            continue
        pair_id = q_def.get("pair_id")
        if pair_id and pair_id in eval_map:
            pair_key = tuple(sorted([qid, pair_id]))
            if pair_key in checked_pairs:
                continue
            checked_pairs.add((pair_key[0], pair_key[1]))

            pair_ev = eval_map[pair_id]
            diff = abs(ev.score - pair_ev.score)
            if diff > 35.0:
                contradictions += 1
                consistency_penalties += (diff - 35.0) * 0.5
                all_flags.append(f"inconsistency_pair_{qid}_{pair_id}")

    # 3. Overall composite Bhorsha Score [0, 100]
    raw_avg = sum(e.score for e in evaluations) / len(evaluations)
    final_score = max(0.0, min(100.0, raw_avg - consistency_penalties))

    # Confidence based on turn completion and gaming indicators
    completion_ratio = min(1.0, len(evaluations) / 10.0)
    flag_penalty = min(0.4, len(all_flags) * 0.1)
    confidence = round(max(0.2, completion_ratio - flag_penalty), 2)
    is_consistent = contradictions == 0

    return BhorshaScoreResult(
        bhorsha_score=round(final_score, 1),
        confidence=confidence,
        dimension_scores=averaged_dims,
        anti_gaming_flags=sorted(set(all_flags)),
        is_consistent=is_consistent,
    )

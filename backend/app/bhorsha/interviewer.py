"""Bhorsha conversational interviewer session manager and feature snapshot updater."""

import uuid
from typing import Any

from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.bhorsha.scorer import (
    AnswerEvaluation,
    BhorshaScoreResult,
    compute_bhorsha_score,
    evaluate_single_answer,
    load_prompt,
    load_question_bank,
)
from app.db.models import FeatureSnapshot, User
from app.llm.client import get_llm_client, register_mock_task
from app.privacy.redaction import redact_pii

DEFAULT_ACK = "ধন্যবাদ, আপনার উত্তরটি লিপিবদ্ধ করা হয়েছে।"
OFF_TOPIC_REPLY = (
    "দুঃখিত, এই আলাপে আমি শুধু আপনার দৈনন্দিন টাকা-পয়সার অভ্যাস নিয়ে প্রশ্ন করতে পারি। চলুন প্রশ্নটিতে ফিরে যাই।"
)
OFF_TOPIC_MARKERS = (
    "cricket",
    "ক্রিকেট",
    "football",
    "ফুটবল",
    "joke",
    "কৌতুক",
    "জোকস",
    "weather",
    "আবহাওয়া",
    "politics",
    "রাজনীতি",
    "নির্বাচন",
    "homework",
    "movie",
    "সিনেমা",
    "ignore previous",
    "ignore your instructions",
    "system prompt",
    "আগের নির্দেশ",
)


class InterviewerTurn(BaseModel):
    acknowledgement: str = DEFAULT_ACK
    off_topic: bool = False


def _mock_interviewer(system: str, user_content: str) -> dict[str, Any]:
    answer = user_content.split("<answer>", 1)[-1].split("</answer>", 1)[0].lower()
    off_topic = any(m in answer for m in OFF_TOPIC_MARKERS)
    return {"acknowledgement": DEFAULT_ACK, "off_topic": off_topic}


register_mock_task("bhorsha_interviewer", _mock_interviewer)


def interviewer_turn(question: dict[str, Any], answer_text: str) -> InterviewerTurn:
    """Ask the interviewer LLM for a warm acknowledgement and an off-topic check."""
    user = f"<question>{question['bangla']}</question>\n<answer>{redact_pii(answer_text)}</answer>"
    try:
        result = get_llm_client().chat(
            [
                {"role": "system", "content": load_prompt("interviewer")},
                {"role": "user", "content": user},
            ],
            schema=InterviewerTurn,
            temperature=0.3,
        )
        return InterviewerTurn.model_validate(result)
    except Exception:  # noqa: BLE001 - fall back to the static acknowledgement
        return InterviewerTurn()


class BhorshaSessionState(BaseModel):
    """In-memory or persistent state of an ongoing Bhorsha psychometric session."""

    session_id: str
    user_id: str
    current_index: int = 0
    evaluations: list[AnswerEvaluation] = Field(default_factory=list)
    answers: list[str] = Field(default_factory=list)
    completed: bool = False


# In-memory session registry (suitable for local dev & single-node demo)
_sessions: dict[str, BhorshaSessionState] = {}


def start_bhorsha_session(user_id: str) -> tuple[str, dict[str, Any]]:
    """Initialize a new Bhorsha assessment session and return the first question."""
    questions = load_question_bank()
    if not questions:
        raise RuntimeError("Bhorsha question bank is empty.")

    session_id = f"bhorsha_{uuid.uuid4().hex[:12]}"
    state = BhorshaSessionState(
        session_id=session_id,
        user_id=user_id,
        current_index=0,
    )
    _sessions[session_id] = state

    first_q = questions[0]
    return session_id, {
        "question_id": first_q["id"],
        "dimension": first_q["dimension"],
        "question_text": first_q["bangla"],
        "english_translation": first_q["english"],
        "turn": 1,
        "total_turns": min(12, len(questions)),
    }


def answer_bhorsha_question(
    session_id: str,
    answer_text: str,
    elapsed_seconds: float = 10.0,
) -> dict[str, Any]:
    """Process an applicant's answer, score it, and advance to the next scenario."""
    state = _sessions.get(session_id)
    if not state:
        raise KeyError(f"Bhorsha session '{session_id}' not found.")

    if state.completed:
        return {
            "completed": True,
            "message": "মূল্যায়ন সম্পূর্ণ হয়েছে। আপনি এখন আপনার ফলাফল দেখতে পারেন।",
        }

    questions = load_question_bank()
    curr_q = questions[state.current_index]

    turn = interviewer_turn(curr_q, answer_text)
    if turn.off_topic:
        # Re-ask the same question; off-topic messages are neither scored nor stored
        return {
            "completed": False,
            "off_topic": True,
            "turn": state.current_index + 1,
            "total_turns": min(12, len(questions)),
            "acknowledgement": OFF_TOPIC_REPLY,
            "question_id": curr_q["id"],
            "dimension": curr_q["dimension"],
            "question_text": curr_q["bangla"],
            "english_translation": curr_q["english"],
        }

    # Evaluate answer against rubric and anti-gaming rules
    evaluation = evaluate_single_answer(
        question=curr_q,
        answer_text=answer_text,
        elapsed_seconds=elapsed_seconds,
        previous_answers=state.answers,
    )

    state.evaluations.append(evaluation)
    state.answers.append(answer_text)
    state.current_index += 1

    # Check if all questions or maximum turns reached
    if state.current_index >= min(12, len(questions)):
        state.completed = True
        return {
            "completed": True,
            "turn": state.current_index,
            "message": "ধন্যবাদ! আপনার সকল উত্তরের ভিত্তিতে ভরসা মূল্যায়ন সম্পন্ন হয়েছে।",
        }

    next_q = questions[state.current_index]
    return {
        "completed": False,
        "turn": state.current_index + 1,
        "total_turns": min(12, len(questions)),
        "acknowledgement": turn.acknowledgement,
        "question_id": next_q["id"],
        "dimension": next_q["dimension"],
        "question_text": next_q["bangla"],
        "english_translation": next_q["english"],
    }


def get_bhorsha_result(
    session_id: str,
    db: Session | None = None,
) -> BhorshaScoreResult:
    """Compute aggregate Bhorsha score and persist directly into user's feature snapshot."""
    state = _sessions.get(session_id)
    if not state:
        raise KeyError(f"Bhorsha session '{session_id}' not found.")

    questions = load_question_bank()
    result = compute_bhorsha_score(state.evaluations, questions)

    # Persist score into applicant FeatureSnapshot in database
    if db is not None:
        user = db.scalars(select(User).where(User.id == state.user_id)).first()
        if user:
            latest_snap = db.scalars(
                select(FeatureSnapshot)
                .where(FeatureSnapshot.user_id == user.id)
                .order_by(FeatureSnapshot.created_at.desc())
            ).first()

            if latest_snap:
                features_dict = dict(latest_snap.features)
                features_dict["bhorsha_score"] = result.bhorsha_score
                latest_snap.features = features_dict
            else:
                new_snap = FeatureSnapshot(
                    user_id=user.id,
                    features={"bhorsha_score": result.bhorsha_score},
                    source_summary="Bhorsha psychometric assessment",
                )
                db.add(new_snap)
            db.commit()

    return result

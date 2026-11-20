"""Unit and integration tests for Bhorsha psychometric chat assessment."""

from app.bhorsha.interviewer import (
    answer_bhorsha_question,
    get_bhorsha_result,
    start_bhorsha_session,
)
from app.bhorsha.scorer import (
    compute_bhorsha_score,
    evaluate_single_answer,
    load_question_bank,
)
from app.db.base import Base
from app.db.models import FeatureSnapshot, User
from app.db.session import create_app_engine, get_db
from app.main import create_app
from app.privacy.consent import grant_consent
from fastapi.testclient import TestClient
from sqlalchemy.orm import sessionmaker


def test_question_bank_and_rubrics_loaded() -> None:
    """Verify questions.yaml contains >= 10 questions with rubrics, dimensions, and pairs."""
    questions = load_question_bank()
    assert len(questions) >= 10

    dimensions = {q["dimension"] for q in questions}
    assert "planning" in dimensions
    assert "saving" in dimensions
    assert "risk" in dimensions
    assert "consistency" in dimensions
    assert "emergency" in dimensions

    pairs = [q for q in questions if q.get("pair_id")]
    assert len(pairs) >= 4, "Expected paired consistency questions"


def test_responsible_persona_scores_higher_than_careless() -> None:
    """Verify responsible financial mindset scores significantly higher than careless/impulsive."""
    questions = load_question_bank()

    # 1. Responsible persona
    responsible_evals = []
    for q in questions:
        ans = (
            "আমি মাসের শুরুতে নির্দিষ্ট বাজেট করি, প্রতি মাসে ডিপিএস ও জরুরি তহবিলে টাকা সঞ্চয় করি, "
            "ঝুঁকিপূর্ণ লটারি বা স্কিমে যাই না এবং ঋণের কিস্তি সবার আগে শোধ করি।"
        )
        ev = evaluate_single_answer(q, ans, elapsed_seconds=8.0)
        responsible_evals.append(ev)

    res_result = compute_bhorsha_score(responsible_evals, questions)
    assert res_result.bhorsha_score >= 75.0
    assert res_result.is_consistent is True

    # 2. Careless persona
    careless_evals = []
    for q in questions:
        ans = (
            "টাকা আসলে সব খরচ করে ফেলি, লটারি খেলে রাতারাতি দ্বিগুণ লাভের আশা করি, "
            "কিস্তির কথা ভুলে যাই আর টান পড়লে উচ্চ সুদে দাদন নিই।"
        )
        ev = evaluate_single_answer(q, ans, elapsed_seconds=8.0)
        careless_evals.append(ev)

    careless_result = compute_bhorsha_score(careless_evals, questions)
    assert careless_result.bhorsha_score <= 50.0

    # 3. Score stability check (deterministic output for same answers)
    evals_retry = [
        evaluate_single_answer(
            q,
            "আমি মাসের শুরুতে নির্দিষ্ট বাজেট করি, প্রতি মাসে ডিপিএস ও জরুরি তহবিলে টাকা সঞ্চয় করি, "
            "ঝুঁকিপূর্ণ লটারি বা স্কিমে যাই না এবং ঋণের কিস্তি সবার আগে শোধ করি।",
            elapsed_seconds=8.0,
        )
        for q in questions
    ]
    retry_result = compute_bhorsha_score(evals_retry, questions)
    assert retry_result.bhorsha_score == res_result.bhorsha_score


def test_anti_gaming_detection() -> None:
    """Verify detection of rapid answering and identical copy-pasted responses."""
    questions = load_question_bank()

    # 1. Rapid submission (< 2s)
    rapid_ev = evaluate_single_answer(questions[0], "ভালো বাজেট করি", elapsed_seconds=0.8)
    assert "rapid_submission" in rapid_ev.anti_gaming_flags

    # 2. Repeated duplicate answer
    dup_ev = evaluate_single_answer(
        questions[1],
        "ভালো বাজেট করি",
        elapsed_seconds=5.0,
        previous_answers=["ভালো বাজেট করি"],
    )
    assert "duplicate_answer" in dup_ev.anti_gaming_flags


def test_bhorsha_session_lifecycle_and_max_12_turns() -> None:
    """Verify session starts, steps through questions, and terminates in <= 12 turns."""
    session_id, first_q = start_bhorsha_session("user-test-session")
    assert session_id.startswith("bhorsha_")
    assert first_q["turn"] == 1
    assert first_q["total_turns"] <= 12

    turns = 1
    completed = False
    for _ in range(15):
        resp = answer_bhorsha_question(session_id, "আমি নিয়ম মেনে খরচের পরিকল্পনা করি ও ডিপিএস করি।")
        if resp["completed"]:
            completed = True
            break
        turns += 1

    assert completed is True
    assert turns <= 12

    result = get_bhorsha_result(session_id)
    assert 0.0 <= result.bhorsha_score <= 100.0


def test_zero_history_user_completes_bhorsha_and_gets_full_score_decision() -> None:
    """End-to-end integration: zero-history user completes Bhorsha, updates snapshot, and receives score decision."""
    engine = create_app_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db_session = TestingSessionLocal()

    app = create_app()
    app.dependency_overrides[get_db] = lambda: db_session
    client = TestClient(app)

    try:
        # 1. Create zero-history applicant
        user = User(
            id="user-zero-history-1",
            phone_hash="zero_phone_1",
            gender="F",
            region="rural",
            division="Rangpur",
        )
        db_session.add(user)
        db_session.commit()

        # 2. Grant bhorsha consent
        grant_consent(db_session, user.id, "bhorsha")

        # 3. Start Bhorsha session
        start_resp = client.post("/bhorsha/start", json={"user_id": user.id})
        assert start_resp.status_code == 201
        session_id = start_resp.json()["session_id"]

        # 4. Answer scenarios
        for _ in range(12):
            ans_resp = client.post(
                f"/bhorsha/{session_id}/answer",
                json={
                    "answer": "নিয়মিত সঞ্চয় করি এবং পরিবারের জরুরি প্রয়োজনের জন্য টাকা আলাদা রাখি।",
                    "elapsed_seconds": 6.0,
                },
            )
            if ans_resp.json()["completed"]:
                break

        # 5. Fetch result -> writes bhorsha_score to FeatureSnapshot
        res_resp = client.get(f"/bhorsha/{session_id}/result")
        assert res_resp.status_code == 200
        bhorsha_data = res_resp.json()
        assert bhorsha_data["bhorsha_score"] >= 70.0

        # Verify FeatureSnapshot was persisted in DB
        snap = db_session.query(FeatureSnapshot).filter_by(user_id=user.id).first()
        assert snap is not None
        assert snap.features["bhorsha_score"] == bhorsha_data["bhorsha_score"]

        # 6. Call /score with user_id — resolves snapshot with only bhorsha_score and scores applicant
        score_resp = client.post("/score", json={"user_id": user.id, "amount_bdt": 10000.0})
        assert score_resp.status_code == 200
        score_data = score_resp.json()
        assert "p_repay" in score_data
        assert "score" in score_data
        assert "band" in score_data
        assert "approved" in score_data
        assert len(score_data["reasons"]) > 0
    finally:
        db_session.close()

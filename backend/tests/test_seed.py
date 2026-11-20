"""Unit tests for the seed script and demo personas creation."""

import pytest
from app.db.base import Base
from app.db.models import DecisionRecord, FeatureSnapshot, User
from scripts.seed_demo import hash_phone, seed_demo_personas
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool


@pytest.fixture
def session() -> Session:
    """Provide an isolated in-memory SQLite session."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    session_factory = sessionmaker(bind=engine)
    sess = session_factory()
    try:
        yield sess
    finally:
        sess.close()


def test_seed_demo_personas(session: Session) -> None:
    """Verify seed script creates the 3 demo personas with expected attributes and decisions."""
    users = seed_demo_personas(session)
    assert len(users) == 4

    # 1. Moon Persona (Garment worker, F_urban)
    moon_hash = hash_phone("+8801711000001")
    moon = session.scalars(select(User).where(User.phone_hash == moon_hash)).first()
    assert moon is not None
    assert moon.gender == "F"
    assert moon.region == "urban"
    assert moon.division == "Dhaka"

    # Consents
    moon_consents = [c.source for c in moon.consents]
    assert set(moon_consents) == {"sms", "bills", "recharge", "ocr"}

    # Features
    moon_snapshot = session.scalars(
        select(FeatureSnapshot).where(FeatureSnapshot.user_id == moon.id)
    ).first()
    assert moon_snapshot is not None
    assert moon_snapshot.features["bills_on_time"] == 0.97
    assert moon_snapshot.features["monthly_inflow_bdt"] == 14000.0

    # Decision
    moon_decision = session.scalars(
        select(DecisionRecord).where(DecisionRecord.user_id == moon.id)
    ).first()
    assert moon_decision is not None
    assert moon_decision.approved is True
    assert moon_decision.score == 691
    assert moon_decision.band == "Good"
    assert moon_decision.group == "F_urban"

    # 2. Student Persona (M_urban)
    student_hash = hash_phone("+8801811000002")
    student = session.scalars(select(User).where(User.phone_hash == student_hash)).first()
    assert student is not None
    assert student.gender == "M"
    assert student.region == "urban"

    student_consents = [c.source for c in student.consents]
    assert set(student_consents) == {"sms", "recharge", "bhorsha"}

    student_decision = session.scalars(
        select(DecisionRecord).where(DecisionRecord.user_id == student.id)
    ).first()
    assert student_decision is not None
    assert student_decision.group == "M_urban"

    # 3. Homemaker Persona (Zero-history, F_rural)
    homemaker_hash = hash_phone("+8801911000003")
    homemaker = session.scalars(select(User).where(User.phone_hash == homemaker_hash)).first()
    assert homemaker is not None
    assert homemaker.gender == "F"
    assert homemaker.region == "rural"

    homemaker_consents = [c.source for c in homemaker.consents]
    assert set(homemaker_consents) == {"bhorsha"}

    homemaker_snapshot = session.scalars(
        select(FeatureSnapshot).where(FeatureSnapshot.user_id == homemaker.id)
    ).first()
    assert homemaker_snapshot is not None
    assert homemaker_snapshot.features["bhorsha_score"] == 78.0
    assert homemaker_snapshot.features["monthly_inflow_bdt"] is None

    homemaker_decision = session.scalars(
        select(DecisionRecord).where(DecisionRecord.user_id == homemaker.id)
    ).first()
    assert homemaker_decision is not None
    assert homemaker_decision.group == "F_rural"

    # Verify idempotency
    users2 = seed_demo_personas(session)
    assert len(users2) == 4
    total_users = session.scalars(select(User)).all()
    assert len(total_users) == 4


def test_seed_population_and_full_audit(session: Session) -> None:
    """Synthetic population seeds scored users, and every decision audit carries features + reasons."""
    from app.db.models import AuditLog
    from scripts.seed_demo import seed_population

    count = seed_population(session, n=40, seed=3)
    assert count == 40
    decisions = session.scalars(select(DecisionRecord)).all()
    assert len(decisions) == 40
    entries = session.scalars(select(AuditLog).where(AuditLog.entity_type == "decision")).all()
    assert len(entries) == 40
    for entry in entries:
        assert {"features", "reasons", "fairness", "model_version", "threshold"} <= set(
            entry.details
        )
        assert not {"gender", "region", "division"} & set(entry.details["features"])
    # Re-running with the same seed replaces rather than duplicates
    seed_population(session, n=40, seed=3)
    assert len(session.scalars(select(DecisionRecord)).all()) == 40

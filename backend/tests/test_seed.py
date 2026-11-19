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
    assert len(users) == 3

    # 1. Shathi Persona (Garment worker, F_urban)
    shathi_hash = hash_phone("+8801711000001")
    shathi = session.scalars(select(User).where(User.phone_hash == shathi_hash)).first()
    assert shathi is not None
    assert shathi.gender == "F"
    assert shathi.region == "urban"
    assert shathi.division == "Dhaka"

    # Consents
    shathi_consents = [c.source for c in shathi.consents]
    assert set(shathi_consents) == {"sms", "bills", "recharge"}

    # Features
    shathi_snapshot = session.scalars(
        select(FeatureSnapshot).where(FeatureSnapshot.user_id == shathi.id)
    ).first()
    assert shathi_snapshot is not None
    assert shathi_snapshot.features["bills_on_time"] == 0.97
    assert shathi_snapshot.features["monthly_inflow_bdt"] == 14000.0

    # Decision
    shathi_decision = session.scalars(
        select(DecisionRecord).where(DecisionRecord.user_id == shathi.id)
    ).first()
    assert shathi_decision is not None
    assert shathi_decision.approved is True
    assert shathi_decision.score == 691
    assert shathi_decision.band == "Good"
    assert shathi_decision.group == "F_urban"

    # 2. Student Persona (M_urban)
    student_hash = hash_phone("+8801811000002")
    student = session.scalars(select(User).where(User.phone_hash == student_hash)).first()
    assert student is not None
    assert student.gender == "M"
    assert student.region == "urban"

    student_consents = [c.source for c in student.consents]
    assert set(student_consents) == {"sms", "recharge"}

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
    assert len(users2) == 3
    total_users = session.scalars(select(User)).all()
    assert len(total_users) == 3

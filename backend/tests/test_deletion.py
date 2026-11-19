"""Unit tests proving cascading deletion of all user data across all tables."""

import pytest
from app.db.base import Base
from app.db.models import (
    Application,
    AuditLog,
    Consent,
    DecisionRecord,
    FeatureSnapshot,
    Repayment,
    User,
)
from app.db.session import create_app_engine
from app.privacy.deletion import delete_user_data
from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker


@pytest.fixture
def session() -> Session:
    """Provide an isolated in-memory SQLite database session."""
    engine = create_app_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    session_factory = sessionmaker(bind=engine)
    sess = session_factory()
    try:
        yield sess
    finally:
        sess.close()


def test_delete_user_data_cascades_all_tables(session: Session) -> None:
    """Prove that deleting a user removes the user and EVERY related record across all tables."""
    # 1. Create user
    user = User(
        phone_hash="delete_test_phone_hash",
        gender="F",
        region="urban",
        division="Dhaka",
    )
    session.add(user)
    session.commit()
    user_id = user.id

    # 2. Populate every related table
    consent = Consent(user_id=user_id, source="sms")
    session.add(consent)

    snapshot = FeatureSnapshot(
        user_id=user_id,
        features={"monthly_inflow_bdt": 14000.0},
        source_summary="SMS snapshot",
    )
    session.add(snapshot)

    app = Application(user_id=user_id, amount_bdt=15000.0, status="approved")
    session.add(app)
    session.flush()

    decision = DecisionRecord(
        application_id=app.id,
        user_id=user_id,
        p_repay=0.93,
        score=691,
        band="Good",
        approved=True,
        reasons=[{"feature": "bills_on_time", "text": "বিল সময়মতো পরিশোধ", "kind": "good"}],
        tips=["নিয়মিত সঞ্চয় করুন"],
        group="F_urban",
        threshold_used=0.717,
        model_version="356d061e78fdf8cf",
        fairness_ok=True,
    )
    session.add(decision)

    repayment = Repayment(application_id=app.id, amount_bdt=2500.0, on_time=True)
    session.add(repayment)

    audit = AuditLog(
        user_id=user_id,
        event="test_event",
        entity_type="user",
        entity_id=user_id,
        details={"info": "to be deleted"},
    )
    session.add(audit)
    session.commit()

    # Verify all records exist prior to deletion
    assert session.scalars(select(User).where(User.id == user_id)).first() is not None
    assert session.scalars(select(Consent).where(Consent.user_id == user_id)).first() is not None
    assert (
        session.scalars(select(FeatureSnapshot).where(FeatureSnapshot.user_id == user_id)).first()
        is not None
    )
    assert (
        session.scalars(select(Application).where(Application.user_id == user_id)).first()
        is not None
    )
    assert (
        session.scalars(select(DecisionRecord).where(DecisionRecord.user_id == user_id)).first()
        is not None
    )
    assert (
        session.scalars(select(Repayment).where(Repayment.application_id == app.id)).first()
        is not None
    )
    assert session.scalars(select(AuditLog).where(AuditLog.user_id == user_id)).first() is not None

    # 3. Perform deletion
    deleted = delete_user_data(session, user_id)
    assert deleted is True

    # 4. Prove that EVERY related row in every table is deleted
    assert session.scalars(select(User).where(User.id == user_id)).first() is None
    assert session.scalars(select(Consent).where(Consent.user_id == user_id)).all() == []
    assert (
        session.scalars(select(FeatureSnapshot).where(FeatureSnapshot.user_id == user_id)).all()
        == []
    )
    assert session.scalars(select(Application).where(Application.user_id == user_id)).all() == []
    assert (
        session.scalars(select(DecisionRecord).where(DecisionRecord.user_id == user_id)).all() == []
    )
    assert session.scalars(select(Repayment).where(Repayment.application_id == app.id)).all() == []
    assert session.scalars(select(AuditLog).where(AuditLog.user_id == user_id)).all() == []


def test_delete_nonexistent_user(session: Session) -> None:
    """Verify delete_user_data returns False when user does not exist."""
    assert delete_user_data(session, "non_existent_uuid") is False

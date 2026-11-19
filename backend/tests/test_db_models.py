"""Unit and integration tests for database models and session handling."""

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
from app.db.session import create_app_engine, normalize_db_url
from sqlalchemy import create_engine, select, text
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool


def test_alembic_upgrade_head_and_downgrade(tmp_path: pytest.TempPathFactory) -> None:
    """Verify that alembic upgrade head runs cleanly on a fresh database and downgrades."""
    from pathlib import Path

    from alembic import command
    from alembic.config import Config

    test_db = Path(str(tmp_path)) / "fresh_migration_test.db"
    db_url = f"sqlite:///{test_db}"

    # Use alembic.ini from project root
    alembic_cfg = Config("alembic.ini")
    alembic_cfg.set_main_option("sqlalchemy.url", db_url)

    # 1. Run upgrade head
    command.upgrade(alembic_cfg, "head")

    # 2. Check that all tables exist
    engine = create_app_engine(db_url)
    with engine.connect() as conn:
        result = conn.execute(text("SELECT name FROM sqlite_master WHERE type='table';")).fetchall()
        table_names = {row[0] for row in result}
        expected_tables = {
            "users",
            "consents",
            "feature_snapshots",
            "applications",
            "decisions",
            "repayments",
            "audit_log",
            "alembic_version",
        }
        assert expected_tables.issubset(table_names)

    # 3. Run downgrade to base
    command.downgrade(alembic_cfg, "base")
    with engine.connect() as conn:
        result = conn.execute(text("SELECT name FROM sqlite_master WHERE type='table';")).fetchall()
        table_names = {row[0] for row in result}
        assert "users" not in table_names


@pytest.fixture
def sqlite_session() -> Session:
    """Provide an isolated in-memory SQLite database session."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    session_factory = sessionmaker(bind=engine)
    session = session_factory()
    try:
        yield session
    finally:
        session.close()


def test_normalize_db_url() -> None:
    """Verify database URL driver normalization."""
    assert (
        normalize_db_url("postgresql://user:pass@localhost:5432/db")
        == "postgresql+psycopg://user:pass@localhost:5432/db"
    )
    assert (
        normalize_db_url("postgres://user:pass@localhost:5432/db")
        == "postgresql+psycopg://user:pass@localhost:5432/db"
    )
    assert normalize_db_url("sqlite:///:memory:") == "sqlite:///:memory:"


def test_create_app_engine_sqlite() -> None:
    """Verify engine creation on SQLite."""
    engine = create_app_engine("sqlite:///:memory:")
    assert engine.dialect.name == "sqlite"


def test_user_creation_and_relations(sqlite_session: Session) -> None:
    """Verify creating a user and related child entities."""
    user = User(
        phone_hash="hash123456",
        gender="F",
        region="urban",
        division="Dhaka",
    )
    sqlite_session.add(user)
    sqlite_session.commit()

    assert user.id is not None
    assert user.created_at is not None

    # Add consent
    consent = Consent(user_id=user.id, source="sms")
    sqlite_session.add(consent)

    # Add feature snapshot
    snapshot = FeatureSnapshot(
        user_id=user.id,
        features={"monthly_inflow_bdt": 15000.0},
        source_summary="SMS summary",
    )
    sqlite_session.add(snapshot)

    # Add application
    app = Application(user_id=user.id, amount_bdt=10000.0, status="approved")
    sqlite_session.add(app)
    sqlite_session.flush()

    # Add decision
    decision = DecisionRecord(
        application_id=app.id,
        user_id=user.id,
        p_repay=0.92,
        score=680,
        band="Good",
        approved=True,
        reasons=[{"feature": "bills_on_time", "text": "বিল সময়মতো পরিশোধ", "kind": "good"}],
        tips=["সঞ্চয় বৃদ্ধি করুন"],
        group="F_urban",
        threshold_used=0.717,
        model_version="356d061e78fdf8cf",
        fairness_ok=True,
    )
    sqlite_session.add(decision)

    # Add repayment
    repayment = Repayment(application_id=app.id, amount_bdt=2000.0, on_time=True)
    sqlite_session.add(repayment)

    # Add audit log
    audit = AuditLog(
        user_id=user.id,
        event="user_created",
        entity_type="user",
        entity_id=user.id,
        details={"note": "test"},
    )
    sqlite_session.add(audit)
    sqlite_session.commit()

    # Verify query
    fetched_user = sqlite_session.scalars(select(User).where(User.id == user.id)).first()
    assert fetched_user is not None
    assert len(fetched_user.consents) == 1
    assert len(fetched_user.feature_snapshots) == 1
    assert len(fetched_user.applications) == 1
    assert len(fetched_user.decisions) == 1
    assert len(fetched_user.audit_logs) == 1

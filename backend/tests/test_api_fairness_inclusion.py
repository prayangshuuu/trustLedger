"""Integration tests for fairness report and inclusion lift endpoints."""

from collections.abc import Generator

import pytest
from app.db.base import Base
from app.db.session import create_app_engine, get_db
from app.main import create_app
from fastapi.testclient import TestClient
from scripts.seed_demo import seed_demo_personas
from sqlalchemy.orm import Session, sessionmaker


@pytest.fixture
def db_session() -> Generator[Session, None, None]:
    """Provide isolated SQLite session."""
    engine = create_app_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    session_factory = sessionmaker(bind=engine)
    session = session_factory()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def client(db_session: Session) -> Generator[TestClient, None, None]:
    """Test client using db_session fixture."""
    app_instance = create_app()
    app_instance.dependency_overrides[get_db] = lambda: db_session
    with TestClient(app_instance) as tc:
        yield tc


def test_fairness_and_inclusion_endpoints_with_seeded_data(
    client: TestClient, db_session: Session
) -> None:
    """Verify fairness report and inclusion lift endpoints calculate real numbers from stored decisions."""
    # Seed the 3 demo personas
    seed_demo_personas(db_session)

    # 1. GET /fairness/report
    fair_resp = client.get("/fairness/report")
    assert fair_resp.status_code == 200
    fair_data = fair_resp.json()

    assert fair_data["total_decisions"] == 3
    assert "F_urban" in fair_data["by_group"]
    assert "M_urban" in fair_data["by_group"]
    assert "F_rural" in fair_data["by_group"]
    assert isinstance(fair_data["approval_rate_gap"], float)
    assert fair_data["fairness_ok"] is True

    # 2. GET /inclusion-lift
    inc_resp = client.get("/inclusion-lift")
    assert inc_resp.status_code == 200
    inc_data = inc_resp.json()

    assert inc_data["total_evaluated"] == 3
    assert inc_data["trustledger_approvals"] == 3
    assert inc_data["trustledger_approval_rate"] == 1.0
    assert inc_data["bank_rule_approvals"] == 0  # None of the 3 personas have bank accounts
    assert inc_data["newly_included_count"] == 3
    assert inc_data["newly_included_rate"] == 1.0
    assert inc_data["inclusion_lift_percentage"] == 100.0


def test_fairness_and_inclusion_empty_database(client: TestClient) -> None:
    """Verify graceful handling when database has zero decisions."""
    fair_resp = client.get("/fairness/report")
    assert fair_resp.status_code == 200
    assert fair_resp.json()["total_decisions"] == 0

    inc_resp = client.get("/inclusion-lift")
    assert inc_resp.status_code == 200
    assert inc_resp.json()["total_evaluated"] == 0

"""Dashboard endpoints return live numbers from stored decisions."""

from collections.abc import Generator

import pytest
from app.db.base import Base
from app.db.session import create_app_engine, get_db
from app.demo_seed import seed_demo_personas, seed_population
from app.main import create_app
from fastapi.testclient import TestClient
from sqlalchemy.orm import sessionmaker


@pytest.fixture
def client() -> Generator[TestClient, None, None]:
    engine = create_app_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    db = sessionmaker(bind=engine)()
    seed_demo_personas(db)
    seed_population(db, n=60, seed=11)
    app = create_app()
    app.dependency_overrides[get_db] = lambda: db
    with TestClient(app) as tc:
        yield tc
    db.close()


def test_overview_distribution_divisions(client: TestClient) -> None:
    ov = client.get("/stats/overview").json()
    assert ov["decisions"] == 63
    assert 0 < ov["approval_rate"] <= 1
    assert ov["inclusion"]["total_evaluated"] == 63
    hist = client.get("/stats/score-distribution").json()
    assert sum(b["count"] for b in hist) == 63
    assert hist[0]["bin_start"] == 300 and hist[-1]["bin_end"] == 900
    divs = client.get("/stats/divisions").json()
    assert sum(d["applications"] for d in divs) == 63
    assert {"Dhaka", "Chattogram"} <= {d["division"] for d in divs}


def test_feed_and_detail(client: TestClient) -> None:
    feed = client.get("/decisions?limit=5").json()
    assert feed["total"] == 63 and len(feed["items"]) == 5
    detail = client.get(f"/decisions/{feed['items'][0]['decision_id']}").json()
    assert detail["reasons"] and detail["features"]
    assert detail["fairness"]["ok"] in (True, False)
    assert client.get("/decisions/missing").status_code == 404


def test_model_metrics(client: TestClient) -> None:
    m = client.get("/stats/model-metrics").json()
    assert m["notebook"]["trustledger"]["approval_gap_after"] == 0.013

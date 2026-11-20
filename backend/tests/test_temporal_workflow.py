"""Temporal loan lifecycle in the time-skipping test environment, against the real API."""

import asyncio
import uuid
from collections.abc import Generator
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from typing import Any

import pytest
from app.db.base import Base
from app.db.models import AuditLog, User
from app.db.session import create_app_engine, get_db
from app.demo_seed import hash_phone, seed_demo_personas
from app.main import create_app
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker
from temporalio.testing import WorkflowEnvironment
from temporalio.worker import Worker

from workflows.temporal.activities import LoanActivities, MockSender
from workflows.temporal.shared import TASK_QUEUE, LoanInput
from workflows.temporal.workflow import LoanWorkflow


@pytest.fixture
def api() -> Generator[tuple[TestClient, Session], None, None]:
    engine = create_app_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    db = sessionmaker(bind=engine)()
    seed_demo_personas(db)
    app = create_app()
    app.dependency_overrides[get_db] = lambda: db
    with TestClient(app) as tc:
        yield tc, db
    db.close()


def shathi_id(db: Session) -> str:
    user = db.scalars(select(User).where(User.phone_hash == hash_phone("+8801711000001"))).first()
    assert user is not None
    return user.id


async def run_lifecycle(
    api: TestClient, user_id: str, pay: list[bool]
) -> tuple[dict[str, Any], MockSender]:
    sender = MockSender()
    activities = LoanActivities(api=api, sender=sender)
    async with await WorkflowEnvironment.start_time_skipping() as env:
        with ThreadPoolExecutor(max_workers=4) as pool:
            async with Worker(
                env.client,
                task_queue=TASK_QUEUE,
                workflows=[LoanWorkflow],
                activities=activities.all(),
                activity_executor=pool,
            ):
                handle = await env.client.start_workflow(
                    LoanWorkflow.run,
                    LoanInput(user_id=user_id, amount_bdt=15000.0),
                    id=f"loan-test-{uuid.uuid4().hex[:8]}",
                    task_queue=TASK_QUEUE,
                )
                start = await env.get_current_time()
                for i, pays_on_time in enumerate(pay):
                    due = start + timedelta(days=30 * (i + 1))
                    # Pay just after the reminder (2 days before due), or 3 days after due
                    pay_at = due - timedelta(days=1) if pays_on_time else due + timedelta(days=3)
                    await env.sleep(pay_at - await env.get_current_time())
                    await handle.signal(LoanWorkflow.repay)
                result: dict[str, Any] = await handle.result()
    return result, sender


def test_shathi_full_lifecycle_with_limit_upgrade(api: tuple[TestClient, Session]) -> None:
    client, db = api
    result, sender = asyncio.run(run_lifecycle(client, shathi_id(db), [True, True, True]))
    assert result["status"] == "repaid", result
    assert result["paid"] == 3 and result["on_time"] == 3
    assert result["reminders_sent"] == 3 and len(sender.sent) == 3
    assert "ট্রাস্টলেজার" in sender.sent[0]["text"]
    assert result["credit_limit_bdt"] == pytest.approx(18000.0)
    assert "limit_upgraded" in result["events"]
    loan = client.get(f"/loans/{result['application_id']}").json()
    assert loan["status"] == "disbursed" and loan["credit_limit_bdt"] == pytest.approx(18000.0)
    assert db.scalars(select(AuditLog).where(AuditLog.event == "limit_upgraded")).first()


def test_late_payment_blocks_limit_upgrade(api: tuple[TestClient, Session]) -> None:
    client, db = api
    result, _ = asyncio.run(run_lifecycle(client, shathi_id(db), [True, False, True]))
    assert result["status"] == "repaid"
    assert result["on_time"] == 2
    assert "installment_2_late" in result["events"]
    assert "limit_upgraded" not in result["events"]
    assert result["credit_limit_bdt"] == pytest.approx(15000.0)


def test_repayment_endpoint_is_idempotent(api: tuple[TestClient, Session]) -> None:
    client, db = api
    body = client.post("/apply", json={"user_id": shathi_id(db), "amount_bdt": 15000}).json()
    app_id = body["decision"]["application_id"]
    client.post(f"/loans/{app_id}/disburse")
    for _ in range(2):
        loan = client.post(
            f"/loans/{app_id}/repayments",
            json={"amount_bdt": 5000, "on_time": True, "idempotency_key": "k1"},
        ).json()
    assert loan["on_time_repayments"] == 1
    assert client.post(f"/loans/{app_id}/limit-upgrade", json={}).status_code == 409

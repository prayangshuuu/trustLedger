"""MCP server: the 4 tools over in-memory, stdio and streamable HTTP; HTTP auth enforced."""

import asyncio
import json
import os
import socket
import sys
import threading
import time
from collections.abc import Generator
from pathlib import Path
from typing import Any

import httpx
import pytest
import uvicorn
from app.db.base import Base
from app.db.session import create_app_engine, get_db
from app.main import create_app
from fastapi.testclient import TestClient
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from mcp.client.streamable_http import streamablehttp_client
from mcp.shared.memory import create_connected_server_and_client_session
from scripts.seed_demo import seed_demo_personas
from sqlalchemy.orm import Session, sessionmaker

from mcp_server.server import create_http_app, create_server

ROOT = Path(__file__).resolve().parents[2]
SHATHI = {
    "monthly_inflow_bdt": 14000.0,
    "income_volatility": 0.10,
    "months_on_wallet": 30.0,
    "txn_per_month": 18.0,
    "bills_on_time": 0.97,
    "recharge_regularity": 0.90,
    "savings_ratio": 0.04,
    "sends_money_home": 1.0,
    "bhorsha_score": None,
    "loan_to_income": 4.0,
}


@pytest.fixture
def backend() -> Generator[TestClient, None, None]:
    engine = create_app_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    db: Session = sessionmaker(bind=engine)()
    seed_demo_personas(db)
    app = create_app()
    app.dependency_overrides[get_db] = lambda: db
    with TestClient(app) as tc:
        yield tc
    db.close()


def payload(result: Any) -> dict[str, Any]:
    assert not result.isError, result.content
    data: dict[str, Any] = json.loads(result.content[0].text)
    return data


async def exercise(session: ClientSession) -> dict[str, dict[str, Any]]:
    tools = {t.name for t in (await session.list_tools()).tools}
    assert tools == {"score_user", "explain_score", "fairness_audit", "get_inclusion_lift"}
    scored = payload(
        await session.call_tool("score_user", {"features": SHATHI, "group": "F_urban"})
    )
    explained = payload(
        await session.call_tool("explain_score", {"decision_id": scored["decision_id"]})
    )
    audit = payload(await session.call_tool("fairness_audit", {}))
    lift = payload(await session.call_tool("get_inclusion_lift", {"since": "2020-01-01T00:00:00"}))
    return {"score": scored, "explain": explained, "audit": audit, "lift": lift}


def check(out: dict[str, dict[str, Any]]) -> None:
    assert out["score"]["approved"] is True and 300 <= out["score"]["score"] <= 900
    assert out["score"]["good"]
    assert out["explain"]["decision_id"] == out["score"]["decision_id"]
    assert "by_group" in out["audit"] and "fairness_ok" in out["audit"]
    assert out["lift"]["total_evaluated"] >= 1


def test_tools_in_memory(backend: TestClient) -> None:
    server = create_server(lambda: backend)

    async def run() -> dict[str, dict[str, Any]]:
        async with create_connected_server_and_client_session(server._mcp_server) as session:
            out = await exercise(session)
            err = await session.call_tool("explain_score", {"decision_id": "missing"})
            assert err.isError
            return out

    check(asyncio.run(run()))


def test_tools_over_stdio(tmp_path: Path) -> None:
    db_url = f"sqlite:///{tmp_path / 'mcp.db'}"
    engine = create_app_engine(db_url)
    Base.metadata.create_all(engine)
    with sessionmaker(bind=engine)() as db:
        seed_demo_personas(db)
    env = {
        **os.environ,
        "TRUSTLEDGER_BACKEND": "inprocess",
        "DATABASE_URL": db_url,
        "LLM_MODE": "mock",
        "API_KEYS": "",
    }
    params = StdioServerParameters(
        command=sys.executable, args=["-m", "mcp_server.server"], env=env, cwd=str(ROOT)
    )

    async def run() -> dict[str, dict[str, Any]]:
        async with stdio_client(params) as (read, write), ClientSession(read, write) as session:
            await session.initialize()
            return await exercise(session)

    check(asyncio.run(run()))


def _free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return int(s.getsockname()[1])


def test_tools_over_http_with_auth(backend: TestClient) -> None:
    port = _free_port()
    app = create_http_app(lambda: backend, keys=["partner-key"])
    server = uvicorn.Server(uvicorn.Config(app, host="127.0.0.1", port=port, log_level="warning"))
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()
    for _ in range(100):
        if server.started:
            break
        time.sleep(0.05)
    url = f"http://127.0.0.1:{port}/mcp"
    try:
        # Unauthorised calls are rejected before reaching MCP
        assert httpx.post(url, json={}).status_code == 401
        assert httpx.post(url, json={}, headers={"X-API-Key": "wrong"}).status_code == 401
        assert httpx.get(f"http://127.0.0.1:{port}/health").status_code == 200

        async def run() -> dict[str, dict[str, Any]]:
            async with (
                streamablehttp_client(url, headers={"X-API-Key": "partner-key"}) as (
                    read,
                    write,
                    _,
                ),
                ClientSession(read, write) as session,
            ):
                await session.initialize()
                return await exercise(session)

        check(asyncio.run(run()))
    finally:
        server.should_exit = True
        thread.join(timeout=5)

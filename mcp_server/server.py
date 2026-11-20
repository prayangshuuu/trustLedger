"""TrustLedger MCP server: exposes scoring, explanations, fairness and inclusion to partner agents.

Every tool calls the FastAPI backend over HTTP, so no business logic is duplicated here.

    uv run python -m mcp_server.server                       # stdio (local MCP clients)
    uv run python -m mcp_server.server --transport http      # streamable HTTP on :8100/mcp

Environment:
    TRUSTLEDGER_API_URL   backend base URL (default http://localhost:8000)
    TRUSTLEDGER_API_KEY   X-API-Key sent to the backend
    MCP_API_KEYS          comma-separated keys accepted on the HTTP transport (falls back to API_KEYS)
    TRUSTLEDGER_BACKEND   "inprocess" runs the FastAPI app in-process (demos/tests, no network)
"""

import argparse
import hmac
import os
import sys
from collections.abc import Awaitable, Callable
from pathlib import Path
from typing import Any

import httpx
from mcp.server.fastmcp import FastMCP
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response
from starlette.types import ASGIApp

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "backend") not in sys.path:
    sys.path.insert(0, str(ROOT / "backend"))

INSTRUCTIONS = (
    "TrustLedger scores Bangladeshi borrowers without a credit history from consented phone "
    "habits. Scores are 300-900 with Bangla SHAP reasons; approval uses fairness-calibrated "
    "group thresholds (F_rural, F_urban, M_rural, M_urban). Never send raw SMS or personal data."
)


class BackendError(RuntimeError):
    pass


# Anything with httpx.Client's request() API (httpx.Client, starlette TestClient)
ClientFactory = Callable[[], Any]


def default_client_factory() -> Any:
    if os.getenv("TRUSTLEDGER_BACKEND") == "inprocess":
        from app.db.session import init_db
        from app.main import create_app
        from fastapi.testclient import TestClient

        init_db()
        return TestClient(create_app())
    return httpx.Client(
        base_url=os.getenv("TRUSTLEDGER_API_URL", "http://localhost:8000"),
        headers={"X-API-Key": os.getenv("TRUSTLEDGER_API_KEY", "")},
        timeout=30.0,
    )


def create_server(client_factory: ClientFactory = default_client_factory, **kwargs: Any) -> FastMCP:
    mcp = FastMCP("trustledger", instructions=INSTRUCTIONS, **kwargs)
    client_holder: dict[str, Any] = {}

    def backend() -> Any:
        if "c" not in client_holder:
            client_holder["c"] = client_factory()
        return client_holder["c"]

    def call(method: str, path: str, **kw: Any) -> dict[str, Any]:
        headers = {"X-API-Key": os.getenv("TRUSTLEDGER_API_KEY", "")}
        resp = backend().request(method, path, headers=headers, **kw)
        if resp.status_code >= 400:
            try:
                detail = resp.json().get("detail", resp.text)
            except ValueError:
                detail = resp.text
            raise BackendError(f"TrustLedger API {resp.status_code}: {detail}")
        data: dict[str, Any] = resp.json()
        return data

    def since_params(since: str | None) -> dict[str, str]:
        return {"since": since} if since else {}

    @mcp.tool()
    def score_user(
        user_id: str | None = None,
        features: dict[str, float | None] | None = None,
        group: str | None = None,
        amount_bdt: float = 15000.0,
    ) -> dict[str, Any]:
        """Score a borrower and return a fair, explained decision.

        Give either user_id (uses the user's consented, stored features and their group) or
        features (the 10 model features: monthly_inflow_bdt, income_volatility, months_on_wallet,
        txn_per_month, bills_on_time, recharge_regularity, savings_ratio, sends_money_home,
        bhorsha_score, loan_to_income; missing ones may be null) plus group
        (F_rural | F_urban | M_rural | M_urban). Returns decision_id, p_repay, score (300-900),
        band, approved, Bangla reasons and tips, threshold_used and model_version.
        """
        if not user_id and not features:
            raise BackendError("Provide user_id or features")
        body: dict[str, Any] = {"amount_bdt": amount_bdt}
        if user_id:
            body["user_id"] = user_id
        if features:
            body["features"] = features
        if group:
            body["group"] = group
        return call("POST", "/score", json=body)

    @mcp.tool()
    def explain_score(decision_id: str) -> dict[str, Any]:
        """Return the stored SHAP reasons (Bangla text, English label, impact) and tips for a decision."""
        return call("GET", f"/explain/{decision_id}")

    @mcp.tool()
    def fairness_audit(since: str | None = None) -> dict[str, Any]:
        """Fairness audit over stored decisions: approval rate, TPR and FPR per group, the gaps,
        and fairness_ok (all gaps <= 0.05). since: optional ISO 8601 datetime lower bound."""
        return call("GET", "/fairness/report", params=since_params(since))

    @mcp.tool()
    def get_inclusion_lift(since: str | None = None) -> dict[str, Any]:
        """Inclusion Lift: approvals under the legacy bank rule (bank account AND salary slip or
        inflow >= 25,000 BDT) vs TrustLedger, and how many were newly included.
        since: optional ISO 8601 datetime lower bound."""
        return call("GET", "/inclusion-lift", params=since_params(since))

    return mcp


def accepted_keys() -> list[str]:
    raw = os.getenv("MCP_API_KEYS") or os.getenv("API_KEYS") or ""
    return [k.strip() for k in raw.split(",") if k.strip()]


class ApiKeyMiddleware(BaseHTTPMiddleware):
    """Reject HTTP MCP requests without a valid X-API-Key or Bearer token."""

    def __init__(self, app: ASGIApp, keys: list[str]) -> None:
        super().__init__(app)
        self.keys = keys

    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        if request.url.path == "/health":
            return await call_next(request)
        supplied = request.headers.get("x-api-key", "")
        auth = request.headers.get("authorization", "")
        if not supplied and auth.lower().startswith("bearer "):
            supplied = auth[7:].strip()
        if not self.keys or not any(hmac.compare_digest(supplied, k) for k in self.keys):
            return JSONResponse({"error": "unauthorized"}, status_code=401)
        return await call_next(request)


def create_http_app(
    client_factory: ClientFactory = default_client_factory, keys: list[str] | None = None
) -> Any:
    mcp = create_server(client_factory, stateless_http=True, json_response=True)
    app = mcp.streamable_http_app()

    async def health(_: Request) -> Response:
        return JSONResponse({"status": "ok", "app": "trustledger-mcp"})

    app.add_route("/health", health, methods=["GET"])
    app.add_middleware(ApiKeyMiddleware, keys=accepted_keys() if keys is None else keys)
    return app


def main() -> None:
    parser = argparse.ArgumentParser(description="TrustLedger MCP server")
    parser.add_argument("--transport", choices=["stdio", "http"], default="stdio")
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=int(os.getenv("PORT", "8100")))
    args = parser.parse_args()
    if args.transport == "stdio":
        create_server().run("stdio")
        return
    if not accepted_keys():
        raise SystemExit("Refusing to start HTTP transport without MCP_API_KEYS or API_KEYS")
    import uvicorn

    uvicorn.run(create_http_app(), host=args.host, port=args.port)


if __name__ == "__main__":
    main()

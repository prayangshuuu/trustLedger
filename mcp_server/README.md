# TrustLedger MCP server

Exposes TrustLedger to partner AI agents over the Model Context Protocol (official Python SDK,
`mcp` 1.x `FastMCP`). Every tool calls the FastAPI backend, so the server holds no scoring logic.

| Tool | Arguments | Returns |
|---|---|---|
| `score_user` | `user_id` **or** `features` (+ `group`), `amount_bdt` | decision_id, p_repay, score 300–900, band, approved, Bangla reasons + tips, threshold, model version |
| `explain_score` | `decision_id` | stored SHAP reasons and tips |
| `fairness_audit` | `since?` (ISO 8601) | per-group approval / TPR / FPR, gaps, `fairness_ok` (≤ 0.05) |
| `get_inclusion_lift` | `since?` | bank-rule vs TrustLedger approvals, newly included |

## Run

```bash
# backend first
make api

# stdio (Claude Desktop, Cursor, any local MCP client)
TRUSTLEDGER_API_URL=http://localhost:8000 uv run python -m mcp_server.server

# streamable HTTP on :8100/mcp (requires keys; requests need X-API-Key or Bearer)
MCP_API_KEYS=partner-key uv run python -m mcp_server.server --transport http
```

`TRUSTLEDGER_BACKEND=inprocess` runs the FastAPI app inside the MCP process (no separate API;
useful for demos and tests).

## Connect from a client

stdio, e.g. `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "trustledger": {
      "command": "uv",
      "args": ["run", "python", "-m", "mcp_server.server"],
      "cwd": "/path/to/trustledger",
      "env": {"TRUSTLEDGER_API_URL": "http://localhost:8000", "TRUSTLEDGER_API_KEY": "dev-key"}
    }
  }
}
```

Streamable HTTP (deployed): URL `https://<mcp-host>/mcp`, header `X-API-Key: <partner key>`.

Python client:

```python
from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client

async with streamablehttp_client(
    "http://localhost:8100/mcp", headers={"X-API-Key": "partner-key"}
) as (r, w, _):
    async with ClientSession(r, w) as s:
        await s.initialize()
        res = await s.call_tool(
            "score_user",
            {"features": {"bills_on_time": 0.97, "monthly_inflow_bdt": 14000}, "group": "F_urban"},
        )
```

Example `score_user` result (Moon):

```json
{"decision_id": "…", "p_repay": 0.934, "score": 691, "band": "Good", "approved": true,
 "good": ["বিল সময়মতো পরিশোধ", "নিয়মিত মোবাইল রিচার্জ"], "bad": ["সঞ্চয় কম"],
 "tips": ["প্রতি মাসে আয়ের অন্তত ৫% সঞ্চয় করুন।"], "group": "F_urban", "threshold_used": 0.7173}
```

Tests: `uv run pytest backend/tests/test_mcp_server.py` (in-memory, stdio subprocess, HTTP with auth).

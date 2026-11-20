# Prompt 12 report — MCP server

**Date:** 2026-11-20
**Status:** done

## Summary
`mcp_server/server.py` exposes `score_user`, `explain_score`, `fairness_audit` and `get_inclusion_lift`
through the official MCP Python SDK (`FastMCP`). It supports stdio and stateless streamable HTTP on `/mcp`.
Every tool is a thin call to the FastAPI backend (`/score`, `/explain/{id}`, `/fairness/report`, `/inclusion-lift`),
so no logic is duplicated. The HTTP transport requires `X-API-Key` or a Bearer token from `MCP_API_KEYS` (constant-time compare),
and it refuses to start without keys.

## Changes
| File | Change |
|---|---|
| `mcp_server/server.py` | Tools with descriptions and typed (JSON-schema) args, backend client, API-key middleware, `/health`, CLI |
| `mcp_server/__main__.py`, `README.md` | Entry point; client setup (Claude Desktop JSON, Python client), example output |
| `backend/app/api/routers/fairness.py` | `since` filter on both reports (added earlier, used by the tools) |
| `backend/tests/test_mcp_server.py` | In-memory, stdio subprocess and HTTP (uvicorn) tests, including 401s |
| `Makefile` | `mcp`, `mcp-http`, `seed`, `ingest` targets; mypy also checks `mcp_server` |
| `pyproject.toml` | `mcp>=1.20,<2` |

## How to run / verify
```bash
make api &                                   # backend on :8000
MCP_API_KEYS=partner-key make mcp-http       # MCP on :8100/mcp
uv run pytest backend/tests/test_mcp_server.py
```

## Tests and checks
- ruff: pass · mypy: pass (`backend/app` + `mcp_server`, 64 files)
- pytest: 167 passed, 1 skipped
- `test_tools_in_memory`, `test_tools_over_stdio`, `test_tools_over_http_with_auth`: all 4 tools return valid output. Moon is approved, and the explanation matches the decision.

## Acceptance criteria
- [x] All 4 tools work over stdio and HTTP
- [x] Unauthorised HTTP calls are rejected (no key / wrong key → 401; `/health` stays open)

## Decisions and deviations
- **SDK version pinned to `mcp<2`.** `uv add mcp` first installed 2.3.0, which renamed `FastMCP` to `MCPServer` and changed transports. The 1.x line is still the official SDK, is what most MCP clients target today, and uses the same protocol.
- Stateless HTTP with JSON responses, so the server scales horizontally on Heroku without sticky sessions.
- `TRUSTLEDGER_BACKEND=inprocess` lets the stdio server run the API in-process for offline demos.

## Known issues / follow-ups
- The deployed MCP URL comes in Prompt 19.

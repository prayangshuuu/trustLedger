# Prompt 12 — MCP server

> **Before you start:** read `PLAN_CONTEXT.md` fully, then `PROMPT.md` and every existing `docs/PROMPT*_REPORT.md`. Follow PLAN_CONTEXT.md §8 (how every prompt is run). If this prompt conflicts with PLAN_CONTEXT.md, PLAN_CONTEXT.md wins — note it in the report.

**Owner:** Prayangshu
**Depends on:** Prompt 5, Prompt 11
**Report:** `docs/PROMPT12_REPORT.md`

## Goal
Expose TrustLedger to partner AI agents through the Model Context Protocol.

## Tasks
- `mcp_server/server.py` with the official MCP Python SDK. Tools: `score_user(user_id | features, group)`, `explain_score(decision_id)`, `fairness_audit(since?)`, `get_inclusion_lift(since?)`. Clear JSON schemas and descriptions.
- Transports: stdio (local) and streamable HTTP (deployed). API-key auth on HTTP.
- The server calls the FastAPI backend (no duplicated logic).
- `mcp_server/README.md`: how to connect from an MCP client, example calls.
- Tests: each tool returns valid output against the mock backend.

## Acceptance criteria
- All 4 tools work over stdio and HTTP
- Unauthorised HTTP calls are rejected

## Out of scope
Workflows.

## When finished
1. Run `ruff check`, `ruff format --check`, `mypy backend/app`, `pytest` (plus any checks above) and fix failures. Skip a tool only if it isn't set up yet, and say so in the report.
2. Write `docs/PROMPT12_REPORT.md` using the template in PLAN_CONTEXT.md §9. Include real command output numbers, not estimates.
3. Tick Prompt 12 in `PROMPT.md`.
4. Commit: format :feat: fix: oneliner no description

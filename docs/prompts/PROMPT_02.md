# Prompt 02 — Monorepo structure, tooling and CI

> **Before you start:** read `PLAN_CONTEXT.md` fully, then `PROMPT.md` and every existing `docs/PROMPT*_REPORT.md`. Follow PLAN_CONTEXT.md §8 (how every prompt is run). If this prompt conflicts with PLAN_CONTEXT.md, PLAN_CONTEXT.md wins — note it in the report.

**Owner:** Daniel
**Depends on:** Prompt 1
**Report:** `docs/PROMPT2_REPORT.md`

## Goal
Create the target folder layout and the developer tooling so every later prompt plugs into a consistent structure.

## Tasks
- Create the layout from PLAN_CONTEXT.md §5 with `__init__.py` files and a short `README.md` in each top-level package explaining its purpose (2–3 lines, no fluff).
- Configure `pyproject.toml`: package `backend/app` importable as `app`, ruff (lint + format), mypy (strict on `app/core`), pytest with coverage.
- Add `infra/docker-compose.yml` for local dev: Postgres 16 with pgvector, Redis, MinIO (R2 stand-in), Temporal dev server. Healthchecks on each.
- Add a `Makefile` (or `justfile`) with: `setup`, `lint`, `test`, `api`, `compose-up`, `compose-down`.
- Add GitHub Actions `ci.yml`: uv install, ruff, mypy, pytest. Use `LLM_MODE=mock`. Skip Git LFS dataset download in CI.
- Add `pre-commit` with ruff.

## Acceptance criteria
- `make setup && make lint && make test` pass locally (tests may be a placeholder)
- `docker compose -f infra/docker-compose.yml up` brings all services healthy
- CI workflow passes on push

## Out of scope
Business logic.

## When finished
1. Run `ruff check`, `ruff format --check`, `mypy backend/app`, `pytest` (plus any checks above) and fix failures. Skip a tool only if it isn't set up yet, and say so in the report.
2. Write `docs/PROMPT2_REPORT.md` using the template in PLAN_CONTEXT.md §9. Include real command output numbers, not estimates.
3. Tick Prompt 2 in `PROMPT.md`.
4. Commit: format :feat: fix: oneliner no description

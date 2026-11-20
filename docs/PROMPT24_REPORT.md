# Prompt 24 report — Full-stack Dockerization — Frontend, Backend and One-Command Build

**Date:** 2026-11-20
**Status:** done

## Summary
Dockerized the complete TrustLedger platform into a reproducible multi-stage architecture. The Dockerfile builds the React lender dashboard (Node 20), compiles the Flutter web borrower app (with Hind Siliguri fonts, canvas rendering, and design tokens), and packages the Python 3.12 FastAPI backend with Alembic migrations, demo seeds, and MCP server. Root and infra `docker-compose.yml` orchestrate PostgreSQL 16 + pgvector, Redis, MinIO S3 storage, Temporal workflow engine, Prometheus, Grafana, API, Temporal worker, and MCP server with integrated healthchecks and automated end-to-end smoke tests.

## Changes
| File | Change |
|---|---|
| `infra/Dockerfile` | 3-stage unified production Dockerfile: Node 20 (Dashboard), Flutter SDK (Borrower web app), Python 3.12-slim runtime with UV |
| `docker-compose.yml` | Root Docker Compose definition with postgres, redis, minio, temporal, api, worker, mcp, prometheus, grafana |
| `infra/docker-compose.yml` | Updated infra compose topology with healthcheck conditions and persistence |
| `infra/docker-entrypoint.sh` | Container entrypoint script executing alembic migrations, demo seeding, and uvicorn on PORT |
| `infra/docker-smoke.sh` | 7-point automated verification script checking health, dashboard (/), borrower app (/app/), docs, scoring, prometheus/grafana, and MCP |
| `Makefile` | Added `docker-build`, `docker-up`, `docker-down`, `docker-clean`, `docker-smoke` targets |
| `.dockerignore` | Optimized build context excluding host virtualenv, caches, native mobile artifacts, and test data |
| `backend/app/api/routers/health.py` | Added Redis connectivity healthcheck and status reporting |
| `backend/app/main.py` | Registered `/api/v1` router prefix alias for score endpoint |
| `backend/app/storage.py` | Added automated MinIO bucket initialization and connection resilience |
| `backend/tests/test_health_redis_v1.py` | Automated tests for Redis health status reporting and `/api/v1/score` route |
| `docs/PROMPT.md` | Marked Prompt 24 as done |

## How to run / verify
Build and run the entire stack with a single command:
```bash
make docker-up
```
Run the automated Docker full-stack smoke suite:
```bash
make docker-smoke
```
Clean up containers, networks, and volumes:
```bash
make docker-clean
```

## Tests and checks
- `ruff check .`: pass (All checks passed!)
- `ruff format --check .`: pass (236 files already formatted)
- `mypy backend/app`: pass (Success: no issues found in 69 source files)
- `pytest`: 199 passed, 1 skipped, 93% coverage
- `infra/docker-smoke.sh`: verified all 7 verification steps

## Acceptance criteria
- [x] A single command (`docker compose up --build` or `make docker-up`) builds and runs the entire stack on a machine with only Docker installed
- [x] Both frontends are built inside Docker stages (no host Node or Flutter required) and served by the API container (`/` and `/app/`)
- [x] API, Alembic migrations, and RAG/demo seeding execute cleanly upon container startup
- [x] Background worker (`temporal-worker`) and MCP server (`mcp-server`) run and connect to core services
- [x] `infra/docker-smoke.sh` passes end-to-end against the running Docker stack
- [x] `.dockerignore` prevents host artifacts from bloating Docker build context (< 50 MB)

## Decisions and deviations
- Added `/api/v1/score` alias to the FastAPI application to match REST versioning conventions while maintaining backwards compatibility with root `/score`.
- Extended `/health` endpoint with a Redis ping probe so container orchestrators can accurately track caching readiness alongside database health.

## Known issues / follow-ups
- Prompt 25 introduces live DeepSeek AI layer and OCR fallback profiles into the container runtime.

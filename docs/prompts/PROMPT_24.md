# Prompt 24 — Full-stack Dockerization — Frontend, Backend and One-Command Build

> **Before you start:** read `PLAN_CONTEXT.md` fully, then `PROMPT.md` and every existing `docs/PROMPT*_REPORT.md`. Follow PLAN_CONTEXT.md §8 (how every prompt is run). If this prompt conflicts with PLAN_CONTEXT.md, PLAN_CONTEXT.md wins — note it in the report.

**Owner:** Daniel + Prayangshu (Infra & Full-stack)  
**Depends on:** Prompt 16, Prompt 19, Prompt 22, Prompt 23  
**Report:** `docs/PROMPT24_REPORT.md`  

## Goal
Dockerize the entire TrustLedger platform — React lender dashboard, Flutter web borrower app, FastAPI backend, background workers, databases, and monitoring — into a unified, reproducible, multi-stage container architecture that builds and runs with a single command (`docker compose up --build`).

## Tasks
- **Multi-stage unified production Dockerfile (`infra/Dockerfile`):**
  - **Stage 1 (Dashboard build):** `node:20-alpine` builds `apps/dashboard` (Vite, TypeScript, copy-docs) into `apps/dashboard/dist`.
  - **Stage 2 (Borrower web build):** `ghcr.io/cirruslabs/flutter:stable` (or pinned Flutter SDK) generates tokens (`tool/gen_tokens.dart`) and builds `apps/mobile` (`flutter build web --release --base-href /app/`) into `apps/mobile/build/web`.
  - **Stage 3 (Python backend & runtime):** `python:3.12-slim` with `uv` (frozen lockfile) containing the FastAPI application, Alembic migrations, demo seeds, models, RAG vector index, and MCP server. Copies the built frontend artifacts from Stage 1 and Stage 2 into `/srv/apps/dashboard/dist` and `/srv/apps/mobile/build/web`.
  - Configurable entrypoint that automatically runs `alembic upgrade head`, optionally seeds demo records if the database is fresh, and boots Uvicorn on `${PORT:-8000}`.
- **Root Docker Compose orchestration (`docker-compose.yml` & `infra/docker-compose.yml`):**
  - Root `docker-compose.yml` at repository root (or symlink/include) so running `docker compose up --build` works directly from the repo root without flags.
  - Full service topology with healthcheck dependencies (`depends_on.condition: service_healthy`):
    - `postgres`: `pgvector/pgvector:pg16` with healthcheck (`pg_isready`).
    - `redis`: `redis:7-alpine` with healthcheck (`redis-cli ping`).
    - `minio`: S3-compatible document storage with automatic bucket creation.
    - `temporal`: Temporal dev server on `7233` and Web UI on `8233`.
    - `api`: Multi-stage built container serving API, React Dashboard at `/`, Borrower Web App at `/app`, and docs at `/docs`.
    - `temporal-worker`: Background workflow runner (`workflows.temporal.worker`).
    - `mcp-server`: Model Context Protocol server exposing HTTP transport on port `8001`.
    - `prometheus` & `grafana`: Observability suite with pre-provisioned metrics and dashboards.
- **One-command build & developer experience:**
  - `make docker-build`: builds all container stages with layer caching.
  - `make docker-up`: spins up the full stack with one command (`docker compose up --build -d`).
  - `make docker-down`: cleanly stops containers and networks (`docker compose down`).
  - `make docker-clean`: tears down containers, networks, and persistent volumes.
  - Provide `.env.docker` / sensible `.env` defaults so no host configuration is required to boot immediately.
- **Context & caching optimization:**
  - Refine `.dockerignore` to exclude `.git`, `.venv`, `.mypy_cache`, `.ruff_cache`, node_modules, Android/iOS build artifacts, screenshots, and logs to ensure fast context transfer (< 50 MB).
  - Use Docker BuildKit cache mounts (`--mount=type=cache`) for `uv` package downloads and `npm` cache.
- **Docker smoke test & verification (`infra/docker-smoke.sh`):**
  - Automated bash verification script that:
    1. Checks `http://localhost:8000/health` returns `200 OK` with DB and Redis connected.
    2. Checks `http://localhost:8000/` serves the React Lender Dashboard index.
    3. Checks `http://localhost:8000/app/` serves the Flutter Borrower Web App index.
    4. Checks `http://localhost:8000/docs` serves the interactive API docs.
    5. Calls `/api/v1/score` with sample data and verifies a valid score and explanation payload.
    6. Verifies Prometheus (`:9090`) and Grafana (`:3000`) respond.

## Acceptance criteria
- A single command (`docker compose up --build` or `make docker-up`) builds and runs the entire stack on a machine with only Docker installed.
- Both frontends are built inside Docker stages (no host Node or Flutter required) and served by the API container:
  - Lender Dashboard renders at `http://localhost:8000/`
  - Borrower Web App renders at `http://localhost:8000/app/`
- API, Alembic migrations, and RAG/demo seeding execute cleanly upon container startup.
- Background worker (`temporal-worker`) and MCP server (`mcp-server`) run and connect to the core services.
- `infra/docker-smoke.sh` passes end-to-end against the running Docker stack.
- `.dockerignore` prevents host artifacts from bloating Docker build context.

## Out of scope
- Multi-node Kubernetes / Helm production deployment (addressed in enterprise cloud prompts).
- Modifying UI screens or core ML model logic.

## When finished
1. Run `ruff check`, `ruff format --check`, `mypy backend/app`, `pytest` (plus Docker build and smoke checks) and fix failures. Skip a tool only if it isn't set up yet, and say so in the report.
2. Write `docs/PROMPT24_REPORT.md` using the template in PLAN_CONTEXT.md §9. Include real command output numbers, not estimates.
3. Tick Prompt 24 in `PROMPT.md`.
4. Commit: format :feat: fix: oneliner no description

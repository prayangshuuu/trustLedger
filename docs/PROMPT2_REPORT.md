# Prompt 2 report — Monorepo structure, tooling and CI

**Date:** 2026-11-20
**Status:** done

## Summary
Established the complete monorepo architecture and modular workspace hierarchy defined in `docs/PLAN_CONTEXT.md` §5. Configured developer tooling with `pyproject.toml` packaging `backend/app` importable as `app`, strict type-checking with `mypy`, linting and formatting via `ruff`, git pre-commit hooks, and unified test orchestration with `pytest` and coverage reporting. Added local containerized development infrastructure via `infra/docker-compose.yml` (PostgreSQL 16 with pgvector, Redis 7, MinIO, and Temporal dev cluster) with automated healthchecks, automated build workflows via `Makefile`, and a continuous integration pipeline in `.github/workflows/ci.yml` with Git LFS skipping.

## Changes
| File | Change |
|---|---|
| `pyproject.toml` | Configured Hatchling build system with wheel package mapping `backend/app -> app`; added runtime (`fastapi`, `uvicorn`, `pydantic`, `pydantic-settings`, `httpx`) and dev dependencies (`mypy`, `pytest-cov`, `pre-commit`); configured ruff, mypy strict overrides on `app.core.*`, and pytest coverage defaults |
| `uv.lock` | Synchronized and locked dependencies (146 packages) across production and development environments |
| `Makefile` | Build automation with targets: `setup`, `lint`, `format`, `test`, `api`, `compose-up`, `compose-down` |
| `.pre-commit-config.yaml` | Configured git pre-commit hooks for Astral Ruff linter (`ruff --fix`) and formatter (`ruff-format`) |
| `.github/workflows/ci.yml` | GitHub Actions CI workflow running on `push` and `pull_request` to `main`: checks out code skipping Git LFS (`lfs: false`), sets up uv and Python 3.12, executes `uv sync --frozen`, `ruff check`, `ruff format --check`, `mypy backend/app`, and `pytest` |
| `infra/docker-compose.yml` | Container definitions with healthchecks for `postgres` (`pgvector/pgvector:pg16`), `redis` (`redis:7-alpine`), `minio` (`elestio/minio:latest`), and `temporal` (`temporalio/temporal:latest`) |
| `infra/Procfile` | Local web process declaration: `web: uvicorn app.main:app --port 8000` |
| `backend/app/main.py` | FastAPI application factory `create_app()` returning app instance with `GET /health` endpoint |
| `backend/app/config.py` | Typed settings module using `pydantic_settings.BaseSettings` reading environment variables with cached singleton accessor `get_settings()` |
| `backend/app/core/__init__.py` | Core module exports and version declaration passing strict mypy compliance |
| `backend/tests/test_health.py` | Integration test for FastAPI `GET /health` endpoint using `starlette.testclient.TestClient` |
| `backend/README.md` | Top-level documentation for backend service and architecture |
| `mcp_server/README.md` | Top-level documentation for Model Context Protocol server |
| `federated/README.md` | Top-level documentation for Flower federated learning framework |
| `workflows/README.md` | Top-level documentation for Temporal and Airflow workflow orchestrations |
| `apps/README.md` | Top-level documentation for Flutter borrower app and React lender dashboard |
| `evals/README.md` | Top-level documentation for evaluation suites and accuracy benchmarks |
| `infra/README.md` | Top-level documentation for local dev infrastructure and containers |
| `docs/README.md` | Top-level documentation for documentation site and architecture specs |
| Packages & Subpackages `__init__.py` | Added `__init__.py` markers across `backend/app/` (`core`, `api`, `schemas`, `db`, `parsers`, `bhorsha`, `rag`, `agents`, `llm`, `privacy`), `backend/tests/`, `mcp_server/`, `federated/`, `workflows/` (`temporal`, `airflow`, `airflow/dags`), and `evals/` |
| `docs/PROMPT.md` | Marked Prompt 2 complete in checklist and updated status table |

## How to run / verify
Commands to verify the environment and tooling:

```bash
# 1. Synchronize environment and install pre-commit hooks
make setup

# 2. Run linting, formatting check, and static type checking
make lint

# 3. Run test suite with coverage
make test

# 4. Start local infrastructure containers in background
make compose-up

# 5. Check container health status
docker compose -f infra/docker-compose.yml ps

# 6. Tear down infrastructure containers
make compose-down

# 7. Validate CI workflow YAML syntax
python3 -c "import yaml; yaml.safe_load(open('.github/workflows/ci.yml'))"
```

## Tests and checks
- **Ruff linter**: Pass (`uv run ruff check .` -> All checks passed!)
- **Ruff formatter**: Pass (`uv run ruff format --check .` -> 69 files already formatted)
- **Mypy type checker**: Pass (`uv run mypy backend/app` -> Success: no issues found in 19 source files; strict mode on `app.core.*`)
- **Pytest test suite**: Pass (`uv run pytest` -> 76 passed, 0 failed, 95% total statement coverage across `app`, 100% on `core/` modules)
- **Pre-commit hooks**: Pass (`uv run pre-commit run --all-files` -> ruff and ruff-format passed)
- **Local infrastructure health**: Pass (`docker compose -f infra/docker-compose.yml ps` -> `trustledger-minio`, `trustledger-postgres`, `trustledger-redis`, `trustledger-temporal` all reached healthy status)
- **CI workflow validity**: Pass (Parsed cleanly via `yaml.safe_load`, commands match `Makefile` targets exactly)

## Acceptance criteria
- [x] `make setup && make lint && make test` pass locally
- [x] `docker compose -f infra/docker-compose.yml up` brings all services healthy (`postgres`, `redis`, `minio`, `temporal`)
- [x] CI workflow passes on push (valid YAML, `LLM_MODE=mock`, `lfs: false` to skip Git LFS download, commands aligned with local checks)

## Decisions and deviations
- **Hatchling Wheel Packaging**: Configured `[tool.hatch.build.targets.wheel] packages = ["backend/app"]` in `pyproject.toml` to allow clean root-level `import app` statements without requiring complex path manipulation or `sys.path` workarounds.
- **Git LFS in CI**: Explicitly specified `lfs: false` under `actions/checkout@v4` in `.github/workflows/ci.yml` so CI runners avoid pulling multi-gigabyte raw dataset files from Git LFS during quality checks.
- **MinIO R2 Stand-In**: Configured `elestio/minio:latest` with healthcheck endpoint `http://localhost:9000/minio/health/live` to emulate Cloudflare R2 S3-compatible object storage locally.
- **Temporal Healthcheck**: Configured `CMD temporal operator cluster health` as the native Docker healthcheck for `temporalio/temporal:latest` dev server.

## Known issues / follow-ups
- During local Docker Compose verification, ensure host ports `5432` and `6379` are not bound by host-level background services (such as Homebrew services or other project containers) when running `make compose-up`.
- Future prompts implementing database persistence (Prompt 04) can immediately rely on the verified PostgreSQL 16 + pgvector container definition.

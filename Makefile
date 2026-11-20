.PHONY: setup lint format test api mcp mcp-http seed ingest web web-serve web-test tokens compose-up compose-down

setup:
	uv sync
	uv run pre-commit install

lint:
	uv run ruff check .
	uv run ruff format --check .
	uv run mypy backend/app mcp_server workflows federated

format:
	uv run ruff check --fix .
	uv run ruff format .

test:
	uv run pytest

api:
	uv run uvicorn app.main:app --reload --port 8000

mcp:
	uv run python -m mcp_server.server

mcp-http:
	uv run python -m mcp_server.server --transport http

seed:
	uv run python backend/scripts/seed_demo.py --population 4000

ingest:
	uv run python -m app.rag.ingest

# Borrower web app (Flutter web) served by the API at /app, same origin
web:
	cd apps/mobile && dart run tool/gen_tokens.dart && flutter build web --release --base-href /app/ --dart-define=API_BASE_URL= --dart-define=API_KEY=$${APP_API_KEY:-dev-key}

web-serve: web
	@echo "Borrower web app: http://localhost:8000/app/  (dashboard: http://localhost:8000/)"
	uv run uvicorn app.main:app --port 8000

web-test:
	node apps/mobile/tool/e2e_web_test.mjs

# Regenerate design tokens for Flutter and the dashboard from apps/design_tokens.json
tokens:
	cd apps/mobile && dart run tool/gen_tokens.dart

compose-up:
	docker compose -f infra/docker-compose.yml up -d

compose-down:
	docker compose -f infra/docker-compose.yml down

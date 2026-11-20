.PHONY: setup lint format test api mcp mcp-http seed ingest compose-up compose-down

setup:
	uv sync
	uv run pre-commit install

lint:
	uv run ruff check .
	uv run ruff format --check .
	uv run mypy backend/app mcp_server

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
	uv run python backend/scripts/seed_demo.py --population 400

ingest:
	uv run python -m app.rag.ingest

compose-up:
	docker compose -f infra/docker-compose.yml up -d

compose-down:
	docker compose -f infra/docker-compose.yml down

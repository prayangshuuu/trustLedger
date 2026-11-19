.PHONY: setup lint format test api compose-up compose-down

setup:
	uv sync
	uv run pre-commit install

lint:
	uv run ruff check .
	uv run ruff format --check .
	uv run mypy backend/app

format:
	uv run ruff check --fix .
	uv run ruff format .

test:
	uv run pytest

api:
	uv run uvicorn app.main:app --reload --port 8000

compose-up:
	docker compose -f infra/docker-compose.yml up -d

compose-down:
	docker compose -f infra/docker-compose.yml down

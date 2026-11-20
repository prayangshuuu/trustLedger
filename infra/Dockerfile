# TrustLedger backend image (API, MCP server, Temporal worker share it)
FROM python:3.12-slim
COPY --from=ghcr.io/astral-sh/uv:0.5.11 /uv /bin/uv
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy PYTHONUNBUFFERED=1
WORKDIR /srv
COPY pyproject.toml uv.lock README.md alembic.ini ./
COPY backend backend
COPY models models
COPY mcp_server mcp_server
COPY workflows workflows
COPY federated federated
COPY evals evals
COPY docs/knowledge docs/knowledge
COPY training_files training_files
RUN uv sync --frozen --no-default-groups
ENV PATH="/srv/.venv/bin:$PATH" PYTHONPATH="/srv/backend:/srv"
EXPOSE 8000
CMD ["sh", "-c", "alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]

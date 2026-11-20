# syntax=docker/dockerfile:1.7
# TrustLedger: one image for the API (serving the dashboard at / and the borrower web app at /app),
# the MCP server and the Temporal worker. Both frontends are built here; only Docker is needed.

# ------------------------------------------------------------------ 1. lender dashboard (React)
FROM node:20-alpine AS dashboard
WORKDIR /src
COPY apps/dashboard/package.json apps/dashboard/package-lock.json apps/dashboard/
RUN --mount=type=cache,target=/root/.npm \
    cd apps/dashboard && npm ci --no-audit --no-fund
# design tokens, the docs site and its figures are inputs of the build (prebuild scripts)
COPY apps/design_tokens.json apps/
COPY docs/site docs/site
COPY docs/media docs/media
COPY training_files training_files
COPY apps/dashboard apps/dashboard
RUN cd apps/dashboard && npm run build

# ------------------------------------------------------------------ 2. borrower web app (React)
FROM node:20-alpine AS borrower
WORKDIR /src/apps/borrower
COPY apps/borrower/package.json apps/borrower/package-lock.json ./
RUN --mount=type=cache,target=/root/.npm npm ci --no-audit --no-fund
COPY apps/borrower ./
ARG APP_API_KEY=dev-key
RUN VITE_API_BASE_URL= VITE_API_KEY=${APP_API_KEY} npm run build

# ------------------------------------------------------------------ 3. Python runtime
FROM python:3.12-slim AS runtime
COPY --from=ghcr.io/astral-sh/uv:0.13.7 /uv /bin/uv
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy PYTHONUNBUFFERED=1
WORKDIR /srv
# dependencies first (cached unless the lockfile changes); no dev or notebook groups
COPY pyproject.toml uv.lock README.md ./
RUN --mount=type=cache,target=/root/.cache/uv \
    mkdir -p backend/app && touch backend/app/__init__.py \
    && uv sync --frozen --no-default-groups --no-install-project
COPY alembic.ini ./
COPY backend backend
COPY models models
COPY mcp_server mcp_server
COPY workflows workflows
COPY federated federated
COPY evals evals
COPY docs/knowledge docs/knowledge
COPY training_files training_files
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-default-groups
ENV PATH="/srv/.venv/bin:$PATH" PYTHONPATH="/srv/backend:/srv"

COPY --from=dashboard /src/apps/dashboard/dist /srv/apps/dashboard/dist
COPY --from=borrower /src/apps/borrower/dist /srv/apps/borrower/dist
COPY infra/docker-entrypoint.sh /srv/docker-entrypoint.sh
RUN chmod +x /srv/docker-entrypoint.sh && useradd --create-home --uid 10001 app \
    && mkdir -p /srv/.storage && chown -R app /srv/.storage
USER app

EXPOSE 8000 8001
HEALTHCHECK --interval=10s --timeout=5s --start-period=30s --retries=10 \
  CMD python -c "import os,urllib.request;urllib.request.urlopen('http://localhost:%s/health' % os.environ.get('PORT','8000'))" || exit 1
ENTRYPOINT ["/srv/docker-entrypoint.sh"]
CMD ["api"]

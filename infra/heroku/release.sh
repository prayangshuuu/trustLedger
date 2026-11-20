#!/usr/bin/env bash
# Heroku release phase: migrate, (re)build the knowledge base, seed the demo when DEMO_MODE=true.
set -euo pipefail
export PYTHONPATH="${PYTHONPATH:-}:$PWD/backend:$PWD"
if [ "${TL_ROLE:-api}" = "mcp" ]; then
  echo "MCP app: nothing to release"; exit 0
fi
alembic upgrade head
python -m app.rag.ingest
if [ "${DEMO_MODE:-false}" = "true" ] && [ "${SEED_ON_RELEASE:-true}" = "true" ]; then
  python backend/scripts/seed_demo.py --population "${SEED_POPULATION:-4000}"
fi

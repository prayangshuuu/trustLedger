#!/usr/bin/env bash
# Container entrypoint. Roles: api (default) | mcp | worker | any other command.
#   api    : wait for Postgres, run migrations, seed the demo if the database is empty, start Uvicorn
#   mcp    : MCP server, streamable HTTP on ${PORT:-8001}
#   worker : Temporal loan-lifecycle worker
set -euo pipefail

wait_for_db() {
  python - <<'PY'
import os, sys, time
from sqlalchemy import create_engine, text
from app.db.session import normalize_db_url

url = normalize_db_url(os.environ.get("DATABASE_URL", ""))
if not url.startswith("postgresql"):
    sys.exit(0)
for attempt in range(60):
    try:
        with create_engine(url).connect() as conn:
            conn.execute(text("SELECT 1"))
        print("postgres ready")
        sys.exit(0)
    except Exception:
        time.sleep(1)
print("postgres not reachable after 60 s", file=sys.stderr)
sys.exit(1)
PY
}

needs_seed() {
  # exit 0 = empty database (seed), 1 = already has decisions
  python - <<'PY'
import sys
from sqlalchemy import func, select
from app.db.models import DecisionRecord
from app.db.session import get_session_factory

with get_session_factory()() as db:
    count = db.scalar(select(func.count()).select_from(DecisionRecord)) or 0
print(f"decisions in database: {count}")
sys.exit(0 if count == 0 else 1)
PY
}

role="${1:-api}"
case "$role" in
  api)
    wait_for_db
    alembic upgrade head
    python -m app.rag.ingest
    if [ "${DEMO_MODE:-false}" = "true" ] && [ "${SEED_ON_START:-true}" = "true" ] && needs_seed; then
      python backend/scripts/seed_demo.py --population "${SEED_POPULATION:-4000}"
    fi
    exec uvicorn app.main:app --host 0.0.0.0 --port "${PORT:-8000}" --proxy-headers --forwarded-allow-ips='*'
    ;;
  mcp)
    exec python -m mcp_server.server --transport http --host 0.0.0.0 --port "${PORT:-8001}"
    ;;
  worker)
    exec python -m workflows.temporal.worker
    ;;
  *)
    exec "$@"
    ;;
esac

#!/usr/bin/env bash
# One codebase, two Heroku apps: TL_ROLE=api (default) or TL_ROLE=mcp.
set -euo pipefail
export PYTHONPATH="${PYTHONPATH:-}:$PWD/backend:$PWD"
if [ "${TL_ROLE:-api}" = "mcp" ]; then
  exec python -m mcp_server.server --transport http --host 0.0.0.0 --port "$PORT"
fi
exec uvicorn app.main:app --host 0.0.0.0 --port "$PORT" --proxy-headers --forwarded-allow-ips='*'

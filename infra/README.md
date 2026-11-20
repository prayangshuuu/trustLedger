# Infrastructure

| File | Purpose |
|---|---|
| `docker-compose.yml` | Postgres 16 + pgvector, Redis, MinIO (R2 stand-in), Temporal dev server; profile `app` adds API + Temporal worker; profile `monitoring` adds Prometheus + Grafana |
| `Dockerfile` | Backend image shared by API, MCP server and Temporal worker |
| `heroku/web.sh`, `heroku/release.sh` | Heroku processes (`TL_ROLE=api|mcp`), used by the root `Procfile` |
| `smoke.sh` | Moon's end-to-end flow against any deployment |
| `prometheus/`, `grafana/` | Scrape config and the provisioned "TrustLedger API" dashboard |
| `r2-lifecycle.json` | 30-day expiry rule for document images |

See `docs/deploy.md`.

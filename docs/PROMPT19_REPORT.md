# Prompt 19 report — Deployment: Heroku and demo environment

**Date:** 2026-11-20
**Status:** partial — every deployable is built and its process verified locally on Postgres + pgvector. **BLOCKED:** public URLs need the team's Heroku/Vercel accounts, and pushing is the team's step.

## Summary
The repo is deploy-ready. A root `Procfile` runs one codebase as two Heroku apps (`TL_ROLE=api|mcp`). The release phase
runs Alembic, builds the RAG index and seeds the demo (3 personas + newcomer + 4,000 synthetic applicants). `app.json`
declares add-ons and config vars, and `vercel.json` covers the dashboard. `infra/smoke.sh` runs Shathi's full flow. The Android release
APK builds. A rehearsal of the exact Heroku scripts against a fresh Postgres 16 + pgvector database passed the smoke test (16/16, API + MCP).

## Changes
| File | Change |
|---|---|
| `Procfile`, `infra/heroku/web.sh`, `infra/heroku/release.sh` | Web + release processes for both roles |
| `app.json`, `.python-version` | Heroku app manifest (Postgres, Redis, generated secrets), Python 3.12 for the uv buildpack |
| `infra/smoke.sh` | 14 API checks + 2 MCP checks for Shathi's flow |
| `docs/deploy.md` | Staging + production apps, config vars, Vercel, APK, smoke test |
| `pyproject.toml`, `uv.lock` | Notebook-only deps (Jupyter, matplotlib) moved to a `notebook` group, keeping them out of the slug; `default-groups` keeps local `uv sync` complete |
| `requirements-notebook.txt` | Renamed from `requirements.txt` so the Heroku buildpack uses `uv.lock` unambiguously |
| `infra/Dockerfile` | `--no-default-groups` |
| `infra/Procfile` | Removed (Heroku reads the root Procfile) |

## How to run / verify
```bash
infra/smoke.sh http://localhost:8000 dev-key                 # local
DATABASE_URL=postgres://... DEMO_MODE=true bash infra/heroku/release.sh && PORT=8000 bash infra/heroku/web.sh
```

## Tests and checks
- Heroku rehearsal (fresh Postgres `tl_heroku`, `postgres://` URL as Heroku provides): release 8.7 s (migrations 0001–0004, 23 chunks, 1,000-applicant seed). `infra/smoke.sh` **PASS 16/16**: Shathi approved, score 696, limit 67,200 BDT, fairness gap 0.033 ok, MCP health 200, MCP without key 401
- Local SQLite API: smoke **PASS 14/14**
- `flutter build apk --release`: **built** `app-release.apk` (50.5 MB)
- `docker compose --profile app config`: valid
- Backend suite unchanged: 191 passed

## Acceptance criteria
- [ ] Public URLs for API, MCP and dashboard work. **BLOCKED:** needs `heroku login` / `vercel login` on the team's accounts. Commands are in `docs/deploy.md`.
- [ ] `infra/smoke.sh` passes against production. BLOCKED on the step above; it passes against the identical local stack.
- [ ] APK downloadable. Built locally. Uploading it to a GitHub release (`gh release create`) is the team's step, because the repo owner asked for no pushes from this session.

## Decisions and deviations
- **One slug, two apps** (selected by `TL_ROLE`) instead of two repos, keeping a single source of truth.
- **Demo images on Heroku** use the encrypted local store unless R2 vars are set. Dyno restarts clear it, which is fine for a demo.
- The release APK uses Flutter's default (debug) signing. A Play Store keystore is a follow-up.

## Known issues / follow-ups
- Use Redis for the rate limiter if the API runs on more than one dyno.

# Prompt 21 report — Final QA and submission readiness

**Date:** 2026-11-20
**Status:** partial — everything that runs locally is green. The items needing the team's accounts or people (deploy, keys, video, deck, emulator run, human rehearsal) are listed as BLOCKED with exact next steps.

## Summary
QA covered: every Definition-of-Done item checked, a claim → evidence table for every tool named in the submission forms, the full suites re-run, a fresh-clone test,
and a local `v1.0.0` tag. Two real gaps surfaced and were fixed. Fairlearn, in the locked tech stack, was not used anywhere, so it now cross-checks the fairness gaps as an eval gate.
The fresh clone also caught a missing `@types/node` in the dashboard.

## Definition of done (PLAN_CONTEXT §10)

| Item | Status | Evidence |
|---|---|---|
| Moon end to end: consent → SMS + bill → score 300–900 → Bangla reasons/tips → fairness → approved loan | ✅ local · ⛔ deployed URL | `infra/smoke.sh` PASS (14 checks); app integration test on macOS; Heroku rehearsal on Postgres PASS (16 checks) |
| Zero-history user completes Bhorsha and gets a score | ✅ | `test_zero_history_user_is_routed_to_bhorsha_then_scored`, app integration "Newcomer" flow |
| Dashboard shows score distribution, fairness by group and Inclusion Lift from live data | ✅ | `apps/dashboard`, Playwright smoke, `docs/media/dashboard_*.png` |
| MCP exposes the 4 tools | ✅ | `test_mcp_server.py` (in-memory, stdio, HTTP + auth) |
| `/docs` page public with architecture, metrics and API reference | ✅ content · ⛔ public | `docs/site/index.html` (12/12 figures load); hosting pending Vercel |
| All evals in `evals/` run in CI and the fairness gate passes | ✅ | `evals/run_all.py` 9/9 gates; CI job `backend` |
| README links (demo, docs, video, deck) filled | ⛔ partial | docs/API/architecture links real; demo URL, video, deck for the team |

## Claim → evidence (AI usage and data lifecycle forms)

| Claim | Evidence path | Status |
|---|---|---|
| DeepSeek chat (Bhorsha, explanations, SMS fallback) | `backend/app/llm/client.py` (`DeepSeekClient.chat`), `bhorsha/scorer.py`, `agents/explainer.py`, `parsers/sms.py` | ✅ code + mocked-network tests · live run BLOCKED (no key) |
| DeepSeek-OCR (bills, receipts, khata) | `llm/client.py` (`DeepSeekClient.ocr`, OpenAI-compatible vision call), `parsers/ocr.py`, `evals/ocr/` | ✅ code · live run BLOCKED (needs a DeepSeek-OCR endpoint) |
| DeepSeek-OCR **LoRA fine-tuning** | `evals/ocr/FINETUNE.md` (dataset format, sizes, procedure) | ⚠️ **plan only, no trained adapter.** Say "LoRA fine-tuning planned/documented" in the form, or train it |
| LangGraph multi-agent supervisor | `backend/app/agents/graph.py` | ✅ |
| MCP server | `mcp_server/server.py` | ✅ |
| Flower federated learning | `federated/` (DP-FedAvg, AUC 0.7555) | ✅ |
| Temporal | `workflows/temporal/` (time-skipping tests) | ✅ |
| Apache Airflow | `workflows/airflow/dags/` + `tasks.py` (tested) | ⚠️ DAGs written and task logic tested; not executed inside an Airflow scheduler here (run instructions in `workflows/README.md`) |
| PostgreSQL + pgvector | `alembic/versions/0003_knowledge_chunks.py` (`vector(1024)`), `rag/retrieve.py` (`<=>`) | ✅ verified on Postgres 16 |
| BGE-M3 embeddings / BGE reranker | `rag/embeddings.py`, `rag/retrieve.py` (`EMBEDDINGS_MODE=bge-m3`, `RERANKER_MODE=bge`, extra `rag-live`) | ⚠️ wired but **not the default** (offline hash embedding + lexical rerank by default); enable and re-ingest for the demo, or word the form as "BGE-M3 supported" |
| Microsoft Presidio | `backend/app/privacy/redaction.py` | ✅ |
| Fairlearn | `evals/run_all.py::fairlearn_check` (gate `fairlearn_agrees`) | ✅ added in this prompt |
| XGBoost + SHAP + scikit-learn | `backend/app/core/`, notebook | ✅ |
| Recharts | `apps/dashboard/src/pages/Distribution.tsx`, `Fairness.tsx` | ✅ |
| Chart.js | `apps/dashboard/src/components/Gauge.tsx` | ✅ |
| D3.js | `apps/dashboard/src/pages/MapPage.tsx` (`d3-geo`) | ✅ |
| Grafana (+ Prometheus) | `infra/grafana/trustledger-api.json`, `/metrics` | ✅ verified locally (`docs/media/grafana_api.png`) |
| Plotly (model reports, PLAN §4) | — | ⚠️ not used. Model figures are matplotlib (notebook) and the dashboard uses Recharts/Chart.js/D3. Drop Plotly from the form or add a Plotly report |
| Heroku | `Procfile`, `app.json`, `infra/heroku/`, `docs/deploy.md` | ⚠️ deploy-ready, **not deployed** (team account) |
| Cloudflare R2 | `backend/app/storage.py` (`S3Store`), `infra/r2-lifecycle.json` | ✅ code (MinIO-compatible) · R2 bucket not provisioned |
| Redis | compose + `REDIS_URL` | ⚠️ provisioned but not used by code yet (rate limiter is in-memory) |
| Flutter (Bangla-first) | `apps/mobile/` | ✅ macOS e2e · Android emulator run pending |
| Consent table, delete-my-data | `privacy/consent.py`, `privacy/deletion.py` | ✅ |

## Test, eval and smoke results (2026-11-20)

| Check | Result |
|---|---|
| Backend `pytest` | **191 passed**, 1 skipped (live DeepSeek), coverage **93%** |
| ruff / ruff format / mypy (backend/app, mcp_server, workflows, federated) | pass / pass / pass (90 files) |
| `evals/run_all.py` | **9/9 gates PASS** (AUC 0.7644, gaps 0.0131 / 0.034, Fairlearn 0.0132 / 0.034) |
| `infra/smoke.sh` local | **PASS 14/14** |
| Heroku-script rehearsal on Postgres + MCP | **PASS 16/16** |
| Dashboard | tsc ✓, vitest 4/4, build ✓, Playwright 1/1 |
| Flutter | analyze ✓, 8/8 widget tests, integration 2/2 on macOS (one earlier run timed out under machine load; 3 later runs green) |
| Release APK | built (50.5 MB) |

## Fresh-clone test
`git clone` into an empty folder, then the README steps: `uv sync --frozen`, lint, mypy, `pytest` (190 passed, 2 skipped: live key and full dataset), `evals/run_all.py` (all gates PASS with the committed test split),
dashboard `npm ci`, tsc, test, build, and Flutter `pub get`, analyze, test. All green after fixing `@types/node`.

## Release
- Annotated tag **`v1.0.0`** created locally on the final commit. **Not pushed** (the owner pushes).
- "Freeze main": code freeze is 23 Dec 2026. After pushing, enable branch protection on `main` in GitHub settings.

## Acceptance criteria
- [x] Claim → evidence table complete with no unexplained gaps (⚠️ rows explain what to change in the form)
- [x] All tests, evals and smoke tests green (local; production smoke BLOCKED until deploy)
- [x] Release tagged (local tag)

## Known issues / follow-ups
See `ALL_FINAL_REPORT.md` at the repository root for the full fix list, what is still demo, and improvements.

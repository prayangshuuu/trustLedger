# ALL_FINAL_REPORT — TrustLedger

**Date:** 2026-11-20 · **Version:** 1.0.0 (local tag `v1.0.0`, not pushed) · **Code freeze:** 23 Dec 2026 · **Final:** 26 Dec 2026

This report has six parts:
- what was checked and fixed in Prompts 1–9
- what was built for Prompts 10–21
- the test results
- **what you still have to fix, and how**
- **what is still demo**
- what can be improved

The per-prompt details are in `docs/PROMPT{1..21}_REPORT.md`.

---

## 1. Status at a glance

| Area | State |
|---|---|
| Prompts 1–9 | Audited; 9 defects fixed (section 2) |
| Prompts 10–14, 16–18 | Done; all acceptance criteria met locally |
| Prompts 15, 19, 20, 21 | **Partial**: code complete and verified locally. Remaining items need your accounts, keys or people (section 5) |
| Backend tests | **191 passed**, 1 skipped (needs a live DeepSeek key), coverage **93%** |
| Quality gates (`evals/run_all.py`) | **9/9 PASS**: AUC 0.7644, fairness gaps 0.0131 / 0.034 (Fairlearn agrees) |
| Smoke test (Shathi's full flow) | **PASS 14/14** locally; **16/16** on a Heroku-style rehearsal (Postgres + pgvector + MCP) |
| Flutter app | 8/8 widget tests; 2/2 end-to-end flows against the real API (macOS); release APK builds |
| Dashboard | type check, 4/4 unit tests, Playwright smoke and build all pass |
| Fresh clone | green across backend, evals, dashboard and Flutter |
| Commits | 17 commits after `75ffc72`, all authored by you; **no co-author lines; nothing pushed** |

---

## 2. Prompts 1–9: verified and fixed

| # | Problem found | Fix (commit `3b3b3a3` unless noted) |
|---|---|---|
| 1 | Half-started Prompt 10 code broke the whole test suite (`Text` not imported in `db/models.py`) | Fixed; RAG finished in Prompt 10 |
| 2 | **No migration for the `documents` table** (Prompt 8): `alembic upgrade head` gave a DB without it | Added `0002_documents`, and `0004` for the bank-rule flags; verified upgrade/downgrade on Postgres 16 |
| 3 | Audit log missed the features, SHAP reasons and fairness result (a PLAN §6 rule); `fairness_ok` was hard-coded `True` | `services/decisions.py`: one `persist_decision` with a full audit entry and a real Fairness sign-off |
| 4 | Inclusion Lift was always 100%: `has_bank_account`/`has_salary_slip` were never stored, so the bank rule approved nobody | Flags on `users`; the lift uses the notebook rule on stored data |
| 5 | Bhorsha (Prompt 9) never called the LLM: the interviewer prompt was unused and scoring was keyword-only | Interviewer + rubric scorer now go through `LLMClient` with versioned prompts, a hidden-reasoning JSON output, PII redaction and off-topic refusal. The mock keeps a deterministic heuristic |
| 6 | Document images were "encrypted" with a byte XOR, and `DELETE /me` left image files behind | `storage.py`: Fernet encryption, R2/MinIO or filesystem backends, 30-day purge; images deleted with the user |
| 7 | The DeepSeek-OCR client posted to a non-existent `/ocr` endpoint | OpenAI-compatible vision call to a DeepSeek-OCR server (`DEEPSEEK_OCR_URL`) |
| 8 | Feature builder invented values: no bills seen → `bills_on_time = 0.95`, no recharges → 0.50; OCR due dates were ignored | Now `None` (missing) when unseen; the OCR due day and paid stamp are used (commit `5937bed`) |
| 9 | Model/meta cache bug: `load_meta()` and `load_meta(model_dir=None)` evicted each other, so the JSON was re-read constantly and thresholds could diverge | Cache keyed by the resolved directory (commit `5937bed`) |
| – | Borrower auth accepted a raw user id as a "token", so anyone could delete anyone's data | HMAC-signed, expiring session tokens via `POST /auth/session` (commit `143bfa7`) |
| – | README claimed the datasets were in the repo via Git LFS; `datasets/` is git-ignored | README corrected (commit `d773d73`) |

---

## 3. Prompts 10–21: built

| # | What | Commit |
|---|---|---|
| 10 | RAG: idempotent ingest, BM25 + pgvector + rerank, cited tips, 30-question eval | `2577523` |
| 11 | LangGraph supervisor (5 agents), `POST /apply`, review band, traces with prompt versions | `5937bed` |
| 12 | MCP server: 4 tools over stdio and authenticated HTTP | `c061af0` |
| 13 | Temporal loan lifecycle (+20% limit), loan endpoints, 4 Airflow DAGs | `3b044de` |
| 14 | Flower DP-FedAvg, 8 divisions, AUC 0.7555 (notebook 0.7574) | `fae900d` |
| 15 | Flutter borrower app, 10 screens, Bangla-first | `143bfa7` |
| 16 | React dashboard: KPIs, fairness gate, D3 map, feed, reports | `79eeeff` |
| 17 | Eval suite + CI gates (now 9) | `24c211d`, `8fcbe58` |
| 18 | Rate limits, upload checks, CORS, PII-free logs, Prometheus/Grafana, `docs/privacy.md` | `5dda2e9` |
| 19 | Heroku Procfile/release/app.json, `infra/smoke.sh`, `docs/deploy.md`, APK | `a119cc2` |
| 20 | Public docs site, README (whole app + notebook), architecture, demo script, judge Q&A | `d773d73` |
| 21 | QA, claim → evidence table, fresh-clone test, tag | this commit |

The root README now covers the whole app plus the notebook: sections, model contract, how to run it, all 11 figures and the data sources.

---

## 4. Test results (exact numbers)

| Check | Result |
|---|---|
| `uv run pytest` | 191 passed, 1 skipped, coverage 93% (`app/core` 100%) |
| `ruff check`, `ruff format --check`, `mypy backend/app mcp_server workflows federated` | all pass |
| `uv run python evals/run_all.py` | 9/9 gates: AUC 0.7644 · KS 0.3901 · Brier 0.168 · ECE 0.0057 · approval gap 0.0996 → **0.0131** · equalized-odds gap 0.0972 → **0.034** · SMS F1 1.0 · OCR F1 1.0 (mock) · RAG precision 0.95, hit rate 1.0 · explanations 300/300 · Bhorsha 100 vs 21 · prompt goldens 6/6 |
| `infra/smoke.sh http://localhost:8000 dev-key` | PASS 14/14 (Shathi approved, score ~696 with her SMS) |
| Heroku rehearsal (`release.sh` + `web.sh` on Postgres, API + MCP roles) | PASS 16/16 |
| `flutter analyze` / `flutter test` / integration (macOS, real API) | clean / 8 passed / 2 passed |
| Dashboard `tsc`, `vitest`, `build`, Playwright | pass / 4 passed / pass / 1 passed |
| Live demo data (4 personas + 4,000 synthetic applicants) | approval 58.9% vs bank rule 12.4%, newly included 49.5%, live approval gap 0.023 PASS |

---

## 5. What YOU still need to fix, and how (priority order)

| # | Item | Why it matters | How to fix |
|---|---|---|---|
| 1 | **Push the work** | 17 local commits and tag `v1.0.0` are not on GitHub (you asked me not to push) | `git push origin main && git push origin v1.0.0` |
| 2 | **Deploy API, MCP and dashboard** (Prompt 19) | Judges need public URLs; the `/docs` site and the smoke test against production depend on it | Follow `docs/deploy.md`: `heroku create` ×2 (TL_ROLE api/mcp), add Postgres + Redis, set config vars, `git push heroku main`, then Vercel for `apps/dashboard` with `VITE_API_BASE_URL`. Afterwards run `infra/smoke.sh <api> <key> <mcp>` |
| 3 | **Set production secrets** | Dev fallbacks exist for `SESSION_SECRET` and `STORAGE_ENCRYPTION_KEY` | Generation commands are in `docs/deploy.md` and `.env.example`; never reuse `dev-key` |
| 4 | **DeepSeek keys → live mode** | All AI runs on deterministic mocks today | Set `LLM_MODE=live DEEPSEEK_API_KEY=…`. For OCR, host DeepSeek-OCR behind an OpenAI-compatible server (e.g. vLLM) and set `DEEPSEEK_OCR_URL`. Then run `LLM_MODE=live uv run python evals/run_all.py` for real OCR/RAG/LLM-judge numbers. Keep `LLM_MODE=mock` as the stage backup |
| 5 | **Fill README links** (demo URL, video, deck) | Prompt 20 acceptance | Edit the link table at the top of `README.md` after steps 2 and 8 |
| 6 | **Replace the Bangladesh Bank summaries with the real circulars** | `docs/knowledge/bb_*.md` are team-written summaries; numbers such as limits and the interest cap are **unverified** and may be outdated | Download the official PDFs from bb.org.bd into `docs/knowledge/`, delete or correct the summaries, update `SOURCES.md`, run `make ingest` |
| 7 | **Correct claims in the submission forms** | Some tools are wired but not exercised | **DeepSeek-OCR LoRA**: only a plan (`evals/ocr/FINETUNE.md`); say "planned" or train it. **BGE-M3/BGE reranker**: supported but off by default; say "supported" or enable `EMBEDDINGS_MODE=bge-m3` (`uv sync --extra rag-live`, ~3 GB). **Airflow**: DAGs and tested tasks, but not run inside Airflow. **Plotly**: not used; remove it from the form. **Redis**: provisioned, not used yet |
| 8 | **Android emulator run + screen recording** (Prompt 15) | No AVD and no screen-capture permission on this machine | `flutter emulators --create --name tl && flutter emulators --launch tl`, then `flutter test integration_test -d emulator-5554 --dart-define=API_BASE_URL=http://10.0.2.2:8000`. Record with QuickTime or the phone into `docs/media/` |
| 9 | **Publish the APK** | Prompt 19 acceptance | `flutter build apk --release --dart-define=API_BASE_URL=<prod> --dart-define=API_KEY=<app key>`, then `gh release create v1.0.0 build/app/outputs/flutter-apk/app-release.apk` |
| 10 | **Human rehearsal of the 3-minute demo** | Prompt 20 acceptance | Use `docs/DEMO_SCRIPT.md`; log the time in its rehearsal table |
| 11 | **Branch protection** ("freeze main") | Prompt 21 | GitHub → Settings → Branches → protect `main` after pushing |
| 12 | Commit-message format | The prompts say `prompt NN: title`, but your existing history uses `feat:`/`fix:` one-liners (the prompts also ask for that) | Kept your style; no action unless you prefer the other |

---

## 6. What is still DEMO / mock (be honest with judges)

| Area | Demo behaviour | Real-world version |
|---|---|---|
| Training data | Model trained on **100,000 simulated** borrowers (validated on real Home Credit and LendingClub) | Retrain on a lender's historical micro-loans; only `models/` changes |
| LLM calls | `LLM_MODE=mock` by default: deterministic Bhorsha rubric, interviewer, explainer summary and SMS fallback | DeepSeek live (step 4) |
| OCR | Mock returns the labelled fields for the 10 eval images, so OCR F1 = 1.0 measures the pipeline only | Live DeepSeek-OCR plus labelled real bills (`evals/ocr/README.md`) |
| Embeddings | Offline 1024-d hash embedding + lexical rerank; weak for English questions over Bangla text | `EMBEDDINGS_MODE=bge-m3`, `RERANKER_MODE=bge` |
| SMS on the server | `/apply` and `/parse/sms` accept raw demo SMS only when `DEMO_MODE=true` (never stored) | On-device parsing in the app; send only features |
| Sign-up | `POST /auth/session` issues a borrower token with just the app API key | Put it behind phone-number OTP |
| Disbursement and reminders | Mock disbursement (status change), `MockSender` reminders | Wallet disbursement API, SMS/WhatsApp gateway |
| Bhorsha sessions | Kept **in memory** per process: lost on restart, not shared across dynos | Store sessions in Postgres/Redis (see improvement 1) |
| Rate limiter | In-memory per process | Redis counters (`REDIS_URL` is ready) |
| Document storage on Heroku | Encrypted filesystem store unless R2 vars are set; wiped on dyno restart | Set `R2_*` and apply `infra/r2-lifecycle.json` |
| Federated learning | Flower server and strategy run in-process with 8 simulated clients | Real clients via `python -m federated.client` over gRPC; add SecAgg+ and privacy accounting |
| Live TPR/FPR on the dashboard | Shows approval parity live; TPR/FPR come from the notebook test set (declined applicants have no outcomes) | Back-testing or reject inference |
| APK signing | Flutter default debug signing | Release keystore for the Play Store |
| Demo personas | Shathi, Rafi, Rina and newcomer Mitu, plus 4,000 synthetic applicants; `POST /demo/reset` re-seeds | Real users |

---

## 7. Improvements I recommend (after the must-fixes)

1. **Persist Bhorsha sessions** in a `bhorsha_sessions` table (JSON state, user id, expiry). This is the main robustness gap for a multi-dyno or restarted demo (~1 hour).
2. **Redis-backed rate limiter** so limits hold across dynos.
3. **Enable BGE-M3 for the final demo** and re-run `evals/rag/evaluate.py`; it improves cross-lingual tips.
4. **Live eval run with keys**: add the LLM-as-judge and live OCR F1 numbers to the README and deck.
5. **Train the DeepSeek-OCR LoRA** on 200–500 labelled Bangla bills/khata pages (procedure in `evals/ocr/FINETUNE.md`) so the form claim becomes true.
6. **OTP sign-up** in the app (phone hash already stored).
7. **Camera picker** for bills in the app (`image_picker`); the demo uses a bundled sample photo.
8. **Dashboard bundle splitting** (~600 kB JS): lazy-load the map and chart pages.
9. **Privacy accounting** (ε, δ) for the Flower DP setup, for judges who ask for a number.
10. **Real repayment webhooks** feeding `/loans/{id}/repayments`, so live TPR/FPR become measurable.

---

## 8. How to run everything

`README.md` → Quick start. The short version:

```bash
uv sync && export DATABASE_URL=sqlite:///./trustledger.db DEMO_MODE=true API_KEYS=dev-key
make seed && make ingest && make api                    # API on :8000 (/docs = Swagger)
infra/smoke.sh http://localhost:8000 dev-key             # Shathi end to end
uv run python evals/run_all.py                           # 9 quality gates
cd apps/dashboard && npm install && npm run dev          # dashboard (+ /docs site)
cd apps/mobile && flutter run -d macos                   # borrower app
```

Where things are documented:

| Topic | File |
|---|---|
| Deployment | `docs/deploy.md` |
| Privacy | `docs/privacy.md` |
| Architecture | `docs/architecture.md` |
| API | `docs/api.md` |
| Demo script and judge Q&A | `docs/DEMO_SCRIPT.md`, `docs/JUDGE_QA.md` |
| Per-step reports | `docs/PROMPT*_REPORT.md` |

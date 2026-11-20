# PROMPT.md

Build tracker for TrustLedger. Run prompts **in order**. Each prompt follows `PLAN_CONTEXT.md`.
When a prompt is finished: its report exists in `docs/`, its box is ticked here, and it is committed as `prompt NN: title`.

**How to run a prompt with Claude Code:**
```
Read PLAN_CONTEXT.md, PROMPT.md and all docs/PROMPT*_REPORT.md. Then execute docs/prompts/PROMPT_NN.md exactly.
```

## Foundation
- [x] **Prompt 1: Repository audit and baseline** — `docs/prompts/PROMPT_01.md` — report: `docs/PROMPT1_REPORT.md`
- [x] **Prompt 2: Monorepo structure, tooling and CI** — `docs/prompts/PROMPT_02.md` — report: `docs/PROMPT2_REPORT.md`

## Scoring and API
- [x] **Prompt 3: Scoring core package** — `docs/prompts/PROMPT_03.md` — report: `docs/PROMPT3_REPORT.md`
- [x] **Prompt 4: Database, consent and persistence** — `docs/prompts/PROMPT_04.md` — report: `docs/PROMPT4_REPORT.md`
- [x] **Prompt 5: FastAPI backend v1** — `docs/prompts/PROMPT_05.md` — report: `docs/PROMPT5_REPORT.md`

## AI layer
- [x] **Prompt 6: LLM client and SMS parser** — `docs/prompts/PROMPT_06.md` — report: `docs/PROMPT6_REPORT.md`
- [x] **Prompt 7: Feature builder** — `docs/prompts/PROMPT_07.md` — report: `docs/PROMPT7_REPORT.md`
- [x] **Prompt 8: Document OCR — bills, receipts and khata** — `docs/prompts/PROMPT_08.md` — report: `docs/PROMPT8_REPORT.md`
- [x] **Prompt 9: Bhorsha — psychometric chat assessment** — `docs/prompts/PROMPT_09.md` — report: `docs/PROMPT9_REPORT.md`
- [x] **Prompt 10: RAG knowledge base** — `docs/prompts/PROMPT_10.md` — report: `docs/PROMPT10_REPORT.md`
- [x] **Prompt 11: LangGraph multi-agent pipeline** — `docs/prompts/PROMPT_11.md` — report: `docs/PROMPT11_REPORT.md`

## Integration and platform
- [x] **Prompt 12: MCP server** — `docs/prompts/PROMPT_12.md` — report: `docs/PROMPT12_REPORT.md`
- [x] **Prompt 13: Workflows — Temporal and Airflow** — `docs/prompts/PROMPT_13.md` — report: `docs/PROMPT13_REPORT.md`
- [x] **Prompt 14: Federated learning with Flower** — `docs/prompts/PROMPT_14.md` — report: `docs/PROMPT14_REPORT.md`

## Apps
- [x] **Prompt 15: Borrower app (Flutter)** — `docs/prompts/PROMPT_15.md` — report: `docs/PROMPT15_REPORT.md`
- [x] **Prompt 16: Lender dashboard (React)** — `docs/prompts/PROMPT_16.md` — report: `docs/PROMPT16_REPORT.md`

## Quality
- [x] **Prompt 17: Evaluation suite and quality gates** — `docs/prompts/PROMPT_17.md` — report: `docs/PROMPT17_REPORT.md`
- [x] **Prompt 18: Security, privacy hardening and observability** — `docs/prompts/PROMPT_18.md` — report: `docs/PROMPT18_REPORT.md`

## Launch
- [x] **Prompt 19: Deployment — Heroku and demo environment** — `docs/prompts/PROMPT_19.md` — report: `docs/PROMPT19_REPORT.md`
- [x] **Prompt 20: Public /docs site, README and submission pack** — `docs/prompts/PROMPT_20.md` — report: `docs/PROMPT20_REPORT.md`
- [x] **Prompt 21: Final QA and submission readiness** — `docs/prompts/PROMPT_21.md` — report: `docs/PROMPT21_REPORT.md`

## Web and Containers
- [x] **Prompt 22: Borrower web app — Flutter Web from the same codebase** — `docs/prompts/PROMPT_22.md` — report: `docs/PROMPT22_REPORT.md`
- [ ] **Prompt 23: Web app polish, design parity QA and deployment** — `docs/prompts/PROMPT_23.md` — report: `docs/PROMPT23_REPORT.md`
- [ ] **Prompt 24: Full-stack Dockerization — Frontend, Backend and One-Command Build** — `docs/prompts/PROMPT_24.md` — report: `docs/PROMPT24_REPORT.md`

## Status

| Prompt | Status | Report | Notes |
|---|---|---|---|
| 1 | done | docs/PROMPT1_REPORT.md | Baseline audit & env configured |
| 2 | done | docs/PROMPT2_REPORT.md | Monorepo structure, tooling & CI |
| 3 | done | docs/PROMPT3_REPORT.md | Scoring core, SHAP explain & fairness checks |
| 4 | done | docs/PROMPT4_REPORT.md | Database, consent & persistence |
| 5 | done | docs/PROMPT5_REPORT.md | FastAPI backend v1, REST endpoints & docs |
| 6 | done | docs/PROMPT6_REPORT.md | LLM client gateway, Presidio redaction, SMS parser |
| 7 | done | docs/PROMPT7_REPORT.md | Feature builder, clipping & demo parse endpoints |
| 8 | done | docs/PROMPT8_REPORT.md | DeepSeek-OCR for bills, receipts & khata |
| 9 | done | docs/PROMPT9_REPORT.md | Bhorsha psychometric chat assessment |
| 10 | done | docs/PROMPT10_REPORT.md | Hybrid RAG, pgvector, 30-question eval |
| 11 | done | docs/PROMPT11_REPORT.md | LangGraph supervisor, /apply, traces |
| 12 | done | docs/PROMPT12_REPORT.md | MCP tools over stdio + HTTP with API keys |
| 13 | done | docs/PROMPT13_REPORT.md | Temporal LoanWorkflow + Airflow DAGs |
| 14 | done | docs/PROMPT14_REPORT.md | Flower DP-FedAvg, AUC 0.7555 |
| 15 | partial | docs/PROMPT15_REPORT.md | Flutter app; macOS e2e passes, emulator pending |
| 16 | done | docs/PROMPT16_REPORT.md | React dashboard, live stats endpoints |
| 17 | done | docs/PROMPT17_REPORT.md | 9 offline gates (incl. Fairlearn), CI fails on bias |
| 18 | done | docs/PROMPT18_REPORT.md | Rate limits, CORS, metrics, Grafana, privacy.md |
| 19 | partial | docs/PROMPT19_REPORT.md | Deploy-ready; public URLs blocked on team accounts |
| 20 | partial | docs/PROMPT20_REPORT.md | Docs site, README, demo script, judge Q&A |
| 21 | partial | docs/PROMPT21_REPORT.md | QA done; deploy/keys/media pending team |
| 22 | done | docs/PROMPT22_REPORT.md | Borrower web app (Flutter Web), design tokens, /app route |
| 23 | pending | docs/PROMPT23_REPORT.md | Web app polish, design parity QA and deployment |
| 24 | pending | docs/PROMPT24_REPORT.md | Dockerize everything frontend & backend, 1-command build |

Timeline: code freeze **23 Dec 2026**, final **26 Dec 2026**.

# Prompt 11 report — LangGraph multi-agent pipeline

**Date:** 2026-11-20
**Status:** done

## Summary
`POST /apply` runs a LangGraph supervisor graph: Data Agent → Bhorsha Router → Scoring Agent →
Explainer Agent → Fairness Agent → finalize. The supervisor routes back after every worker and stops early
when consent or data is missing, or when Bhorsha is required. Borderline cases (|p − threshold| ≤ 0.03) go to `needs_review`,
and nothing is approved without Fairness Agent sign-off. Every run stores a trace in `audit_log` with node timings,
model version and the versions of all six prompts.

## Changes
| File | Change |
|---|---|
| `backend/app/agents/graph.py` | `PipelineState`, supervisor + 5 workers + finalize, `run_pipeline()` with trace persistence |
| `backend/app/agents/explainer.py` | SHAP reasons, RAG-grounded tips (one source each), LLM Bangla summary checked so it names only SHAP features, with a template fallback |
| `backend/app/agents/prompts/*.md`, `prompts.py` | 6 versioned role prompts (role, objective, constraints, output schema) |
| `backend/app/api/routers/apply.py`, `schemas/apply.py` | `POST /apply`, `GET /traces/{trace_id}` |
| `backend/app/services/decisions.py` | Fairness sign-off used by the agent; explicit non-approved status is never stored as approved |
| `backend/app/parsers/features.py` | Fix: `bills_on_time`/`recharge_regularity` are now `None` when unseen (were 0.95 / 0.50 defaults), OCR due day and paid stamp used |
| `backend/app/core/model.py` | Fix: cache keyed by resolved directory (`load_meta()` and `load_meta(model_dir=None)` used to evict each other and reload the JSON) |
| `backend/tests/test_agents.py`, `test_feature_builder.py`, `test_model.py` | 10 agent tests, 2 new feature-formula tests |

## How to run / verify
```bash
uv run pytest backend/tests/test_agents.py
make api   # then POST /apply {"user_id": "<shathi id from seed>", "amount_bdt": 15000}
```

## Tests and checks
- ruff: pass · mypy: pass (61 files)
- pytest: 164 passed, 1 skipped (live key)
- Personas through `run_pipeline` (mock, 15,000 BDT):

| Persona | Group | Status | Score | p_repay | Node path |
|---|---|---|---|---|---|
| Shathi | F_urban | approved | 717 | 0.953 | data → router → scoring → explainer → fairness → finalize |
| Student | M_urban | approved | 674 | 0.918 | same |
| Homemaker (Bhorsha only) | F_rural | approved | 650 | 0.889 | same |

Shathi scores 717 here rather than 691 because `loan_to_income` is recomputed from the requested amount (15,000 / 14,000 ≈ 1.07, not 4.0).
At 56,000 BDT from her 12-month SMS history she is approved with loan_to_income = 4.0 (test).

## Acceptance criteria
- [x] `/apply` works end to end in mock mode for all 3 personas (tests + table)
- [x] Each decision has a complete trace (`agent_trace` audit row; also `trace_id` in the decision's audit entry)
- [x] Prompt files exist and are referenced by version in traces
- [x] Tests: Shathi end-to-end approved, zero-history user routed to Bhorsha (and scored after it), borderline goes to review, Fairness Agent blocks a missing threshold

## Decisions and deviations
- **Deterministic supervisor:** routing is code, not an LLM call. Lending decisions must be reproducible and auditable. The policy still lives in `prompts/supervisor.md` and is versioned in traces.
- **LLM use:** only the Explainer summary uses DeepSeek. Scoring and fairness are deterministic, and the summary is rejected if it mentions a feature not in the SHAP output.
- **Missing threshold:** `score_applicant` already refuses an unknown group. The pipeline returns `rejected_input` in that case, and `fairness_check` blocks it independently (covered by a direct test).

## Known issues / follow-ups
- MCP (Prompt 12) and Temporal (Prompt 13) call `/apply` and `/score`.

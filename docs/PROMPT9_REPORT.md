# Prompt 9 report — Bhorsha — psychometric chat assessment

**Date:** 2026-11-20
**Status:** done

## Summary
Engineered the Bhorsha (ভরসা) conversational psychometric credit assessment module enabling zero-history borrowers to qualify for loans without bank statements or digital transaction trails. Developed a 12-question scenario bank (`backend/app/bhorsha/questions.yaml`) in natural Bengali and English across planning, saving, risk attitude, consistency, and emergency preparedness with consistency-paired verification. Built the interviewer dialogue agent (`backend/app/bhorsha/interviewer.py`), rubric-based scorer with hidden chain-of-thought and anti-gaming controls (`backend/app/bhorsha/scorer.py`), and REST endpoints (`/bhorsha/start`, `/bhorsha/{session_id}/answer`, `/bhorsha/{session_id}/result`) that write calibrated `bhorsha_score` directly into applicant feature snapshots.

## Changes
| File | Change |
|---|---|
| `backend/app/bhorsha/questions.yaml` | Authored 12 situational questions with rubrics (strong, moderate, weak) across 5 psychometric dimensions, including 4 consistency-check question pairs. |
| `backend/app/bhorsha/prompts/interviewer.md` | Defined system role prompt for the Bhorsha conversational agent in warm, polite colloquial Bengali with strict privacy boundaries (never asking for NID or PINs). |
| `backend/app/bhorsha/scorer.py` | Implemented rubric scoring (`evaluate_single_answer`, `compute_bhorsha_score`), consistency checks across paired questions, and anti-gaming detectors (rapid submission <2s, identical copy-paste repetition, minimal/evasive answers). |
| `backend/app/bhorsha/interviewer.py` | Session manager controlling multi-turn conversational progression (<=12 turns), turn sequencing, and persisting final `bhorsha_score` into `FeatureSnapshot`. |
| `backend/app/bhorsha/__init__.py` | Exported `start_bhorsha_session`, `answer_bhorsha_question`, `get_bhorsha_result`, `compute_bhorsha_score`, `evaluate_single_answer`, and `load_question_bank`. |
| `backend/app/schemas/bhorsha.py` | Defined Pydantic models: `BhorshaStartRequest`, `BhorshaStartResponse`, `BhorshaAnswerRequest`, `BhorshaAnswerResponse`, and `BhorshaResultResponse`. |
| `backend/app/api/routers/bhorsha.py` | Implemented REST endpoints: `POST /bhorsha/start`, `POST /bhorsha/{session_id}/answer`, `GET /bhorsha/{session_id}/result`. Enforces active `bhorsha` consent before session initiation. |
| `backend/app/main.py` | Registered `bhorsha_router`. |
| `backend/tests/test_bhorsha.py` | Built comprehensive test suite covering question bank loading, persona scoring separation (responsible >= 75 vs. careless <= 50), score stability, anti-gaming flags, <=12 turn lifecycle, and end-to-end zero-history borrower scoring flow. |
| `docs/PROMPT.md` | Marked Prompt 9 complete in checklist and updated status table. |

## How to run / verify
```bash
# Run Bhorsha unit and integration tests
uv run pytest backend/tests/test_bhorsha.py -v

# Run full test suite with coverage
uv run pytest

# Run linting and type checks
uv run ruff check
uv run ruff format --check
uv run mypy backend/app
```

## Tests and checks
- **ruff check:** pass (`uv run ruff check` -> `All checks passed!`)
- **ruff format:** pass (`uv run ruff format --check` -> `127 files already formatted`)
- **mypy:** pass (`uv run mypy backend/app` -> `Success: no issues found in 47 source files`)
- **pytest:** pass (`uv run pytest` -> 137 passed, 1 skipped, 0 failed, 94% statement coverage)
- **Zero-history end-to-end check:** pass (`test_zero_history_user_completes_bhorsha_and_gets_full_score_decision` verified user with zero financial history completes Bhorsha, saves snapshot, and obtains full `ScoreResponse` from `/score`).
- **Persona discrimination check:** pass (`test_responsible_persona_scores_higher_than_careless` verified responsible answers score >= 75.0, careless score <= 50.0).
- **Anti-gaming check:** pass (`test_anti_gaming_detection` verified rapid submissions (<2s) and copy-paste duplicates trigger audit flags).

## Acceptance criteria
- [x] A zero-history user completes Bhorsha and then gets a full `Decision` from `/score` — verified in `test_zero_history_user_completes_bhorsha_and_gets_full_score_decision`.
- [x] Scores are stable (same answers -> same score in mock mode) — verified in `test_responsible_persona_scores_higher_than_careless`.
- [x] Questions and prompts reviewed and listed in the report — 12 scenarios across 5 dimensions (`plan_01`, `save_01`, `risk_01`, `emerg_01`, `const_01`, `debt_01`, `plan_02_pair`, `save_02_pair`, `risk_02_pair`, `emerg_02_pair`, `const_02_pair`, `honesty_01`) and role prompt in `backend/app/bhorsha/prompts/interviewer.md`.

## Decisions and deviations
- Paired questions (`pair_id`) check cross-consistency: if an applicant claims high emergency savings on `save_01` but admits having zero fallback on `emerg_02_pair`, a contradiction penalty reduces the overall score and triggers `inconsistency_pair_*` flags.

## Known issues / follow-ups
- Ready for Prompt 10 to implement RAG knowledge base for grounding explanation tips in Bangladesh Bank regulations and financial literacy guides.

# Prompt 09 — Bhorsha — psychometric chat assessment

> **Before you start:** read `PLAN_CONTEXT.md` fully, then `PROMPT.md` and every existing `docs/PROMPT*_REPORT.md`. Follow PLAN_CONTEXT.md §8 (how every prompt is run). If this prompt conflicts with PLAN_CONTEXT.md, PLAN_CONTEXT.md wins — note it in the report.

**Owner:** Dipanwita (content) + Prayangshu
**Depends on:** Prompt 5, Prompt 6
**Report:** `docs/PROMPT9_REPORT.md`

## Goal
Let zero-history users earn a `bhorsha_score` (0–100) through a short, friendly Bangla chat.

## Tasks
- `bhorsha/questions.yaml`: 10–12 scenario questions in Bangla (with English translations) covering planning, saving, risk attitude, consistency, handling emergencies. Each question has a rubric (what a strong / weak answer shows) and 2 consistency-pair questions asked in different words.
- `bhorsha/interviewer.py`: DeepSeek-driven conversation (role prompt in `bhorsha/prompts/interviewer.md`): warm, simple Bangla, one question at a time, never asks for sensitive data, refuses off-topic requests.
- `bhorsha/scorer.py`: per-answer rubric scoring with a hidden chain-of-thought (only the final JSON is kept), consistency check across paired questions, anti-gaming signals (copy-paste detection, answer timing, identical answers), final 0–100 score with confidence.
- Endpoints: `POST /bhorsha/start`, `POST /bhorsha/{session}/answer`, `GET /bhorsha/{session}/result` → writes `bhorsha_score` into the user's feature snapshot.
- Tests in mock mode: a responsible persona scores higher than a careless one; copy-pasted answers are flagged; session completes in ≤ 12 turns.

## Acceptance criteria
- A zero-history user completes Bhorsha and then gets a full `Decision` from `/score`
- Scores are stable (same answers → same score in mock mode)
- Questions and prompts reviewed and listed in the report

## Out of scope
UI.

## When finished
1. Run `ruff check`, `ruff format --check`, `mypy backend/app`, `pytest` (plus any checks above) and fix failures. Skip a tool only if it isn't set up yet, and say so in the report.
2. Write `docs/PROMPT9_REPORT.md` using the template in PLAN_CONTEXT.md §9. Include real command output numbers, not estimates.
3. Tick Prompt 9 in `PROMPT.md`.
4. Commit: format :feat: fix: oneliner no description 

# Prompt 10 — RAG knowledge base

> **Before you start:** read `PLAN_CONTEXT.md` fully, then `PROMPT.md` and every existing `docs/PROMPT*_REPORT.md`. Follow PLAN_CONTEXT.md §8 (how every prompt is run). If this prompt conflicts with PLAN_CONTEXT.md, PLAN_CONTEXT.md wins — note it in the report.

**Owner:** Fariha (content) + Prayangshu
**Depends on:** Prompt 4, Prompt 6
**Report:** `docs/PROMPT10_REPORT.md`

## Goal
Ground improvement tips and Bhorsha answers in real Bangladesh Bank rules and Bangla financial-literacy content.

## Tasks
- `docs/knowledge/` with source documents (public Bangladesh Bank circulars on digital lending/MFS that the team downloads, plus team-written Bangla financial-literacy notes). Record each source URL in `docs/knowledge/SOURCES.md`.
- `rag/ingest.py`: load PDF/HTML/Markdown → semantic chunking (~400 tokens) → contextual header per chunk → BGE-M3 embeddings → pgvector.
- `rag/retrieve.py`: hybrid BM25 + vector, BGE reranker, return chunks with source and URL.
- `rag/compress.py`: optional LLMLingua compression before LLM calls (feature-flagged).
- Use in the Explainer: each tip may cite one source.
- `evals/rag/`: 30 question/answer pairs; RAGAS faithfulness + context precision script (runs with mock LLM, real numbers in live mode).

## Acceptance criteria
- Ingestion runs from one command and is idempotent
- Retrieval returns relevant chunks for 5 sample queries listed in the report
- RAG eval script runs

## Out of scope
Agent orchestration.

## When finished
1. Run `ruff check`, `ruff format --check`, `mypy backend/app`, `pytest` (plus any checks above) and fix failures. Skip a tool only if it isn't set up yet, and say so in the report.
2. Write `docs/PROMPT10_REPORT.md` using the template in PLAN_CONTEXT.md §9. Include real command output numbers, not estimates.
3. Tick Prompt 10 in `PROMPT.md`.
4. Commit: format :feat: fix: oneliner no description

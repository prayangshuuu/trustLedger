# Prompt 10 report — RAG knowledge base

**Date:** 2026-11-20
**Status:** done (BGE-M3 / BGE reranker live models optional, see deviations)

## Summary
Built a hybrid RAG knowledge base over `docs/knowledge/`: one-command idempotent ingestion
(Markdown/HTML/PDF/text, section-aware ~400-token chunks with a `Title > Section` contextual header,
1024-d embeddings stored in pgvector), hybrid BM25 + vector retrieval fused with reciprocal rank and
reranked, a feature-flagged compressor, and tip grounding so each Bangla tip can cite one source.
A 30-question eval computes RAGAS-style context precision, recall and faithfulness.

## Changes
| File | Change |
|---|---|
| `backend/app/rag/ingest.py` | Loaders, section + window chunking, contextual headers, content-hash idempotency, stale-doc cleanup, CLI |
| `backend/app/rag/retrieve.py` | BM25, pgvector `<=>` search (SQLite cosine fallback), RRF fusion, BGE / lexical reranker |
| `backend/app/rag/embeddings.py` | `EMBEDDINGS_MODE=bge-m3` (sentence-transformers) or deterministic 1024-d hash embedding |
| `backend/app/rag/compress.py` | `RAG_COMPRESSION` flag; LLMLingua-2 when installed, numeric-safe heuristic otherwise |
| `backend/app/rag/tips.py` | `ground_tips()` attaches one `{title, url, excerpt}` source per tip (used by the Explainer in Prompt 11) |
| `backend/app/db/models.py`, `alembic/versions/0003_knowledge_chunks.py` | `knowledge_chunks` with `vector(1024)` on Postgres, `content_hash` |
| `docs/knowledge/*` | 6 documents (2 new team-written Bangla guides), `SOURCES.md` with verification status |
| `evals/rag/qa.json`, `evaluate.py`, `README.md` | 30 Q/A pairs, metrics script (mock + live) |
| `backend/tests/test_rag.py` | 9 tests |
| `pyproject.toml` | `rag-live` optional extra (sentence-transformers, llmlingua) |

## How to run / verify
```bash
uv run python -m app.rag.ingest          # run twice: second run reports "unchanged"
uv run python evals/rag/evaluate.py
uv run pytest backend/tests/test_rag.py
```

## Tests and checks
- ruff: pass · mypy: pass (56 files)
- pytest: 152 passed, 1 skipped (live DeepSeek), coverage 92% total; `app/rag` 88–92%
- Ingestion: 23 chunks from 6 documents; second run: all "unchanged", count still 23 (SQLite and Postgres 16 + pgvector)
- RAG eval (mock, k=3): context_precision **0.95**, context_recall **0.972**, hit_rate **1.00**, faithfulness 1.00 (extractive answers, so ~1.0 by construction)

Five sample queries (Postgres, pgvector, top hit):

| Query | Top chunk |
|---|---|
| বিল সময়মতো পরিশোধ করলে স্কোরে কী প্রভাব পড়ে? | trustledger_score_guide_bn › ২. সময়মতো বিল পরিশোধ |
| জরুরি তহবিল কত মাসের খরচের সমান হওয়া উচিত? | financial_literacy_bangla_guide › ৩. জরুরি তহবিল |
| পিন বা ওটিপি কাউকে বলা যাবে কি? | data_rights_and_safety_bn › ৩. পিন ও ওটিপি নিরাপত্তা |
| What is the maximum digital nano loan amount? | bb_digital_lending_guidelines (sections 1–2) |
| MFS wallet maximum balance ceiling | bb_mfs_regulations_2022 › 1. Transaction Limits |

## Acceptance criteria
- [x] Ingestion runs from one command and is idempotent
- [x] Retrieval returns relevant chunks for 5 sample queries (table above, also a parametrised test)
- [x] RAG eval script runs

## Decisions and deviations
- **Embeddings/reranker:** BGE-M3 and `bge-reranker-v2-m3` are wired (`EMBEDDINGS_MODE=bge-m3`, `RERANKER_MODE=bge`, `uv sync --extra rag-live`) but not the default, because they need ~3 GB of model downloads and would break offline CI and Heroku slug limits. The default hash embedding keeps the same 1024-d pgvector schema. It is lexical only, so English questions over Bangla text retrieve poorly until BGE-M3 is enabled.
- **RAGAS:** the metrics follow RAGAS definitions but are implemented directly (the `ragas` package pulls LangChain and needs an LLM for every metric).
- **Sources:** the Bangladesh Bank files are team-written summaries, not the circular text. `SOURCES.md` marks them unverified. The `trustledger.org` URLs, which pointed to a domain the team does not own, were replaced with repository links.

## Known issues / follow-ups
- BLOCKED for the team: download the real Bangladesh Bank circular PDFs into `docs/knowledge/` and re-run ingestion; check every figure in the summaries.
- Prompt 11's Explainer calls `ground_tips()`.

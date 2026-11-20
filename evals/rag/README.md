# RAG evaluation

`qa.json` holds 30 question / ground-truth pairs (Bangla and English) over `docs/knowledge/`, each
labelled with the document and section that answers it.

```bash
uv run python evals/rag/evaluate.py            # offline, mock LLM
LLM_MODE=live DEEPSEEK_API_KEY=... uv run python evals/rag/evaluate.py
```

Metrics (RAGAS definitions, implemented directly so the suite has no heavy dependencies):

| Metric | Meaning |
|---|---|
| context_precision | Mean precision@i over the ranks that hold a relevant chunk |
| context_recall | Share of ground-truth tokens present in the retrieved context |
| hit_rate | Share of questions with a relevant chunk in the top k |
| faithfulness | Share of answer claims supported by the context |

In mock mode answers are extractive, so faithfulness is close to 1.0 by construction; the
meaningful offline numbers are precision, recall and hit rate. Live mode has DeepSeek write and
judge answers. With `EMBEDDINGS_MODE=bge-m3` (install `uv sync --extra rag-live`) cross-lingual
queries (English question, Bangla source) improve; the offline hash embedding is lexical only.

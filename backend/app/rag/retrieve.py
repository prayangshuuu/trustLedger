"""Hybrid retrieval: BM25 + vector search fused with reciprocal rank, then reranked.

Vector search runs in Postgres with pgvector (``<=>`` cosine distance); on SQLite it falls back
to an in-process cosine scan. Reranking uses BAAI/bge-reranker-v2-m3 when
``RERANKER_MODE=bge`` (needs the ``rag-live`` extra), otherwise a lexical-overlap reranker.
"""

import math
from collections import Counter
from dataclasses import dataclass
from functools import lru_cache
from typing import Any

from pgvector.sqlalchemy import Vector
from pydantic import BaseModel
from sqlalchemy import cast, literal, select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.db.models import KnowledgeChunk
from app.rag.embeddings import cosine, get_embedding, tokenize

RRF_K = 60


class RetrievedChunk(BaseModel):
    chunk_id: str
    doc_id: str
    title: str
    header: str
    source_url: str
    content: str
    score: float


@dataclass
class _Index:
    ids: list[str]
    rows: dict[str, KnowledgeChunk]
    tokens: list[list[str]]
    df: Counter[str]
    avgdl: float


_index_cache: dict[int, _Index] = {}


def clear_index_cache() -> None:
    _index_cache.clear()


def _build_index(db: Session) -> _Index:
    key = id(db.get_bind())
    cached = _index_cache.get(key)
    count = db.query(KnowledgeChunk).count()
    if cached is not None and len(cached.ids) == count:
        return cached
    rows = list(
        db.scalars(
            select(KnowledgeChunk).order_by(KnowledgeChunk.doc_id, KnowledgeChunk.chunk_index)
        )
    )
    for r in rows:
        db.expunge(r)
    tokens = [tokenize(f"{r.contextual_header} {r.content}") for r in rows]
    df: Counter[str] = Counter()
    for toks in tokens:
        df.update(set(toks))
    avgdl = sum(len(t) for t in tokens) / max(1, len(tokens))
    index = _Index([r.id for r in rows], {r.id: r for r in rows}, tokens, df, avgdl)
    _index_cache[key] = index
    return index


def bm25_scores(index: _Index, query: str, k1: float = 1.5, b: float = 0.75) -> dict[str, float]:
    q_terms = tokenize(query)
    n = len(index.ids)
    scores: dict[str, float] = {}
    for cid, toks in zip(index.ids, index.tokens, strict=True):
        tf = Counter(toks)
        s = 0.0
        for term in q_terms:
            if term not in tf:
                continue
            idf = math.log(1 + (n - index.df[term] + 0.5) / (index.df[term] + 0.5))
            freq = tf[term]
            s += idf * freq * (k1 + 1) / (freq + k1 * (1 - b + b * len(toks) / index.avgdl))
        if s > 0:
            scores[cid] = s
    return scores


def vector_ranking(db: Session, index: _Index, query: str, limit: int) -> list[str]:
    q_vec = get_embedding(query)
    if db.get_bind().dialect.name == "postgresql":
        stmt = (
            select(KnowledgeChunk.id)
            .order_by(
                KnowledgeChunk.embedding.op("<=>")(cast(literal(str(q_vec)), Vector(len(q_vec))))
            )
            .limit(limit)
        )
        return list(db.scalars(stmt))
    sims = {cid: cosine(q_vec, list(row.embedding)) for cid, row in index.rows.items()}
    return [cid for cid, _ in sorted(sims.items(), key=lambda kv: -kv[1])[:limit]]


@lru_cache(maxsize=1)
def _bge_reranker() -> Any:
    from sentence_transformers import CrossEncoder

    return CrossEncoder("BAAI/bge-reranker-v2-m3")


def rerank(
    query: str, candidates: list[KnowledgeChunk], bm25: dict[str, float] | None = None
) -> list[tuple[KnowledgeChunk, float]]:
    """BGE cross-encoder when enabled; otherwise 0.6 * normalised BM25 + 0.4 * cosine."""
    if not candidates:
        return []
    if get_settings().RERANKER_MODE.lower() == "bge":
        scores = _bge_reranker().predict([(query, c.content) for c in candidates])
        pairs = [(c, float(s)) for c, s in zip(candidates, scores, strict=True)]
    else:
        bm25 = bm25 or {}
        top_bm25 = max((bm25.get(c.id, 0.0) for c in candidates), default=0.0) or 1.0
        q_vec = get_embedding(query)
        pairs = [
            (
                c,
                0.6 * bm25.get(c.id, 0.0) / top_bm25
                + 0.4 * max(0.0, cosine(q_vec, list(c.embedding))),
            )
            for c in candidates
        ]
    return sorted(pairs, key=lambda p: -p[1])


def retrieve(db: Session, query: str, k: int = 3, candidates: int = 10) -> list[RetrievedChunk]:
    """Top-k chunks for a query, each with its source title and URL."""
    index = _build_index(db)
    if not index.ids:
        return []
    bm25 = bm25_scores(index, query)
    bm25_rank = [cid for cid, _ in sorted(bm25.items(), key=lambda kv: -kv[1])[:candidates]]
    vec_rank = vector_ranking(db, index, query, candidates)

    fused: dict[str, float] = {}
    for ranking in (bm25_rank, vec_rank):
        for rank, cid in enumerate(ranking):
            fused[cid] = fused.get(cid, 0.0) + 1.0 / (RRF_K + rank + 1)
    top = [
        index.rows[cid]
        for cid, _ in sorted(fused.items(), key=lambda kv: -kv[1])[:candidates]
        if cid in index.rows
    ]

    return [
        RetrievedChunk(
            chunk_id=c.id,
            doc_id=c.doc_id,
            title=c.title,
            header=c.contextual_header,
            source_url=c.source_url,
            content=c.content,
            score=round(score, 4),
        )
        for c, score in rerank(query, top, bm25)[:k]
    ]

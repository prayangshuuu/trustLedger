"""Embeddings for the RAG knowledge base.

``EMBEDDINGS_MODE=bge-m3`` uses BAAI/bge-m3 through sentence-transformers (install the
``rag-live`` extra; ~2.3 GB model download). The default ``hash`` mode is a deterministic
1024-d feature-hashing embedding so ingestion, retrieval and CI work fully offline with the
same vector dimension, which keeps the pgvector column identical in both modes.
"""

import hashlib
import math
import re
from functools import lru_cache
from typing import Any, Final

from app.config import get_settings

EMBEDDING_DIM: Final[int] = 1024
TOKEN_RE = re.compile(r"[\wঀ-৿]+")


def tokenize(text: str) -> list[str]:
    return TOKEN_RE.findall(text.lower())


def hash_embedding(text: str) -> list[float]:
    """Unit-length 1024-d hashed unigram + bigram embedding (Bangla and English)."""
    words = tokenize(text) or ["empty"]
    vector = [0.0] * EMBEDDING_DIM
    for i, word in enumerate(words):
        h1 = int(hashlib.md5(word.encode("utf-8")).hexdigest(), 16)
        vector[h1 % EMBEDDING_DIM] += 1.0 if (h1 >> 10) % 2 == 0 else -1.0
        if i < len(words) - 1:
            h2 = int(hashlib.sha256(f"{word}_{words[i + 1]}".encode()).hexdigest(), 16)
            vector[h2 % EMBEDDING_DIM] += 0.5 if (h2 >> 10) % 2 == 0 else -0.5
    norm = math.sqrt(sum(x * x for x in vector)) or 1.0
    return [x / norm for x in vector]


@lru_cache(maxsize=1)
def _bge_model() -> Any:
    from sentence_transformers import SentenceTransformer

    return SentenceTransformer("BAAI/bge-m3")


def embedding_mode() -> str:
    return get_settings().EMBEDDINGS_MODE.lower()


def get_embeddings(texts: list[str]) -> list[list[float]]:
    if embedding_mode() == "bge-m3":
        vectors = _bge_model().encode(texts, normalize_embeddings=True)
        return [list(map(float, v)) for v in vectors]
    return [hash_embedding(t) for t in texts]


def get_embedding(text: str) -> list[float]:
    return get_embeddings([text])[0]


def cosine(a: list[float], b: list[float]) -> float:
    return float(sum(x * y for x, y in zip(a, b, strict=False)))

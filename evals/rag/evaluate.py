"""RAG evaluation: context precision, context recall and faithfulness (RAGAS definitions).

Offline (LLM_MODE=mock): answers are extractive (best-supported sentence from the retrieved
context) and faithfulness is checked with token overlap. Live (LLM_MODE=live + key): DeepSeek
writes the answer from the context and judges each claim, as RAGAS does.

    uv run python evals/rag/evaluate.py [--k 3] [--json out.json]
"""

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))

from app.db.base import Base
from app.db.session import create_app_engine
from app.llm.client import get_llm_client, is_live
from app.rag.embeddings import tokenize
from app.rag.ingest import ingest_directory
from app.rag.retrieve import RetrievedChunk, retrieve
from pydantic import BaseModel
from sqlalchemy.orm import Session, sessionmaker

QA_FILE = Path(__file__).with_name("qa.json")
SENT_SPLIT = re.compile(r"(?<=[.!?।])\s+")


def is_relevant(chunk: RetrievedChunk, item: dict[str, Any]) -> bool:
    section = chunk.header.split(">")[-1].strip()
    return chunk.doc_id == item["relevant_doc"] and section.startswith(item["relevant_section"])


def context_precision(chunks: list[RetrievedChunk], item: dict[str, Any]) -> float:
    """RAGAS context precision: mean precision@i over ranks i holding a relevant chunk."""
    hits, total = 0, 0.0
    for i, c in enumerate(chunks, start=1):
        if is_relevant(c, item):
            hits += 1
            total += hits / i
    return total / hits if hits else 0.0


def overlap(sentence: str, context: str) -> float:
    s = set(tokenize(sentence))
    return len(s & set(tokenize(context))) / (len(s) or 1)


def extractive_answer(question: str, chunks: list[RetrievedChunk]) -> str:
    sentences = [
        s for c in chunks for s in SENT_SPLIT.split(c.content.replace("- ", "")) if s.strip()
    ]
    if not sentences:
        return ""
    return max(sentences, key=lambda s: overlap(question, s))


class Verdicts(BaseModel):
    supported: list[bool]


def live_answer_and_faithfulness(question: str, context: str) -> tuple[str, float]:
    llm = get_llm_client()
    answer = str(
        llm.chat(
            [
                {
                    "role": "system",
                    "content": "Answer only from the context, in the question's language, in one or two sentences.",
                },
                {
                    "role": "user",
                    "content": f"<context>{context}</context>\n<question>{question}</question>",
                },
            ]
        )
    )
    claims = [s for s in SENT_SPLIT.split(answer) if s.strip()]
    verdicts = llm.chat(
        [
            {
                "role": "system",
                "content": 'For each claim say if the context supports it. JSON: {"supported": [true|false, ...]}',
            },
            {
                "role": "user",
                "content": f"<context>{context}</context>\n<claims>{json.dumps(claims, ensure_ascii=False)}</claims>",
            },
        ],
        schema=Verdicts,
    )
    sup = verdicts.supported[: len(claims)]
    return answer, (sum(sup) / len(claims)) if claims else 0.0


def evaluate(db: Session, k: int = 3) -> dict[str, Any]:
    items = json.loads(QA_FILE.read_text(encoding="utf-8"))
    live = is_live()
    rows = []
    for item in items:
        chunks = retrieve(db, item["question"], k=k)
        context = "\n".join(c.content for c in chunks)
        if live:
            answer, faith = live_answer_and_faithfulness(item["question"], context)
        else:
            answer = extractive_answer(item["question"], chunks)
            sents = [s for s in SENT_SPLIT.split(answer) if s.strip()]
            faith = sum(overlap(s, context) >= 0.6 for s in sents) / len(sents) if sents else 0.0
        rows.append(
            {
                "id": item["id"],
                "context_precision": context_precision(chunks, item),
                "context_recall": overlap(item["ground_truth"], context),
                "hit_at_k": any(is_relevant(c, item) for c in chunks),
                "faithfulness": faith,
            }
        )
    n = len(rows)
    return {
        "mode": "live" if live else "mock",
        "k": k,
        "questions": n,
        "context_precision": round(sum(r["context_precision"] for r in rows) / n, 4),
        "context_recall": round(sum(r["context_recall"] for r in rows) / n, 4),
        "hit_rate": round(sum(r["hit_at_k"] for r in rows) / n, 4),
        "faithfulness": round(sum(r["faithfulness"] for r in rows) / n, 4),
        "misses": [r["id"] for r in rows if not r["hit_at_k"]],
    }


def run(k: int = 3) -> dict[str, Any]:
    engine = create_app_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with sessionmaker(bind=engine)() as db:
        ingest_directory(db)
        return evaluate(db, k)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--k", type=int, default=3)
    parser.add_argument("--json", type=Path)
    args = parser.parse_args()
    result = run(args.k)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    if args.json:
        args.json.write_text(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

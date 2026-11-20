"""RAG: idempotent ingestion, hybrid retrieval, tip grounding and compression flag."""

from pathlib import Path

import pytest
from app.db.base import Base
from app.db.models import KnowledgeChunk
from app.db.session import create_app_engine
from app.rag.compress import compress_context
from app.rag.ingest import chunk_document, ingest_directory, load_text
from app.rag.retrieve import retrieve
from app.rag.tips import ground_tips
from sqlalchemy.orm import Session, sessionmaker


@pytest.fixture
def db() -> Session:
    engine = create_app_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine)()
    ingest_directory(session)
    return session


def test_ingestion_is_idempotent(db: Session) -> None:
    first = db.query(KnowledgeChunk).count()
    assert first >= 20
    again = ingest_directory(db)
    assert all(n == 0 for n in again.values())
    assert db.query(KnowledgeChunk).count() == first
    chunk = db.query(KnowledgeChunk).first()
    assert chunk is not None and " > " in chunk.contextual_header and chunk.source_url


@pytest.mark.parametrize(
    ("query", "doc_id"),
    [
        ("বিল সময়মতো পরিশোধ করলে স্কোরে কী প্রভাব পড়ে?", "trustledger_score_guide_bn"),
        ("জরুরি তহবিল কত মাসের খরচের সমান হওয়া উচিত?", "financial_literacy_bangla_guide"),
        ("পিন বা ওটিপি কাউকে বলা যাবে কি?", "data_rights_and_safety_bn"),
        ("What is the maximum digital nano loan amount?", "bb_digital_lending_guidelines"),
        ("MFS wallet maximum balance ceiling", "bb_mfs_regulations_2022"),
    ],
)
def test_retrieval_returns_relevant_chunk_with_source(db: Session, query: str, doc_id: str) -> None:
    hits = retrieve(db, query, k=3)
    assert hits[0].doc_id == doc_id
    assert hits[0].source_url and hits[0].title


def test_tips_cite_one_source(db: Session) -> None:
    grounded = ground_tips(db, [("savings_ratio", "প্রতি মাসে আয়ের অন্তত ৫% সঞ্চয় করুন।")])
    assert grounded[0].source is not None
    assert grounded[0].source.url
    assert ground_tips(None, [("savings_ratio", "x")])[0].source is None


def test_html_and_long_section_chunking(tmp_path: Path) -> None:
    html = tmp_path / "note.html"
    html.write_text("<h1>T</h1><h2>Sec</h2><p>" + "word " * 900 + "</p><script>x</script>")
    text = load_text(html)
    assert "x" not in text.split()
    chunks = chunk_document("# T\n" + text, "T")
    assert len(chunks) >= 2
    assert all(c.token_count <= 400 for c in chunks)


def test_compression_is_feature_flagged() -> None:
    text = "the " * 30 + "ঋণ ৫০০০ টাকা"
    assert compress_context(text, enabled=False) == text
    compressed = compress_context(text, enabled=True)
    assert len(compressed) < len(text) and "৫০০০" in compressed

"""Ingest the knowledge base into ``knowledge_chunks``.

Load (Markdown / HTML / PDF / text) -> split by headings, then ~400-token windows -> contextual
header ``Title > Section`` prepended for embedding -> embeddings -> store. Idempotent: a document
whose content hash is unchanged is skipped; a changed one has its chunks replaced.

    uv run python -m app.rag.ingest            # ingest docs/knowledge
"""

import argparse
import hashlib
import re
from dataclasses import dataclass
from html.parser import HTMLParser
from pathlib import Path

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.db.models import KnowledgeChunk
from app.rag.embeddings import get_embeddings, tokenize

KNOWLEDGE_DIR = Path(__file__).resolve().parents[3] / "docs" / "knowledge"
SUPPORTED = {".md", ".markdown", ".txt", ".html", ".htm", ".pdf"}
SKIP_FILES = {"SOURCES.md", "README.md"}
CHUNK_TOKENS = 400
OVERLAP_TOKENS = 50
URL_RE = re.compile(r"\*\*Source URL:\*\*\s*(\S+)")
META_RE = re.compile(r"^\*\*[^*]{1,40}:\*\*")


@dataclass
class Chunk:
    index: int
    header: str
    content: str
    token_count: int


class _TextExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.parts: list[str] = []
        self._skip = False

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag in ("script", "style"):
            self._skip = True
        if tag in ("h1", "h2", "h3"):
            self.parts.append("\n## ")

    def handle_endtag(self, tag: str) -> None:
        if tag in ("script", "style"):
            self._skip = False
        if tag in ("p", "li", "h1", "h2", "h3", "div", "br"):
            self.parts.append("\n")

    def handle_data(self, data: str) -> None:
        if not self._skip:
            self.parts.append(data)


def load_text(path: Path) -> str:
    suffix = path.suffix.lower()
    if suffix == ".pdf":
        from pypdf import PdfReader

        return "\n".join(page.extract_text() or "" for page in PdfReader(str(path)).pages)
    raw = path.read_text(encoding="utf-8")
    if suffix in (".html", ".htm"):
        parser = _TextExtractor()
        parser.feed(raw)
        return "".join(parser.parts)
    return raw


def document_title(text: str, path: Path) -> str:
    for line in text.splitlines():
        if line.startswith("# "):
            return line[2:].strip()
    return path.stem.replace("_", " ")


def split_sections(text: str) -> list[tuple[str, str]]:
    """Split Markdown-ish text into (section heading, body) pairs."""
    sections: list[tuple[str, str]] = []
    heading = ""
    buf: list[str] = []
    for line in text.splitlines():
        if re.match(r"^#{2,3}\s", line):
            if "".join(buf).strip():
                sections.append((heading, "\n".join(buf).strip()))
            heading = line.lstrip("#").strip()
            buf = []
        elif line.startswith("# ") or META_RE.match(line):
            continue  # title and metadata lines are carried by the contextual header
        else:
            buf.append(line)
    if "".join(buf).strip():
        sections.append((heading, "\n".join(buf).strip()))
    return sections


def chunk_document(text: str, title: str) -> list[Chunk]:
    """Semantic chunking: one chunk per section, long sections windowed at ~400 tokens."""
    chunks: list[Chunk] = []
    for heading, body in split_sections(text):
        header = f"{title} > {heading}" if heading else title
        words = body.split()
        if len(tokenize(body)) <= CHUNK_TOKENS:
            windows = [words]
        else:
            step = CHUNK_TOKENS - OVERLAP_TOKENS
            windows = [words[i : i + CHUNK_TOKENS] for i in range(0, len(words), step)]
        for window in windows:
            content = " ".join(window).strip()
            if content:
                chunks.append(Chunk(len(chunks), header[:255], content, len(tokenize(content))))
    return chunks


def ingest_file(db: Session, path: Path) -> int:
    """Ingest one file. Returns the number of chunks written (0 when unchanged)."""
    text = load_text(path)
    content_hash = hashlib.sha256(text.encode("utf-8")).hexdigest()
    doc_id = path.stem[:64]
    existing = db.scalars(
        select(KnowledgeChunk.content_hash).where(KnowledgeChunk.doc_id == doc_id)
    ).first()
    if existing == content_hash:
        return 0

    db.execute(delete(KnowledgeChunk).where(KnowledgeChunk.doc_id == doc_id))
    title = document_title(text, path)
    url_match = URL_RE.search(text)
    source_url = url_match.group(1) if url_match else f"docs/knowledge/{path.name}"
    chunks = chunk_document(text, title)
    vectors = get_embeddings([f"{c.header}\n{c.content}" for c in chunks])
    for chunk, vector in zip(chunks, vectors, strict=True):
        db.add(
            KnowledgeChunk(
                doc_id=doc_id,
                title=title[:255],
                source_url=source_url[:512],
                content_hash=content_hash,
                chunk_index=chunk.index,
                content=chunk.content,
                contextual_header=chunk.header,
                embedding=vector,
                token_count=chunk.token_count,
            )
        )
    return len(chunks)


def ingest_directory(db: Session, directory: Path = KNOWLEDGE_DIR) -> dict[str, int]:
    """Ingest every supported file. Removes chunks of files that no longer exist."""
    results: dict[str, int] = {}
    files = sorted(
        p for p in directory.iterdir() if p.suffix.lower() in SUPPORTED and p.name not in SKIP_FILES
    )
    for path in files:
        results[path.stem] = ingest_file(db, path)
    present = {p.stem[:64] for p in files}
    stale = set(db.scalars(select(KnowledgeChunk.doc_id).distinct())) - present
    if stale:
        db.execute(delete(KnowledgeChunk).where(KnowledgeChunk.doc_id.in_(stale)))
    db.commit()
    from app.rag.retrieve import clear_index_cache

    clear_index_cache()
    return results


def main() -> None:
    parser = argparse.ArgumentParser(description="Ingest the TrustLedger knowledge base")
    parser.add_argument("--dir", type=Path, default=KNOWLEDGE_DIR)
    args = parser.parse_args()

    from app.db.session import get_session_factory, init_db

    init_db()
    with get_session_factory()() as db:
        results = ingest_directory(db, args.dir)
        total = db.query(KnowledgeChunk).count()
    for doc, n in results.items():
        print(f"  {doc}: {'unchanged' if n == 0 else f'{n} chunks'}")
    print(f"knowledge_chunks total: {total}")


if __name__ == "__main__":
    main()

"""Optional context compression before LLM calls (feature flag ``RAG_COMPRESSION``).

Uses LLMLingua-2 when the ``llmlingua`` package is installed; otherwise a light filter that
drops filler words but never numbers, amounts or Bangla currency terms.
"""

import re
from functools import lru_cache
from typing import Any

from app.config import get_settings

STOPWORDS = {
    "টি", "টা", "গুলো", "থেকে", "হলো", "হয়ে", "একটি", "এমন",
    "the", "a", "an", "is", "are", "very", "also", "further", "in", "of", "and",
}  # fmt: skip


@lru_cache(maxsize=1)
def _lingua() -> Any:
    from llmlingua import PromptCompressor

    return PromptCompressor(
        model_name="microsoft/llmlingua-2-xlm-roberta-large-meetingbank", use_llmlingua2=True
    )


def _heuristic(text: str) -> str:
    out = []
    for para in text.split("\n\n"):
        tokens = re.split(r"(\s+)", para)
        kept = [
            t
            for t in tokens
            if any(ch.isdigit() for ch in t)
            or "টাকা" in t
            or "bdt" in t.lower()
            or not (t.strip().lower() in STOPWORDS and len(tokens) > 20)
        ]
        out.append(re.sub(r"\s{2,}", " ", "".join(kept)))
    return "\n\n".join(out)


def compress_context(text: str, target_ratio: float = 0.6, enabled: bool | None = None) -> str:
    """Return compressed text when enabled (argument or RAG_COMPRESSION), else unchanged."""
    if enabled is None:
        enabled = get_settings().RAG_COMPRESSION
    if not enabled or not text:
        return text
    try:
        result = _lingua().compress_prompt(text, rate=target_ratio)
        return str(result["compressed_prompt"])
    except Exception:  # noqa: BLE001 - llmlingua not installed or failed
        return _heuristic(text)

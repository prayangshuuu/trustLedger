"""Shared test setup: offline LLM mode and an isolated document store."""

import os
import tempfile

os.environ.setdefault("LLM_MODE", "mock")
os.environ["DOCUMENT_STORAGE_DIR"] = tempfile.mkdtemp(prefix="tl-docs-")
os.environ.pop("R2_ENDPOINT", None)

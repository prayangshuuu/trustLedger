"""Shared test setup: offline LLM mode and an isolated document store."""

import os
import tempfile

import pytest

os.environ.setdefault("LLM_MODE", "mock")
os.environ["DOCUMENT_STORAGE_DIR"] = tempfile.mkdtemp(prefix="tl-docs-")
os.environ.pop("R2_ENDPOINT", None)


def pytest_collection_modifyitems(config, items):
    if not os.getenv("DEEPSEEK_API_KEY"):
        skip_live = pytest.mark.skip(reason="requires DEEPSEEK_API_KEY environment variable")
        for item in items:
            if "live" in item.keywords:
                item.add_marker(skip_live)

"""Every setting and environment variable the code reads is documented in .env.example."""

import re
from pathlib import Path

from app.config import Settings

ROOT = Path(__file__).resolve().parents[2]


def test_env_example_lists_every_variable() -> None:
    documented = set(
        re.findall(r"^#?\s*([A-Z][A-Z0-9_]+)=", (ROOT / ".env.example").read_text(), re.MULTILINE)
    )
    used = set(Settings.model_fields)
    for folder in ("backend/app", "mcp_server", "workflows", "federated"):
        for py in (ROOT / folder).rglob("*.py"):
            used |= set(re.findall(r'os\.(?:getenv|environ\.get)\("([A-Z_]+)"', py.read_text()))
    assert used - documented == set()

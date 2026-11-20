"""Versioned agent role prompts (agents/prompts/*.md)."""

import re
from functools import lru_cache
from pathlib import Path

PROMPTS_DIR = Path(__file__).resolve().parent / "prompts"
AGENT_NAMES = (
    "supervisor",
    "data_agent",
    "bhorsha_router",
    "scoring_agent",
    "explainer_agent",
    "fairness_agent",
)


@lru_cache(maxsize=16)
def load_prompt(name: str) -> str:
    return (PROMPTS_DIR / f"{name}.md").read_text(encoding="utf-8")


def prompt_version(name: str) -> str:
    match = re.search(r'version="([^"]+)"', load_prompt(name))
    return match.group(1) if match else "unknown"


def prompt_versions() -> dict[str, str]:
    return {name: prompt_version(name) for name in AGENT_NAMES}

"""SMS parser evaluation: macro F1 over transaction type, direction and amount accuracy.

uv run python evals/sms/evaluate.py
"""

import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))

from app.parsers.sms import parse_sms

FIXTURES = ROOT / "backend" / "tests" / "fixtures" / "sms" / "synthetic_sms.json"


def macro_f1(pairs: list[tuple[str, str]]) -> float:
    labels = {t for t, _ in pairs} | {p for _, p in pairs}
    scores = []
    for label in labels:
        tp = sum(t == label and p == label for t, p in pairs)
        fp = sum(t != label and p == label for t, p in pairs)
        fn = sum(t == label and p != label for t, p in pairs)
        prec = tp / (tp + fp) if tp + fp else 0.0
        rec = tp / (tp + fn) if tp + fn else 0.0
        scores.append(2 * prec * rec / (prec + rec) if prec + rec else 0.0)
    return sum(scores) / len(scores) if scores else 0.0


def run() -> dict[str, Any]:
    items = json.loads(FIXTURES.read_text(encoding="utf-8"))
    type_pairs: list[tuple[str, str]] = []
    direction_ok = amount_ok = amount_n = 0
    for item in items:
        tx = parse_sms(item["text"], use_llm_fallback=True)
        exp = item["expected"]
        type_pairs.append((exp["type"], tx.type))
        direction_ok += tx.direction == exp["direction"]
        if exp.get("amount_bdt") is not None:
            amount_n += 1
            amount_ok += abs(tx.amount_bdt - float(exp["amount_bdt"])) < 0.01
    return {
        "fixtures": len(items),
        "type_macro_f1": round(macro_f1(type_pairs), 4),
        "type_accuracy": round(sum(t == p for t, p in type_pairs) / len(items), 4),
        "direction_accuracy": round(direction_ok / len(items), 4),
        "amount_accuracy": round(amount_ok / amount_n, 4) if amount_n else None,
    }


if __name__ == "__main__":
    print(json.dumps(run(), indent=2))

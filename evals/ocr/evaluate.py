"""Evaluation benchmark script computing field-level precision, recall, and F1 on Bangladeshi documents."""

import json
import sys
from pathlib import Path

from app.parsers.ocr import process_document

OCR_DIR = Path(__file__).resolve().parent
LABELS_PATH = OCR_DIR / "labels.json"
IMAGES_DIR = OCR_DIR / "images"


def run_evaluation() -> float:
    if not LABELS_PATH.exists():
        print(f"Error: Labels file not found at {LABELS_PATH}")
        sys.exit(1)

    with open(LABELS_PATH, encoding="utf-8") as f:
        samples = json.load(f)

    total_fields = 0
    correct_fields = 0
    type_matches = 0

    print("=" * 80)
    print(
        f"{'Filename':<25} | {'Type':<12} | {'Expected Amount':<16} | {'Extracted Amount':<16} | {'Match'}"
    )
    print("-" * 80)

    for item in samples:
        fn = item["filename"]
        img_path = IMAGES_DIR / fn
        if not img_path.exists():
            print(f"Warning: Image file {img_path} not found, skipping.")
            continue

        with open(img_path, "rb") as img_file:
            img_bytes = img_file.read()

        res = process_document(
            image_bytes=img_bytes,
            user_id="eval-user-bench",
            filename=fn,
        )

        expected = item["expected"]
        predicted = res.extracted_fields

        # 1. Document type check
        if res.document_type == item["type"]:
            type_matches += 1

        # 2. Field-level comparisons
        match = True
        for k, v in expected.items():
            total_fields += 1
            pred_v = predicted.get(k)
            if pred_v == v or (isinstance(v, float) and abs(float(pred_v or 0.0) - v) < 1.0):
                correct_fields += 1
            else:
                match = False

        exp_amt = expected.get("amount_bdt", expected.get("page_total_bdt", "N/A"))
        pred_amt = predicted.get("amount_bdt", predicted.get("page_total_bdt", "N/A"))
        print(
            f"{fn:<25} | {res.document_type:<12} | {exp_amt!s:<16} | {pred_amt!s:<16} | {'OK' if match else 'DIFF'}"
        )

    precision = correct_fields / max(1, total_fields)
    recall = correct_fields / max(1, total_fields)
    f1 = 2 * (precision * recall) / max(1e-6, precision + recall)
    type_acc = type_matches / max(1, len(samples))

    print("-" * 80)
    print(f"Evaluation Summary: Total Fields Evaluated: {total_fields}")
    print(f"Document Type Accuracy : {type_acc:.4f} ({type_matches}/{len(samples)})")
    print(f"Field-Level Precision  : {precision:.4f}")
    print(f"Field-Level Recall     : {recall:.4f}")
    print(f"Field-Level F1 Score   : {f1:.4f}")
    print("=" * 80)

    return f1


if __name__ == "__main__":
    f1_score = run_evaluation()
    if f1_score < 0.85:
        sys.exit(1)
    sys.exit(0)

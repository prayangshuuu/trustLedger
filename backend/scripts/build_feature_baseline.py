"""Build models/feature_baseline.json: decile bin edges and proportions per feature from the
synthetic training data. Used by the nightly drift check (PSI).

    uv run python backend/scripts/build_feature_baseline.py
"""

import json
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
FEATURES = json.loads((ROOT / "models" / "trustledger_meta.json").read_text())["features"]


def main() -> None:
    df = pd.read_csv(ROOT / "datasets" / "trustledger_synthetic_bd.csv", usecols=FEATURES)
    baseline: dict[str, dict[str, object]] = {}
    for f in FEATURES:
        col = df[f].dropna().to_numpy(dtype=float)
        edges = np.unique(np.quantile(col, np.linspace(0, 1, 11)))
        counts, _ = np.histogram(np.clip(col, edges[0], edges[-1]), bins=edges)
        baseline[f] = {
            "edges": [round(float(e), 6) for e in edges],
            "proportions": [round(float(c / counts.sum()), 6) for c in counts],
            "missing_rate": round(float(df[f].isna().mean()), 6),
        }
    out = ROOT / "models" / "feature_baseline.json"
    out.write_text(
        json.dumps(
            {"source": "datasets/trustledger_synthetic_bd.csv", "n": len(df), "features": baseline},
            indent=2,
        )
    )
    print(f"wrote {out}")


if __name__ == "__main__":
    main()

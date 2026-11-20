"""Dataset loading and the notebook's split / preprocessing, partitioned by division."""

from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split

ROOT = Path(__file__).resolve().parents[1]
DATA_PATH = ROOT / "datasets" / "trustledger_synthetic_bd.csv"
SEED = 42
FEATURES = [
    "monthly_inflow_bdt", "income_volatility", "months_on_wallet", "txn_per_month", "bills_on_time",
    "recharge_regularity", "savings_ratio", "sends_money_home", "bhorsha_score", "loan_to_income",
]  # fmt: skip


def sig(z: np.ndarray) -> np.ndarray:
    return np.asarray(1.0 / (1.0 + np.exp(-z)))


@dataclass
class Partitioned:
    clients: dict[str, tuple[np.ndarray, np.ndarray]]  # division -> (X, y)
    X_test: np.ndarray
    y_test: np.ndarray
    n_features: int


def load_dataset(path: Path | None = None, fallback_rows: int = 20000) -> pd.DataFrame:
    """The notebook's synthetic CSV, or (when it is absent, e.g. in CI) the same generator."""
    path = path or DATA_PATH
    if path.exists():
        csv: pd.DataFrame = pd.read_csv(path)
        return csv
    import sys

    sys.path.insert(0, str(ROOT / "backend"))
    from app.demo_seed import generate_population

    rows = generate_population(fallback_rows, seed=SEED)
    df = pd.DataFrame(
        [{**r["features"], "division": r["division"], "repaid": int(r["repaid"])} for r in rows]
    )
    return df


def partition(df: pd.DataFrame) -> Partitioned:
    """Same split as the notebook (60/20/20 stratified, seed 42); train split by division."""
    tr, rest = train_test_split(df, test_size=0.4, stratify=df.repaid, random_state=SEED)
    _, te = train_test_split(rest, test_size=0.5, stratify=rest.repaid, random_state=SEED)

    # Standardisation stats: the notebook computes them on the pooled train set. In a real
    # deployment these come from public priors or one secure-aggregation round of sums.
    fill = tr[FEATURES].median()
    mu = tr[FEATURES].fillna(fill).mean()
    sd = tr[FEATURES].fillna(fill).std() + 1e-9

    def prep(d: pd.DataFrame) -> np.ndarray:
        z = ((d[FEATURES].fillna(fill) - mu) / sd).to_numpy()
        return np.asarray(np.c_[z, d[FEATURES].isna().to_numpy().astype(float)])

    clients = {
        str(div): (prep(g), g.repaid.to_numpy().astype(float)) for div, g in tr.groupby("division")
    }
    X_test = prep(te)
    return Partitioned(clients, X_test, te.repaid.to_numpy().astype(float), X_test.shape[1])

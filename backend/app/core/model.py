"""Model and metadata loading for TrustLedger scoring.

Loads the production XGBoost classifier and metadata configuration from MODEL_DIR once
and caches them in memory. Exposes model version hash.
"""

import hashlib
import json
import os
from functools import lru_cache
from pathlib import Path
from typing import Any

import xgboost as xgb


def get_model_dir(model_dir: Path | str | None = None) -> Path:
    """Resolve directory containing model artifacts.

    Priority:
    1. Explicitly passed `model_dir` argument.
    2. Environment variable `MODEL_DIR`.
    3. Project repository `models/` directory relative to this module.
    4. Current working directory `./models`.
    """
    if model_dir is not None:
        return Path(model_dir)

    env_dir = os.getenv("MODEL_DIR")
    if env_dir:
        return Path(env_dir)

    # backend/app/core/model.py -> repo_root is 3 parents up
    repo_models = Path(__file__).resolve().parents[3] / "models"
    if repo_models.exists():
        return repo_models

    return Path("models")


@lru_cache(maxsize=1)
def load_model(model_dir: Path | str | None = None) -> xgb.XGBClassifier:
    """Load and return the production XGBoost model from the model directory.

    Caches the loaded model instance in memory.
    """
    resolved_dir = get_model_dir(model_dir)
    model_path = resolved_dir / "trustledger_xgb.json"
    if not model_path.exists():
        raise FileNotFoundError(f"Production model artifact not found at {model_path}")

    model = xgb.XGBClassifier()
    model.load_model(str(model_path))
    return model


@lru_cache(maxsize=1)
def load_meta(model_dir: Path | str | None = None) -> dict[str, Any]:
    """Load and return the production metadata JSON configuration.

    Caches the metadata dictionary in memory.
    """
    resolved_dir = get_model_dir(model_dir)
    meta_path = resolved_dir / "trustledger_meta.json"
    if not meta_path.exists():
        raise FileNotFoundError(f"Model metadata configuration not found at {meta_path}")

    with open(meta_path, encoding="utf-8") as f:
        meta_dict: dict[str, Any] = json.load(f)
    return meta_dict


@lru_cache(maxsize=1)
def get_model_version(model_dir: Path | str | None = None) -> str:
    """Return SHA-256 fingerprint hash of the production model artifact file."""
    resolved_dir = get_model_dir(model_dir)
    model_path = resolved_dir / "trustledger_xgb.json"
    if not model_path.exists():
        raise FileNotFoundError(f"Model artifact not found to compute version at {model_path}")

    return hashlib.sha256(model_path.read_bytes()).hexdigest()[:16]


def clear_cache() -> None:
    """Clear memory caches for model, metadata, and version."""
    load_model.cache_clear()
    load_meta.cache_clear()
    get_model_version.cache_clear()

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


# Cache keys are the resolved directory, so load_meta() and load_meta(model_dir=None) share
# one cached object (lru_cache would otherwise treat them as different keys).


def load_model(model_dir: Path | str | None = None) -> xgb.XGBClassifier:
    """Load (once per directory) and return the production XGBoost model."""
    return _load_model(str(get_model_dir(model_dir)))


@lru_cache(maxsize=4)
def _load_model(dir_str: str) -> xgb.XGBClassifier:
    resolved_dir = Path(dir_str)
    model_path = resolved_dir / "trustledger_xgb.json"
    if not model_path.exists():
        raise FileNotFoundError(f"Production model artifact not found at {model_path}")

    model = xgb.XGBClassifier()
    model.load_model(str(model_path))
    return model


def load_meta(model_dir: Path | str | None = None) -> dict[str, Any]:
    """Load (once per directory) and return the production metadata JSON."""
    return _load_meta(str(get_model_dir(model_dir)))


@lru_cache(maxsize=4)
def _load_meta(dir_str: str) -> dict[str, Any]:
    resolved_dir = Path(dir_str)
    meta_path = resolved_dir / "trustledger_meta.json"
    if not meta_path.exists():
        raise FileNotFoundError(f"Model metadata configuration not found at {meta_path}")

    with open(meta_path, encoding="utf-8") as f:
        meta_dict: dict[str, Any] = json.load(f)
    return meta_dict


def get_model_version(model_dir: Path | str | None = None) -> str:
    """Return the SHA-256 fingerprint (first 16 hex chars) of the production model file."""
    return _model_version(str(get_model_dir(model_dir)))


@lru_cache(maxsize=4)
def _model_version(dir_str: str) -> str:
    resolved_dir = Path(dir_str)
    model_path = resolved_dir / "trustledger_xgb.json"
    if not model_path.exists():
        raise FileNotFoundError(f"Model artifact not found to compute version at {model_path}")

    return hashlib.sha256(model_path.read_bytes()).hexdigest()[:16]


def clear_cache() -> None:
    """Clear memory caches for model, metadata, and version."""
    _load_model.cache_clear()
    _load_meta.cache_clear()
    _model_version.cache_clear()

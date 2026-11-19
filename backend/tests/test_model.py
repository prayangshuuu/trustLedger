"""Unit tests for model and metadata loading."""

import json
from pathlib import Path

import pytest
import xgboost as xgb
from app.core.model import (
    clear_cache,
    get_model_dir,
    get_model_version,
    load_meta,
    load_model,
)


def test_get_model_dir_resolution(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Verify model directory resolution order across all priority levels."""
    # Priority 1: Explicit argument (both Path and str)
    assert get_model_dir(tmp_path) == tmp_path
    assert get_model_dir(str(tmp_path)) == tmp_path

    # Priority 2: Environment variable
    monkeypatch.setenv("MODEL_DIR", str(tmp_path))
    assert get_model_dir() == tmp_path

    # Priority 3: Project repository models/ directory relative to module
    monkeypatch.delenv("MODEL_DIR", raising=False)
    resolved = get_model_dir()
    assert resolved.exists()
    assert (resolved / "trustledger_xgb.json").exists()

    # Priority 4: Fallback to cwd ./models when repo_models does not exist
    original_exists = Path.exists

    def mock_exists(self: Path) -> bool:
        # Mock repo_models check returning False
        if str(self).endswith("models") and "app" not in str(self):
            return False
        return original_exists(self)

    monkeypatch.setattr(Path, "exists", mock_exists)
    assert get_model_dir() == Path("models")


def test_load_model_and_caching() -> None:
    """Verify XGBoost model loading and LRU caching."""
    clear_cache()
    model1 = load_model()
    assert isinstance(model1, xgb.XGBClassifier)

    hits_before = load_model.cache_info().hits
    model2 = load_model()
    assert model1 is model2
    assert load_model.cache_info().hits == hits_before + 1


def test_load_meta_and_caching() -> None:
    """Verify metadata configuration loading and contract."""
    clear_cache()
    meta1 = load_meta()
    assert isinstance(meta1, dict)
    assert "features" in meta1
    assert len(meta1["features"]) == 10
    assert "group_thresholds" in meta1
    assert "score_scale" in meta1
    assert "reasons" in meta1
    assert "tips" in meta1

    hits_before = load_meta.cache_info().hits
    meta2 = load_meta()
    assert meta1 is meta2
    assert load_meta.cache_info().hits == hits_before + 1


def test_get_model_version() -> None:
    """Verify model version extraction as a deterministic 16-char hex hash."""
    clear_cache()
    version = get_model_version()
    assert isinstance(version, str)
    assert len(version) == 16
    assert int(version, 16) >= 0  # valid hex
    # Verify exact deterministic hash of production trustledger_xgb.json
    assert version == "356d061e78fdf8cf"

    # Verify version caching
    hits_before = get_model_version.cache_info().hits
    cached_version = get_model_version()
    assert cached_version == version
    assert get_model_version.cache_info().hits == hits_before + 1


def test_clear_cache_invalidation() -> None:
    """Verify clear_cache properly invalidates all LRU caches."""
    # Populate caches
    m1 = load_model()
    meta1 = load_meta()
    v1 = get_model_version()

    assert load_model.cache_info().currsize == 1
    assert load_meta.cache_info().currsize == 1
    assert get_model_version.cache_info().currsize == 1

    # Invalidate all caches
    clear_cache()

    assert load_model.cache_info().currsize == 0
    assert load_meta.cache_info().currsize == 0
    assert get_model_version.cache_info().currsize == 0

    # Next call should reload fresh objects
    m2 = load_model()
    meta2 = load_meta()
    v2 = get_model_version()

    assert m1 is not m2
    assert meta1 is not meta2
    assert v1 == v2


def test_model_not_found(tmp_path: Path) -> None:
    """Verify FileNotFoundError when artifacts are missing for Path and str."""
    clear_cache()
    # Test with Path object
    with pytest.raises(FileNotFoundError, match="Production model artifact not found"):
        load_model(tmp_path)

    with pytest.raises(FileNotFoundError, match="Model metadata configuration not found"):
        load_meta(tmp_path)

    with pytest.raises(FileNotFoundError, match="Model artifact not found"):
        get_model_version(tmp_path)

    # Test with string path
    with pytest.raises(FileNotFoundError, match="Production model artifact not found"):
        load_model(str(tmp_path))

    with pytest.raises(FileNotFoundError, match="Model metadata configuration not found"):
        load_meta(str(tmp_path))

    with pytest.raises(FileNotFoundError, match="Model artifact not found"):
        get_model_version(str(tmp_path))


def test_corrupt_metadata_raises(tmp_path: Path) -> None:
    """Verify JSONDecodeError when metadata file contains invalid JSON."""
    clear_cache()
    corrupt_file = tmp_path / "trustledger_meta.json"
    corrupt_file.write_text("invalid json content {{{", encoding="utf-8")

    with pytest.raises(json.JSONDecodeError):
        load_meta(tmp_path)

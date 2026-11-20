"""Flower federated simulation: runs, learns, and stays close to the notebook when data exists."""

import json
from pathlib import Path

import pytest

from federated.data import DATA_PATH, load_dataset, partition
from federated.simulate import run_simulation

METRICS = json.loads(
    (Path(__file__).resolve().parents[2] / "training_files/metrics.json").read_text()
)


def test_partition_has_eight_division_clients() -> None:
    data = partition(load_dataset())
    assert len(data.clients) == 8
    assert data.n_features == 20


def test_simulation_learns_on_generated_data(tmp_path: Path) -> None:
    history = run_simulation(rounds=8, save=False, data_path=tmp_path / "missing.csv")
    assert len(history) == 8
    assert history[-1] > 0.65


@pytest.mark.skipif(not DATA_PATH.exists(), reason="synthetic dataset not present (CI)")
def test_simulation_matches_notebook_federated_auc() -> None:
    history = run_simulation(rounds=40, save=False)
    assert abs(history[-1] - METRICS["trustledger"]["federated_auc"]) <= 0.02

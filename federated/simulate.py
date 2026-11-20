"""Federated simulation: 8 Flower clients (one per division) with DP FedAvg, in one process.

Uses Flower's real Server, ClientManager and DP strategy; clients run in-process instead of
over gRPC (no Ray needed). Compares the final AUC with the notebook's federated AUC and the
central XGBoost AUC from training_files/metrics.json.

    uv run python -m federated.simulate [--rounds 40]
"""

import argparse
import json
from pathlib import Path

import numpy as np
from flwr.client import Client
from flwr.common import (
    DisconnectRes,
    EvaluateIns,
    EvaluateRes,
    FitIns,
    FitRes,
    GetParametersIns,
    GetParametersRes,
    GetPropertiesIns,
    GetPropertiesRes,
    ReconnectIns,
    parameters_to_ndarrays,
)
from flwr.server import Server, SimpleClientManager
from flwr.server.client_proxy import ClientProxy

from federated.client import TrustLedgerClient
from federated.data import load_dataset, partition
from federated.server import build_strategy, central_evaluate

ROOT = Path(__file__).resolve().parents[1]
METRICS_PATH = ROOT / "training_files" / "metrics.json"


class InProcessClientProxy(ClientProxy):
    """ClientProxy that calls a Flower Client directly (stand-in for the gRPC connection)."""

    def __init__(self, cid: str, client: Client) -> None:
        super().__init__(cid)
        self.client = client

    def get_properties(
        self, ins: GetPropertiesIns, timeout: float | None, group_id: int | None
    ) -> GetPropertiesRes:
        return self.client.get_properties(ins)

    def get_parameters(
        self, ins: GetParametersIns, timeout: float | None, group_id: int | None
    ) -> GetParametersRes:
        return self.client.get_parameters(ins)

    def fit(self, ins: FitIns, timeout: float | None, group_id: int | None) -> FitRes:
        return self.client.fit(ins)

    def evaluate(
        self, ins: EvaluateIns, timeout: float | None, group_id: int | None
    ) -> EvaluateRes:
        return self.client.evaluate(ins)

    def reconnect(
        self, ins: ReconnectIns, timeout: float | None, group_id: int | None
    ) -> DisconnectRes:
        return DisconnectRes(reason="in-process")


def run_simulation(
    rounds: int = 40,
    save: bool = True,
    seed: int = 42,
    data_path: Path | None = None,
    noise_multiplier: float | None = None,
) -> list[float]:
    """Run the federated simulation and return test AUC per round."""
    np.random.seed(seed)  # Flower's Gaussian noise uses numpy's global RNG
    data = partition(load_dataset(data_path))
    history: list[float] = []
    kwargs = {} if noise_multiplier is None else {"noise_multiplier": noise_multiplier}
    strategy = build_strategy(
        data.n_features,
        len(data.clients),
        evaluate_fn=central_evaluate(data.X_test, data.y_test, history),
        **kwargs,
    )
    manager = SimpleClientManager()
    for division, (X, y) in data.clients.items():
        manager.register(InProcessClientProxy(division, TrustLedgerClient(X, y).to_client()))
    server = Server(client_manager=manager, strategy=strategy)
    server.fit(num_rounds=rounds, timeout=None)
    weights = parameters_to_ndarrays(server.parameters)[0]

    if save:
        save_outputs(history, weights, sorted(data.clients))
    return history


def save_outputs(history: list[float], weights: np.ndarray, clients: list[str]) -> None:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    metrics = json.loads(METRICS_PATH.read_text())["trustledger"]
    np.save(ROOT / "models" / "flower_weights.npy", weights)
    plt.figure(figsize=(6, 3.5))
    plt.plot(
        range(1, len(history) + 1), history, label="Flower DP-FedAvg (8 divisions)", color="#14B8A6"
    )
    plt.axhline(
        metrics["federated_auc"],
        ls=":",
        c="#F5B942",
        label=f"notebook FedAvg {metrics['federated_auc']:.4f}",
    )
    plt.axhline(metrics["auc"], ls="--", c="grey", label=f"central XGBoost {metrics['auc']:.4f}")
    plt.xlabel("round")
    plt.ylabel("test AUC")
    plt.title("Federated training with Flower")
    plt.legend(loc="lower right")
    plt.savefig(ROOT / "training_files" / "flower_federated.png", dpi=150, bbox_inches="tight")
    out = {
        "rounds": len(history),
        "clients": clients,
        "auc_per_round": [round(a, 4) for a in history],
        "final_auc": round(history[-1], 4),
        "notebook_federated_auc": metrics["federated_auc"],
        "central_xgboost_auc": metrics["auc"],
        "gap_vs_notebook": round(abs(history[-1] - metrics["federated_auc"]), 4),
    }
    (ROOT / "training_files" / "flower_metrics.json").write_text(json.dumps(out, indent=2))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--rounds", type=int, default=40)
    args = parser.parse_args()
    history = run_simulation(args.rounds)
    metrics = json.loads(METRICS_PATH.read_text())["trustledger"]
    for i in (0, 4, 9, 19, len(history) - 1):
        if i < len(history):
            print(f"round {i + 1:>2}: AUC {history[i]:.4f}")
    print(
        f"final {history[-1]:.4f} | notebook federated {metrics['federated_auc']:.4f} "
        f"(gap {abs(history[-1] - metrics['federated_auc']):.4f}) | central XGBoost {metrics['auc']:.4f}"
    )


if __name__ == "__main__":
    main()

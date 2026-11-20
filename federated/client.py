"""Flower client: trains the logistic scorer on data that never leaves the client.

Only the model weights (an update of 21 numbers) are sent back; the server clips and noises them.
"""

import numpy as np
from flwr.client import NumPyClient
from flwr.common import Config, Metrics
from sklearn.metrics import roc_auc_score

from federated.data import sig


def local_step(
    w: np.ndarray, X: np.ndarray, y: np.ndarray, epochs: int = 3, lr: float = 0.1
) -> np.ndarray:
    """Full-batch gradient descent on L2-regularised logistic loss (same as the notebook)."""
    for _ in range(epochs):
        err = sig(X @ w[:-1] + w[-1]) - y
        w = w - lr * np.r_[X.T @ err / len(y) + 1e-3 * w[:-1], err.mean()]
    return w


class TrustLedgerClient(NumPyClient):
    def __init__(self, X: np.ndarray, y: np.ndarray, epochs: int = 3, lr: float = 0.1) -> None:
        self.X, self.y, self.epochs, self.lr = X, y, epochs, lr

    def get_parameters(self, config: Config) -> list[np.ndarray]:
        return [np.zeros(self.X.shape[1] + 1)]

    def fit(
        self, parameters: list[np.ndarray], config: Config
    ) -> tuple[list[np.ndarray], int, Metrics]:
        w = local_step(parameters[0].copy(), self.X, self.y, self.epochs, self.lr)
        return [w], len(self.y), {}

    def evaluate(self, parameters: list[np.ndarray], config: Config) -> tuple[float, int, Metrics]:
        w = parameters[0]
        p = sig(self.X @ w[:-1] + w[-1])
        loss = float(-np.mean(self.y * np.log(p + 1e-9) + (1 - self.y) * np.log(1 - p + 1e-9)))
        auc = float(roc_auc_score(self.y, p)) if len(set(self.y)) > 1 else 0.5
        return loss, len(self.y), {"auc": auc}


def main() -> None:
    """Join a running Flower server with one division's local data (data never leaves)."""
    import argparse

    import flwr as fl

    from federated.data import load_dataset, partition

    parser = argparse.ArgumentParser()
    parser.add_argument("--division", default="Dhaka")
    parser.add_argument("--server", default="127.0.0.1:8080")
    args = parser.parse_args()
    X, y = partition(load_dataset()).clients[args.division]
    fl.client.start_client(server_address=args.server, client=TrustLedgerClient(X, y).to_client())


if __name__ == "__main__":
    main()

"""Flower server strategy: FedAvg wrapped in server-side fixed clipping + Gaussian noise (DP).

Run a real networked server (clients connect over gRPC):
    uv run python -m federated.server --rounds 40 --address 0.0.0.0:8080
"""

import argparse
from collections.abc import Callable

import numpy as np
from flwr.common import NDArrays, Scalar, ndarrays_to_parameters
from flwr.server.strategy import DifferentialPrivacyServerSideFixedClipping, FedAvg, Strategy
from sklearn.metrics import roc_auc_score

from federated.data import sig

CLIPPING_NORM = 1.0  # same clip as the notebook
NOISE_MULTIPLIER = 0.08  # noise std on the aggregate = 0.08 * 1.0 / n_clients


def central_evaluate(
    X_test: np.ndarray, y_test: np.ndarray, history: list[float]
) -> Callable[[int, NDArrays, dict[str, Scalar]], tuple[float, dict[str, Scalar]]]:
    def evaluate(
        server_round: int, parameters: NDArrays, config: dict[str, Scalar]
    ) -> tuple[float, dict[str, Scalar]]:
        w = parameters[0]
        p = sig(X_test @ w[:-1] + w[-1])
        auc = float(roc_auc_score(y_test, p))
        if server_round > 0:
            history.append(auc)
        loss = float(-np.mean(y_test * np.log(p + 1e-9) + (1 - y_test) * np.log(1 - p + 1e-9)))
        return loss, {"auc": auc}

    return evaluate


def build_strategy(
    n_features: int,
    n_clients: int,
    evaluate_fn: Callable[[int, NDArrays, dict[str, Scalar]], tuple[float, dict[str, Scalar]]]
    | None = None,
    noise_multiplier: float = NOISE_MULTIPLIER,
    clipping_norm: float = CLIPPING_NORM,
) -> Strategy:
    base = FedAvg(
        fraction_fit=1.0,
        fraction_evaluate=0.0,
        min_fit_clients=n_clients,
        min_available_clients=n_clients,
        initial_parameters=ndarrays_to_parameters([np.zeros(n_features + 1)]),
        evaluate_fn=evaluate_fn,
    )
    return DifferentialPrivacyServerSideFixedClipping(
        base,
        noise_multiplier=noise_multiplier,
        clipping_norm=clipping_norm,
        num_sampled_clients=n_clients,
    )


def main() -> None:
    import flwr as fl

    parser = argparse.ArgumentParser()
    parser.add_argument("--rounds", type=int, default=40)
    parser.add_argument("--clients", type=int, default=8)
    parser.add_argument("--features", type=int, default=20)
    parser.add_argument("--address", default="0.0.0.0:8080")
    args = parser.parse_args()
    fl.server.start_server(
        server_address=args.address,
        config=fl.server.ServerConfig(num_rounds=args.rounds),
        strategy=build_strategy(args.features, args.clients),
    )


if __name__ == "__main__":
    main()

# Federated learning (Flower)

The notebook's FedAvg simulation, rebuilt on Flower (`flwr`) with differential privacy.

| File | Role |
|---|---|
| `data.py` | Notebook split (60/20/20 stratified, seed 42) and preprocessing; train set partitioned by the 8 divisions |
| `client.py` | `TrustLedgerClient` (NumPyClient): 3 local epochs of logistic regression; `python -m federated.client` joins a server over gRPC |
| `server.py` | FedAvg wrapped in `DifferentialPrivacyServerSideFixedClipping` (clip 1.0, noise multiplier 0.08); `python -m federated.server` |
| `simulate.py` | 8 clients in one process using Flower's real `Server` + `ClientManager` (no Ray) |

```bash
uv run python -m federated.simulate            # 40 rounds, writes the plot + weights + metrics
# networked: one server, one client per division
uv run python -m federated.server --rounds 40 &
uv run python -m federated.client --division Dhaka &
...
```

Outputs: `training_files/flower_federated.png`, `training_files/flower_metrics.json`, `models/flower_weights.npy`.

Result (40 rounds): **AUC 0.7555** vs notebook FedAvg **0.7574** (gap 0.002) and central XGBoost **0.7644**.

## How a phone would participate

1. The app already computes the 10 features on the device from SMS (raw SMS never leaves the phone).
2. When the phone is idle, charging and on Wi-Fi, it fetches the current global weights (21 numbers) and the round config.
3. It trains locally for a few epochs on its own labelled history (its repayment outcomes) and computes the weight **update**.
4. Only the update is sent. The server clips every update to L2 norm ≤ 1.0 and adds Gaussian noise to the aggregate
   (`DifferentialPrivacyServerSideFixedClipping`), so no single phone's data can be reconstructed from the model.
5. In production, use Flower's secure aggregation (SecAgg+) so the server only ever sees the sum. You can also move clipping
   to the client (`DifferentialPrivacyClientSideFixedClipping`) for local DP, and sample a fraction of phones per round.

Notes: standardisation statistics are computed on the pooled train set (as in the notebook). In a real deployment they come from public priors or one secure-aggregation round of sums.
The production scorer stays the central XGBoost model. The federated logistic model shows that
the bank-network setup reaches 99% of central performance without pooling raw data.

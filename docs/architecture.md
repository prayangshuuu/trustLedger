# Architecture

```mermaid
flowchart LR
  subgraph Clients
    APP["Borrower app<br/>Flutter, Bangla-first"]
    DASH["Lender dashboard<br/>React + Recharts + Chart.js + D3"]
    PARTNER["Partner AI agents"]
  end
  APP -->|REST + signed borrower token| API
  DASH -->|REST + X-API-Key| API
  PARTNER -->|MCP stdio / streamable HTTP| MCP["MCP server<br/>score_user · explain_score<br/>fairness_audit · get_inclusion_lift"]
  MCP -->|REST| API

  subgraph Backend["FastAPI backend"]
    API["Routers: consent · apply · score · documents · bhorsha<br/>loans · fairness · stats · metrics"]
    subgraph Agents["LangGraph supervisor (POST /apply)"]
      SUP{{Supervisor}} --> DA["Data Agent<br/>SMS parser + DeepSeek-OCR → features"]
      DA --> BR{"No history?"}
      BR -->|yes| BH["Bhorsha chat<br/>bhorsha_score 0–100"]
      BR -->|no| SC["Scoring Agent<br/>XGBoost → p_repay → 300–900"]
      SC --> EX["Explainer Agent<br/>SHAP + RAG-cited Bangla tips"]
      EX --> FA["Fairness Agent<br/>group threshold · review band · can block"]
    end
    API --> SUP
    LLM["LLMClient<br/>DeepSeek chat / DeepSeek-OCR / mock<br/>Presidio redaction first"]
    DA -.-> LLM
    BH -.-> LLM
    EX -.-> LLM
    RAG["RAG<br/>BM25 + pgvector + reranker"]
    EX -.-> RAG
  end

  API --> PG[("PostgreSQL 16 + pgvector<br/>users · consents · features · decisions · audit_log · knowledge_chunks")]
  API --> R2[("R2 / MinIO<br/>encrypted images, 30-day expiry")]
  API --> PROM["/metrics → Prometheus → Grafana"]
  TEMP["Temporal LoanWorkflow<br/>apply → disburse → reminders → repayments → +20% limit"] -->|REST| API
  AIR["Airflow DAGs<br/>weekly fairness audit · nightly PSI drift · document purge · FL round"] -->|REST / DB| API
  FL["Flower DP-FedAvg<br/>8 division clients"] -.->|weights| AIR
```

## Request path: Moon applies

1. **Consent.** The app records one consent per source (`/consent`). Every later step checks it.
2. **Data Agent.** In the demo, raw SMS goes to `/apply` and is parsed in memory (regex first, then a PII-redacted DeepSeek fallback). Bill photos were already read by DeepSeek-OCR via `/documents`. Only the 10 derived features are stored.
3. **Bhorsha router.** Under 3 months of wallet history and no `bhorsha_score` → status `bhorsha_required`. The app then runs the 12-question Bangla chat.
4. **Scoring Agent.** XGBoost predicts `p_repay`, mapped to 300–900 (600 = 4:1 odds, +50 doubles the odds) and a band.
5. **Explainer Agent.** It takes the top-2 positive and negative SHAP reasons (|impact| ≥ 0.02, non-missing) in Bangla, adds tips that each cite one knowledge-base source, and writes an LLM summary that is rejected if it names any non-SHAP feature.
6. **Fairness Agent.** It applies the group threshold (`F_rural`, `F_urban`, `M_rural`, `M_urban`), checks that no sensitive input reached the model, and blocks on any failure. Cases within ±0.03 of the threshold go to `needs_review`.
7. **Finalize.** The decision and a complete audit entry (features, reasons, threshold, checks, model and prompt versions, node timings) are written. `trace_id` is returned.

Gender, region, division and age are never model inputs. They only choose the threshold and feed audits.

## Components and files

| Component | Code |
|---|---|
| Scoring core (pure, no I/O) | `backend/app/core/` |
| Agents + versioned prompts | `backend/app/agents/` |
| LLM gateway, mocks | `backend/app/llm/client.py` |
| SMS parser, feature builder, OCR | `backend/app/parsers/` |
| Bhorsha | `backend/app/bhorsha/` |
| RAG | `backend/app/rag/`, `docs/knowledge/` |
| Privacy (consent, deletion, Presidio) | `backend/app/privacy/`, `backend/app/storage.py` |
| Observability, rate limits | `backend/app/observability.py`, `infra/grafana/` |
| MCP | `mcp_server/` |
| Temporal, Airflow | `workflows/` |
| Federated learning | `federated/` |
| Apps | `apps/mobile/`, `apps/dashboard/` |
| Evaluations | `evals/` |
| Training | `trustLedger_model_training.ipynb` → `models/`, `training_files/` |

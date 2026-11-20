// Typed client for the TrustLedger API. The lender's API key is kept in sessionStorage.
// Production builds default to same origin (the API serves the dashboard on Heroku).
export const API_BASE: string =
  import.meta.env.VITE_API_BASE_URL ?? (import.meta.env.DEV ? "http://localhost:8000" : "");
const KEY_STORAGE = "tl_api_key";

export class ApiError extends Error {
  constructor(public status: number, message: string) {
    super(message);
  }
}

export function getApiKey(): string {
  try {
    return sessionStorage.getItem(KEY_STORAGE) ?? "";
  } catch {
    return "";
  }
}

export function setApiKey(key: string | null): void {
  try {
    if (key === null) sessionStorage.removeItem(KEY_STORAGE);
    else sessionStorage.setItem(KEY_STORAGE, key);
  } catch {
    /* storage unavailable: key lives only for this page */
  }
}

export async function apiGet<T>(path: string, key: string = getApiKey()): Promise<T> {
  const resp = await fetch(`${API_BASE}${path}`, { headers: key ? { "X-API-Key": key } : {} });
  if (!resp.ok) {
    let detail = resp.statusText;
    try {
      detail = (await resp.json()).detail ?? detail;
    } catch {
      /* non-JSON error */
    }
    throw new ApiError(resp.status, String(detail));
  }
  return (await resp.json()) as T;
}

export interface Reason {
  feature: string;
  label: string;
  text: string;
  impact: number;
  kind: "good" | "bad";
}

export interface InclusionLift {
  total_evaluated: number;
  bank_rule_approvals: number;
  bank_rule_approval_rate: number;
  trustledger_approvals: number;
  trustledger_approval_rate: number;
  newly_included_count: number;
  newly_included_rate: number;
  inclusion_lift_percentage: number;
  rule_description: string;
}

export interface Overview {
  applications: number;
  decisions: number;
  approval_rate: number;
  repayments: number;
  repayment_rate: number;
  avg_score: number;
  by_band: Record<string, number>;
  needs_review: number;
  inclusion: InclusionLift;
  fairness_ok: boolean;
  approval_rate_gap: number;
}

export interface GroupMetrics {
  group: string;
  count: number;
  approval_rate: number;
  tpr: number | null;
  fpr: number | null;
}

export interface FairnessReport {
  total_decisions: number;
  by_group: Record<string, GroupMetrics>;
  approval_rate_gap: number;
  tpr_gap: number | null;
  fpr_gap: number | null;
  equalized_odds_gap: number | null;
  fairness_ok: boolean;
}

export interface Bin {
  bin_start: number;
  bin_end: number;
  count: number;
  approved: number;
}

export interface DivisionStat {
  division: string;
  applications: number;
  approvals: number;
  approval_rate: number;
}

export interface DecisionRow {
  decision_id: string;
  application_id: string | null;
  created_at: string | null;
  score: number;
  band: string;
  p_repay: number;
  approved: boolean;
  group: string;
  division: string | null;
  threshold_used: number;
  fairness_ok: boolean;
  model_version: string;
  reasons: Reason[];
  tips: string[];
}

export interface TraceNode {
  node: string;
  ms: number;
  ok: boolean;
  detail: Record<string, unknown>;
}

export interface DecisionDetail extends DecisionRow {
  status: string | null;
  amount_bdt: number | null;
  features: Record<string, number | null>;
  fairness: { ok: boolean; checks: Record<string, boolean>; blocked_reason: string | null } | null;
  trace_id: string | null;
  trace: { nodes: TraceNode[]; prompt_versions: Record<string, string>; total_ms: number } | null;
}

export interface ModelMetrics {
  notebook?: {
    trustledger: {
      auc: number;
      ks: number;
      brier: number;
      approval_gap_before: number;
      approval_gap_after: number;
      eq_odds_gap_before: number;
      eq_odds_gap_after: number;
      federated_auc: number;
      inclusion: Record<string, number>;
    };
  };
  flower?: { final_auc: number; auc_per_round: number[] };
}

export const api = {
  overview: () => apiGet<Overview>("/stats/overview"),
  fairness: () => apiGet<FairnessReport>("/fairness/report"),
  distribution: () => apiGet<Bin[]>("/stats/score-distribution"),
  divisions: () => apiGet<DivisionStat[]>("/stats/divisions"),
  decisions: (limit = 50) => apiGet<{ total: number; items: DecisionRow[] }>(`/decisions?limit=${limit}`),
  decision: (id: string) => apiGet<DecisionDetail>(`/decisions/${id}`),
  modelMetrics: () => apiGet<ModelMetrics>("/stats/model-metrics"),
};

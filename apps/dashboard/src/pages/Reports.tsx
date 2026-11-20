import { api } from "../api/client";
import { useApi } from "../api/hooks";
import { Card, ErrorBox, GateBadge, Loading } from "../components/ui";
import { download, fairnessCsv, inclusionCsv } from "../lib/csv";
import { GROUP_LABELS, pct } from "../lib/format";

export default function Reports() {
  const fairness = useApi(api.fairness);
  const overview = useApi(api.overview);
  if (fairness.error) return <ErrorBox error={fairness.error} onRetry={fairness.reload} />;
  if (overview.error) return <ErrorBox error={overview.error} onRetry={overview.reload} />;
  if (!fairness.data || !overview.data) return <Loading />;
  const f = fairness.data;
  const lift = overview.data.inclusion;
  const stamp = new Date().toISOString().slice(0, 10);
  return (
    <>
      <h1>Reports</h1>
      <p className="subtitle">Generated {new Date().toLocaleString()} from live data.</p>
      <div className="no-print" style={{ display: "flex", gap: 8, marginBottom: 16, flexWrap: "wrap" }}>
        <button className="btn" data-testid="export-fairness" onClick={() => download(`fairness_${stamp}.csv`, fairnessCsv(f))}>Fairness CSV</button>
        <button className="btn" data-testid="export-inclusion" onClick={() => download(`inclusion_${stamp}.csv`, inclusionCsv(lift))}>Inclusion CSV</button>
        <button className="btn secondary" onClick={() => window.print()}>Print / save as PDF</button>
      </div>
      <div className="grid two">
        <Card title="Fairness audit">
          <p>Approval-rate gap <strong>{f.approval_rate_gap.toFixed(3)}</strong> · equalized-odds gap <strong>{f.equalized_odds_gap?.toFixed(3) ?? "n/a"}</strong> <GateBadge ok={f.fairness_ok} /></p>
          <table>
            <thead><tr><th>Group</th><th>n</th><th>Approval</th><th>TPR</th><th>FPR</th></tr></thead>
            <tbody>
              {Object.values(f.by_group).map((g) => (
                <tr key={g.group}><td>{GROUP_LABELS[g.group] ?? g.group}</td><td>{g.count}</td><td>{pct(g.approval_rate)}</td><td>{pct(g.tpr)}</td><td>{pct(g.fpr)}</td></tr>
              ))}
            </tbody>
          </table>
        </Card>
        <Card title="Inclusion Lift">
          <table>
            <tbody>
              <tr><td>Evaluated</td><td>{lift.total_evaluated}</td></tr>
              <tr><td>Bank rule approvals</td><td>{lift.bank_rule_approvals} ({pct(lift.bank_rule_approval_rate)})</td></tr>
              <tr><td>TrustLedger approvals</td><td>{lift.trustledger_approvals} ({pct(lift.trustledger_approval_rate)})</td></tr>
              <tr><td>Newly included</td><td>{lift.newly_included_count} ({pct(lift.newly_included_rate)})</td></tr>
            </tbody>
          </table>
          <p className="subtitle">Bank rule: {lift.rule_description}</p>
        </Card>
      </div>
    </>
  );
}

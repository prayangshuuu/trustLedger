import { Bar, BarChart, CartesianGrid, Legend, ReferenceLine, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { api } from "../api/client";
import { useApi } from "../api/hooks";
import { Card, ErrorBox, GateBadge, Loading } from "../components/ui";
import { GAP_LIMIT, GROUP_LABELS, pct } from "../lib/format";

export default function Fairness() {
  const report = useApi(api.fairness, [], 15000);
  const metrics = useApi(api.modelMetrics);
  if (report.error) return <ErrorBox error={report.error} onRetry={report.reload} />;
  if (!report.data) return <Loading />;
  const r = report.data;
  const groups = Object.values(r.by_group).map((g) => ({
    group: GROUP_LABELS[g.group] ?? g.group,
    approval: g.approval_rate,
    tpr: g.tpr,
    fpr: g.fpr,
  }));
  const gaps = [
    { name: "Approval-rate gap", value: r.approval_rate_gap },
    ...(r.equalized_odds_gap !== null ? [{ name: "Equalized-odds gap", value: r.equalized_odds_gap }] : []),
  ];
  const nb = metrics.data?.notebook?.trustledger;
  const beforeAfter = nb
    ? [
        { name: "Approval gap", before: nb.approval_gap_before, after: nb.approval_gap_after },
        { name: "Equalized-odds gap", before: nb.eq_odds_gap_before, after: nb.eq_odds_gap_after },
      ]
    : [];
  return (
    <>
      <h1>
        Fairness <GateBadge ok={r.fairness_ok} labels={["PASS ≤ 0.05", "FAIL > 0.05"]} />
      </h1>
      <p className="subtitle">
        {r.total_decisions} stored decisions. Gender, region and division are never model inputs; they set group thresholds and audits only.
        {Math.min(...Object.values(r.by_group).map((g) => g.count)) < 500 &&
          " Small groups (< 500 decisions) make live gaps noisy; the CI gate runs on the 20,000-person test set."}
      </p>
      <div className="grid two">
        <Card title="Approval, TPR and FPR by group (live)">
          <div style={{ height: 300 }}>
            <ResponsiveContainer>
              <BarChart data={groups}>
                <CartesianGrid strokeDasharray="3 3" stroke="var(--grid)" />
                <XAxis dataKey="group" stroke="var(--muted)" interval={0} tick={{ fontSize: 12 }} />
                <YAxis domain={[0, 1]} stroke="var(--muted)" tickFormatter={(v: number) => pct(v, 0)} />
                <Tooltip formatter={(v: number) => pct(v)} />
                <Legend />
                <Bar dataKey="approval" name="Approval rate" fill="#14B8A6" />
                <Bar dataKey="tpr" name="TPR" fill="#0F172A" />
                <Bar dataKey="fpr" name="FPR" fill="#F5B942" />
              </BarChart>
            </ResponsiveContainer>
          </div>
          {r.tpr_gap === null && <p className="subtitle">TPR/FPR appear once repayment outcomes exist for approved and declined applicants.</p>}
        </Card>
        <Card title="Gaps vs the 0.05 gate (live)">
          <div style={{ height: 300 }}>
            <ResponsiveContainer>
              <BarChart data={gaps} layout="vertical" margin={{ left: 40 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="var(--grid)" />
                <XAxis type="number" domain={[0, Math.max(0.12, ...gaps.map((g) => g.value + 0.02))]} stroke="var(--muted)" />
                <YAxis type="category" dataKey="name" width={140} stroke="var(--muted)" />
                <Tooltip formatter={(v: number) => v.toFixed(3)} />
                <ReferenceLine x={GAP_LIMIT} stroke="#DC2626" strokeDasharray="6 3" label={{ value: "0.05", fill: "#DC2626", position: "top" }} />
                <Bar dataKey="value" fill="#14B8A6" />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </Card>
        {nb && (
          <Card title="Before / after fair thresholds (notebook test set, 20,000 people)">
            <div style={{ height: 280 }}>
              <ResponsiveContainer>
                <BarChart data={beforeAfter}>
                  <CartesianGrid strokeDasharray="3 3" stroke="var(--grid)" />
                  <XAxis dataKey="name" stroke="var(--muted)" />
                  <YAxis stroke="var(--muted)" />
                  <Tooltip />
                  <Legend />
                  <ReferenceLine y={GAP_LIMIT} stroke="#DC2626" strokeDasharray="6 3" />
                  <Bar dataKey="before" name="Single threshold" fill="#94A3B8" />
                  <Bar dataKey="after" name="Group thresholds" fill="#14B8A6" />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </Card>
        )}
        <Card title="Per-group table">
          <table>
            <thead>
              <tr><th>Group</th><th>n</th><th>Approval</th><th>TPR</th><th>FPR</th></tr>
            </thead>
            <tbody>
              {Object.values(r.by_group).map((g) => (
                <tr key={g.group}>
                  <td>{GROUP_LABELS[g.group] ?? g.group}</td>
                  <td>{g.count}</td>
                  <td>{pct(g.approval_rate)}</td>
                  <td>{pct(g.tpr)}</td>
                  <td>{pct(g.fpr)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </Card>
      </div>
    </>
  );
}

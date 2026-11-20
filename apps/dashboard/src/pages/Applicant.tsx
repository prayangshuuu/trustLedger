import { Link, useParams } from "react-router-dom";
import { api } from "../api/client";
import { useApi } from "../api/hooks";
import { Card, ErrorBox, GateBadge, Kpi, Loading } from "../components/ui";
import { BAND_COLORS, GROUP_LABELS, pct } from "../lib/format";

export default function Applicant() {
  const { id = "" } = useParams();
  const { data, error, reload } = useApi(() => api.decision(id), [id]);
  if (error) return <ErrorBox error={error} onRetry={reload} />;
  if (!data) return <Loading />;
  return (
    <>
      <p className="no-print"><Link to="/feed">← Feed</Link></p>
      <h1>Applicant decision</h1>
      <p className="subtitle">Decision {data.decision_id} · model {data.model_version}</p>
      <div className="grid kpis">
        <Kpi label="Score" value={<span style={{ color: BAND_COLORS[data.band] }}>{data.score}</span>} hint={data.band} />
        <Kpi label="P(repay)" value={pct(data.p_repay)} hint={`threshold ${pct(data.threshold_used)} for ${GROUP_LABELS[data.group] ?? data.group}`} />
        <Kpi label="Decision" value={data.approved ? "Approved" : "Declined"} hint={data.status ?? undefined} />
        <Kpi label="Fairness sign-off" value={<GateBadge ok={data.fairness_ok} labels={["OK", "BLOCKED"]} />} hint={data.fairness?.blocked_reason ?? "all checks passed"} />
      </div>
      <div className="grid two" style={{ marginTop: 16 }}>
        <Card title="SHAP reasons">
          <table>
            <tbody>
              {data.reasons.map((r) => (
                <tr key={r.feature}>
                  <td className={r.kind === "good" ? "reason-good" : "reason-bad"}>{r.kind === "good" ? "▲" : "▼"} {r.text}</td>
                  <td>{r.label}</td>
                  <td>{r.impact.toFixed(3)}</td>
                </tr>
              ))}
            </tbody>
          </table>
          {data.tips.length > 0 && <p><strong>Tips:</strong> {data.tips.join(" ")}</p>}
        </Card>
        <Card title="Features used (derived only, no raw data)">
          <table>
            <tbody>
              {Object.entries(data.features).map(([k, v]) => (
                <tr key={k}><td>{k}</td><td>{v === null ? "missing" : Number(v).toLocaleString()}</td></tr>
              ))}
            </tbody>
          </table>
        </Card>
        <Card title="Fairness checks">
          <table>
            <tbody>
              {Object.entries(data.fairness?.checks ?? {}).map(([k, v]) => (
                <tr key={k}><td>{k}</td><td><GateBadge ok={v} labels={["yes", "no"]} /></td></tr>
              ))}
            </tbody>
          </table>
        </Card>
        <Card title={`Agent trace ${data.trace_id ?? ""}`}>
          {data.trace ? (
            <div className="timeline">
              {data.trace.nodes.map((n) => (
                <div key={n.node}><span>{n.ok ? "✓" : "✗"} {n.node}</span><span>{n.ms.toFixed(1)} ms</span></div>
              ))}
              <small>prompts: {Object.entries(data.trace.prompt_versions).map(([k, v]) => `${k}@${v}`).join(", ")}</small>
            </div>
          ) : (
            <p className="subtitle">Scored directly via /score (no agent trace).</p>
          )}
        </Card>
      </div>
    </>
  );
}

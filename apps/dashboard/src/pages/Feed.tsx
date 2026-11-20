import { useNavigate } from "react-router-dom";
import { api } from "../api/client";
import { useApi } from "../api/hooks";
import { Card, ErrorBox, Loading } from "../components/ui";
import { BAND_COLORS, GROUP_LABELS, pct } from "../lib/format";

export default function Feed() {
  const { data, error, reload } = useApi(() => api.decisions(50), [], 5000);
  const navigate = useNavigate();
  if (error) return <ErrorBox error={error} onRetry={reload} />;
  if (!data) return <Loading />;
  return (
    <>
      <h1>Live decision feed</h1>
      <p className="subtitle">{data.total} decisions · newest first · refreshes every 5 s · click a row for the applicant detail.</p>
      <Card title="Latest 50">
        <table>
          <thead>
            <tr><th>Time</th><th>Score</th><th>Decision</th><th>Group</th><th>Top reasons (Bangla)</th></tr>
          </thead>
          <tbody>
            {data.items.map((d) => (
              <tr key={d.decision_id} className="clickable" onClick={() => navigate(`/applicant/${d.decision_id}`)}>
                <td>{d.created_at ? new Date(d.created_at).toLocaleTimeString() : "—"}</td>
                <td>
                  <strong style={{ color: BAND_COLORS[d.band] }}>{d.score}</strong> <small>{d.band}</small>
                </td>
                <td>
                  <span className={`badge ${d.approved ? "pass" : "fail"}`}>{d.approved ? "Approved" : "Declined"}</span>
                  <br />
                  <small>p {pct(d.p_repay)} vs {pct(d.threshold_used)}</small>
                </td>
                <td>{GROUP_LABELS[d.group] ?? d.group}</td>
                <td>
                  {d.reasons.slice(0, 3).map((r) => (
                    <div key={r.feature} className={r.kind === "good" ? "reason-good" : "reason-bad"}>
                      {r.kind === "good" ? "▲" : "▼"} {r.text}
                    </div>
                  ))}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </Card>
    </>
  );
}

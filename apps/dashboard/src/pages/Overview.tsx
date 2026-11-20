import { api } from "../api/client";
import { useApi } from "../api/hooks";
import { Gauge } from "../components/Gauge";
import { Card, ErrorBox, GateBadge, Kpi, Loading } from "../components/ui";
import { num, pct } from "../lib/format";

export default function Overview() {
  const { data, error, loading, reload } = useApi(api.overview, [], 10000);
  if (error) return <ErrorBox error={error} onRetry={reload} />;
  if (loading && !data) return <Loading />;
  if (!data) return null;
  const lift = data.inclusion;
  return (
    <>
      <h1>Overview</h1>
      <p className="subtitle">Live numbers from stored decisions (refreshes every 10 s).</p>
      <div className="grid kpis">
        <Kpi testId="kpi-applications" label="Applications" value={num(data.applications)} hint={`${num(data.decisions)} decisions`} />
        <Kpi testId="kpi-approval" label="Approval rate" value={pct(data.approval_rate)} hint={`${data.needs_review} in review`} />
        <Kpi testId="kpi-repayment" label="On-time repayment rate" value={pct(data.repayment_rate)} hint={`${num(data.repayments)} repayments`} />
        <Kpi
          testId="kpi-lift"
          label="Inclusion Lift"
          value={`+${pct(lift.newly_included_rate)}`}
          hint={`${num(lift.newly_included_count)} people the bank rule would reject`}
        />
      </div>
      <div className="grid two" style={{ marginTop: 16 }}>
        <Card title="Approvals: bank rule vs TrustLedger">
          <div className="grid" style={{ gridTemplateColumns: "1fr 1fr" }}>
            <Gauge value={lift.bank_rule_approval_rate} color="#94A3B8" label="Bank rule" />
            <Gauge value={lift.trustledger_approval_rate} label="TrustLedger" />
          </div>
          <p className="subtitle" style={{ marginTop: 8 }}>Bank rule: {lift.rule_description}</p>
        </Card>
        <Card title="Fairness gate (approval-rate gap ≤ 0.05)">
          <div style={{ fontSize: 30, fontWeight: 700 }}>
            {data.approval_rate_gap.toFixed(3)} <GateBadge ok={data.fairness_ok} />
          </div>
          <p className="subtitle">Average score {data.avg_score} · bands {Object.entries(data.by_band).map(([b, c]) => `${b} ${c}`).join(" · ")}</p>
        </Card>
      </div>
    </>
  );
}

import { Bar, BarChart, CartesianGrid, Legend, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { api } from "../api/client";
import { useApi } from "../api/hooks";
import { Card, ErrorBox, Loading } from "../components/ui";

export default function Distribution() {
  const { data, error, reload } = useApi(api.distribution, [], 15000);
  if (error) return <ErrorBox error={error} onRetry={reload} />;
  if (!data) return <Loading />;
  const rows = data.map((b) => ({ range: `${b.bin_start}`, approved: b.approved, declined: b.count - b.approved }));
  return (
    <>
      <h1>Score distribution</h1>
      <p className="subtitle">TrustLedger scores (300–900) of stored decisions. Bands: Building &lt;550, Fair 550, Good 650, Excellent 750+.</p>
      <Card title="Decisions per 25-point bin">
        <div style={{ height: 380 }}>
          <ResponsiveContainer>
            <BarChart data={rows}>
              <CartesianGrid strokeDasharray="3 3" stroke="var(--grid)" />
              <XAxis dataKey="range" stroke="var(--muted)" />
              <YAxis allowDecimals={false} stroke="var(--muted)" />
              <Tooltip />
              <Legend />
              <Bar dataKey="approved" stackId="a" fill="#14B8A6" />
              <Bar dataKey="declined" stackId="a" fill="#94A3B8" />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </Card>
    </>
  );
}

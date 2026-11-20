import { ArcElement, Chart as ChartJS, Tooltip } from "chart.js";
import { Doughnut } from "react-chartjs-2";

ChartJS.register(ArcElement, Tooltip);

/** Small half-doughnut gauge (Chart.js) for a 0-1 rate. */
export function Gauge({ value, color = "#14B8A6", label }: { value: number; color?: string; label: string }) {
  const v = Math.max(0, Math.min(1, value));
  return (
    <div style={{ position: "relative", width: "100%", maxWidth: 220, margin: "0 auto" }} aria-label={`${label} ${(v * 100).toFixed(0)}%`}>
      <Doughnut
        data={{ datasets: [{ data: [v, 1 - v], backgroundColor: [color, "rgba(148,163,184,0.25)"], borderWidth: 0 }] }}
        options={{
          rotation: -90,
          circumference: 180,
          cutout: "72%",
          maintainAspectRatio: true,
          aspectRatio: 1.6,
          plugins: { tooltip: { enabled: false } },
          animation: { duration: 600 },
        }}
      />
      <div style={{ position: "absolute", left: 0, right: 0, bottom: 4, textAlign: "center" }}>
        <div style={{ fontSize: 22, fontWeight: 700 }}>{(v * 100).toFixed(1)}%</div>
        <div style={{ fontSize: 12, color: "var(--muted)" }}>{label}</div>
      </div>
    </div>
  );
}

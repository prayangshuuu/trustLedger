import { geoMercator, geoPath } from "d3-geo";
import type { FeatureCollection, Geometry } from "geojson";
import { useEffect, useMemo, useState } from "react";
import { api } from "../api/client";
import { useApi } from "../api/hooks";
import { Card, ErrorBox, Loading } from "../components/ui";
import { pct } from "../lib/format";

type Geo = FeatureCollection<Geometry, { name: string }>;

function color(rate: number | undefined, lo = 0, hi = 1): string {
  if (rate === undefined) return "rgba(148,163,184,0.3)";
  // teal ramp scaled to the observed min..max so differences between divisions are visible
  const t = hi > lo ? Math.max(0, Math.min(1, (rate - lo) / (hi - lo))) : 0.5;
  const mix = (a: number, b: number) => Math.round(a + (b - a) * t);
  return `rgb(${mix(204, 15)}, ${mix(251, 118)}, ${mix(241, 110)})`;
}

export default function MapPage() {
  const stats = useApi(api.divisions, [], 15000);
  const [geo, setGeo] = useState<Geo | null>(null);
  const [hover, setHover] = useState<{ x: number; y: number; name: string } | null>(null);

  useEffect(() => {
    fetch("/bd-divisions.geojson")
      .then((r) => r.json())
      .then(setGeo)
      .catch(() => setGeo(null));
  }, []);

  const byName = useMemo(() => new Map((stats.data ?? []).map((d) => [d.division, d])), [stats.data]);
  const rates = (stats.data ?? []).map((d) => d.approval_rate);
  const lo = rates.length ? Math.min(...rates) : 0;
  const hi = rates.length ? Math.max(...rates) : 1;
  const width = 520;
  const height = 620;
  const path = useMemo(() => (geo ? geoPath(geoMercator().fitSize([width, height], geo)) : null), [geo]);

  if (stats.error) return <ErrorBox error={stats.error} onRetry={stats.reload} />;
  if (!stats.data || !geo || !path) return <Loading />;
  const hovered = hover ? byName.get(hover.name) : undefined;
  return (
    <>
      <h1>Approvals by division</h1>
      <p className="subtitle">Aggregate approval rate per division (D3). Division is never a model input.</p>
      <div className="grid two">
        <Card title="Map">
          <div style={{ position: "relative" }}>
            <svg viewBox={`0 0 ${width} ${height}`} width="100%" role="img" aria-label="Bangladesh divisions map">
              {geo.features.map((f) => (
                <path
                  key={f.properties.name}
                  d={path(f) ?? undefined}
                  fill={color(byName.get(f.properties.name)?.approval_rate, lo, hi)}
                  stroke="var(--panel)"
                  strokeWidth={1.5}
                  data-division={f.properties.name}
                  onMouseMove={(e) => {
                    const box = (e.currentTarget.ownerSVGElement as SVGSVGElement).getBoundingClientRect();
                    setHover({ x: e.clientX - box.left + 12, y: e.clientY - box.top + 12, name: f.properties.name });
                  }}
                  onMouseLeave={() => setHover(null)}
                />
              ))}
            </svg>
            {hover && (
              <div className="map-tooltip" style={{ left: hover.x, top: hover.y }}>
                <strong>{hover.name}</strong>
                <br />
                {hovered ? `${pct(hovered.approval_rate)} of ${hovered.applications}` : "no applications"}
              </div>
            )}
          </div>
          <p className="subtitle" style={{ fontSize: 12 }}>
            Light = {pct(lo)} · dark = {pct(hi)} approval. Boundaries: geoBoundaries (CC0).
          </p>
        </Card>
        <Card title="Divisions">
          <table>
            <thead>
              <tr><th>Division</th><th>Applications</th><th>Approved</th><th>Rate</th></tr>
            </thead>
            <tbody>
              {stats.data.map((d) => (
                <tr key={d.division}>
                  <td><span style={{ display: "inline-block", width: 10, height: 10, background: color(d.approval_rate, lo, hi), marginRight: 6 }} />{d.division}</td>
                  <td>{d.applications}</td>
                  <td>{d.approvals}</td>
                  <td>{pct(d.approval_rate)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </Card>
      </div>
    </>
  );
}

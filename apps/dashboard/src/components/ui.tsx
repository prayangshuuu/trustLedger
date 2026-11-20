import type { ReactNode } from "react";

export function Kpi({ label, value, hint, testId }: { label: string; value: ReactNode; hint?: string; testId?: string }) {
  return (
    <div className="card kpi" data-testid={testId}>
      <h2>{label}</h2>
      <div className="value">{value}</div>
      {hint && <div className="hint">{hint}</div>}
    </div>
  );
}

export function Card({ title, children, actions }: { title: string; children: ReactNode; actions?: ReactNode }) {
  return (
    <section className="card">
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
        <h2>{title}</h2>
        {actions}
      </div>
      {children}
    </section>
  );
}

export function GateBadge({ ok, labels = ["PASS", "FAIL"] }: { ok: boolean; labels?: [string, string] }) {
  return <span className={`badge ${ok ? "pass" : "fail"}`}>{ok ? labels[0] : labels[1]}</span>;
}

export function Loading() {
  return <p style={{ color: "var(--muted)" }}>Loading…</p>;
}

export function ErrorBox({ error, onRetry }: { error: Error; onRetry?: () => void }) {
  return (
    <div className="error" role="alert">
      {error.message}{" "}
      {onRetry && (
        <button className="btn secondary" onClick={onRetry}>
          Retry
        </button>
      )}
    </div>
  );
}

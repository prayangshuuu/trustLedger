import type { FairnessReport, InclusionLift } from "../api/client";

function escape(v: unknown): string {
  const s = v === null || v === undefined ? "" : String(v);
  return /[",\n]/.test(s) ? `"${s.replace(/"/g, '""')}"` : s;
}

export function toCsv(rows: Record<string, unknown>[]): string {
  if (rows.length === 0) return "";
  const cols = Object.keys(rows[0]);
  return [cols.join(","), ...rows.map((r) => cols.map((c) => escape(r[c])).join(","))].join("\n");
}

export function fairnessCsv(report: FairnessReport): string {
  const rows: Record<string, unknown>[] = Object.values(report.by_group).map((g) => ({
    section: "group",
    group: g.group,
    count: g.count,
    approval_rate: g.approval_rate,
    tpr: g.tpr,
    fpr: g.fpr,
  }));
  rows.push(
    { section: "gap", group: "approval_rate_gap", count: report.total_decisions, approval_rate: report.approval_rate_gap, tpr: "", fpr: "" },
    { section: "gap", group: "equalized_odds_gap", count: report.total_decisions, approval_rate: report.equalized_odds_gap, tpr: "", fpr: "" },
    { section: "gate", group: "fairness_ok (<= 0.05)", count: "", approval_rate: report.fairness_ok, tpr: "", fpr: "" },
  );
  return toCsv(rows);
}

export function inclusionCsv(lift: InclusionLift): string {
  return toCsv(Object.entries(lift).map(([metric, value]) => ({ metric, value })));
}

export function download(filename: string, content: string, type = "text/csv;charset=utf-8"): void {
  const url = URL.createObjectURL(new Blob([content], { type }));
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  a.click();
  URL.revokeObjectURL(url);
}

export const pct = (v: number | null | undefined, digits = 1): string =>
  v === null || v === undefined ? "—" : `${(v * 100).toFixed(digits)}%`;

export const num = (v: number | null | undefined): string =>
  v === null || v === undefined ? "—" : v.toLocaleString("en-US");

export const GAP_LIMIT = 0.05;

export const BAND_COLORS: Record<string, string> = {
  Excellent: "#16A34A",
  Good: "#14B8A6",
  Fair: "#F5B942",
  Building: "#D97706",
};

export const GROUP_LABELS: Record<string, string> = {
  F_rural: "Women · rural",
  F_urban: "Women · urban",
  M_rural: "Men · rural",
  M_urban: "Men · urban",
};

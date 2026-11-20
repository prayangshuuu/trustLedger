import { ReactNode, createContext, useCallback, useContext, useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { ApiException } from "./lib/api";
import { AppState, motion } from "./lib/state";

// ------------------------------------------------------------------ icons (Material, 24px grid)
const paths = {
  verified_user: "M12 1L3 5v6c0 5.55 3.84 10.74 9 12 5.16-1.26 9-6.45 9-12V5l-9-4zm-2 16l-4-4 1.41-1.41L10 14.17l6.59-6.59L18 9l-8 8z",
  lock_open: "M12 17c1.1 0 2-.9 2-2s-.9-2-2-2-2 .9-2 2 .9 2 2 2zm6-9h-1V6c0-2.76-2.24-5-5-5S7 3.24 7 6h1.9c0-1.71 1.39-3.1 3.1-3.1 1.71 0 3.1 1.39 3.1 3.1v2H6c-1.1 0-2 .9-2 2v10c0 1.1.9 2 2 2h12c1.1 0 2-.9 2-2V10c0-1.1-.9-2-2-2zm0 12H6V10h12v10z",
  lock: "M12 17c1.1 0 2-.9 2-2s-.9-2-2-2-2 .9-2 2 .9 2 2 2zm6-9h-1V6c0-2.76-2.24-5-5-5S7 3.24 7 6v2H6c-1.1 0-2 .9-2 2v10c0 1.1.9 2 2 2h12c1.1 0 2-.9 2-2V10c0-1.1-.9-2-2-2zM8.9 6c0-1.71 1.39-3.1 3.1-3.1s3.1 1.39 3.1 3.1v2H8.9V6zM18 20H6V10h12v10z",
  wallet: "M21 18v1c0 1.1-.9 2-2 2H5c-1.11 0-2-.9-2-2V5c0-1.1.89-2 2-2h14c1.1 0 2 .9 2 2v1h-9c-1.11 0-2 .9-2 2v8c0 1.1.89 2 2 2h9zm-9-2h10V8H12v8zm4-2.5c-.83 0-1.5-.67-1.5-1.5s.67-1.5 1.5-1.5 1.5.67 1.5 1.5-.67 1.5-1.5 1.5z",
  arrow_forward: "M12 4l-1.41 1.41L16.17 11H4v2h12.17l-5.58 5.59L12 20l8-8z",
  arrow_back: "M20 11H7.83l5.59-5.59L12 4l-8 8 8 8 1.41-1.41L7.83 13H20v-2z",
  arrow_up: "M4 12l1.41 1.41L11 7.83V20h2V7.83l5.58 5.59L20 12l-8-8-8 8z",
  arrow_down: "M20 12l-1.41-1.41L13 16.17V4h-2v12.17l-5.58-5.59L4 12l8 8 8-8z",
  check_circle: "M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm-2 15l-5-5 1.41-1.41L10 14.17l7.59-7.59L19 8l-9 9z",
  unchecked: "M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm0 18c-4.42 0-8-3.58-8-8s3.58-8 8-8 8 3.58 8 8-3.58 8-8 8z",
  sms: "M20 2H4c-1.1 0-1.99.9-1.99 2L2 22l4-4h14c1.1 0 2-.9 2-2V4c0-1.1-.9-2-2-2zM9 11H7V9h2v2zm4 0h-2V9h2v2zm4 0h-2V9h2v2z",
  receipt: "M19.5 3.5L18 2l-1.5 1.5L15 2l-1.5 1.5L12 2l-1.5 1.5L9 2 7.5 3.5 6 2 4.5 3.5 3 2v20l1.5-1.5L6 22l1.5-1.5L9 22l1.5-1.5L12 22l1.5-1.5L15 22l1.5-1.5L18 22l1.5-1.5L21 22V2l-1.5 1.5zM19 19.09H5V4.91h14v14.18zM6 15h12v2H6zm0-4h12v2H6zm0-4h12v2H6z",
  upload_file: "M14 2H6c-1.1 0-1.99.9-1.99 2L4 20c0 1.1.89 2 1.99 2H18c1.1 0 2-.9 2-2V8l-6-6zm4 18H6V4h7v5h5v11zM8 15.01l1.41 1.41L11 14.84V19h2v-4.16l1.59 1.59L16 15.01 12.01 11z",
  photo_library: "M22 16V4c0-1.1-.9-2-2-2H8c-1.1 0-2 .9-2 2v12c0 1.1.9 2 2 2h12c1.1 0 2-.9 2-2zm-11-4l2.03 2.71L16 11l4 5H8l3-4zM2 6v14c0 1.1.9 2 2 2h14v-2H4V6H2z",
  camera: "M12 15.2a3.2 3.2 0 100-6.4 3.2 3.2 0 000 6.4zM9 2L7.17 4H4c-1.1 0-2 .9-2 2v12c0 1.1.9 2 2 2h16c1.1 0 2-.9 2-2V6c0-1.1-.9-2-2-2h-3.17L15 2H9zm3 15c-2.76 0-5-2.24-5-5s2.24-5 5-5 5 2.24 5 5-2.24 5-5 5z",
  edit: "M3 17.25V21h3.75L17.81 9.94l-3.75-3.75L3 17.25zM20.71 7.04a.996.996 0 000-1.41l-2.34-2.34a.996.996 0 00-1.41 0l-1.83 1.83 3.75 3.75 1.83-1.83z",
  delete: "M6 19c0 1.1.9 2 2 2h8c1.1 0 2-.9 2-2V7H6v12zM8 9h8v10H8V9zm7.5-5l-1-1h-5l-1 1H5v2h14V4z",
  delete_forever: "M6 19c0 1.1.9 2 2 2h8c1.1 0 2-.9 2-2V7H6v12zm2.46-7.12l1.41-1.41L12 12.59l2.12-2.12 1.41 1.41L13.41 14l2.12 2.12-1.41 1.41L12 15.41l-2.12 2.12-1.41-1.41L10.59 14l-2.13-2.12zM15.5 4l-1-1h-5l-1 1H5v2h14V4z",
  lightbulb: "M9 21c0 .55.45 1 1 1h4c.55 0 1-.45 1-1v-1H9v1zm3-19C8.14 2 5 5.14 5 9c0 2.38 1.19 4.47 3 5.74V17c0 .55.45 1 1 1h6c.55 0 1-.45 1-1v-2.26c1.81-1.27 3-3.36 3-5.74 0-3.86-3.14-7-7-7zm2.85 11.1l-.85.6V16h-4v-2.3l-.85-.6A4.997 4.997 0 017 9c0-2.76 2.24-5 5-5s5 2.24 5 5c0 1.63-.8 3.16-2.15 4.1z",
  shield: "M12 1L3 5v6c0 5.55 3.84 10.74 9 12 5.16-1.26 9-6.45 9-12V5l-9-4zm0 2.18l7 3.12v4.7c0 4.52-2.98 8.69-7 9.93-4.02-1.24-7-5.41-7-9.93V6.3l7-3.12z",
  warning: "M12 5.99L19.53 19H4.47L12 5.99M12 2L1 21h22L12 2zm1 14h-2v2h2v-2zm0-6h-2v4h2v-4z",
  send: "M2.01 21L23 12 2.01 3 2 10l15 2-15 2z",
  settings: "M19.14 12.94c.04-.3.06-.61.06-.94 0-.32-.02-.64-.07-.94l2.03-1.58c.18-.14.23-.41.12-.61l-1.92-3.32c-.12-.22-.37-.29-.59-.22l-2.39.96c-.5-.38-1.03-.7-1.62-.94l-.36-2.54c-.04-.24-.24-.41-.48-.41h-3.84c-.24 0-.43.17-.47.41l-.36 2.54c-.59.24-1.13.57-1.62.94l-2.39-.96c-.22-.08-.47 0-.59.22L2.74 8.87c-.12.21-.08.47.12.61l2.03 1.58c-.05.3-.09.63-.09.94s.02.64.07.94l-2.03 1.58c-.18.14-.23.41-.12.61l1.92 3.32c.12.22.37.29.59.22l2.39-.96c.5.38 1.03.7 1.62.94l.36 2.54c.05.24.24.41.48.41h3.84c.24 0 .44-.17.47-.41l.36-2.54c.59-.24 1.13-.56 1.62-.94l2.39.96c.22.08.47 0 .59-.22l1.92-3.32c.12-.22.07-.47-.12-.61l-2.01-1.58zM12 15.6c-1.98 0-3.6-1.62-3.6-3.6s1.62-3.6 3.6-3.6 3.6 1.62 3.6 3.6-1.62 3.6-3.6 3.6z",
} as const;

export type IconName = keyof typeof paths;

export function Icon({ name, size = 24, color, label }: { name: IconName; size?: number; color?: string; label?: string }) {
  return (
    <svg
      className="icon"
      width={size}
      height={size}
      viewBox="0 0 24 24"
      style={{ fill: color ?? "currentColor" }}
      role={label ? "img" : undefined}
      aria-label={label}
      aria-hidden={label ? undefined : true}
    >
      <path d={paths[name]} />
    </svg>
  );
}

export const WalletIcon = ({ size = 28 }: { size?: number }) => (
  <Icon name="wallet" size={size} color="var(--teal-dark)" label="wallet" />
);

export const Spinner = ({ size = 24, light = false }: { size?: number; light?: boolean }) => (
  <span className={`spinner${light ? " light" : ""}`} style={{ width: size, height: size }} role="progressbar" />
);

// ------------------------------------------------------------------ snackbar
type Toast = { id: number; text: string; action?: { label: string; onClick: () => void } };
const ToastCtx = createContext<(t: Omit<Toast, "id">) => void>(() => {});

export function ToastProvider({ children }: { children: ReactNode }) {
  const [toast, setToast] = useState<Toast | null>(null);
  const show = useCallback((t: Omit<Toast, "id">) => setToast({ ...t, id: Date.now() }), []);
  useEffect(() => {
    if (!toast) return;
    const timer = setTimeout(() => setToast(null), 5000);
    return () => clearTimeout(timer);
  }, [toast]);
  return (
    <ToastCtx.Provider value={show}>
      {children}
      <div className="snackbar-host" role="status" aria-live="polite">
        {toast && (
          <div className="snackbar" key={toast.id}>
            <span>{toast.text}</span>
            {toast.action && (
              <button
                className="snackbar-action"
                onClick={() => {
                  setToast(null);
                  toast.action!.onClick();
                }}
              >
                {toast.action.label}
              </button>
            )}
          </div>
        )}
      </div>
    </ToastCtx.Provider>
  );
}

export const useToast = () => useContext(ToastCtx);

/** Show a Bangla-friendly error with an optional retry action. */
export function useShowError(state: AppState) {
  const toast = useToast();
  return useCallback(
    (error: unknown, onRetry?: () => void) => {
      const key = error instanceof ApiException ? error.l10nKey : "err_generic";
      toast({ text: state.t(key), action: onRetry ? { label: state.t("retry"), onClick: onRetry } : undefined });
    },
    [state, toast],
  );
}

// ------------------------------------------------------------------ frame
export function LangToggle({ state }: { state: AppState }) {
  return (
    <button
      className="text-btn on-brand"
      data-testid="lang_toggle"
      onClick={state.toggleLanguage}
      aria-label={state.lang === "bn" ? "Switch to English" : "বাংলায় দেখুন"}
    >
      {state.lang === "bn" ? "English" : "বাংলা"}
    </button>
  );
}

const canGoBack = () => ((window.history.state as { idx?: number } | null)?.idx ?? 0) > 0;

export function AppBar({ title, children }: { title: string; children?: ReactNode }) {
  const navigate = useNavigate();
  return (
    <header className="appbar">
      {canGoBack() && (
        <button className="icon-btn on-brand" aria-label="Back" onClick={() => navigate(-1)}>
          <Icon name="arrow_back" />
        </button>
      )}
      <h1 className="appbar-title">{title}</h1>
      <div className="appbar-actions">{children}</div>
    </header>
  );
}

/** Shared page frame: title, language toggle and settings. */
export function TLScaffold({
  state,
  title,
  children,
  bottom,
  bodyClass = "body-list",
}: {
  state: AppState;
  title: string;
  children: ReactNode;
  bottom?: ReactNode;
  bodyClass?: string;
}) {
  const navigate = useNavigate();
  return (
    <div className="scaffold">
      <AppBar title={title}>
        <LangToggle state={state} />
        {state.userId != null && (
          <button
            className="icon-btn on-brand"
            data-testid="open_settings"
            title={state.t("settings")}
            aria-label={state.t("settings")}
            onClick={() => navigate("/settings")}
          >
            <Icon name="settings" />
          </button>
        )}
      </AppBar>
      <main className={bodyClass}>{children}</main>
      {bottom && <footer className="bottom-bar">{bottom}</footer>}
    </div>
  );
}

export const SectionHeader = ({ children }: { children: ReactNode }) => <h2 className="section-header">{children}</h2>;

export function Switch({ checked, onChange, disabled, testId, label }: {
  checked: boolean;
  onChange: (v: boolean) => void;
  disabled?: boolean;
  testId?: string;
  label?: string;
}) {
  return (
    <button
      type="button"
      role="switch"
      aria-checked={checked}
      aria-label={label}
      data-testid={testId}
      disabled={disabled}
      className={`switch${checked ? " on" : ""}`}
      onClick={() => onChange(!checked)}
    >
      <span className="switch-thumb" />
    </button>
  );
}

/** Card with a title/subtitle and a switch on the right; the whole row toggles. */
export function SwitchTile({ title, subtitle, checked, onChange, disabled, testId, card = true }: {
  title: ReactNode;
  subtitle?: ReactNode;
  checked: boolean;
  onChange: (v: boolean) => void;
  disabled?: boolean;
  testId?: string;
  card?: boolean;
}) {
  return (
    <div
      className={`tile${card ? " card" : ""}${disabled ? " disabled" : ""}`}
      onClick={() => !disabled && onChange(!checked)}
    >
      <div className="tile-text">
        <div className="tile-title semibold">{title}</div>
        {subtitle && <div className="tile-subtitle">{subtitle}</div>}
      </div>
      <span onClick={(e) => e.stopPropagation()}>
        <Switch checked={checked} onChange={onChange} disabled={disabled} testId={testId} label={typeof title === "string" ? title : undefined} />
      </span>
    </div>
  );
}

// ------------------------------------------------------------------ score meter
export function bandColor(band: string) {
  return (
    { Excellent: "var(--band-excellent)", Good: "var(--band-good)", Fair: "var(--band-fair)" }[band] ?? "var(--band-building)"
  );
}

const bands: [number, number, string][] = [
  [300, 550, "var(--band-building)"],
  [550, 650, "var(--gold)"],
  [650, 750, "var(--teal)"],
  [750, 900, "var(--good)"],
];

/** Animated 300-900 score gauge with band-coloured segments; skipped under reduced motion. */
export function ScoreMeter({ score, label, color, duration = 1800 }: { score: number; label: string; color: string; duration?: number }) {
  const target = Math.min(900, Math.max(300, score));
  const [value, setValue] = useState(() => (motion(duration) ? 300 : target));
  useEffect(() => {
    const ms = motion(duration);
    if (!ms) return setValue(target);
    let raf = 0;
    const start = performance.now();
    const tick = (now: number) => {
      const p = Math.min(1, (now - start) / ms);
      const eased = 1 - Math.pow(1 - p, 3); // easeOutCubic
      setValue(300 + (target - 300) * eased);
      if (p < 1) raf = requestAnimationFrame(tick);
    };
    raf = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(raf);
  }, [target, duration]);

  const W = 280, H = 150;
  const cx = W / 2, cy = H - 6, r = W / 2 - 16;
  const angle = (v: number) => Math.PI + ((v - 300) / 600) * Math.PI;
  const pt = (a: number, rad: number) => [cx + Math.cos(a) * rad, cy + Math.sin(a) * rad];
  const arc = (lo: number, hi: number) => {
    const a0 = angle(lo), a1 = angle(hi) - 0.02;
    const [x0, y0] = pt(a0, r), [x1, y1] = pt(a1, r);
    return `M ${x0} ${y0} A ${r} ${r} 0 0 1 ${x1} ${y1}`;
  };
  const [nx, ny] = pt(angle(value), r - 26);
  return (
    <div className="meter" role="img" aria-label={`${score}, ${label}`}>
      <svg width={W} height={H} viewBox={`0 0 ${W} ${H}`} aria-hidden>
        {bands.map(([lo, hi, c]) => (
          <path key={lo} d={arc(lo, hi)} style={{ stroke: c }} strokeOpacity={0.85} strokeWidth={18} fill="none" />
        ))}
        <line x1={cx} y1={cy} x2={nx} y2={ny} style={{ stroke: "var(--navy)" }} strokeWidth={4} strokeLinecap="round" />
        <circle cx={cx} cy={cy} r={7} style={{ fill: "var(--navy)" }} />
      </svg>
      <div className="meter-score" data-testid="score_value">{Math.round(value)}</div>
      <div className="meter-label" style={{ color }}>{label}</div>
    </div>
  );
}

// ------------------------------------------------------------------ files
export type PickedFile = { name: string; file: File };

/** Opens the browser file picker (camera capture on phones when camera is true). */
export function pickFile(accept: string, camera = false): Promise<PickedFile | null> {
  return new Promise((resolve) => {
    const input = document.createElement("input");
    input.type = "file";
    input.accept = accept;
    if (camera) input.setAttribute("capture", "environment");
    input.onchange = () => {
      const f = input.files?.[0];
      resolve(f ? { name: f.name, file: f } : null);
    };
    input.click();
  });
}

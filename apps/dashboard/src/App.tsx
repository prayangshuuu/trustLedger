import { type FormEvent, useEffect, useState } from "react";
import { NavLink, Navigate, Route, Routes } from "react-router-dom";
import { ApiError, api, apiGet, getApiKey, setApiKey } from "./api/client";
import Applicant from "./pages/Applicant";
import Distribution from "./pages/Distribution";
import Fairness from "./pages/Fairness";
import Feed from "./pages/Feed";
import MapPage from "./pages/MapPage";
import Overview from "./pages/Overview";
import Reports from "./pages/Reports";

type Theme = "light" | "dark";

function initialTheme(): Theme {
  try {
    const saved = localStorage.getItem("tl_theme");
    if (saved === "light" || saved === "dark") return saved;
  } catch {
    /* ignore */
  }
  return window.matchMedia?.("(prefers-color-scheme: dark)").matches ? "dark" : "light";
}

function Login({ onLogin }: { onLogin: (key: string) => void }) {
  const [key, setKey] = useState("");
  const [error, setError] = useState<string | null>(null);
  const submit = async (e: FormEvent) => {
    e.preventDefault();
    try {
      await apiGet("/stats/overview", key);
      onLogin(key);
    } catch (err) {
      setError(err instanceof ApiError && err.status === 401 ? "Invalid API key" : "Cannot reach the TrustLedger API");
    }
  };
  return (
    <div className="login">
      <form onSubmit={submit} aria-label="login">
        <div className="brand" style={{ color: "var(--text)", margin: 0 }}>Trust<span>Ledger</span></div>
        <p className="subtitle" style={{ margin: 0 }}>Lender dashboard · sign in with your API key</p>
        <input aria-label="API key" type="password" placeholder="X-API-Key" value={key} onChange={(e) => setKey(e.target.value)} autoFocus />
        {error && <div className="error">{error}</div>}
        <button className="btn" type="submit">Sign in</button>
      </form>
    </div>
  );
}

const NAV = [
  ["/", "Overview"],
  ["/distribution", "Score distribution"],
  ["/fairness", "Fairness"],
  ["/map", "Division map"],
  ["/feed", "Live feed"],
  ["/reports", "Reports"],
] as const;

export default function App() {
  const [authed, setAuthed] = useState<boolean | null>(null);
  const [theme, setTheme] = useState<Theme>(initialTheme);

  useEffect(() => {
    document.documentElement.dataset.theme = theme;
    try {
      localStorage.setItem("tl_theme", theme);
    } catch {
      /* ignore */
    }
  }, [theme]);

  useEffect(() => {
    // A stored key, or an API running without keys (local dev), skips the login form
    api.overview().then(() => setAuthed(true), () => setAuthed(false));
  }, []);

  if (authed === null) return null;
  if (!authed)
    return (
      <Login
        onLogin={(key) => {
          setApiKey(key);
          setAuthed(true);
        }}
      />
    );

  return (
    <div className="layout">
      <aside className="sidebar">
        <div className="brand">Trust<span>Ledger</span></div>
        <nav className="nav">
          {NAV.map(([to, label]) => (
            <NavLink key={to} to={to} end={to === "/"}>{label}</NavLink>
          ))}
        </nav>
        <div className="spacer" />
        <button onClick={() => setTheme(theme === "dark" ? "light" : "dark")}>{theme === "dark" ? "Light theme" : "Dark theme"}</button>
        {getApiKey() && (
          <button onClick={() => { setApiKey(null); setAuthed(false); }}>Sign out</button>
        )}
      </aside>
      <main>
        <Routes>
          <Route path="/" element={<Overview />} />
          <Route path="/distribution" element={<Distribution />} />
          <Route path="/fairness" element={<Fairness />} />
          <Route path="/map" element={<MapPage />} />
          <Route path="/feed" element={<Feed />} />
          <Route path="/applicant/:id" element={<Applicant />} />
          <Route path="/reports" element={<Reports />} />
          <Route path="*" element={<Navigate to="/" />} />
        </Routes>
      </main>
    </div>
  );
}

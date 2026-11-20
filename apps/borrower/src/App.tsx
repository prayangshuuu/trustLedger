import { ReactNode } from "react";
import { Navigate, Route, Routes, useLocation } from "react-router-dom";
import { AppState, useAppState } from "./lib/state";
import Bhorsha from "./pages/Bhorsha";
import Connect from "./pages/Connect";
import Consent from "./pages/Consent";
import Loan from "./pages/Loan";
import Processing from "./pages/Processing";
import Reasons from "./pages/Reasons";
import Repay from "./pages/Repay";
import Review from "./pages/Review";
import Score from "./pages/Score";
import Settings from "./pages/Settings";
import Welcome from "./pages/Welcome";
import { ResponsiveFrame } from "./responsive";

/** Routes behind the session redirect to / when it is missing; routes that need a decision fall back to /connect. */
export function redirectFor(state: AppState, location: string): string | null {
  if (location === "/") return null;
  if (!state.hasSession) return "/";
  if (["/score", "/reasons", "/loan"].includes(location) && state.decision == null) return "/connect";
  if (location === "/repay" && state.applicationId == null) return "/connect";
  return null;
}

function Guard({ children }: { children: ReactNode }) {
  const s = useAppState();
  const { pathname } = useLocation();
  const target = redirectFor(s, pathname);
  return target ? <Navigate to={target} replace /> : <>{children}</>;
}

const page = (el: ReactNode, maxWidth?: number) => (
  <Guard>
    <ResponsiveFrame maxWidth={maxWidth}>{el}</ResponsiveFrame>
  </Guard>
);

export default function App() {
  return (
    <Routes>
      <Route path="/" element={page(<Welcome />)} />
      <Route path="/consent" element={page(<Consent />)} />
      <Route path="/connect" element={page(<Connect />)} />
      <Route path="/review" element={page(<Review />)} />
      <Route path="/processing" element={page(<Processing />)} />
      <Route path="/score" element={page(<Score />)} />
      <Route path="/reasons" element={page(<Reasons />)} />
      <Route path="/loan" element={page(<Loan />)} />
      <Route path="/repay" element={page(<Repay />, 960)} />
      <Route path="/bhorsha" element={page(<Bhorsha />)} />
      <Route path="/settings" element={page(<Settings />, 960)} />
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}

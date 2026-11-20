import { ReactNode, useEffect, useState } from "react";

const compactMax = 600;

/** True below 600px (phone width), matching the Flutter Breakpoint.compact. */
export function useCompact() {
  const query = `(max-width: ${compactMax - 0.02}px)`;
  const [compact, setCompact] = useState(() => window.matchMedia(query).matches);
  useEffect(() => {
    const mq = window.matchMedia(query);
    const on = () => setCompact(mq.matches);
    mq.addEventListener("change", on);
    return () => mq.removeEventListener("change", on);
  }, [query]);
  return compact;
}

/** Phone width: the page as-is. Wider: centred in a column on a soft branded backdrop. */
export function ResponsiveFrame({ children, maxWidth = 520 }: { children: ReactNode; maxWidth?: number }) {
  const compact = useCompact();
  if (compact) return <div className="frame compact">{children}</div>;
  return (
    <div className="frame backdrop">
      <div className="frame-card" style={{ maxWidth }}>{children}</div>
    </div>
  );
}

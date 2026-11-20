import { useNavigate } from "react-router-dom";
import { useAppState } from "../lib/state";
import { ScoreMeter, TLScaffold, bandColor } from "../ui";

export default function Score() {
  const s = useAppState();
  const navigate = useNavigate();
  const d = s.decision;
  if (d == null) return null;
  const band = d.band as string;
  return (
    <TLScaffold
      state={s}
      title={s.t("your_score")}
      bodyClass="body-center"
      bottom={
        <button className="btn btn-filled" data-testid="see_reasons" onClick={() => navigate("/reasons")}>
          {s.t("why")}
        </button>
      }
    >
      <div data-testid="band_chip">
        <ScoreMeter score={d.score as number} label={s.t(`band_${band}`)} color={bandColor(band)} />
      </div>
      <div className="muted mt-sm">300 — 900</div>
    </TLScaffold>
  );
}

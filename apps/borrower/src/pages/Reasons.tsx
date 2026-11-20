import { useNavigate } from "react-router-dom";
import { Json } from "../lib/api";
import { Lang, num2 } from "../lib/l10n";
import { useAppState } from "../lib/state";
import { Icon, SectionHeader, TLScaffold } from "../ui";

function ReasonCard({ reason, good, lang }: { reason: Json; good: boolean; lang: Lang }) {
  return (
    <div className={`card tile list-tile ${good ? "tint-good" : "tint-warn"}`} data-testid={`reason_${reason.feature}`}>
      <Icon
        name={good ? "check_circle" : "warning"}
        size={30}
        color={good ? "var(--good)" : "var(--warn)"}
        label={good ? "helped" : "to improve"}
      />
      <div className="tile-text">
        <div className="tile-title semibold">{lang === "bn" ? reason.text : reason.label}</div>
        <div className="tile-subtitle">{lang === "bn" ? reason.label : reason.text}</div>
      </div>
    </div>
  );
}

export default function Reasons() {
  const s = useAppState();
  const navigate = useNavigate();
  const result = s.result;
  const d = s.decision;
  if (result == null || d == null) return null;
  const reasons = (d.reasons ?? []) as Json[];
  const good = reasons.filter((r) => r.kind === "good");
  const bad = reasons.filter((r) => r.kind === "bad");
  const tips = (result.grounded_tips ?? []) as Json[];
  const status = result.status as string;
  const dq = result.data_quality ?? d.data_quality ?? s.lastDataQuality;

  return (
    <TLScaffold
      state={s}
      title={s.t("why")}
      bottom={
        status === "approved" ? (
          <button className="btn btn-filled" data-testid="see_offer" onClick={() => navigate("/loan")}>{s.t("see_offer")}</button>
        ) : (
          <button className="btn btn-outlined block" onClick={() => navigate("/")}>{s.t("home")}</button>
        )
      }
    >
      {result.summary_bn != null && <div className="card pad-lg summary">{result.summary_bn}</div>}
      {good.length > 0 && <SectionHeader>{s.t("helped")}</SectionHeader>}
      {good.map((r) => <ReasonCard key={r.feature} reason={r} good lang={s.lang} />)}
      {bad.length > 0 && <SectionHeader>{s.t("improve")}</SectionHeader>}
      {bad.map((r) => <ReasonCard key={r.feature} reason={r} good={false} lang={s.lang} />)}
      {tips.length > 0 && <SectionHeader>{s.t("tips")}</SectionHeader>}
      {tips.map((tip, i) => (
        <div className="card tile list-tile" key={i}>
          <Icon name="lightbulb" color="var(--gold)" />
          <div className="tile-text">
            <div className="tile-title">{tip.text}</div>
            {tip.source != null && <div className="tile-subtitle caption">{`${s.t("source")}: ${tip.source.title}`}</div>}
          </div>
        </div>
      ))}
      {dq != null && (
        <>
          <SectionHeader>{s.t("data_quality_title")}</SectionHeader>
          <div className="card pad" data-testid="data_quality_card">
            <div className="row">
              <Icon name="shield" color="var(--teal)" />
              <strong>{`${s.t("data_confidence")}: ${num2(Math.round((dq.confidence ?? 1.0) * 100), s.lang)}%`}</strong>
              <span className="spacer" />
              <span className="muted caption">{`${num2(dq.months_covered ?? 0, s.lang)} মাস`}</span>
            </div>
            {((dq.notes_bn ?? []) as unknown[]).map((note, i) => (
              <div className="note" key={i}>
                <span className="bullet">• </span>
                <span className="small">{String(note)}</span>
              </div>
            ))}
          </div>
        </>
      )}
      {status === "needs_review" && <div className="card pad-lg notice-gold">{s.t("review")}</div>}
      {(status === "rejected" || status === "blocked") && <div className="card pad-lg notice-warn">{s.t("rejected")}</div>}
    </TLScaffold>
  );
}

import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { Json } from "../lib/api";
import { Lang } from "../lib/l10n";
import { useAppState } from "../lib/state";
import { Icon, LangToggle, Spinner, SwitchTile, WalletIcon, useShowError } from "../ui";

function personaName(key: string, lang: Lang) {
  const bn: Record<string, string> = {
    moon: "মুন — পোশাক শ্রমিক",
    student: "রাফি — ছাত্র ও ফ্রিল্যান্সার",
    homemaker: "রিনা — গৃহিণী (ভরসা সম্পন্ন)",
  };
  const en: Record<string, string> = {
    moon: "Moon — garment worker",
    student: "Rafi — student and freelancer",
    homemaker: "Rina — homemaker (Bhorsha done)",
  };
  if (lang === "bn") return bn[key] ?? "মিতু — নতুন (কোনো ইতিহাস নেই)";
  return en[key] ?? "Mitu — newcomer (no history)";
}

export default function Welcome() {
  const s = useAppState();
  const navigate = useNavigate();
  const showError = useShowError(s);
  const [personas, setPersonas] = useState<Json[] | null>(null);
  const [personaErr, setPersonaErr] = useState(false);
  const [busy, setBusy] = useState(false);
  const [showDemo, setShowDemo] = useState(false);

  const loadPersonas = () => {
    setPersonaErr(false);
    setPersonas(null);
    s.api.personas().then(setPersonas, () => setPersonaErr(true));
  };
  useEffect(loadPersonas, []); // eslint-disable-line react-hooks/exhaustive-deps

  const startReal = async () => {
    setBusy(true);
    try {
      await s.startRealSession();
      navigate("/consent");
    } catch (e) {
      showError(e, startReal);
    } finally {
      setBusy(false);
    }
  };

  const pick = async (p: Json) => {
    setBusy(true);
    try {
      await s.selectPersona(p);
      navigate("/consent");
    } catch (e) {
      showError(e, () => pick(p));
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="welcome">
      <div className="welcome-inner">
        <div className="row-end">
          <LangToggle state={s} />
        </div>
        <div className="welcome-logo">
          <Icon name="verified_user" size={64} color="var(--teal)" label="TrustLedger" />
        </div>
        <h1 className="welcome-title">{s.t("app_name")}</h1>
        <p className="welcome-tagline">{s.t("tagline")}</p>
        <button className="btn btn-hero" data-testid="use_own_data" disabled={busy} onClick={startReal}>
          <Icon name="lock_open" /> {s.t("use_own_data")}
        </button>
        <SwitchTile
          testId="try_demo_switch"
          title={s.t("try_demo")}
          subtitle={s.t("demo_mode")}
          checked={showDemo}
          onChange={setShowDemo}
        />
        {showDemo && (
          <div className="personas">
            {personaErr ? (
              <div className="center-col">
                <p className="on-brand-text">{s.t("err_network")}</p>
                <button className="text-btn teal" onClick={loadPersonas}>{s.t("retry")}</button>
              </div>
            ) : personas == null ? (
              <div className="center-col"><Spinner /></div>
            ) : (
              personas.map((p) => (
                <button key={p.key} className="card tile list-tile" data-testid={`persona_${p.key}`} disabled={busy} onClick={() => pick(p)}>
                  <WalletIcon />
                  <div className="tile-text">
                    <div className="tile-title semibold">{personaName(p.key, s.lang)}</div>
                    <div className="tile-subtitle">{p.description}</div>
                  </div>
                  {!busy && <Icon name="arrow_forward" />}
                </button>
              ))
            )}
          </div>
        )}
      </div>
    </div>
  );
}

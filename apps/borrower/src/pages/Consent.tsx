import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useAppState } from "../lib/state";
import { Spinner, SwitchTile, TLScaffold, useShowError } from "../ui";

export const consentSources = ["sms", "bills", "recharge", "ocr", "bhorsha"];

export default function Consent() {
  const s = useAppState();
  const navigate = useNavigate();
  const showError = useShowError(s);
  const [selected, setSelected] = useState(() => new Set(s.consents));
  const [busy, setBusy] = useState(false);

  const toggle = (src: string, on: boolean) =>
    setSelected((prev) => {
      const next = new Set(prev);
      if (on) next.add(src);
      else next.delete(src);
      return next;
    });

  const cont = async () => {
    setBusy(true);
    try {
      await s.saveConsents(selected);
      const hasData = selected.has("sms") || selected.has("ocr") || selected.has("bills");
      navigate(hasData ? "/connect" : "/processing");
    } catch (e) {
      showError(e, cont);
    } finally {
      setBusy(false);
    }
  };

  return (
    <TLScaffold
      state={s}
      title={s.t("consent_title")}
      bottom={
        <button className="btn btn-filled" data-testid="consent_continue" disabled={busy || selected.size === 0} onClick={cont}>
          {busy ? <Spinner light /> : s.t("continue")}
        </button>
      }
    >
      <p className="body-text">{s.t("consent_intro")}</p>
      {consentSources.map((src) => (
        <SwitchTile
          key={src}
          testId={`consent_${src}`}
          title={s.t(`src_${src}`)}
          subtitle={s.t(`src_${src}_d`)}
          checked={selected.has(src)}
          onChange={(on) => toggle(src, on)}
        />
      ))}
    </TLScaffold>
  );
}

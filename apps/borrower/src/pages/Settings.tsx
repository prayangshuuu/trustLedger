import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useAppState } from "../lib/state";
import { useCompact } from "../responsive";
import { AppBar, Icon, LangToggle, SwitchTile, useShowError, useToast } from "../ui";
import { consentSources } from "./Consent";

export default function Settings() {
  const s = useAppState();
  const navigate = useNavigate();
  const showError = useShowError(s);
  const toast = useToast();
  const compact = useCompact();
  const [busy, setBusy] = useState(false);
  const [confirming, setConfirming] = useState(false);

  const toggle = async (source: string, on: boolean) => {
    setBusy(true);
    try {
      if (on) await s.api.grantConsent(s.userId!, source);
      else await s.api.revokeConsent(source);
      await s.refreshProfile();
    } catch (e) {
      showError(e);
    } finally {
      setBusy(false);
    }
  };

  const doDelete = async () => {
    setConfirming(false);
    try {
      await s.deleteAll();
      navigate("/");
      toast({ text: s.t("deleted") });
    } catch (e) {
      showError(e);
    }
  };

  const consentsList = (
    <>
      <h3 className="list-heading">{s.t("active_consents")}</h3>
      {consentSources.map((src) => (
        <SwitchTile
          key={src}
          card={false}
          testId={`settings_consent_${src}`}
          title={s.t(`src_${src}`)}
          checked={s.consents.has(src)}
          disabled={busy || s.userId == null}
          onChange={(on) => toggle(src, on)}
        />
      ))}
    </>
  );

  const deleteBtn = (
    <button className="btn btn-outlined danger block" data-testid="delete_data" disabled={s.userId == null} onClick={() => setConfirming(true)}>
      <Icon name="delete_forever" /> {s.t("delete_data")}
    </button>
  );

  return (
    <div className="scaffold">
      <AppBar title={s.t("settings")}>
        <LangToggle state={s} />
      </AppBar>
      {compact ? (
        <main className="body-list">
          {consentsList}
          <hr className="divider" />
          {deleteBtn}
        </main>
      ) : (
        <main className="body-wide">
          <div className="col card pad-lg" style={{ flex: 3 }}>{consentsList}</div>
          <div className="col card pad-lg" style={{ flex: 2 }}>
            <h3 className="list-heading danger-text">{s.t("delete_data")}</h3>
            <p className="muted small">{s.t("delete_confirm")}</p>
            <div className="mt-xl" />
            {deleteBtn}
          </div>
        </main>
      )}
      {confirming && (
        <div className="sheet-backdrop dialog" onClick={() => setConfirming(false)}>
          <div className="dialog-box" role="alertdialog" aria-modal onClick={(e) => e.stopPropagation()}>
            <p>{s.t("delete_confirm")}</p>
            <div className="dialog-actions">
              <button className="text-btn teal" onClick={() => setConfirming(false)}>{s.t("cancel")}</button>
              <button className="btn btn-danger" data-testid="confirm_delete" onClick={doDelete}>{s.t("confirm")}</button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

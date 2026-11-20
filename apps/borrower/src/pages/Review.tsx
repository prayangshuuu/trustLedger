import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { Json } from "../lib/api";
import { num2 } from "../lib/l10n";
import { useAppState } from "../lib/state";
import { Icon, Spinner, TLScaffold, useShowError } from "../ui";

const txTypes: [string, string][] = [
  ["income", "আয় (Income)"],
  ["bill", "বিল (Bill)"],
  ["recharge", "রিচার্জ (Recharge)"],
  ["transfer", "লেনদেন (Transfer)"],
  ["savings", "সঞ্চয় (Savings)"],
  ["other", "অন্যান্য (Other)"],
];

function EditSheet({ tx, onSave, onClose }: { tx: Json; onSave: (t: Json) => void; onClose: () => void }) {
  const s = useAppState();
  const [amt, setAmt] = useState(String(tx.amount_bdt ?? "0"));
  const [type, setType] = useState(String(tx.type ?? "other"));
  const [counter, setCounter] = useState(String(tx.counterparty ?? ""));
  const save = () => {
    const parsed = Number.parseFloat(amt);
    onSave({ amount_bdt: Number.isNaN(parsed) ? Number(tx.amount_bdt) : parsed, type, counterparty: counter.trim(), confidence: 1.0 });
  };
  return (
    <div className="sheet-backdrop" onClick={onClose}>
      <div className="sheet" role="dialog" aria-modal onClick={(e) => e.stopPropagation()}>
        <h2 className="sheet-title">{s.t("edit")}</h2>
        <label className="field">
          <span>{s.t("amount")}</span>
          <input className="input" inputMode="decimal" value={amt} onChange={(e) => setAmt(e.target.value)} autoFocus />
        </label>
        <label className="field">
          <span>{s.t("type")}</span>
          <select className="input" value={type} onChange={(e) => setType(e.target.value)}>
            {!txTypes.some(([v]) => v === type) && <option value={type}>{type}</option>}
            {txTypes.map(([v, l]) => <option key={v} value={v}>{l}</option>)}
          </select>
        </label>
        <label className="field">
          <span>{s.t("provider")}</span>
          <input className="input" value={counter} onChange={(e) => setCounter(e.target.value)} />
        </label>
        <button className="btn btn-filled" onClick={save}>{s.t("save")}</button>
      </div>
    </div>
  );
}

export default function Review() {
  const s = useAppState();
  const navigate = useNavigate();
  const showError = useShowError(s);
  const [busy, setBusy] = useState(false);
  const [editing, setEditing] = useState<number | null>(null);
  const txs = s.extractedTransactions;
  const bills = s.extractedBills;

  const confirm = async () => {
    setBusy(true);
    try {
      const res = await s.confirmAndExtract();
      navigate(res.needs_bhorsha === true ? "/bhorsha" : "/processing", { replace: true });
    } catch (e) {
      showError(e, confirm);
    } finally {
      setBusy(false);
    }
  };

  const removeAt = (list: Json[], i: number) => {
    list.splice(i, 1);
    s.notify();
  };

  return (
    <TLScaffold
      state={s}
      title={s.t("review_title")}
      bottom={
        <button className="btn btn-filled" data-testid="confirm_review" disabled={busy} onClick={confirm}>
          {busy ? <Spinner size={20} light /> : s.t("confirm_data")}
        </button>
      }
    >
      <p className="muted body-text">{s.t("review_intro")}</p>
      {bills.length > 0 && (
        <>
          <h3 className="list-heading">{`${s.t("src_bills")} (${num2(bills.length, s.lang)})`}</h3>
          {bills.map((b, i) => (
            <div className="card tile list-tile" key={i}>
              <Icon name="receipt" color="var(--teal)" />
              <div className="tile-text">
                <div className="tile-title semibold">{`${b.provider ?? b.merchant_or_platform ?? "Utility"} · ৳${num2(b.amount_bdt ?? 0, s.lang)}`}</div>
                <div className="tile-subtitle small">{`${b.due_date ?? b.bill_month ?? ""}`}</div>
              </div>
              <button className="icon-btn" aria-label={s.t("delete")} onClick={() => removeAt(bills, i)}>
                <Icon name="delete" color="var(--bad)" />
              </button>
            </div>
          ))}
        </>
      )}
      <h3 className="list-heading">{`${s.t("src_sms")} (${num2(txs.length, s.lang)})`}</h3>
      {txs.length === 0 ? (
        <div className="card pad muted">{s.t("sms_loaded")}</div>
      ) : (
        txs.map((tx, i) => (
          <div className="card tile list-tile tight" key={i} data-testid={`tx_item_${i}`}>
            <Icon
              name={tx.direction === "in" ? "arrow_down" : "arrow_up"}
              size={20}
              color={tx.direction === "in" ? "var(--good)" : "var(--navy)"}
            />
            <div className="tile-text">
              <div className="tile-title row">
                <strong>{`৳${num2(tx.amount_bdt ?? 0, s.lang)}`}</strong>
                <span className="muted small">{`(${tx.type ?? ""})`}</span>
                <span className="spacer" />
                {(tx.confidence ?? 1.0) < 0.7 && <span className="chip-warn">{s.t("low_confidence")}</span>}
              </div>
              <div className="tile-subtitle small ellipsis">{`${tx.counterparty ?? tx.txn_id ?? ""}`}</div>
            </div>
            <button className="icon-btn" aria-label={s.t("edit")} onClick={() => setEditing(i)}>
              <Icon name="edit" size={20} />
            </button>
            <button className="icon-btn" aria-label={s.t("delete")} onClick={() => removeAt(txs, i)}>
              <Icon name="delete" size={20} color="var(--bad)" />
            </button>
          </div>
        ))
      )}
      {editing != null && txs[editing] && (
        <EditSheet
          tx={txs[editing]}
          onClose={() => setEditing(null)}
          onSave={(patch) => {
            Object.assign(txs[editing], patch);
            setEditing(null);
            s.notify();
          }}
        />
      )}
    </TLScaffold>
  );
}

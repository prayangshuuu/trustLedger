import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { num2 } from "../lib/l10n";
import { useAppState } from "../lib/state";
import { Spinner, TLScaffold, WalletIcon, useShowError } from "../ui";

export default function Loan() {
  const s = useAppState();
  const navigate = useNavigate();
  const showError = useShowError(s);
  const [busy, setBusy] = useState(false);

  const accept = async () => {
    setBusy(true);
    try {
      await s.api.disburse(s.applicationId!);
      await s.refreshLoan();
      navigate("/repay", { replace: true });
    } catch (e) {
      showError(e, accept);
    } finally {
      setBusy(false);
    }
  };

  return (
    <TLScaffold
      state={s}
      title={s.t("offer_title")}
      bodyClass="body-list pad-xl"
      bottom={
        <button className="btn btn-filled" data-testid="accept_offer" disabled={busy} onClick={accept}>
          {busy ? <Spinner light /> : s.t("accept")}
        </button>
      }
    >
      <div className="center-col">
        <WalletIcon size={56} />
        <p className="body-text mt-lg">{s.t("offer_amount")}</p>
        <div className="offer-amount" data-testid="offer_amount">{`৳ ${num2(s.amount, s.lang)}`}</div>
        <p className="body-text mt-sm">{`${s.t("installments")} · ৳ ${num2(s.amount / 3, s.lang)}`}</p>
      </div>
    </TLScaffold>
  );
}

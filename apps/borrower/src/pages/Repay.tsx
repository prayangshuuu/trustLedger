import { useEffect, useState } from "react";
import { num2 } from "../lib/l10n";
import { useAppState } from "../lib/state";
import { Icon, SectionHeader, TLScaffold, useShowError } from "../ui";
import { useCompact } from "../responsive";

export default function Repay() {
  const s = useAppState();
  const showError = useShowError(s);
  const compact = useCompact();
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    if (s.loan == null) s.refreshLoan().catch(() => {});
  }, [s]);

  const run = async (action: () => Promise<unknown>) => {
    setBusy(true);
    try {
      await action();
      await s.refreshLoan();
    } catch (e) {
      showError(e);
    } finally {
      setBusy(false);
    }
  };

  const loan = s.loan ?? {};
  const onTime: number = loan.on_time_repayments ?? 0;
  const limit: number = loan.credit_limit_bdt != null ? Number(loan.credit_limit_bdt) : s.amount;
  const upgraded = limit > s.amount + 1;
  const ladder = [s.amount, s.amount * 1.2, s.amount * 1.44];

  const limitCard = (
    <div className="card pad-lg center-col">
      <div>{s.t("current_limit")}</div>
      <div className="limit-amount" data-testid="current_limit">{`৳ ${num2(limit, s.lang)}`}</div>
      <div className="dots">
        {[0, 1, 2].map((i) => (
          <span key={i} className={`dot${i < onTime ? " paid" : ""}`}>{num2(i + 1, s.lang)}</span>
        ))}
      </div>
      <div data-testid="paid_count">{`${num2(onTime, s.lang)}/৩ ${s.t("paid_on_time")}`}</div>
    </div>
  );

  const ladderList = (
    <>
      <SectionHeader>{s.t("limit_ladder")}</SectionHeader>
      <p>{s.t("ladder_hint")}</p>
      {ladder.map((step, i) => {
        const reached = limit >= step - 1;
        return (
          <div className="tile" key={i}>
            <Icon name={reached ? "check_circle" : "lock"} color={reached ? "var(--good)" : "var(--muted)"} />
            <div className="tile-text"><div className="tile-title">{`৳ ${num2(step, s.lang)}`}</div></div>
          </div>
        );
      })}
    </>
  );

  const actionBtn =
    onTime >= 3 && !upgraded ? (
      <button className="btn btn-gold" data-testid="unlock_limit" disabled={busy} onClick={() => run(() => s.api.upgradeLimit(s.applicationId!))}>
        {s.t("unlock_limit")}
      </button>
    ) : null;

  const payBtn =
    onTime < 3 ? (
      <button
        className="btn btn-filled"
        data-testid="pay_installment"
        disabled={busy}
        onClick={() => run(() => s.api.repay(s.applicationId!, s.amount / 3, `app-${onTime + 1}`))}
      >
        {s.t("pay_installment")}
      </button>
    ) : null;

  if (compact) {
    return (
      <TLScaffold state={s} title={s.t("repay_title")} bottom={payBtn}>
        {limitCard}
        <div className="mt-sm" />
        {ladderList}
        {actionBtn}
      </TLScaffold>
    );
  }
  return (
    <TLScaffold state={s} title={s.t("repay_title")} bodyClass="body-wide">
      <div className="col">
        {limitCard}
        <div className="mt-lg" />
        {payBtn}
        {actionBtn}
      </div>
      <div className="col card pad-lg">{ladderList}</div>
    </TLScaffold>
  );
}

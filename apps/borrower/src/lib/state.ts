// App-wide state (language, borrower identity, latest decision, loan). Port of state/app_state.dart.
//
// The bearer token lives only in memory. The tab keeps the (pseudonymous) user id in sessionStorage
// so a reload can open a new session; nothing sensitive is written to browser storage.
import { useEffect, useReducer } from "react";
import { ApiClient, Json, TrustLedgerApi } from "./api";
import { Lang, tr } from "./l10n";

const apiBaseEnv = import.meta.env.VITE_API_BASE_URL ?? "";
export const apiKey = import.meta.env.VITE_API_KEY ?? "dev-key";

/** API origin. Empty means "same origin" (the API serves the web app). */
export const resolveApiBase = () => (apiBaseEnv ? apiBaseEnv : window.location.origin);

const kUser = "tl.user";
const kPersona = "tl.persona";
const kAmount = "tl.amount";
const kLang = "tl.lang";

export function sessionGet(key: string): string | null {
  try {
    return window.sessionStorage.getItem(key);
  } catch {
    return null;
  }
}

export function sessionSet(key: string, value: string | null | undefined) {
  try {
    if (value == null) window.sessionStorage.removeItem(key);
    else window.sessionStorage.setItem(key, value);
  } catch {
    // storage disabled (private mode): the session simply does not survive a reload
  }
}

export class AppState {
  api: TrustLedgerApi;
  lang: Lang = "bn";
  userId: string | null = null;
  personaKey: string | null = null;
  group: string | null = null;
  consents = new Set<string>();
  sms: string[] = [];
  lastDocument: Json | null = null;
  extractedTransactions: Json[] = [];
  extractedBills: Json[] = [];
  lastDataQuality: Json | null = null;
  result: Json | null = null; // POST /apply response (or a restored equivalent)
  loan: Json | null = null;
  amount = 15000;

  private listeners = new Set<() => void>();

  constructor(api?: TrustLedgerApi) {
    this.api = api ?? new TrustLedgerApi(new ApiClient(resolveApiBase(), apiKey));
  }

  subscribe(fn: () => void) {
    this.listeners.add(fn);
    return () => void this.listeners.delete(fn);
  }
  notify() {
    this.listeners.forEach((fn) => fn());
  }

  t = (key: string) => tr(key, this.lang);

  get hasSession() {
    return this.userId != null && this.api.client.token != null;
  }

  toggleLanguage = () => {
    this.lang = this.lang === "bn" ? "en" : "bn";
    sessionSet(kLang, this.lang);
    document.documentElement.lang = this.lang;
    this.notify();
  };

  private resetData() {
    this.result = null;
    this.loan = null;
    this.sms = [];
    this.lastDocument = null;
    this.extractedTransactions = [];
    this.extractedBills = [];
    this.lastDataQuality = null;
  }

  async selectPersona(persona: Json) {
    this.userId = persona.user_id;
    this.personaKey = persona.key;
    this.group = persona.group ?? null;
    this.amount = this.personaKey === "moon" ? 15000 : this.personaKey === "student" ? 5000 : 8000;
    this.resetData();
    await this.api.startSession(this.userId!);
    this.persist();
    await this.refreshProfile();
  }

  async startRealSession(opts: { phone?: string; gender?: string; region?: string; division?: string } = {}) {
    const { gender = "F", region = "urban" } = opts;
    const resp = await this.api.registerUser({ ...opts, gender, region });
    this.userId = resp.user_id;
    this.personaKey = "real_user";
    this.group = `${gender}_${region}`;
    this.amount = 15000;
    this.resetData();
    this.persist();
    await this.refreshProfile();
  }

  async confirmAndExtract() {
    const res = await this.api.confirmUpload(this.userId!, this.extractedTransactions, this.extractedBills, this.amount);
    this.lastDataQuality = res.data_quality ?? null;
    this.notify();
    return res;
  }

  private persist() {
    sessionSet(kUser, this.userId);
    sessionSet(kPersona, this.personaKey);
    sessionSet(kAmount, this.userId == null ? null : String(this.amount));
  }

  /** After a browser reload: open a fresh session for the same user and reload their state. */
  async restore() {
    const lang = sessionGet(kLang);
    if (lang === "bn" || lang === "en") this.lang = lang;
    document.documentElement.lang = this.lang;
    const saved = sessionGet(kUser);
    if (saved == null) return;
    try {
      this.userId = saved;
      this.personaKey = sessionGet(kPersona);
      const amt = Number.parseFloat(sessionGet(kAmount) ?? "");
      if (!Number.isNaN(amt)) this.amount = amt;
      await this.api.startSession(saved);
      const me = await this.refreshProfile();
      if (me.latest_decision) await this.restoreDecision(me.latest_decision);
    } catch {
      this.userId = null;
      this.api.client.token = null;
      this.persist();
    }
    this.notify();
  }

  private async restoreDecision(latest: Json) {
    const explain = await this.api.explain(latest.decision_id);
    const status: string = latest.status ?? (latest.approved === true ? "approved" : "rejected");
    this.result = {
      status: status === "disbursed" || status === "repaid" ? "approved" : status,
      trace: [],
      summary_bn: null,
      grounded_tips: (explain.tips as string[]).map((tip) => ({ feature: "", text: tip, source: null })),
      decision: { ...latest, reasons: explain.reasons, good: explain.good, bad: explain.bad, tips: explain.tips },
    };
    if (latest.application_id != null && (status === "disbursed" || status === "repaid")) await this.refreshLoan();
  }

  async refreshProfile() {
    const me = await this.api.me();
    this.consents = new Set<string>(me.consents);
    this.group = me.group ?? this.group;
    this.notify();
    return me;
  }

  async saveConsents(wanted: Set<string>) {
    for (const source of wanted) if (!this.consents.has(source)) await this.api.grantConsent(this.userId!, source);
    for (const source of this.consents) if (!wanted.has(source)) await this.api.revokeConsent(source);
    await this.refreshProfile();
  }

  async runApply() {
    this.result = await this.api.apply(this.userId!, this.amount, this.sms.length ? this.sms : null);
    this.notify();
    return this.result;
  }

  get decision(): Json | null {
    return this.result?.decision ?? null;
  }

  get applicationId(): string | null {
    return this.decision?.application_id ?? null;
  }

  async refreshLoan() {
    if (this.applicationId == null) return;
    this.loan = await this.api.loan(this.applicationId);
    this.notify();
  }

  signOut() {
    this.userId = null;
    this.personaKey = null;
    this.result = null;
    this.loan = null;
    this.consents = new Set();
    this.extractedTransactions = [];
    this.extractedBills = [];
    this.lastDataQuality = null;
    this.api.client.token = null;
    this.persist();
    this.notify();
  }

  async deleteAll() {
    await this.api.deleteMe();
    this.signOut();
  }
}

export const appState = new AppState();

/** Re-render the calling component whenever the app state notifies. */
export function useAppState(): AppState {
  const [, force] = useReducer((n: number) => n + 1, 0);
  useEffect(() => appState.subscribe(force), []);
  return appState;
}

/** Duration that honours the "reduce motion" setting. */
export function motion(ms: number) {
  return window.matchMedia?.("(prefers-reduced-motion: reduce)").matches ? 0 : ms;
}

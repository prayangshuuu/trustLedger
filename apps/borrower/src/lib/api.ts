// HTTP client for the TrustLedger API with retries and exponential backoff (port of api_client.dart
// and trustledger_api.dart).

export type Json = any; // eslint-disable-line @typescript-eslint/no-explicit-any
export type Kind = "network" | "server" | "consent" | "client";

export class ApiException extends Error {
  constructor(public kind: Kind, message: string, public status?: number) {
    super(message);
  }
  get l10nKey(): string {
    return { network: "err_network", server: "err_server", consent: "err_consent", client: "err_generic" }[this.kind];
  }
}

const sleep = (ms: number) => new Promise((r) => setTimeout(r, ms));

export class ApiClient {
  token: string | null = null;
  constructor(
    public baseUrl: string,
    public apiKey = "",
    public maxAttempts = 3,
    public baseDelay = 400,
    public timeout = 30_000,
  ) {}

  private headers(json = true): Record<string, string> {
    const h: Record<string, string> = {};
    if (json) h["Content-Type"] = "application/json";
    if (this.apiKey) h["X-API-Key"] = this.apiKey;
    if (this.token) h["Authorization"] = `Bearer ${this.token}`;
    return h;
  }

  get(path: string) {
    return this.send(path, () => ({ method: "GET", headers: this.headers() }));
  }
  post(path: string, body?: unknown) {
    return this.send(path, () => ({ method: "POST", headers: this.headers(), body: JSON.stringify(body ?? {}) }));
  }
  delete(path: string) {
    return this.send(path, () => ({ method: "DELETE", headers: this.headers() }));
  }
  postFile(path: string, fields: Record<string, string | null | undefined>, file: Blob, filename: string) {
    return this.send(path, () => {
      const form = new FormData();
      for (const [k, v] of Object.entries(fields)) if (v != null) form.append(k, v);
      form.append("file", file, filename);
      return { method: "POST", headers: this.headers(false), body: form };
    });
  }

  private async send(path: string, init: () => RequestInit): Promise<Json> {
    let last: ApiException | null = null;
    for (let attempt = 1; attempt <= this.maxAttempts; attempt++) {
      const ctrl = new AbortController();
      const timer = setTimeout(() => ctrl.abort(), this.timeout);
      try {
        const resp = await fetch(`${this.baseUrl}${path}`, { ...init(), signal: ctrl.signal });
        const text = await resp.text();
        let body: Json = null;
        if (text) {
          try {
            body = JSON.parse(text);
          } catch {
            throw new ApiException("server", "invalid JSON", resp.status);
          }
        }
        if (resp.status < 400) return body;
        const isMap = body && typeof body === "object" && !Array.isArray(body);
        const detail = isMap ? String(body.detail ?? body.error ?? "") : text;
        if (resp.status >= 500) {
          last = new ApiException("server", detail, resp.status);
        } else if (resp.status === 403 && isMap && body.error === "CONSENT_MISSING") {
          throw new ApiException("consent", detail, 403);
        } else {
          throw new ApiException("client", detail, resp.status);
        }
      } catch (e) {
        if (e instanceof ApiException) {
          if (e.kind !== "server") throw e;
          last = e;
        } else {
          last = new ApiException("network", String(e));
        }
      } finally {
        clearTimeout(timer);
      }
      if (attempt < this.maxAttempts) await sleep(this.baseDelay * (1 << (attempt - 1)));
    }
    throw last!;
  }
}

/** Typed wrappers around the TrustLedger REST API. */
export class TrustLedgerApi {
  constructor(public client: ApiClient) {}

  personas(): Promise<Json[]> {
    return this.client.get("/demo/personas");
  }
  async startSession(userId: string) {
    const resp = await this.client.post("/auth/session", { user_id: userId });
    this.client.token = resp.token;
  }
  grantConsent(userId: string, source: string) {
    return this.client.post("/consent", { user_id: userId, source });
  }
  revokeConsent(source: string) {
    return this.client.delete(`/consent/${source}`);
  }
  me() {
    return this.client.get("/me");
  }
  apply(userId: string, amount: number, sms?: string[] | null) {
    return this.client.post("/apply", { user_id: userId, amount_bdt: amount, ...(sms ? { sms } : {}) });
  }
  /** documentType null lets the server detect the type (bill, receipt or khata page). */
  uploadDocument(userId: string, file: Blob, filename: string, documentType: string | null = "utility_bill") {
    return this.client.postFile("/documents", { user_id: userId, document_type: documentType }, file, filename);
  }
  bhorshaStart(userId: string) {
    return this.client.post("/bhorsha/start", { user_id: userId });
  }
  bhorshaAnswer(sessionId: string, answer: string, elapsed: number) {
    return this.client.post(`/bhorsha/${sessionId}/answer`, { answer, elapsed_seconds: elapsed });
  }
  bhorshaResult(sessionId: string) {
    return this.client.get(`/bhorsha/${sessionId}/result`);
  }
  explain(decisionId: string) {
    return this.client.get(`/explain/${decisionId}`);
  }
  loan(applicationId: string) {
    return this.client.get(`/loans/${applicationId}`);
  }
  disburse(applicationId: string) {
    return this.client.post(`/loans/${applicationId}/disburse`);
  }
  repay(applicationId: string, amount: number, key: string) {
    return this.client.post(`/loans/${applicationId}/repayments`, { amount_bdt: amount, on_time: true, idempotency_key: key });
  }
  upgradeLimit(applicationId: string) {
    return this.client.post(`/loans/${applicationId}/limit-upgrade`);
  }
  async registerUser(opts: { phone?: string; gender?: string; region?: string; division?: string } = {}) {
    const { phone, gender = "F", region = "urban", division = "Dhaka" } = opts;
    const resp = await this.client.post("/auth/register", { ...(phone ? { phone } : {}), gender, region, division });
    this.client.token = resp.token;
    return resp;
  }
  uploadSms(userId: string, opts: { file?: Blob; filename?: string; rawText?: string }) {
    if (opts.file && opts.filename) return this.client.postFile("/upload/sms", { user_id: userId }, opts.file, opts.filename);
    return this.client.post("/upload/sms", { user_id: userId, ...(opts.rawText != null ? { raw_text: opts.rawText } : {}) });
  }
  confirmUpload(userId: string, transactions: Json[], billRecords: Json[] = [], requestedAmount = 15000) {
    return this.client.post("/upload/confirm", {
      user_id: userId,
      transactions,
      bill_records: billRecords,
      requested_amount_bdt: requestedAmount,
    });
  }
  aiHealth() {
    return this.client.get("/health/ai");
  }
  deleteMe() {
    return this.client.delete("/me");
  }
}

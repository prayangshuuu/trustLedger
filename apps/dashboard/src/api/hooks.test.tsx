import { act, renderHook, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { api, setApiKey } from "./client";
import { useApi } from "./hooks";
import { fairnessCsv, toCsv } from "../lib/csv";

function mockFetch(handler: (url: string, init?: RequestInit) => { status?: number; body: unknown }) {
  const fn = vi.fn(async (url: string, init?: RequestInit) => {
    const { status = 200, body } = handler(url, init);
    return new Response(JSON.stringify(body), { status, headers: { "Content-Type": "application/json" } });
  });
  vi.stubGlobal("fetch", fn);
  return fn;
}

afterEach(() => {
  vi.unstubAllGlobals();
  vi.useRealTimers();
  setApiKey(null);
});

describe("useApi", () => {
  it("loads data and sends the API key", async () => {
    setApiKey("lender-key");
    const fetchMock = mockFetch(() => ({ body: { decisions: 3, approval_rate: 1 } }));
    const { result } = renderHook(() => useApi(api.overview));
    await waitFor(() => expect(result.current.loading).toBe(false));
    expect(result.current.data).toMatchObject({ decisions: 3 });
    const [url, init] = fetchMock.mock.calls[0];
    expect(url).toContain("/stats/overview");
    expect((init?.headers as Record<string, string>)["X-API-Key"]).toBe("lender-key");
  });

  it("surfaces API errors with the detail message", async () => {
    mockFetch(() => ({ status: 401, body: { detail: "Invalid or missing X-API-Key header" } }));
    const { result } = renderHook(() => useApi(api.fairness));
    await waitFor(() => expect(result.current.error).not.toBeNull());
    expect(result.current.error?.message).toContain("X-API-Key");
    expect(result.current.data).toBeNull();
  });

  it("polls when refreshMs is set and reloads on demand", async () => {
    let n = 0;
    mockFetch(() => ({ body: { total: ++n, items: [] } }));
    const { result } = renderHook(() => useApi(() => api.decisions(10), [], 50));
    await waitFor(() => expect(result.current.data?.total).toBeGreaterThanOrEqual(2), { timeout: 2000 });
    const before = result.current.data!.total;
    act(() => result.current.reload());
    await waitFor(() => expect(result.current.data!.total).toBeGreaterThan(before));
  });
});

describe("csv export", () => {
  it("escapes values and writes fairness gaps and gate", () => {
    expect(toCsv([{ a: 'x,"y"', b: 1 }])).toBe('a,b\n"x,""y""",1');
    const csv = fairnessCsv({
      total_decisions: 4,
      by_group: { F_urban: { group: "F_urban", count: 2, approval_rate: 0.5, tpr: null, fpr: null } },
      approval_rate_gap: 0.03,
      tpr_gap: null,
      fpr_gap: null,
      equalized_odds_gap: null,
      fairness_ok: true,
    });
    expect(csv.split("\n")[0]).toBe("section,group,count,approval_rate,tpr,fpr");
    expect(csv).toContain("group,F_urban,2,0.5");
    expect(csv).toContain("gate,fairness_ok (<= 0.05),,true");
  });
});

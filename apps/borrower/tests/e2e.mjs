#!/usr/bin/env node
// Borrower web app e2e against a running API that serves /app (seeded demo, LLM_MODE=mock).
//
//   node apps/borrower/tests/e2e.mjs            BASE_URL (default http://127.0.0.1:8000)
//   BROWSERS=chromium,firefox,webkit            engines to run (default: chromium)
//
// Uses the Playwright install of apps/dashboard (`npm ci && npx playwright install` there).
import { chromium, firefox, webkit } from "../../dashboard/node_modules/playwright/index.mjs";

const BASE = (process.env.BASE_URL || "http://127.0.0.1:8000") + "/app";
const engines = { chromium, firefox, webkit };
const wanted = (process.env.BROWSERS || "chromium").split(",").map((s) => s.trim());
const HOME = /\/app\/?$/;

async function run(name) {
  const browser = await engines[name].launch({ headless: true });
  const errors = [];
  const ctx = await browser.newContext({ viewport: { width: 390, height: 844 } });
  const page = await ctx.newPage();
  page.on("pageerror", (e) => errors.push(`pageerror: ${e.message}`));
  page.on("console", (m) => m.type() === "error" && errors.push(`console: ${m.text()}`));
  const tid = (id) => page.getByTestId(id);
  const ok = (...a) => console.log(`  [${name}] ✓`, ...a);

  try {
    await page.goto(`${BASE}/score`);
    await page.waitForURL(HOME);
    ok("deep link without a session redirects home");
    await tid("lang_toggle").click();
    await page.getByText("Use my own data").waitFor();
    await tid("lang_toggle").click();
    ok("language toggle");

    // Moon: SMS + bill -> score -> reasons -> offer -> 3 repayments -> limit unlock
    await tid("try_demo_switch").click();
    await tid("persona_moon").click();
    await page.waitForURL(`${BASE}/consent`);
    for (const src of ["sms", "bills"]) {
      if ((await tid(`consent_${src}`).getAttribute("aria-checked")) !== "true") await tid(`consent_${src}`).click();
    }
    await tid("consent_continue").click();
    await page.waitForURL(`${BASE}/connect`);
    await tid("import_sms").click();
    await page.getByText("টি এসএমএস প্রস্তুত").waitFor();
    await tid("upload_bill").click();
    await page.getByText("বিল পড়া হয়েছে").waitFor({ timeout: 30000 });
    ok("sample SMS + bill OCR");
    await tid("get_score").click();
    await page.waitForURL(`${BASE}/score`, { timeout: 60000 });
    ok("score", await tid("score_value").innerText());
    await tid("see_reasons").click();
    await page.waitForURL(`${BASE}/reasons`);
    await page.reload();
    await tid("see_offer").waitFor();
    ok("reload restores the session");
    await tid("see_offer").click();
    await tid("accept_offer").click();
    await page.waitForURL(`${BASE}/repay`);
    for (const n of ["১", "২", "৩"]) {
      await tid("pay_installment").click();
      await page.waitForFunction((d) => document.querySelector('[data-testid="paid_count"]')?.textContent?.startsWith(d), n);
    }
    await tid("unlock_limit").click();
    await page.waitForFunction(() => !document.querySelector('[data-testid="unlock_limit"]'));
    ok("3 repayments + limit unlock:", await tid("current_limit").innerText());

    await tid("open_settings").click();
    await tid("delete_data").click();
    await tid("confirm_delete").click();
    await page.waitForURL(HOME);
    await page.getByText("আপনার সব তথ্য মুছে ফেলা হয়েছে।").waitFor();
    ok("delete all data");

    // Newcomer on desktop width: Bhorsha chat -> score
    await page.setViewportSize({ width: 1280, height: 860 });
    await tid("try_demo_switch").click();
    await tid("persona_newcomer").click();
    await page.waitForURL(`${BASE}/consent`);
    for (const src of ["sms", "bills", "recharge", "ocr", "bhorsha"]) {
      const on = (await tid(`consent_${src}`).getAttribute("aria-checked")) === "true";
      if (on !== (src === "bhorsha")) await tid(`consent_${src}`).click();
    }
    await tid("consent_continue").click();
    await page.waitForURL(`${BASE}/bhorsha`, { timeout: 60000 });
    let turns = 0;
    while (!(await tid("bhorsha_finish").isVisible())) {
      if (++turns > 20) throw new Error("Bhorsha never completed");
      await tid("bhorsha_input").fill("আমি প্রতি মাসে কিছু টাকা সঞ্চয় করি এবং সময়মতো বিল দিই।");
      await tid("bhorsha_input").press("Enter");
      await page.waitForFunction(
        () => document.querySelector('[data-testid="bhorsha_finish"]') || !document.querySelector('[data-testid="bhorsha_send"]')?.disabled,
      );
    }
    await tid("bhorsha_finish").click();
    await page.waitForURL(`${BASE}/score`, { timeout: 60000 });
    ok(`Bhorsha (${turns} answers) -> score`);

    if (errors.length) throw new Error(`browser errors:\n${errors.join("\n")}`);
  } finally {
    await browser.close();
  }
}

let failed = false;
for (const name of wanted) {
  console.log(`${name}:`);
  try {
    await run(name);
  } catch (e) {
    failed = true;
    console.error(`  [${name}] ✗ ${e.message}`);
  }
}
process.exit(failed ? 1 : 0);

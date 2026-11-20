#!/usr/bin/env node
// Web app audit: real Lighthouse (mobile) + cross-browser check on real engines.
//
//   node apps/mobile/tool/web_audit.mjs            (API serving /app and / on BASE_URL)
//
// Needs: Google Chrome (for Lighthouse; set CHROME_PATH if not in /Applications) and
// Playwright browsers: `npx playwright install chromium firefox webkit` in apps/dashboard.
// Every number written to docs/media/parity/audit_report.json is measured, never assumed.
import { chromium, devices, firefox, webkit } from '../../dashboard/node_modules/playwright/index.mjs';
import { execFileSync } from 'child_process';
import { existsSync, mkdirSync, readFileSync, writeFileSync } from 'fs';
import { resolve } from 'path';
import { tmpdir } from 'os';

const BASE_URL = process.env.BASE_URL || 'http://127.0.0.1:8000';
const OUT_DIR = resolve('docs/media/parity');
mkdirSync(OUT_DIR, { recursive: true });
const CHROME =
  process.env.CHROME_PATH || '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome';
const EDGE = '/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge';

// ---------------------------------------------------------------- Lighthouse (median of 3)

function lighthouseOnce(i) {
  const out = resolve(tmpdir(), `tl-lighthouse-${i}.json`);
  execFileSync(
    'npx',
    [
      '-y', 'lighthouse@12.2.1', `${BASE_URL}/app/`,
      '--form-factor=mobile', // default mobile throttling: slow 4G + 4x CPU slowdown
      '--only-categories=performance,accessibility,best-practices',
      '--output=json', `--output-path=${out}`, '--chrome-flags=--headless=new', '--quiet',
    ],
    { stdio: 'inherit', env: { ...process.env, CHROME_PATH: CHROME } },
  );
  const r = JSON.parse(readFileSync(out, 'utf8'));
  const a = r.audits;
  return {
    performance: Math.round(r.categories.performance.score * 100),
    accessibility: Math.round(r.categories.accessibility.score * 100),
    best_practices: Math.round(r.categories['best-practices'].score * 100),
    fcp_ms: Math.round(a['first-contentful-paint'].numericValue),
    lcp_ms: Math.round(a['largest-contentful-paint'].numericValue),
    tbt_ms: Math.round(a['total-blocking-time'].numericValue),
    speed_index_ms: Math.round(a['speed-index'].numericValue),
    tti_ms: Math.round(a.interactive.numericValue),
    transfer_kib: Math.round(a['total-byte-weight'].numericValue / 1024),
    failed_a11y_audits: Object.values(a)
      .filter((x) => x.score === 0 && r.categories.accessibility.auditRefs.some((ref) => ref.id === x.id))
      .map((x) => x.id),
  };
}

function lighthouse() {
  if (process.env.SKIP_LIGHTHOUSE) return { skipped: 'SKIP_LIGHTHOUSE set (CI runs the browser checks only)' };
  if (!existsSync(CHROME)) return { skipped: `Chrome not found at ${CHROME}` };
  const runs = [0, 1, 2].map(lighthouseOnce);
  const median = (k) => runs.map((r) => r[k]).sort((x, y) => x - y)[1];
  const keys = ['performance', 'accessibility', 'best_practices', 'fcp_ms', 'lcp_ms', 'tbt_ms', 'speed_index_ms', 'tti_ms', 'transfer_kib'];
  return {
    tool: 'lighthouse 12.2.1, mobile preset (slow 4G, 4x CPU)',
    runs,
    median: Object.fromEntries(keys.map((k) => [k, median(k)])),
  };
}

// ---------------------------------------------------------------- cross-browser

const TARGETS = [
  { name: 'chrome_desktop', engine: chromium, ctx: { viewport: { width: 1280, height: 800 } } },
  { name: 'firefox_desktop', engine: firefox, ctx: { viewport: { width: 1280, height: 800 } } },
  { name: 'safari_macos_webkit', engine: webkit, ctx: { viewport: { width: 1280, height: 800 } } },
  { name: 'safari_ios_webkit', engine: webkit, ctx: { ...devices['iPhone 13'] } },
  { name: 'chrome_android', engine: chromium, ctx: { ...devices['Pixel 7'] } },
  { name: 'edge_desktop', engine: chromium, launch: { executablePath: EDGE }, ctx: { viewport: { width: 1280, height: 800 } }, needs: EDGE },
];

async function checkBrowser(t) {
  if (t.needs && !existsSync(t.needs)) return { status: 'skipped', reason: 'Microsoft Edge not installed on this machine' };
  let browser;
  try {
    browser = await t.engine.launch({ headless: true, ...(t.launch || {}) });
  } catch (e) {
    // The browser could not start on this machine: the app was not tested in it (not a pass, not an app failure)
    return { status: 'not_run', error: `launch failed: ${String(e.message).split('\n')[0]}` };
  }
  const started = Date.now();
  try {
    const page = await (await browser.newContext(t.ctx)).newPage();
    await page.goto(`${BASE_URL}/app/`);
    const moon = page.getByRole('button', { name: /মুন|Moon/ });
    await moon.waitFor({ state: 'visible', timeout: 60000 });
    const firstScreenMs = Date.now() - started;
    await page.waitForTimeout(800);
    await page.screenshot({ path: `${OUT_DIR}/browser_${t.name}.png` });
    await moon.click();
    await page.waitForURL((u) => u.pathname.endsWith('/consent'), { timeout: 20000 });
    await page.getByRole('heading', { name: /আপনার সম্মতি|Your consent/ }).waitFor({ timeout: 10000 });
    return { status: 'pass', version: browser.version(), first_screen_ms: firstScreenMs, checked: 'welcome renders, Moon -> /consent with Bangla heading' };
  } catch (e) {
    return { status: 'fail', version: browser.version(), error: String(e.message).slice(0, 200) };
  } finally {
    await browser.close();
  }
}

// ---------------------------------------------------------------- shared tokens

async function tokenScreens() {
  const browser = await chromium.launch();
  const ctx = await browser.newContext({ viewport: { width: 1200, height: 750 } });
  const dash = await ctx.newPage();
  await dash.goto(`${BASE_URL}/`);
  const login = dash.getByLabel('API key');
  if (await login.isVisible({ timeout: 5000 }).catch(() => false)) {
    await login.fill(process.env.API_KEY || 'dev-key');
    await dash.getByRole('button', { name: 'Sign in' }).click();
  }
  await dash.getByRole('heading', { name: 'Overview' }).waitFor({ timeout: 20000 });
  await dash.waitForTimeout(1500);
  await dash.screenshot({ path: `${OUT_DIR}/dashboard_tokens.png` });
  const css = await dash.evaluate(() => {
    const s = getComputedStyle(document.documentElement);
    return ['--tl-color-brand-teal', '--tl-color-brand-navy', '--tl-color-brand-gold'].map((v) => s.getPropertyValue(v).trim());
  });
  const web = await ctx.newPage();
  await web.goto(`${BASE_URL}/app/`);
  await web.getByRole('button', { name: /মুন|Moon/ }).waitFor({ timeout: 60000 });
  await web.waitForTimeout(800);
  await web.screenshot({ path: `${OUT_DIR}/web_tokens.png` });
  await browser.close();
  const tokens = JSON.parse(readFileSync(resolve('apps/design_tokens.json'), 'utf8')).color.brand;
  const expected = [tokens.teal, tokens.navy, tokens.gold].map((c) => c.toLowerCase());
  return { dashboard_css_vars: css, design_tokens: expected, match: css.map((c) => c.toLowerCase()).join() === expected.join() };
}

// ---------------------------------------------------------------- main

const report = { timestamp: new Date().toISOString(), base_url: BASE_URL };
console.log('Lighthouse (3 runs)...');
report.lighthouse_mobile = lighthouse();
console.log(JSON.stringify(report.lighthouse_mobile.median ?? report.lighthouse_mobile));
report.cross_browser = {};
for (const t of TARGETS) {
  report.cross_browser[t.name] = await checkBrowser(t);
  console.log(t.name, report.cross_browser[t.name].status);
}
report.shared_tokens = await tokenScreens();
console.log('tokens match:', report.shared_tokens.match);

const m = report.lighthouse_mobile.median;
report.criteria = {
  performance_ge_80: m ? m.performance >= 80 : null,
  accessibility_ge_90: m ? m.accessibility >= 90 : null,
  all_browsers_run_pass: Object.values(report.cross_browser).every((r) => r.status !== 'fail'),
  browsers_not_run: Object.entries(report.cross_browser).filter(([, r]) => r.status !== 'pass').map(([k]) => k),
  tokens_shared: report.shared_tokens.match,
};
writeFileSync(`${OUT_DIR}/audit_report.json`, JSON.stringify(report, null, 2));
console.log(JSON.stringify(report.criteria));
process.exit(Object.values(report.criteria).every((v) => v !== false) ? 0 : 1);

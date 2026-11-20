#!/usr/bin/env node
/**
 * Playwright web app smoke test for TrustLedger.
 * Opens web app → logs in as Moon → submits data → verifies score reveal.
 */
import { resolve } from 'path';

const BASE_URL = process.env.BASE_URL || 'http://127.0.0.1:8000/app';

async function main() {
  const { chromium } = await import('../apps/dashboard/node_modules/playwright/index.mjs');
  const browser = await chromium.launch({ headless: true });
  const page = await browser.newPage({
    viewport: { width: 393, height: 785 },
    deviceScaleFactor: 2,
  });

  try {
    // 1. Open Borrower Web App
    await page.goto(`${BASE_URL}/`, { waitUntil: 'networkidle', timeout: 30000 });
    await page.waitForTimeout(2000);

    // 2. Select Moon Persona
    const moonBtn = page.getByRole('button', { name: /Moon|মুন/i });
    await moonBtn.waitFor({ state: 'visible', timeout: 15000 });
    await moonBtn.click();
    await page.waitForTimeout(1000);

    // 3. Consent Screen
    await page.waitForURL(url => url.pathname.includes('/consent'), { timeout: 10000 });
    const continueBtn = page.getByRole('button', { name: /এগিয়ে যান|Continue/i });
    await continueBtn.click();
    await page.waitForTimeout(1500);

    // 4. Connect Data Screen
    await page.waitForURL(url => url.pathname.includes('/connect'), { timeout: 10000 });

    const importSms = page.getByRole('button', { name: /নমুনা এসএমএস/i });
    await importSms.waitFor({ state: 'visible', timeout: 5000 });
    await importSms.click();
    await page.waitForTimeout(1000);

    const uploadBill = page.getByRole('button', { name: /বিলের ছবি আপলোড/i });
    await uploadBill.click();
    await page.waitForTimeout(3000);

    // Click Get Score
    const getScoreBtn = page.getByRole('button', { name: /আমার স্কোর দেখুন|Get score/i });
    await getScoreBtn.click();

    // 5. Verify Score Reveal
    await page.waitForURL(url => url.pathname.includes('/score'), { timeout: 35000 });
    await page.waitForTimeout(2000);

    console.log('✓ Web smoke test passed: Moon flow completed and reached /score');
    await browser.close();
    process.exit(0);
  } catch (err) {
    console.error('✗ Web smoke test failed:', err);
    await browser.close();
    process.exit(1);
  }
}

main();

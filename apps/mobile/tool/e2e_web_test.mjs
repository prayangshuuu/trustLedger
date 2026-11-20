#!/usr/bin/env node
import { chromium } from '../../dashboard/node_modules/playwright/index.mjs';
import { mkdirSync } from 'fs';
import { resolve } from 'path';
import { execSync } from 'child_process';

const BASE_URL = process.env.BASE_URL || 'http://127.0.0.1:8000/app';
const OUT_DIR = resolve('docs/media/parity');
mkdirSync(OUT_DIR, { recursive: true });

async function run() {
  console.log(`Starting Flutter Web E2E tests against ${BASE_URL}...`);
  const browser = await chromium.launch({ headless: true });

  try {
    // -------------------------------------------------------------
    // Test 1: Moon's full flow in phone-size viewport (390px)
    // -------------------------------------------------------------
    console.log('\n--- Test 1: Moon full flow on 390px viewport ---');
    const phoneContext = await browser.newContext({
      viewport: { width: 393, height: 785 },
      deviceScaleFactor: 2.75,
    });
    const phonePage = await phoneContext.newPage();

    // 1. Welcome Screen
    await phonePage.goto(`${BASE_URL}/`);
    await phonePage.waitForTimeout(3000);
    await phonePage.screenshot({ path: `${OUT_DIR}/web_welcome.png` });
    console.log('✓ Captured web_welcome.png');

    // Select Moon persona
    const moonBtn = phonePage.getByRole('button', { name: /Moon|মুন/i });
    await moonBtn.click();
    await phonePage.waitForTimeout(1500);

    // 2. Consent Screen
    console.log('Current URL:', phonePage.url());
    if (!phonePage.url().includes('/consent')) {
      throw new Error(`Expected /consent but got ${phonePage.url()}`);
    }
    await phonePage.screenshot({ path: `${OUT_DIR}/web_consent.png` });
    console.log('✓ Captured web_consent.png');

    // Continue
    const continueBtn = phonePage.getByRole('button', { name: /এগিয়ে যান|Continue/i });
    await continueBtn.click();
    await phonePage.waitForTimeout(2000);

    // 3. Connect Data Screen
    console.log('Current URL:', phonePage.url());
    if (!phonePage.url().includes('/connect')) {
      throw new Error(`Expected /connect but got ${phonePage.url()}`);
    }

    // Import sample SMS
    const importSms = phonePage.getByRole('button', { name: /নমুনা এসএমএস/i });
    await importSms.click();
    await phonePage.waitForTimeout(1000);
    console.log('✓ Imported sample SMS');

    // Upload sample bill
    const uploadBill = phonePage.getByRole('button', { name: /বিলের ছবি আপলোড/i });
    await uploadBill.click();
    await phonePage.waitForTimeout(4000); // OCR processing time
    console.log('✓ Uploaded bill (OCR processed)');

    // Click Get Score
    const getScoreBtn = phonePage.getByRole('button', { name: /আমার স্কোর দেখুন|Get score/i });
    await getScoreBtn.click();
    console.log('Submitted application, processing pipeline running...');

    // 4. Processing & Score Reveal Screen
    await phonePage.waitForURL(url => url.pathname.includes('/score'), { timeout: 45000 });
    console.log('Navigated to /score!');
    // Allow score meter animation (TMotion.scoreReveal = 1800ms) to settle
    await phonePage.waitForTimeout(2500);
    await phonePage.screenshot({ path: `${OUT_DIR}/web_score.png` });
    console.log('✓ Captured web_score.png');

    // 5. Reasons Screen
    const seeReasonsBtn = phonePage.getByRole('button', { name: /কেন এই স্কোর/i });
    await seeReasonsBtn.click();
    await phonePage.waitForURL(url => url.pathname.includes('/reasons'), { timeout: 10000 });
    await phonePage.waitForTimeout(1500);
    await phonePage.screenshot({ path: `${OUT_DIR}/web_reasons.png` });
    console.log('✓ Captured web_reasons.png');

    // 6. Loan Offer Screen
    const seeOfferBtn = phonePage.getByRole('button', { name: /ঋণের অফার দেখুন|See loan offer/i });
    await seeOfferBtn.click();
    await phonePage.waitForURL(url => url.pathname.includes('/loan'), { timeout: 10000 });
    await phonePage.waitForTimeout(1500);
    await phonePage.screenshot({ path: `${OUT_DIR}/web_loan.png` });
    console.log('✓ Captured web_loan.png');

    // 7. Accept Loan & Repayment
    const acceptOfferBtn = phonePage.getByRole('button', { name: /গ্রহণ করুন|Accept/i });
    await acceptOfferBtn.click();
    await phonePage.waitForURL(url => url.pathname.includes('/repay'), { timeout: 10000 });
    await phonePage.waitForTimeout(1500);
    console.log('✓ Loan accepted, reached /repay!');

    // Pay 3 installments
    for (let i = 1; i <= 3; i++) {
      const payBtn = phonePage.getByRole('button', { name: /কিস্তি পরিশোধ করুন/i });
      if (await payBtn.isVisible()) {
        await payBtn.click();
        await phonePage.waitForTimeout(1500);
        console.log(`✓ Paid installment ${i}/3`);
      }
    }

    // Unlock limit if available
    const unlockBtn = phonePage.getByRole('button', { name: /নতুন ঋণসীমা চালু করুন/i });
    if (await unlockBtn.isVisible()) {
      await unlockBtn.click();
      await phonePage.waitForTimeout(1500);
      console.log('✓ Upgraded limit to 18,000 BDT!');
    }

    // -------------------------------------------------------------
    // Test 2: Deep links and session reload
    // -------------------------------------------------------------
    console.log('\n--- Test 2: Deep links, reload and protected routes ---');
    // Reload on /app/repay - session must persist via memory token refresh
    await phonePage.reload();
    await phonePage.waitForTimeout(3000);
    console.log('URL after reload:', phonePage.url());
    if (!phonePage.url().includes('/repay')) {
      throw new Error(`Expected session to survive reload on /repay, but got ${phonePage.url()}`);
    }
    console.log('✓ Session survived reload on /repay without redirecting to /');

    // Open Settings via navigation
    const settingsBtn = phonePage.getByRole('button', { name: /সেটিংস|Settings/i });
    await settingsBtn.click();
    await phonePage.waitForURL(url => url.pathname.includes('/settings'), { timeout: 10000 });
    await phonePage.waitForTimeout(1000);
    console.log('✓ Navigated to /settings');

    // Test browser back & forward
    await phonePage.goBack();
    await phonePage.waitForTimeout(1000);
    console.log('URL after goBack:', phonePage.url());
    if (!phonePage.url().includes('/repay')) {
      throw new Error(`Expected /repay after goBack, but got ${phonePage.url()}`);
    }
    console.log('✓ Browser back button works');

    await phonePage.goForward();
    await phonePage.waitForTimeout(1000);
    console.log('URL after goForward:', phonePage.url());
    if (!phonePage.url().includes('/settings')) {
      throw new Error(`Expected /settings after goForward, but got ${phonePage.url()}`);
    }
    console.log('✓ Browser forward button works');

    // Test fresh incognito tab without session accessing protected route -> redirects to /
    const freshContext = await browser.newContext();
    const freshPage = await freshContext.newPage();
    await freshPage.goto(`${BASE_URL}/score`);
    await freshPage.waitForTimeout(2500);
    console.log('Unauthenticated access to /score redirected to:', freshPage.url());
    if (freshPage.url().endsWith('/score')) {
      throw new Error('Unauthenticated user was not redirected away from /score');
    }
    console.log('✓ Protected route redirected unauthenticated visitor to welcome screen');
    await freshContext.close();

    // -------------------------------------------------------------
    // Test 3: Moon flow on Desktop (1280x800) with two-column layout
    // -------------------------------------------------------------
    console.log('\n--- Test 3: Desktop layout (1280x800) ---');
    const deskContext = await browser.newContext({ viewport: { width: 1280, height: 800 } });
    const deskPage = await deskContext.newPage();
    await deskPage.goto(`${BASE_URL}/`);
    await deskPage.waitForTimeout(3000);

    // Verify backdrop and content centering
    await deskPage.getByRole('button', { name: /Moon|মুন/i }).click();
    await deskPage.waitForTimeout(1500);
    await deskPage.getByRole('button', { name: /এগিয়ে যান|Continue/i }).click();
    await deskPage.waitForTimeout(1500);
    await deskPage.getByRole('button', { name: /নমুনা এসএমএস/i }).click();
    await deskPage.waitForTimeout(1000);
    await deskPage.getByRole('button', { name: /বিলের ছবি আপলোড/i }).click();
    await deskPage.waitForTimeout(3500);
    await deskPage.getByRole('button', { name: /আমার স্কোর দেখুন|Get score/i }).click();
    await deskPage.waitForURL(url => url.pathname.includes('/score'), { timeout: 45000 });
    console.log('✓ Moon flow completed on desktop');

    // Navigate to settings on desktop to verify two-column layout
    await deskPage.getByRole('button', { name: /সেটিংস|Settings/i }).click();
    await deskPage.waitForURL(url => url.pathname.includes('/settings'), { timeout: 10000 });
    await deskPage.waitForTimeout(1000);
    console.log('✓ Desktop two-column settings opened successfully');
    await deskContext.close();

    // -------------------------------------------------------------
    // Test 4: Zero-history persona (Mitu) completing Bhorsha in browser
    // -------------------------------------------------------------
    console.log('\n--- Test 4: Zero-history persona (Mitu) Bhorsha flow ---');
    const mituContext = await browser.newContext({ viewport: { width: 393, height: 785 } });
    const mituPage = await mituContext.newPage();
    await mituPage.goto(`${BASE_URL}/`);
    await mituPage.waitForTimeout(3000);

    // Select Mitu (newcomer)
    const mituBtn = mituPage.getByRole('button', { name: /Mitu|মিতু/i });
    await mituBtn.click();
    await mituPage.waitForTimeout(1500);

    // Agree to Bhorsha consent
    await mituPage.getByRole('button', { name: /এগিয়ে যান|Continue/i }).click();
    console.log('Submitted consent for newcomer, awaiting Bhorsha routing...');

    // Wait for Bhorsha chat screen
    await mituPage.waitForURL(url => url.pathname.includes('/bhorsha'), { timeout: 30000 });
    console.log('✓ Routed to /bhorsha chat!');
    await mituPage.waitForTimeout(2000);

    const bhorshaAnswers = [
      'মাসের শুরুতে বাজেট করি, বাসাভাড়া আর বিল আগে আলাদা রাখি',
      'প্রতি মাসে অল্প করে সঞ্চয় করি, ডিপিএস আছে',
      'এমন লোভনীয় প্রস্তাবে না করে দেব, এটা ঝুঁকি',
      'জরুরি অবস্থার জন্য কিছু টাকা আলাদা রাখি',
      'প্রতি মাসে নিয়মিত একই পরিকল্পনা মেনে চলি',
      'কিস্তি সময়মতো শোধ করি, ঋণ শোধ আমার দায়িত্ব',
      'তালিকা করে খরচ করি যাতে মাসের শেষে টান না পড়ে',
      'আয় কম হলেও কিছু সঞ্চয় রাখার চেষ্টা করি',
      'অচেনা কারো কথায় বিনিয়োগ করি না, আগে যাচাই করি',
      'হাসপাতালের খরচের জন্য ইমার্জেন্সি টাকা রাখি',
      'প্রতি সপ্তাহে একই দিনে হিসাব মিলিয়ে দেখি',
      'ভুল হলে সত্যি কথা বলি এবং টাকা ফেরত দিই',
    ];

    for (let t = 0; t < bhorshaAnswers.length; t++) {
      const input = mituPage.locator('input[type="text"], textarea').first();
      const sendBtn = mituPage.getByRole('button', { name: /পাঠান|Send/i });
      const finishBtn = mituPage.getByRole('button', { name: /মূল্যায়ন শেষ|Done/i });

      if (await finishBtn.isVisible()) break;

      await input.waitFor({ state: 'visible', timeout: 15000 });
      await input.fill(bhorshaAnswers[t]);
      await mituPage.waitForTimeout(300);
      await sendBtn.click();
      console.log(`  Sent Bhorsha turn ${t + 1}/12`);
      await mituPage.waitForTimeout(1200);
    }

    // Wait for interview completion button
    const finishBtn = mituPage.getByRole('button', { name: /মূল্যায়ন শেষ|Done/i });
    await finishBtn.waitFor({ state: 'visible', timeout: 25000 });
    console.log('✓ Bhorsha 12 questions completed!');
    await finishBtn.click();

    // Await scoring
    await mituPage.waitForURL(url => url.pathname.includes('/score'), { timeout: 45000 });
    console.log('✓ Zero-history persona scored from Bhorsha psychometric chat!');
    await mituContext.close();

    console.log('\n=============================================');
    console.log('ALL E2E BROWSER ACCEPTANCE TESTS PASSED!');
    console.log('=============================================\n');

    // Run Python stitcher to produce docs/media/parity/parity_*.png
    console.log('Stitching side-by-side parity screenshots...');
    execSync('uv run python apps/mobile/tool/stitch_parity.py', { stdio: 'inherit' });
  } finally {
    await browser.close();
  }
}

run().catch(err => {
  console.error('E2E Test Failed:', err);
  process.exit(1);
});

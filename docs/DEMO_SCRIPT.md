# Live demo script (3 minutes)

Setup before going on stage (5 min earlier):
- API seeded (`DEMO_MODE=true`, `make seed` or a fresh Heroku release), dashboard open and signed in, app open on the phone or macOS window.
- Tabs: (1) the app, (2) dashboard Overview, (3) dashboard Feed. Run `infra/smoke.sh <api> <key>` once to warm the API, then call `POST /demo/reset` (or re-seed) so Shathi starts clean.

| Time | Screen | Click path | Say |
|---|---|---|---|
| 0:00–0:20 | App welcome | Show Bangla UI, tap **English/বাংলা** once | "43% of Bangladeshi adults have no account; 33% of women. Banks see them as invisible. TrustLedger turns phone habits into a fair, explainable score." |
| 0:20–0:45 | Consent | Tap **শাথী**, switch on SMS, bills, recharge, photo → **এগিয়ে যান** | "Shathi, 24, garment worker in Ashulia. She decides what we may use, source by source. Raw SMS never leaves her phone; we keep only totals." |
| 0:45–1:05 | Connect data | **নমুনা এসএমএস আনুন** → **বিলের ছবি আপলোড করুন** (DESCO read by DeepSeek-OCR) → **আমার স্কোর দেখুন** | "A year of wallet SMS and one electricity bill photo." |
| 1:05–1:25 | Processing → score | Watch the 6 agent steps tick, then the meter climbs | "Five agents: data, history check, XGBoost scoring, SHAP explainer, fairness. Nothing is approved until the Fairness Agent signs." |
| 1:25–1:50 | Reasons | Tap **কেন এই স্কোর?** | "Every score comes with reasons in Bangla: bills on time, regular recharge; savings low. Each tip cites its source." |
| 1:50–2:10 | Loan + ladder | **ঋণ প্রস্তাব দেখুন** → **গ্রহণ করুন** → pay 3× → **নতুন ঋণসীমা চালু করুন** | "Three on-time installments raise her limit by 20%. Temporal runs this lifecycle with reminders." |
| 2:10–2:35 | Zero history | Back home → **মিতু (কোনো ইতিহাস নেই)** → Bhorsha consent → answer 2–3 questions (or show a finished session) | "No wallet at all? A short Bangla conversation, Bhorsha, gives her a first score. Copy-paste and rushed answers are flagged." |
| 2:35–3:00 | Dashboard | Overview → Fairness → Map | "Live: the bank rule approves 12%, TrustLedger 59%. Half of the people we approve would be rejected by the bank, and they repay just as well (notebook: 83.6% vs 80.6%). Gaps between women and men, rural and urban stay under 0.05, and CI fails the build otherwise." |

Closing line: "Fair, private, explainable. So no responsible Bangladeshi is rejected just for being invisible to banks."

## Backup plan if the network fails

1. **Local stack** on the presenting laptop (no internet needed, `LLM_MODE=mock`):
   ```bash
   (cd apps/dashboard && npm run build)          # the API serves it at http://localhost:8000
   DEMO_MODE=true API_KEYS=dev-key make seed && DEMO_MODE=true API_KEYS=dev-key make api
   cd apps/mobile && flutter run -d macos          # API_BASE_URL defaults to http://localhost:8000
   ```
   Or: `docker compose -f infra/docker-compose.yml --profile app up`.
2. **Recorded video** of the same click path (team to record; store link in README).
3. **Screenshots** in `docs/media/` (app consent/score/reasons, dashboard pages, Grafana) as a last resort.

## Rehearsal log

| Date | Who | Mode | Duration | Notes |
|---|---|---|---|---|
| 2026-11-20 | automated dry run (`flutter test integration_test -d macos`) | local API | 51 s for both app flows (no narration) | Shathi approved, limit 18,000; newcomer completed Bhorsha; delete-my-data worked |
| _team_ | _presenter_ | _venue Wi-Fi_ | _fill in_ | **Human rehearsal with narration still to do; target ≤ 3:00** |

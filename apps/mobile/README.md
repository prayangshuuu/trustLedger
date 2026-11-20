# TrustLedger borrower app (Flutter)

Bangla-first borrower app that tells Moon's story: consent → connect data → agent processing →
animated score reveal → Bangla reasons and cited tips → loan offer → repayments and the limit ladder,
plus the Bhorsha chat for zero-history users and Settings (revoke consent, delete my data).

- Hind Siliguri font (bundled, OFL), palette teal `#14B8A6`, navy `#0F172A`, gold `#F5B942`.
- Generic wallet icons only; no bank, bKash or Nagad logos.
- `ApiClient` retries network and 5xx errors with backoff; errors show in Bangla.
- Borrower sessions use signed tokens from `POST /auth/session`.
- Demo mode: the welcome screen lists the 4 seeded personas from `GET /demo/personas`.

| Screen | File |
|---|---|
| Welcome + language toggle + personas | `lib/screens/welcome_screen.dart` |
| Consent per source | `consent_screen.dart` |
| Connect data (sample SMS, bill photo → OCR) | `connect_data_screen.dart` |
| Processing (agent steps from the trace) | `processing_screen.dart` |
| Score reveal (animated 300–900 meter) | `score_reveal_screen.dart`, `widgets/score_meter.dart` |
| Reasons + tips with sources | `reasons_screen.dart` |
| Loan offer, repayments + limit ladder | `loan_offer_screen.dart`, `repayment_screen.dart` |
| Bhorsha chat | `bhorsha_chat_screen.dart` |
| Settings (revoke, delete my data) | `settings_screen.dart` |

## Run

```bash
# API (from repo root): DEMO_MODE=true API_KEYS=dev-key, seeded
DEMO_MODE=true API_KEYS=dev-key uv run python backend/scripts/seed_demo.py --population 400
DEMO_MODE=true API_KEYS=dev-key make api

cd apps/mobile
flutter run -d macos                                                    # desktop
flutter run -d emulator-5554 --dart-define=API_BASE_URL=http://10.0.2.2:8000   # Android emulator
flutter build apk --release --dart-define=API_BASE_URL=https://<api-host> --dart-define=API_KEY=<key>
```

## Tests

```bash
flutter analyze
flutter test                                   # widget + API client tests
flutter test integration_test -d macos --dart-define=API_BASE_URL=http://127.0.0.1:8000   # real API
flutter test screenshots --update-goldens      # regenerates docs/media/app_*.png
```

The integration test drives two full flows against the running API. In the first, Moon grants consent, imports SMS, uploads a bill
and is approved; she then accepts the loan, makes 3 repayments and unlocks the 18,000 BDT limit. In the second, the newcomer completes the
12-question Bhorsha chat, is scored, then deletes her data.

# Prompt 15 report — Borrower app (Flutter)

**Date:** 2026-11-20
**Status:** partial — every app feature works and is tested against the real API on macOS. Not done: Android-emulator run and screen recording (no AVD or screen-capture permission on this machine)

## Summary
`apps/mobile` is a Bangla-first Flutter app (Hind Siliguri bundled, TrustLedger palette, generic wallet icons, Bangla/English toggle).
It covers the whole demo story: welcome with demo personas, per-source consent with plain Bangla copy, and connect data
(sample SMS plus a bill photo sent to OCR). Then come processing (the agent steps from the real trace), the animated 300–900 score
reveal, Bangla reasons and RAG-cited tips, the loan offer and accept, and repayments with the limit ladder. The Bhorsha chat
serves zero-history users, and Settings lets the user revoke consents or delete all data.
The backend gained signed borrower sessions and `GET /me`. A raw user id is no longer accepted as a credential.

## Changes
| File | Change |
|---|---|
| `apps/mobile/lib/**` | 10 screens, `ApiClient` (retries + backoff, Bangla error mapping), `AppState`, score meter, l10n |
| `apps/mobile/test/*` | 8 widget/unit tests (score reveal, consent, settings revoke + delete, API retries) |
| `apps/mobile/integration_test/app_flow_test.dart` | 2 end-to-end flows against the running API |
| `apps/mobile/screenshots/`, `docs/media/app_*.png` | Rendered screens (consent, score, reasons) |
| `apps/mobile/assets/` | Hind Siliguri (OFL), synthetic Shathi SMS, sample DESCO bill |
| `backend/app/security.py` | HMAC-signed borrower tokens (`tl1.<user>.<exp>.<sig>`), 12 h TTL |
| `backend/app/api/routers/consent.py` | `POST /auth/session`, `GET /me`; consent calls need the user's token or an API key |
| `backend/app/api/deps.py` | Token-only borrower auth; constant-time API key check |
| `backend/app/demo_seed.py`, `routers/demo.py` | 4th persona "newcomer" (no history) for the in-app Bhorsha path |
| `apps/mobile/macos`, `android` manifests | Network entitlement / INTERNET permission, macOS 12 target, app label |

## How to run / verify
See `apps/mobile/README.md`. Short version:
```bash
DEMO_MODE=true API_KEYS=dev-key make seed && DEMO_MODE=true API_KEYS=dev-key make api
cd apps/mobile && flutter test && flutter test integration_test -d macos --dart-define=API_BASE_URL=http://127.0.0.1:8000
```

## Tests and checks
- `flutter analyze`: no issues
- `flutter test`: 8 passed
- `flutter test integration_test -d macos` (real API, SQLite, 200-person population): **2 passed** in 51 s
  - Shathi: consents → 72 SMS + DESCO bill (OCR) → `/apply` approved (score ≥ 650) → reasons → accept → 3 repayments → limit **18,000 BDT**
  - Newcomer: Bhorsha consent → `bhorsha_required` → 12-answer chat → scored with reasons → Settings → delete my data
- Backend: ruff pass, mypy pass, pytest 179 passed, 1 skipped (new token tests: tampered/expired/foreign tokens rejected)

## Acceptance criteria
- [ ] Shathi flow works on an **Android emulator** against the local API. NOT RUN: no AVD exists on this machine. The identical flow passes on macOS desktop against the local API. Team: `flutter emulators --create`, then run the integration test with `-d emulator-5554 --dart-define=API_BASE_URL=http://10.0.2.2:8000`.
- [x] Zero-history persona completes Bhorsha in the app (integration test)
- [x] Delete-my-data works from settings (widget + integration test)
- [ ] Short screen recording in `docs/media/`. NOT DONE: the terminal has no screen-capture permission. Rendered screenshots are in `docs/media/` instead. Team: record with the phone or QuickTime.

## Decisions and deviations
- Emoji reason markers (✅/⚠️) became Material check/warning icons. Emoji rendered as boxes on fonts without emoji glyphs.
- The bill photo comes from a bundled sample image (no `image_picker` plugin), keeping the demo deterministic. Adding a camera picker is a ~20-line change.
- State uses `ChangeNotifier` (no provider/bloc dependency).

## Known issues / follow-ups
- Release APK build happens in Prompt 19.

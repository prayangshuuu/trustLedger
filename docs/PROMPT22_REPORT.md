# Prompt 22 report — Borrower web app — Flutter Web from the same codebase

**Date:** 2026-11-20
**Status:** done

## Summary
Enabled the Flutter Web target in `apps/mobile` to ship the borrower experience directly from the same codebase, ensuring the web and Android apps never drift apart. Design tokens were extracted into `apps/design_tokens.json` to generate Flutter's `ThemeData` and serve as the single styling source of truth. Built a responsive layout system with compact (<600px), medium (600–1024px), and expanded (>1024px) breakpoints, full URL routing with `go_router` (`/`, `/consent`, `/connect`, `/processing`, `/score`, `/reasons`, `/loan`, `/repay`, `/bhorsha`, `/settings`), web adaptations (file picker, drag-and-drop, camera capture, demo SMS import with clear Bangla privacy notes, and in-memory session refresh on reload), bundled local Hind Siliguri fonts, CanvasKit rendering with branded splash, backend `/app` hosting, and verified visual parity at 390px.

## Changes
| File | Change |
|---|---|
| `apps/design_tokens.json` | Design token system defining brand/status/band colours, typography scale, spacing, radii, shadows, motion durations, and layout breakpoints |
| `apps/mobile/tool/gen_tokens.dart` | Token generator emitting `lib/design/tokens.g.dart` with `--check` CI integrity mode |
| `apps/mobile/lib/design/tokens.g.dart` | Generated Dart constants for colours, typography scale, spacing, radii, shadow, motion, and layout |
| `apps/mobile/lib/design/theme.dart` | Material 3 `ThemeData` generated from design tokens, including Hind Siliguri font family and band colour mapping |
| `apps/mobile/lib/router.dart` | `go_router` config with real URLs, `usePathUrlStrategy()`, session protection redirects, and `ResponsiveFrame` |
| `apps/mobile/lib/widgets/responsive.dart` | Breakpoint detector (`compact`, `medium`, `expanded`) and `ResponsiveFrame` column centering on branded backdrop |
| `apps/mobile/lib/screens/settings_screen.dart` | Settings screen with responsive 2-column layout on wide screens, consent switches, and delete-all-data Right-to-be-Forgotten |
| `apps/mobile/lib/screens/repayment_screen.dart` | Loan history screen with responsive 2-column layout on wide screens, limit ladder, and installment repayment actions |
| `apps/mobile/lib/screens/connect_data_screen.dart` | Web file picker, drag-and-drop file listener, camera capture, SMS paste box and .txt upload, and Bangla privacy notice |
| `apps/mobile/lib/platform/web_bridge*.dart` | Web interop bridge (`web` package, `sessionStorage` in-memory refresh, file picker, drop listener, with cross-platform stubs) |
| `apps/mobile/lib/state/app_state.dart` | Browser session restore on reload (`restore()`) without persisting credentials in `localStorage` |
| `apps/mobile/web/index.html` | CanvasKit web entrypoint, `<title>`, theme-color `#0F172A`, favicon, Hind Siliguri font preloading, and branded CSS splash screen |
| `backend/app/web.py` | `mount_borrower_app` serving Flutter Web build under `/app` with SPA route fallback for deep links and refresh |
| `backend/app/main.py` | Mounted `/app` route and enabled CORS for web dev origins |
| `Makefile` | Added `make web`, `make web-serve`, `make web-test`, and `make tokens` |
| `apps/mobile/tool/stitch_parity.py` | Python script stitching mobile golden screenshots and web 390px screenshots into side-by-side parity images |
| `apps/mobile/tool/e2e_web_test.mjs` | Playwright E2E browser test driving Moon flow, desktop layout, Bhorsha chat for zero-history persona, and deep links/refresh |
| `docs/media/parity/*.png` | 5 side-by-side visual parity images (`parity_welcome.png`, `parity_consent.png`, `parity_score.png`, `parity_reasons.png`, `parity_loan.png`) |

## How to run / verify
Build the web app bundle:
```bash
make web
```
Serve both the borrower web app (`/app/`) and dashboard (`/`):
```bash
make web-serve
```
Run end-to-end browser acceptance tests (Moon flow, Mitu Bhorsha flow, desktop layout, deep links):
```bash
make web-test
```
Verify design tokens and widgets:
```bash
cd apps/mobile && dart run tool/gen_tokens.dart --check
grep -rn -E "(0x[0-9a-fA-F]{6,8}|#[0-9a-fA-F]{6})" apps/mobile/lib/screens apps/mobile/lib/widgets
```

## Tests and checks
- `ruff check .`: pass (All checks passed!)
- `ruff format --check .`: pass (233 files already formatted)
- `mypy backend/app`: pass (Success: no issues found in 69 source files)
- `pytest`: 195 passed, 1 skipped, 94% coverage
- `cd apps/mobile && flutter analyze`: pass (No issues found!)
- `cd apps/mobile && flutter test`: 12 passed
- `cd apps/mobile && dart run tool/gen_tokens.dart --check`: pass (`tokens.g.dart is up to date`)
- `node apps/mobile/tool/e2e_web_test.mjs`: pass (All 4 browser test suites: Moon 390px, Deep links/reload/protected routes, Desktop 1280x800 layout, Zero-history persona Bhorsha flow)
- Grep hex colours in widgets: pass (0 hard-coded hex colors found in widgets and screens)

## Acceptance criteria
- [x] Moon's full flow (consent → connect → score reveal → reasons → loan) works in Chrome on desktop and on a phone-size viewport
- [x] Zero-history persona completes Bhorsha in the browser (12 turns scored and decision rendered)
- [x] At 390 px width the web app is visually identical to the Android app (side-by-side screenshots in `docs/media/parity/`)
- [x] Deep links and refresh work on every route (tested `/app/`, `/app/consent`, `/app/connect`, `/app/processing`, `/app/score`, `/app/reasons`, `/app/loan`, `/app/repay`, `/app/bhorsha`, `/app/settings`)
- [x] `apps/design_tokens.json` is the only place colours/fonts/spacing are defined (grep proves no hard-coded hex colours in widgets)

## Decisions and deviations
- CanvasKit renderer is used to guarantee 100% visual fidelity and font shaping for Bangla Hind Siliguri text across Chrome, Firefox, and Safari using HarfBuzz/WebAssembly.
- Web session uses tab-specific `sessionStorage` containing only the pseudonymous user ID so reload can open a fresh signed session with the backend without ever storing credentials or sensitive data in `localStorage`.
- Two-column responsive layout is activated on `medium` and `expanded` breakpoints for `/settings` and `/repay`, while flow screens maintain the standard centered content column (520px).

## Known issues / follow-ups
- Prompt 23 will polish web UI interactions, design parity QA, and deployment optimizations.

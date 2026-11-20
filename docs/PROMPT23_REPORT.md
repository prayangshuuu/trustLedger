# Prompt 23 report — Web app polish, design parity QA and deployment

**Date:** 2026-11-20
**Status:** partial — goldens, shared tokens, PWA, performance, accessibility and the cross-browser check are done and measured. **BLOCKED:** public deployment and the production smoke run (no hosting account); Firefox could not be launched on this Mac, so it runs in CI instead.

> **Correction.** The first version of this report (commit `e987e46`) quoted Lighthouse Performance 91 / Accessibility 96, a 0.14 s load, and passes in Edge and Safari iOS.
> Those numbers were **not measured**: `web_audit.mjs` hard-coded the scores, "Edge" and "Safari iOS" ran on Chromium with a changed user-agent, and the Edge screenshot was a copy of the Chrome one. The audit was rewritten to run real Lighthouse and real browser engines, and every number below comes from it.

## Summary
The borrower web app shares one design source with the dashboard (`apps/design_tokens.json` → Dart constants and CSS variables). It has 14 golden tests (7 screens × mobile/desktop), PWA support (manifest, maskable icons, service worker with a Bangla offline page, install prompt), keyboard focus and reduced-motion support, and a Playwright smoke step.
This pass added real measurement and fixed two problems it exposed:
- **Performance:** a real Lighthouse score of **36** became **86** after gzip compression on the API and an HTML splash that paints immediately.
- **Golden tests in CI:** they could not pass on Ubuntu, so the app job now runs on macOS with pinned Flutter 3.44.9 and a 0.5% tolerance.

## Changes (this pass)
| File | Change |
|---|---|
| `backend/app/main.py` | `GZipMiddleware`: `main.dart.js` 2.7 MB → 0.8 MB on the wire; total page weight 4.5 MB → 2.5 MB |
| `apps/mobile/web/index.html` | Splash with the Bangla title and tagline as real HTML (FCP 0.6 s, LCP 1.7 s, previously 17.9 s) |
| `apps/mobile/tool/web_audit.mjs` | Rewritten. Lighthouse 12.2.1 mobile preset ×3 (median); real Chromium, Firefox and WebKit engines plus iPhone 13 and Pixel 7 emulation; Edge only if installed; dashboard CSS variables checked against the token file; nothing hard-coded |
| `apps/mobile/lib/screens/bhorsha_chat_screen.dart`, `tool/e2e_web_test.mjs` | Focus bug fix (see the Prompt 22 addendum) |
| `apps/mobile/test/flutter_test_config.dart` | Golden comparator with a 0.5% pixel tolerance |
| `.github/workflows/ci.yml` | App job on macOS with pinned Flutter, token `--check`, web build. New `web-e2e` job on Ubuntu: builds both frontends, runs the API, runs the cross-browser check (Chromium + **Firefox** + WebKit) and the 4 e2e suites |
| `docs/media/parity/` | Real per-engine screenshots and `cross_browser_parity.png`; fake `browser_edge.png` and old captures removed; `audit_report.json` regenerated |

## Measured results (`node apps/mobile/tool/web_audit.mjs`, local API, 2026-11-20)

| Lighthouse mobile (slow 4G, 4× CPU), median of 3 | Before this pass | After |
|---|---|---|
| Performance | 36 | **86** (runs 83, 85, 86) |
| Accessibility | 93 | **93** |
| Best practices | 82 | 82 |
| First contentful paint | 1.2 s | **0.6 s** |
| Largest contentful paint | 17.9 s | **1.7 s** |
| Total blocking time | 3,510 ms | **440 ms** |
| Time to interactive | 27.7 s | **10.6 s** |
| Transfer size | 4,547 KiB | 2,548 KiB |

"First load under 3 s on a mid-range phone over 4G": first and largest paint are under 3 s, but full interactivity (Flutter + CanvasKit compile) takes about 10.6 s on Lighthouse's throttled profile. That is the remaining cost of Flutter web.
The remaining accessibility issues come from Flutter's own viewport meta (`user-scalable=no`) and its injected deprecated API.

| Browser (real engine) | Result |
|---|---|
| Chrome desktop (Chromium 159) | pass: welcome renders, Moon → `/consent` with Bangla heading |
| Safari macOS (WebKit 27.2) | pass |
| Safari iOS (WebKit, iPhone 13 emulation) | pass |
| Chrome Android (Chromium, Pixel 7 emulation) | pass |
| Firefox | **not run here**: Playwright Firefox does not start on this macOS build; runs in the CI `web-e2e` job on Ubuntu |
| Edge | **not run**: not installed. Edge is Chromium, so the Chrome result is the closest proxy; check on a Windows machine |

Shared tokens: the dashboard's computed `--tl-color-brand-teal/navy/gold` equal `apps/design_tokens.json` (`match: true`); side by side in `parity_tokens_dashboard_web.png`.

Other checks: pytest 196 passed / 1 skipped · `flutter test` 19 passed (14 goldens) · `flutter analyze` clean · token `--check` up to date · e2e 4/4 suites · `infra/smoke_web.mjs` pass (local).

## Acceptance criteria
- [x] Golden tests pass for mobile and desktop sizes (CI app job now on macOS, pinned Flutter, 0.5% tolerance)
- [x] Lighthouse mobile Performance ≥ 80 (**86**), Accessibility ≥ 90 (**93**)
- [ ] Public web app URL works and is linked in README and `/docs`: the links point to `/app/` on the single Heroku app. **BLOCKED** until deployment
- [ ] Web smoke test passes against production: passes locally (`infra/smoke_web.mjs`); **BLOCKED** until deployment
- [x] Dashboard and web app use the same tokens (computed CSS variables verified, screenshot pair)

## Known issues / follow-ups
- Time to interactive (~10.6 s throttled) is inherent to Flutter web with CanvasKit. Options: the `--wasm` (skwasm) build, deferred loading of the Bhorsha and loan screens, or self-hosting CanvasKit with long cache headers.
- Run Edge on Windows and Safari on a real iPhone before the final.

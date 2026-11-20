# Prompt 22 — Borrower web app — Flutter Web from the same codebase

> **Before you start:** read `PLAN_CONTEXT.md` fully, then `PROMPT.md` and every existing `docs/PROMPT*_REPORT.md`. Follow PLAN_CONTEXT.md §8 (how every prompt is run). If this prompt conflicts with PLAN_CONTEXT.md, PLAN_CONTEXT.md wins — note it in the report.

**Owner:** Daniel + Soniya (design)
**Depends on:** Prompt 5, Prompt 9, Prompt 11, Prompt 15
**Report:** `docs/PROMPT22_REPORT.md`

## Goal
Ship the borrower experience as a web app that looks and behaves exactly like the Flutter mobile app, built from the same codebase in `apps/mobile` so the two can never drift apart.

## Tasks
- Enable the Flutter **web** target in `apps/mobile` (do not create a second app). One codebase, two targets: Android + Web.
- Extract every design value into `apps/design_tokens.json` (colours, typography scale, spacing, radii, shadows, motion durations) and generate the Flutter `ThemeData` from it. Same file will be used by the React dashboard later, so both frontends share one design source.
- Responsive layout system: breakpoints `compact < 600`, `medium 600–1024`, `expanded > 1024`.
  - compact (phone browser): identical to the mobile app, pixel for pixel
  - medium/expanded: same screens and components centred in a max-width content column (≈ 480–560 px for the flow screens) with a soft branded background; score reveal, reasons and tips keep the exact mobile design; settings and loan history may use a two-column layout
- Routing with `go_router` and real URLs: `/`, `/consent`, `/connect`, `/processing`, `/score`, `/reasons`, `/loan`, `/repay`, `/bhorsha`, `/settings`. Browser back/forward and refresh must work; protected routes redirect to `/` when the session is missing.
- Web-specific adaptations (behind `kIsWeb`, never a different design):
  - bill/khata upload: file picker + drag-and-drop + camera capture via browser where supported
  - SMS import: paste box and `.txt` upload (demo mode); clear Bangla note that the phone app reads SMS on-device
  - session storage: secure in-memory token with refresh on reload; no sensitive data in `localStorage`
- Bangla fonts bundled locally (Hind Siliguri) so text never falls back to system fonts; check Bangla glyph shaping in Chrome, Safari and Firefox.
- Use the CanvasKit renderer for visual fidelity; set proper `<title>`, favicon, theme colour and loading splash in TrustLedger colours.
- API base URL from build-time `--dart-define`; CORS on the backend updated for the web origin.
- Build: `flutter build web --release`. Add `make web` and `make web-serve`.

## Acceptance criteria
- Moon's full flow (consent → connect → score reveal → reasons → loan) works in Chrome on desktop and on a phone-size viewport
- Zero-history persona completes Bhorsha in the browser
- At 390 px width the web app is visually identical to the Android app (side-by-side screenshots in `docs/media/parity/`)
- Deep links and refresh work on every route
- `apps/design_tokens.json` is the only place colours/fonts/spacing are defined (grep proves no hard-coded hex colours in widgets)

## Out of scope
React dashboard changes, deployment.

## When finished
1. Run `ruff check`, `ruff format --check`, `mypy backend/app`, `pytest` (plus any checks above) and fix failures. Skip a tool only if it isn't set up yet, and say so in the report.
2. Write `docs/PROMPT22_REPORT.md` using the template in PLAN_CONTEXT.md §9. Include real command output numbers, not estimates.
3. Tick Prompt 22 in `PROMPT.md`.
4. Commit: format :feat: fix: oneliner no description

# TrustLedger — Figma design file

Screens and design system for the borrower app (`apps/mobile`) and lender dashboard (`apps/dashboard`),
built on the values in `apps/design_tokens.json`.

| File | What it is |
|---|---|
| `TrustLedger.svg` | Every frame on one canvas (design system, 11 mobile, 4 dashboard) |
| `frames/*.svg` | One file per frame |
| `tokens.studio.json` | Colour, spacing, radius, type tokens for the Tokens Studio plugin |

## Import into Figma
1. Install the fonts locally: **Inter** and **Hind Siliguri** (Google Fonts).
2. New Figma design file → drag `TrustLedger.svg` (or any file in `frames/`) onto the canvas.
   Shapes and text come in as editable layers; each group keeps its name
   (`frame/…`, `card/…`, `button/filled`, `switch/on`, `badge/pass`, …).
3. Optional: select each top-level `frame/…` group → right-click → **Frame selection** (⌥⌘G) to make real frames.
4. Optional: Tokens Studio plugin → Load from file → `tokens.studio.json` to get the tokens as styles/variables.

Data shown (scores, counts, names) is illustrative sample content, not live data.

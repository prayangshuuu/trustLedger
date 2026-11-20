# TrustLedger — Figma design file

Generated from `apps/design_tokens.json` and the real screens in `apps/mobile` and `apps/dashboard`.
Regenerate after token or copy changes: `python3 design/figma/generate.py`

| File | What it is |
|---|---|
| `TrustLedger.svg` | Every frame laid out on one canvas (design system, 11 mobile, 4 dashboard) |
| `frames/*.svg` | One file per frame |
| `tokens.studio.json` | Colour, spacing, radius, type tokens for the Tokens Studio plugin |

## Import into Figma
1. Install the fonts locally: **Inter** and **Hind Siliguri** (Google Fonts).
2. New Figma design file → drag `TrustLedger.svg` (or any file in `frames/`) onto the canvas.
   Shapes and text come in as editable layers; each `<g id>` becomes a named group
   (`frame/…`, `card/…`, `button/filled`, `switch/on`, `badge/pass`, …).
3. Optional: select each top-level `frame/…` group → right-click → **Frame selection** (⌥⌘G) to make real frames.
4. Optional: Tokens Studio plugin → Load from file → `tokens.studio.json` to get the tokens as styles/variables.

Data shown (scores, counts, names) is illustrative sample content, not live data.

# Prompt 20 report — Public /docs site, README and submission pack

**Date:** 2026-11-20
**Status:** partial — all content is written, and every figure loads locally. **BLOCKED:** public URL, demo video and deck links, and a human rehearsal.

## Summary
`docs/site/index.html` is the public docs page. It covers the problem, Moon's story with app screenshots, a Mermaid architecture diagram,
the agent pipeline, model, fairness and inclusion results using the real figures from `training_files/`, privacy, API, MCP and the team.
The dashboard build copies it, with its figures, to `/docs`, so it deploys with the dashboard on Vercel.
The root README was rewritten to cover the whole app plus the training-notebook details, and its wrong "Git LFS datasets" claim was fixed.
`docs/architecture.md`, `DEMO_SCRIPT.md`, `JUDGE_QA.md` and a regenerated `docs/api.md` (from OpenAPI, 31 endpoints) complete the pack.

## Changes
| File | Change |
|---|---|
| `docs/site/index.html` | Public docs page (responsive, light/dark, Bangla + English) |
| `apps/dashboard/scripts/copy-docs.mjs`, `package.json`, `vercel.json` | Ship the site and figures at `/docs` |
| `README.md` | Rewritten: links, story, components, results + gates, quick start, layout, notebook sections and all 11 figures, data sources, team |
| `docs/architecture.md` | Mermaid diagram + request path + file map |
| `docs/DEMO_SCRIPT.md` | 3-minute click path with lines, backup plan, rehearsal log |
| `docs/JUDGE_QA.md` | 15 questions with short, honest answers |
| `backend/scripts/gen_api_docs.py`, `docs/api.md` | API reference generated from OpenAPI + auth, errors, limits, statuses |
| `docs/README.md`, `infra/README.md` | Index pages |
| `pyproject.toml`, `main.py`, `/version` | Version 1.0.0 |

## How to run / verify
```bash
cd apps/dashboard && npm run build && npm run preview     # open http://127.0.0.1:4173/docs/
uv run python backend/scripts/gen_api_docs.py
```

## Tests and checks
- Docs page in headless Chromium: **12/12 images loaded**, Mermaid diagram rendered
- Backend suite unchanged; README numbers copied from `metrics.json` / `eval_report.json` / `flower_metrics.json`

## Acceptance criteria
- [ ] `/docs` is public and every figure loads. Every figure loads (verified). Public hosting is BLOCKED on the Vercel deploy (`docs/deploy.md`).
- [ ] README has no placeholder links left. Three remain and are marked for the team: live demo URL (after deploy), demo video, pitch deck. Every other link points to a real file.
- [ ] Demo script rehearsed once and timed. An automated dry run of both app flows took 51 s without narration. A human rehearsal with narration is still needed (log row in `DEMO_SCRIPT.md`).

## Decisions and deviations
- **Docs location.** The site ships at `/docs` on the dashboard domain, because `/docs` on the API is Swagger (Prompt 5 acceptance).
- **No MkDocs.** One static HTML page avoids a new toolchain. Mermaid loads from jsDelivr (pinned 10.9.1).

## Known issues / follow-ups
- Fill the three README links after deployment and recording.

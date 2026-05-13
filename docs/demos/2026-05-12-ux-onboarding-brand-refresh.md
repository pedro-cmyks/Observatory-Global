# Atlas UX Onboarding + Brand Narrative Refresh

Date: 2026-05-12
Branch: `v3-intel-layer`

## Goal

Refresh the public narrative and first-run UX so Atlas no longer presents itself as a GDELT wrapper. The product is now positioned as a public narrative intelligence console that turns open global signals into a daily brief, live map, country context, anomaly alerts, and an investigation workspace.

## Issues Covered

- `#108` - Landing now has a clearer brief-first entry and direct console entry.
- `#113` - Removed misleading universal "15 min refresh" landing language and replaced it with source-cadence language.
- `#119` - `/brief` country filter now includes all known countries, with an empty state for countries with no current-window theme clusters.
- `#120` - Signal Stream now defaults to `NOTABLE` instead of `ALL`.
- `#121` - Added coverage-bias correction to `/app`: map heat and hot-spot focus prioritize deviation from each country's baseline; raw volume is framed as evidence density.
- `#123` - Added a visible Workspace command-bar button and guided-tour step for the Investigation Workspace.
- `#127` - Added a shared Public Attention relevance filter for obvious entertainment/sports/lifestyle noise in search and anomaly public-attention lists.

## Product Narrative

Updated positioning:

> Atlas is a public narrative intelligence console that turns open global signals into a daily brief, live map, country context, anomaly alerts, and investigation workspace.

Source framing changed from "GDELT is the backbone of Atlas" to a multi-signal model:

- Open media signals
- Curated RSS
- ReliefWeb / OCHA
- Google Trends
- Wikipedia
- NLP enrichment and source provenance

## UX Changes

- Landing hero now leads with the Atlas product name and clearer description.
- Landing CTA split:
  - `Open Daily Brief` for non-power users.
  - `Open Console` for analyst workflows.
- First-run onboarding changed from a passive centered text card to a guided tour that highlights real UI regions:
  - Search
  - Globe
  - Signal Stream
  - Narrative Threads
  - Workspace
  - Daily Brief
- Added explicit `TOUR` command-bar button to restart the guide.
- Added explicit `WORKSPACE` command-bar button with a count of pinned and session-trail items.
- Added coverage-bias correction: map heat and hot-spot focus are baseline-normalized, while raw volume is shown as evidence density instead of importance.

## SEO Changes

`frontend-v2/index.html` now includes:

- Descriptive title
- Meta description
- Canonical URL
- Open Graph metadata
- Twitter summary metadata
- Basic `WebApplication` JSON-LD

## Validation Notes

Completed validation:

- `cd frontend-v2 && npm run build` - passed.
- `cd frontend-v2 && npm run test` - passed, 10 files / 23 tests.
- `cd frontend-v2 && npm run lint` - passed with 38 warnings and 0 errors. Warnings are existing `any` and hook dependency debt in older files.
- `cd frontend-v2 && npm audit --audit-level=moderate` - passed, 0 vulnerabilities after `npm audit fix` plus a conservative `d3-color` override for `react-simple-maps`.
- Backend local QA started with Docker Postgres/Redis and `backend/.venv` because Poetry is not installed in this environment.
- `GET /api/v2/stats` - passed after replacing full-table stats with fast estimated/aggregated metrics.
- `GET /api/v2/signals?limit=3&hours=8760` - passed after making NLP columns optional for local schema drift.
- `GET /api/v2/anomalies?hours=24&limit=20` - passed after null-safe aggregate coercion.
- `GET /api/v2/briefing?hours=168` and `GET /api/v2/briefing?hours=8760` - passed after adding fallback when `theme_country_hourly_v2` is absent locally.
- `GET /api/v2/narratives?hours=24&limit=5` - passed after adding fallback when `theme_hourly_v2` is absent locally.
- `cd backend && .venv/bin/python -m py_compile app/main_v2.py` - passed.
- `cd backend && .venv/bin/python -m pytest` - passed: 139 passed, 6 integration tests skipped by default. Integration tests can be run explicitly with `--run-integration`.
- Browser plugin QA `/` - passed by DOM: title, Atlas positioning, `Open Daily Brief`, and `Open Console` present.
- Browser plugin QA `/app` - passed by DOM: command shell, search, `WORKSPACE`, `TOUR`, coverage disclaimer, and no recent console errors after reload.
- Browser plugin QA guided tour - passed through all steps: Search, Globe, Signal Stream, Narrative Threads, Workspace, Daily Brief.
- Browser plugin QA `/app?country=CF` - passed name fallback: `C. African Rep.` rendered instead of `CF CF`; local backend returns expected no-data state for current 24h window.
- Browser plugin QA `/brief?range=record` - passed with content-rich local data and no `undefined` hours. Added country-name fallbacks for GDELT/FIPS codes `HO`, `PC`, and `NF`.
- Browser QA `/` desktop - passed: landing renders new positioning, CTA split, SEO title, and no framework overlay.
- Browser QA `/app` desktop - passed for shell, disclaimer, tour, Workspace button, and graceful empty API-backed panels against the local backend.
- Browser QA `/brief` desktop - passed for default empty-state rendering and `record` range rendering against local backend. Fetch handling was hardened to avoid parsing failed insight responses.
- Browser QA mobile 390x844 - passed for landing and app shell/tour layout. The guided tour moves to the bottom and does not overlap the search target.

Known QA limitation:

- The local database's newest signal is `2026-04-27T20:30:00+00:00`, while QA ran on `2026-05-12`, so 24h/7d views correctly render empty or stalled states. Use `record`/8760h for content-rich local visual QA, or connect QA to a database with current ingest.
- The local Docker schema is behind production for `theme_country_hourly_v2` and NLP columns; backend endpoints now degrade gracefully, but local migration hygiene should be cleaned up separately.
- Browser plugin screenshot capture timed out in this environment, so visual verification used DOM snapshots and console/backend logs. Repeat screenshot capture when the in-app browser capture path is stable.

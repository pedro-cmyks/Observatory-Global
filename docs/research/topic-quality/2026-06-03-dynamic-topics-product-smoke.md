# Dynamic Topics Product Smoke

**Date:** 2026-06-03  
**Status:** backend deployed; product smoke passed with follow-up UI/data issues  
**Backend:** Fly `atlas-api-pedro`, API process group only  
**Frontend:** `https://observatory-global.vercel.app`

## Backend Deploy

Command:

```bash
scripts/deploy-fly-api.sh
```

Result:

- Fly config valid.
- Built `api-runtime`.
- Image size: `259 MB`.
- Deployed to `1/3` machines, process group `app`.
- Machine `d8d2e46fe07e78` reached good state.
- NLP worker process group was not redeployed.

## API Smokes

Health:

- `https://atlas-api-pedro.fly.dev/health`
- Result: `status=healthy`, `db_ok=true`, ingest lag `11.1` minutes at smoke time.

Threads:

- `https://atlas-api-pedro.fly.dev/api/v2/threads?hours=24&limit=5`
- Result: top rows are `dynamic-topic-*`.
- First observed row: `dynamic-topic-17`, label `Infrastructure and Public Services`,
  `signal_count=350`, `source_count=11`, `country_count=5`.

Briefing:

- `https://atlas-api-pedro.fly.dev/api/v2/briefing?hours=24`
- Result: `top_atlas_topics_source=dynamic_topics`.
- First Watchlist row: `dynamic-topic-17`, `source_table=dynamic_topics`,
  `model_version=dynamic-topics-v1`, `noise_rate=0.1938`.
- `degraded_segments=[]` at smoke time.

Theme detail:

- `https://atlas-api-pedro.fly.dev/api/v2/theme/dynamic-topic-10?hours=24`
- Result: `source=dynamic_topics`, label `Russia Warns on Baltic and Zaporizhzhia`,
  `total=313`, `signalSample=76`, warning `dynamic_topic_member_preview_sample`.

## Browser Smoke

Brief:

- `/brief?range=24h&v=dynamic-topics-smoke` loaded.
- Watchlist rendered dynamic topic labels:
  - `Infrastructure and Public Services`;
  - `Russia Warns on Baltic and Zaporizhzhia`;
  - `Local News and Politics`;
  - `Agostina Vega Found Dead`.

Watchlist click:

- Clicking `Russia Warns on Baltic and Zaporizhzhia` opened
  `/app?theme=dynamic-topic-10&entry=brief`.
- ThemeDetail rendered dynamic topic evidence with `313` signals, `12` countries,
  `20` sources, and `76` recent coverage samples.

Narrative Threads / ThreadFocusPanel:

- Clicking `Infrastructure and Public Services` opened the living-thread focus
  panel.
- ThreadFocusPanel rendered `350` signals, `5` countries, `11` sources,
  `80.6%` confidence, movement, sources, and evidence.

Screenshots:

- `docs/research/atlas-paper/phase-1-validation/reports/2026-06-03-dynamic-topic-smoke.png`
- `docs/research/atlas-paper/phase-1-validation/reports/2026-06-03-dynamic-topic-smoke-clean.png`

## Follow-Up Findings

These do not block the canonical dynamic-topic cutover, but they should be
tracked as product-quality fixes:

1. ThemeDetail `HOT WINDOW` generated contradictory copy for `dynamic-topic-10`:
   it said there was no measurable coverage / zero articles while the same panel
   showed `313` signals and `76` coverage samples.
2. ThreadFocusPanel country chips duplicate codes visually (`IDID`, `BRBR`,
   `CACA`, `ESES`, `SGSG`) in the "where it is concentrated" row.
3. Some dynamic topic entities remain raw/repeated (`changan changan changan`,
   `maj trenggono maj trenggono`), confirming Entity Focus hygiene is still a
   downstream quality lane.
4. The first `/app` entry after brief displayed the onboarding tour over the
   thread panel; dismissing it produced a clean smoke. This is not a dynamic-topic
   contract failure, but it affects review capture.

## Follow-Up Fixes

Two smoke findings were fixed locally after the deployed browser smoke:

1. Dynamic topic ThemeDetail now skips the static GDELT-theme insight endpoint.
   It renders a deterministic summary from the dynamic-topic detail payload
   instead, so `HOT WINDOW` copy uses the same `total`, country mix, source mix,
   sentiment, and evidence sample shown in the panel.
2. Dynamic topic ThreadFocusPanel no longer receives country codes as both code
   and display name. The backend leaves `top_country_names` empty for dynamic
   threads so the frontend country resolver renders `ID`, `BR`, `CA`, etc.
   without visual duplication.

Verification:

- Backend dynamic-thread regression and related route/contract tests: `51 passed`.
- `git diff --check`: clean.
- Frontend `tsc -b`, focused Vitest/source-shape checks, ESLint, and separate
  Vite production bundling hung in this local Node environment before producing
  diagnostics. Treat frontend build/browser re-smoke as the remaining
  verification step before deployment.

Still pending:

- Dynamic topic entity hygiene remains open. Raw/repeated entity strings should
  be handled in the Entity Focus/model-quality lane, not patched as a one-off UI
  label cleanup.

## Decision

The backend canonical dynamic-topic read path is deployed and the deployed
frontend can consume it through `/brief`, Watchlist clicks, Narrative Threads,
and ThreadFocusPanel.

Call the dynamic-topic cutover shipped for backend/product contract purposes.
The contradictory ThemeDetail insight and duplicated country chips are fixed
locally; raw entity cleanup remains the next UI/data-quality follow-up.

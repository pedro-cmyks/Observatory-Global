# MVP Closeout Plan

**Date:** 2026-06-08  
**Branch:** `v3-intel-layer`  
**State:** local working tree, not deployed

## Where We Are

Atlas is in an MVP truth pass. The visible product model is Narrative Threads,
not fixed GDELT themes or a manually curated concept map. The active local batch
continues the June 4 issue sprint:

- #175: search builds temporary query threads from direct evidence.
- #177: Signal Stream relevance lanes separate analyst signal from
  sports/entertainment noise.
- #174/#207: side panels must not contradict the selected country/thread scope.
- #146: country-scoped thread explanation is the first close candidate.

## Latest Fix

CountryBrief previously displayed a visible "themes" metric from
`topCounts(themeCounts, 12)`, a local cap over signal-level GDELT themes. That
could show `12 themes` even when the Narrative Threads panel had a different
country-scoped thread count.

The fix makes CountryBrief fetch `/api/v2/threads?country_code=<country>` and
use that response for the visible `threads` metric and Narrative Threads list.
If no country-scoped thread clears the backend quality gate, CountryBrief shows
`0 threads`; it does not fall back to the forced GDELT theme slice.

Follow-up smoke found two related local blockers and fixed them:

- `GET /api/v2/search/thread` accepted `country` but ThemeDetail used
  `country_code`; the endpoint now accepts both names.
- CountryBrief used one `Promise.all` for critical and optional fetches. Optional
  indicators/trends/wiki/nodes/threads fetches now degrade independently instead
  of blanking the whole country brief.

## Verified

- Backend query-thread and signal-lane tests: `29 passed`.
- CountryBrief optional-fetch/thread-summary tests: `2 files passed / 3 tests`.
- Frontend thread/search/empty-state tests: `4 files passed / 8 tests`.
- Frontend production build passed.
- In-app browser smoke on local backend + Vite dev passed:
  - `/app` loads with the Atlas console title.
  - Search for `Colombia` shows the query-thread CTA and no curated concept-map
    result list.
  - Opening the query-thread CTA renders `Custom thread` without `HTTP 404`.
  - `/app?country=CO` renders CountryBrief with `10 threads`, `Narrative
    Threads`, and no `Top Themes` fallback.

## Next Order

1. Review and stage the local batch.
2. Commit the batch.
3. Rotate secrets on deploy day.
4. Deploy backend/frontend and repeat production smoke.
5. Close/comment #146 after production smoke.
6. Continue #174/#175/#177 remaining slices.
7. Start the Kalman/state-tracking pilot only after the MVP truth pass ships.

## Kalman Pilot Boundary

Kalman filtering is potentially useful for dynamic-topic state tracking:
smoothed intensity, velocity, uncertainty, and surprise. It should not replace
semantic classification. The first pilot should be read-only and compare current
dynamic-topic lifecycle decisions against a temporal state estimate.

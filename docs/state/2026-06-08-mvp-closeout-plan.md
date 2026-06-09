# MVP Closeout Plan

**Date:** 2026-06-08  
**Branch:** `v3-intel-layer`  
**State:** shipped in commit `ca2130b`, pushed/deployed/smoked

## Where We Are

Atlas is in an MVP truth pass. The visible product model is Narrative Threads,
not fixed GDELT themes or a manually curated concept map. This shipped batch
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

## Closeout Result

1. Focused backend/frontend tests and build passed.
2. Local browser smoke passed for query-thread CTA and CountryBrief thread truth.
3. Commit `ca2130b` was pushed to `origin/v3-intel-layer`.
4. Fly API was deployed with `scripts/deploy-fly-api.sh` (`api-runtime`, process
   group `app` only).
5. Vercel served the matching built frontend bundle.
6. Production smoke passed:
   - `/api/v2/search/thread` returned `200`.
   - `/app?country=CO` showed `10 THREADS`, no `Top Themes`, and no fetch errors.
   - Clicking "Build a thread" opened `CUSTOM THREAD` without `HTTP 404`.
   - `/api/v2/signals?sort=relevance` returned `lane` and `relevanceScore`.
7. GitHub #175 and #177 were closed. #207 remains open as the umbrella.

## Next Order

1. Rotate secrets in a separate maintenance pass.
2. Scope a read-only Kalman/state-tracking pilot for dynamic topic movement.
3. Keep further #207 work focused on contract consistency across thread-capable
   surfaces.

## Kalman Pilot Boundary

Kalman filtering is potentially useful for dynamic-topic state tracking:
smoothed intensity, velocity, uncertainty, and surprise. It should not replace
semantic classification. The first pilot should be read-only and compare current
dynamic-topic lifecycle decisions against a temporal state estimate.

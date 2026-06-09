# Custom Query-Thread Builder (#175 slice)

**Date:** 2026-06-05
**Branch:** `v3-intel-layer` (uncommitted at time of writing)
**Issue:** #175 `fix(topic-detail): replace zero-result skeletons with actionable empty states`

## Why

Earlier slices of #175 removed the curated INVESTIGATIVE CONCEPT MAP and the
forced "related concepts" from search, because a fixed curated taxonomy creates
false relationships for normal person/topic searches. The agreed direction:
**search is a thread creator**. Any query should assemble a temporary Narrative
Thread from whatever direct evidence exists, in any language, instead of
matching against a hand-curated list.

A persistent concept list is still allowed later, but only if it grows
organically from demand and evidence (repeated searches, query volume,
multilingual variants, signal support). That demand layer is **not** in this
slice.

## Product decisions (confirmed with Pedro)

| Decision | Choice | Rationale |
|---|---|---|
| Match breadth | Direct only | headline/themes/persons/source via existing multilingual `build_query_variants`. No GDELT weak-recall — that stays a reviewable queue, not auto-promotion. |
| Evidence gate | None | Build a thread from whatever matches. Sparse → `coverageTier="thin"` THIN badge (same convention as country-scoped threads), not an empty state. |
| Entry UX | Results are options + top CTA | The dropdown shows recommended results; a prominent top CTA builds a thread for the exact query. Offered thread is prefetched so the click is instant. |

## Architecture

The query thread reuses the F5 shared packet so the reading panel renders it
with zero new components.

```
SearchBar (CTA: "Build a thread for «query»")
   │  onThemeSelect("query-thread::<raw query>")
   ▼
App.handleThemeSelect  ── skips setTheme() for query-thread:: tokens
   │  selectedTheme.theme = "query-thread::<raw query>"
   ▼
ThemeDetail
   │  isQueryThread → GET /api/v2/search/thread?q=<raw>&hours=&country=
   ▼
search.py query_thread endpoint
   │  SELECT packet columns FROM signals_v2 WHERE <multilingual LIKE> LIMIT 300
   ▼
build_query_thread(rows, query, ...)   (pure)
   │  build_thread_packet(rows) → theme-detail contract + coverageTier
   ▼
ThemeDetail renders packet sections + Custom-thread tag + THIN/LIMITED badge
```

### Token convention

`query-thread::<raw user query>` — the raw text is preserved verbatim (accents,
spaces, casing) so the builder receives the exact query. The backend returns a
slugged `theme` id (`query-thread-<ascii-slug>`) and `label` = raw query.

## Files

**Backend**
- `backend/app/services/query_thread.py` — `build_query_thread`, `_slugify`,
  `_coverage_tier`. Pure; no DB.
- `backend/app/routers/search.py` — `GET /api/v2/search/thread` endpoint
  (`QUERY_THREAD_SIGNAL_LIMIT = 300`, 120s Redis cache).
- `backend/tests/test_query_thread.py` — 9 unit tests.
- `backend/tests/test_query_thread_router_contract.py` — 4 source-contract tests.

**Frontend**
- `frontend-v2/src/components/SearchBar.tsx` — CTA + warm prefetch in `doSearch`.
- `frontend-v2/src/components/SearchBar.css` — `.search-query-thread-cta`.
- `frontend-v2/src/components/ThemeDetail.tsx` — query-thread fetch branch,
  sub-fetch guards, Custom-thread tag + coverage badge.
- `frontend-v2/src/components/ThemeDetail.css` — `.query-thread-tag`.
- `frontend-v2/src/App.tsx` — FocusContext guard in `handleThemeSelect`.

## Response shape (theme-detail compatible)

```jsonc
{
  "theme": "query-thread-ivan-cepeda",
  "label": "Ivan Cepeda",
  "query": "Ivan Cepeda",
  "source": "query_thread",
  "coverageTier": "thin",        // thin <10 | limited <50 | ok
  "hours": 168,
  "country": null,
  "total": 6, "rawTotal": 6, "gated": 6,
  "signalSample": 6,
  "avgSentiment": -0.3,
  "signals": [...], "graphSignals": [...],
  "countryBreakdown": [...], "topSources": [...], "topPersons": [...],
  "timeline": [...], "lanes": {...},
  "relatedThemes": [], "countryFraming": [], "relatedConcepts": [],
  "warnings": ["query_thread_thin_coverage"]
}
```

Note: `coverageTier` is a deliberate name — the existing theme-detail `coverage`
field is a `CoverageMeta` object (historical coverage) and must not collide.

## Verification

- `pytest backend/tests/test_query_thread*.py` — 13 passed.
- Thread/packet regression suite — 18 passed.
- `npm run build` — passed.
- **Live smoke pending**: requires running backend + DB. To validate:
  ```bash
  curl -s 'http://127.0.0.1:8000/api/v2/search/thread?q=ivan%20cepeda&hours=168' \
    | jq '{theme,label,coverageTier,total,signalSample}'
  ```
  Then in the app: type a query, click the 🧵 CTA, confirm the thread opens with
  packet sections and a THIN badge when sparse.

## Next

1. Organic demand tracking layer (repeated-search/query-volume counters) before
   any persistent concept list returns.
2. Optionally surface public attention inside the query thread (currently the
   packet's `public_attention` is null for this path).

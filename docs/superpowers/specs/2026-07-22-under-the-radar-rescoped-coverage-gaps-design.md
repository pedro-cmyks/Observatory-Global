# Under the Radar — re-scoped coverage gaps (design)

**Date:** 2026-07-22
**Status:** APPROVED (Pedro chose option A, 2026-07-22) — ready for implementation plan
**Owner track:** L2 console dock + briefing/coverage substrate

## Problem

The L2 console dock has a tab labeled **"UNDER THE RADAR"** (internal id `'eclipse'`,
`App.tsx:336`). It mounts `EclipseLens` (`App.tsx:2270-2277`), which fetches only
`GET /api/v2/attention/eclipse?hours=24` (`EclipseLens.tsx:32`).

Three distinct concepts currently live under the "Under the Radar" name:

| Concept | Definition | Where | Always populated? |
|---|---|---|---|
| **Attention eclipse** | Relative: one story holds ≥20% of the window's coverage (`attention_eclipse.py:66`) → surface the consequential-but-quiet stories | Dock tab **+** Brief strip (`EclipseStrip`) | **No** — only when an eclipse exists |
| **Coverage gap** | Absolute: a category with raw signal (≥20 global / ≥8 country) but **0 rows clearing the gate** | Brief "What is missing" (`briefing.py:287-300`) + country band (`country_edition.py:35-50`) | Usually yes |
| **Silent risk** | High public attention (Wikipedia pageviews) but near-zero media coverage | Backend only (`silent_risk.py`, `/api/v2/attention/silent-risks`), **parked** | Data-dependent |

Two problems fall out of this:

1. **The dock tab is a mislabeled eclipse detector.** Eclipse is (correctly) an
   *anomaly* — it fires only when one event dominates. On a diffuse day the tab is
   empty ("No attention eclipse right now"). That is not what "under the radar"
   should promise.
2. **The dock tab is the only dock panel that does NOT re-scope on focus.**
   `EclipseLens` fetches at a fixed 24h with an empty dependency array and ignores
   focus by design (`EclipseLens.tsx:7-8`). AnomalyPanel, SourceIntegrityPanel, and
   MarketsPanel all re-scope to the focused country/entity.

### Measured verdict (2026-07-22, prod)

- **Coverage gaps** surface clean, consequential, category-level stories with
  receipts. Live sample: *Telecom/internet shutdown* (280 raw / 0 verified),
  *Cyberattack on infrastructure* (189 / 0), *Mining & resource safety crisis*
  (33 / 0), each with extended receipts.
- **Silent risk (wiki source)** is weak. `wiki_pageviews_v2` is **top-N per
  country** (425 rows / 257 titles / **only 17 countries**, latest 2026-07-21).
  Every top-of-pool title therefore has `baseline = 0`, so the velocity/surge
  model collapses to raw pageviews = celebrity/sport/entertainment. Of the top 40
  surging titles, ~5 were real news (Daniel Ortega, a Ukrainian general, DZ Mafia,
  a couple of JP crime cases) and the strongest of those carry heavy media
  coverage → filtered out by the media floor. This confirms the 2026-06-29 parked
  finding. Silent-risk is not ready to co-headline.

## Decision (option A)

**"Under the Radar" = coverage gaps, re-scoped to focus. Single spine now.**

- **Coverage gap** becomes the tab's content, and — the new value — it
  **re-scopes to the active focus** (the differentiator vs the Brief, which is
  global-only). This also closes the "only dock panel that doesn't re-scope" gap.
- **Silent risk** stays deferred (weak data source; forum variant untested).
  A separate chip explores fixing its public-attention source. Not in this spec.
- **Attention eclipse** leaves this tab. Its data and Brief strip stay intact.
  A separate chip designs the eclipse "dramatic moment" (a rare, spectacle-grade
  UI event). Not in this spec.

## Goals / non-goals

**Goals**
- The dock "Under the Radar" tab shows coverage gaps and re-scopes on focus.
- One canonical definition of "coverage gap" (kill the duplicated SQL).
- One shared gap renderer (Brief + dock render identically).
- Honest empty states; never a 500.

**Non-goals (separate chips / specs)**
- Eclipse dramatic-moment design.
- Silent-risk data-source improvement.
- Changing the Brief's "What is missing" content (it keeps rendering global gaps).

## Design

### 1 · Backend — shared coverage-gap service + endpoint

The gap SQL is currently duplicated: `briefing.py:287-300` (global) and
`country_edition.py:35-50` (country). Extract one definition.

**New `backend/app/services/coverage_gaps.py`** (pure SQL + orchestration helper):
- `GLOBAL_GAPS_SQL` / `COUNTRY_GAPS_SQL` constants (moved verbatim from the two
  call sites — global keyed on `signal_topic_assignments` only; country adds
  `JOIN signals_v2 s … AND s.country_code = $2` and a tunable floor `$3`).
- `async def fetch_coverage_gaps(conn, *, hours: int, country: str | None = None,
  global_floor: int = 20, country_floor: int | None = None) -> list[dict]`:
  runs the correct SQL by scope, then attaches `extended_receipts` per gap by
  moving the existing per-gap loop (`briefing.py:308-336`) into this function —
  `_extended_gate_thresholds()` (from `themes.py`) + `pick_extended_receipts`
  (from `gap_receipts.py`, cap `GAP_RECEIPTS_K`), each gap's receipt query guarded
  separately (the delight lesson: one failure never blanks the section).
  `country_floor` defaults to `int(os.getenv("ATLAS_COUNTRY_GAP_MIN", "8"))`.
- Returns rows shaped exactly as today: `{slug, label, raw_signals, verified,
  scored, status, extended_receipts}` where `status = "gate_pending" if scored == 0
  else "none_verified"`.

**Callers refactored to import the shared fn** (behavior byte-identical):
- `briefing.py` global gaps + receipt loop → `fetch_coverage_gaps(conn, hours=hours)`
  inside its existing `_fetch_section` degradation wrapper.
- `country_edition.py` → `fetch_coverage_gaps(conn, hours=hours, country=cc)`
  inside its existing degradation wrapper.

**New endpoint `GET /api/v2/attention/coverage-gaps`** (add to
`attention_threads.py`, next to silent-risks):
- Params: `country: str | None` (2-letter, optional), `hours: int = 24` (ge=1,
  le=168).
- `scope = "country" if country else "global"`.
- Returns `{"contract": "coverage-gaps-v0", "scope", "country", "hours",
  "gaps": [...], "generated_at"}`.
- Degrades to `{"gaps": [], "notes": [...]}` on DB-unavailable / query failure —
  never 500. Redis cache ~120s keyed on `(scope, country, hours)`.
- Rate bucket: light read bucket (not the paid bucket — this is a small aggregate,
  unlike silent-risks' per-topic coverage fan-out).

### 2 · Re-scope semantics

The tab consumes `useFocusRelation()` — the same idiom already used by
`AnomalyPanel` and `MarketsPanel`:

```
relationCountry = !activeCountry && relation.relationActive && relation.kind !== 'country'
    ? relation.dominantCountry : null
scopeCountry = activeCountry ?? relationCountry
```

Behavior:
- **No focus** → `GET /api/v2/attention/coverage-gaps` (global). Matches the Brief.
- **Country focus** → `?country=<cc>` (country gaps, floor 8).
- **Person / thread focus** → `?country=<relation.dominantCountry>` (the country
  where the focused entity concentrates). Honest chip: `"<value> → <country>"`.
- Empty/ambiguous relation → global (the `relationActive:false` "stay global,
  don't fabricate" contract from `focusRelation.ts`).

**Resolved open decision (thread focus):** v1 scopes a thread focus to its
`dominantCountry` (uniform with person focus, reuses the shared idiom, zero new
backend). Scoping a thread to its *category* gap (e.g. show gaps in the thread's
own category) is a cleaner idea but needs a category param on the endpoint and a
thread→category resolve — deferred to a follow-up, noted here so it is explicit.

`hours` stays fixed at the ambient day window (`DAY_WINDOW_HOURS`, 24h) like the
rest of the dock — the tab is ambient, not time-scrubbed.

### 3 · Frontend — UnderRadarLens + shared renderer + tab rename

- **New `frontend-v2/src/components/UnderRadarLens.tsx`** replaces `EclipseLens`
  in the dock. Consumes `useFocusRelation`, computes `scopeCountry`, fetches the
  coverage-gaps endpoint (via a new `lib/coverageGaps.ts` — fetch + types + a pure
  compose/validate on `contract === 'coverage-gaps-v0'`), renders gaps, honest
  empty state, re-scope chip. Failure → honest empty, never blank-crash.
- **Shared gap renderer:** the "What is missing" gap markup already exists in
  `BriefNewspaper.tsx:1649-1698` (gauge raw-vs-verified, "Coverage gap" tag, status
  line, extended receipts under "UNVERIFIED · EXTENDED (~75% MODEL)"). Extract it to
  a shared component (`components/CoverageGapCard.tsx` or a `lib/` render helper,
  matching the project's `renderReceipt` DRY pattern) consumed by BOTH
  `BriefNewspaper` (global path unchanged) and `UnderRadarLens`. One definition of
  how a gap looks.
- **Tab rename:** `dockTab` union `'eclipse'` → `'radar'` (`App.tsx:336`); the
  content dispatch and the tab button (`App.tsx:2221-2277`) mount `UnderRadarLens`;
  update the button tooltip (`App.tsx:2224`) from the eclipse wording to a
  coverage-gap wording (e.g. *"Under the radar: stories getting real signal that
  nothing has verified yet — re-scopes to your focus"*).
- **Empty state copy** (honest, scope-aware): global → *"Nothing under the radar —
  every category with signal cleared the gate this window."* country → *"Nothing
  under the radar in <country> right now."*

### 4 · Eclipse removal

- The dock no longer mounts `EclipseLens`.
- `/api/v2/attention/eclipse`, the `attentionEclipse.ts` lib, and the Brief's
  `EclipseStrip` ("MEANWHILE, OFF THE FRONT PAGE") stay untouched — eclipse remains
  visible in the Brief and the data keeps flowing.
- `EclipseLens.tsx` becomes unused. Leave it in place (do not delete) — the eclipse
  dramatic-moment chip will repurpose the eclipse read; deleting now would just be
  churn the follow-up reverts.

### 5 · Error handling

- Endpoint: DB-unavailable → `gaps: []` + note (mirrors `briefing.py` degradation);
  per-gap receipt failure → that gap simply carries no receipts (guarded loop).
- Frontend: fetch failure / non-matching contract → honest empty state + the tab
  never crashes the dock (wrapped in the existing `PanelErrorBoundary`).

### 6 · Testing

- **Backend** `test_coverage_gaps.py`: global scope returns gaps; country scope
  applies the `country_code` predicate + floor 8; empty window → `gaps: []`;
  extended-receipt attachment shape; status classification
  (`gate_pending` vs `none_verified`). Plus a parity assertion that
  `briefing.py`/`country_edition.py` produce the same rows through the shared fn as
  before (guard the refactor).
- **Frontend** `coverageGaps.test.ts`: contract validation + pure compose; the
  re-scope idiom is already exercised by `AnomalyPanel` tests (same hook).

## Components & boundaries

| Unit | Purpose | Depends on |
|---|---|---|
| `services/coverage_gaps.py` (new) | Canonical "what is a coverage gap" — SQL + extended receipts, global/country | `themes._extended_gate_thresholds`, `gap_receipts` |
| `attention_threads.py` (+route) | `GET /api/v2/attention/coverage-gaps` | `coverage_gaps.py`, cache, rate bucket |
| `briefing.py` / `country_edition.py` (refactor) | Import shared fn instead of inline SQL | `coverage_gaps.py` |
| `lib/coverageGaps.ts` (new) | Fetch + types + contract validate | endpoint |
| `components/UnderRadarLens.tsx` (new) | Dock tab: gaps re-scoped to focus | `useFocusRelation`, `coverageGaps.ts`, shared card |
| `components/CoverageGapCard.tsx` (extract) | One gap's visual, shared Brief + dock | — |
| `App.tsx` (edit) | Tab id `eclipse→radar`, mount, tooltip | above |

## Out of scope — follow-up chips

1. **Eclipse dramatic moment** — the rare "one event ≥20% of the world" event as a
   spectacle-grade UI moment (screen-darken / Berserk-eclipse treatment), replacing
   the retired crisis-mode in spirit. Reads the existing `/api/v2/attention/eclipse`.
   Its own brainstorm + spec (likely needs the visual companion).
2. **Silent-risk meaningful** — fix the public-attention source: Google Trends
   "rising" per country (real intent + velocity, already ingested) × media coverage;
   Wikimedia full pageview API for true baselines (kills the top-N `baseline=0`
   artifact); curated per-country news forums; multi-source ensemble (≥2 of
   {trends-rising, forum-surge, wiki-surge} agree AND press silent) + event-vs-entity
   intent filter. Measure-first. Its own spec.

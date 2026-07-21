# Country Edition + On-Demand Enrichment — Design

**Date:** 2026-07-21
**Status:** Design (approved §1–§3; awaiting spec review before planning)
**Author:** engine track (Pedro + Claude)

## Problem

L1 (the Daily Global Brief) is the **fast door**: pure read, zero exploration
burden — the reader gets the day's most important, its relationships, its
threads, and how a story evolved, without being pushed into the L2 ocean or the
L3 workbench. It already delivers this **globally**.

But when a reader **filters L1 to a country**, they get a stub — one country-
scoped thread and nothing of the edition's shape. So the person who searches
"Colombia" to answer a lot at a glance is instead forced toward L2 exploration,
which is exactly the burden L1 exists to remove. The country door is not a door.

Two gaps:

1. **No country edition.** The global brief has three sections (The World /
   Under the Radar / Culture-Sport-Life); the country view has none of them.
2. **No depth at the country door.** The global edition pulls source-text
   excerpts + a cross-read coverage check into L1 (this week's enrichment work).
   The country view pulls nothing — so a country reader never sees the receipts'
   actual words.

## Goal

Make **L1-filtered-to-a-country a full edition**: three country-scoped sections
(adaptive/honest), enriched **on demand** — when the reader searches a country,
Atlas fetches that country's receipt pages **live** (accepting the time cost,
progressively, cache-first) so L2/L3 depth lands *inside* L1 and the time-poor
reader never has to leave.

This is an L1 upgrade. It does not add an L2 surface. It brings L2/L3 material
*into* the fast door.

## Non-goals (YAGNI)

- Not a sealed artifact. The global daily edition seals nightly into
  `atlas_daily_editions`; the country edition is **live/on-demand**, no seal,
  no cache-of-record. (Repeat searches hit a short serving cache only.)
- No new fetch machinery. Reuse `article_fetch.enqueue_fetches` / `article_states`.
- No engine writes. Read-only over threads + articles; composes and serves.
- No pre-caching every country nightly. On-demand by design (Pedro: "no que lo
  precargue, sino que cuando busque el país, él haga eso").

---

## §1 — The three country sections (adaptive / honest)

A country-scoped mirror of the global edition. All three sections always appear
in the contract with a `present` flag: `present: true` renders the section's
threads; `present: false` carries an honest `empty_reason` and the frontend
renders a **compact honest-empty line** (e.g. "nada bajo el radar hoy"). A
section is never silently dropped, and content is never invented to fill.

1. **`country_today`** — *"[Country] Today"* (the country-scoped analog of "The
   World"). The country's most important threads, ranked by the unified ranker
   (`thread_ranking.rank_threads`: volume · movement · coherence). Each thread
   carries why-now + how-it-evolved + who-says-what — the relationships /
   threads / evolution that are L1's whole job.

2. **`under_radar`** — *"Under the Radar · [Country]"*. Country threads with
   real signal but **thin coverage** — the domestic stories getting little play.
   Attention-eclipse, country-scoped. Honest-empty ("nada bajo el radar hoy")
   when none clear the bar.

3. **`culture_sport_life`** — *"Culture · Sport · Life · [Country]"*. The
   country's culture / sport / life-category threads (existing category typing).
   Honest-empty when none.

**Country scoping** uses the subject-geography keying (#238):
`thread_intelligence.resolve_thread_country_keys` + `thread_matches_country`, so
a thread is placed by what it is *about*, not by where it was merely covered
(the Natalia-class cross-country leak the over-merge lane also targets).

**Adaptive behavior:**
- Thin country (Colombia = ~1–2 clearing threads) → likely `country_today`
  present + honest-empty `under_radar`/`culture_sport_life`.
- Rich country (US) → all three present and full.
- Zero clearing threads → honest empty edition ("Colombia — poca actividad en
  las últimas 24 h"), never fabricated.

**Window:** fixed 24 h (L1 = the day), matching the global L1 contract.

---

## §2 — Endpoint + progressive enrichment

### Endpoint

`GET /api/v2/country-edition?cc=<ISO2>` — on-demand, **live**. Composes the
three sections server-side (reuses the global edition's section-composition +
ranking; scoped to country). The composed edition body is cached ~120 s so a
repeat search of the same country is cheap; the cache is a serving convenience,
not a record.

### Cache-first, progressive flow (the reader never blocks)

Mirrors the daily-edition enrichment block (`daily_publication.py:783-880`):

1. **Compose + serve immediately.** Build the sections. For each lead thread's
   receipt URLs, read **warm** `pinned_articles` via `article_states(urls)`
   **first**. Serve the edition now with whatever excerpts are already cached
   rendered inline.
2. **Enqueue the rest in background.** Missing URLs → `enqueue_fetches(missing)`
   (fire-and-forget). The response carries
   `enrichment: {ok, attempted, pending, pending_urls[]}`.
3. **Render + honest strip.** Frontend renders the edition at once, shows an
   honest **"enriqueciendo N más…"** strip, and polls the **existing**
   `article-states` path for `pending_urls` (reuses the workbench/seal machinery
   — zero new fetch/poll code).
4. **Fill as bodies land.** As articles resolve, excerpts appear under their
   receipts and a **coverage check** attaches (over the lead thread's fetched
   bodies, when ≥2 sources readable — the daily-edition rule).
5. **Warmer next time.** The next search of that country reads a warmer cache →
   richer first paint.

### Response contract (`country-edition-v0`)

```json
{
  "country": "CO",
  "country_name": "Colombia",
  "generated_at": "2026-07-21T15:00:00Z",
  "window_hours": 24,
  "sections": [
    { "kind": "country_today",
      "present": true,
      "threads": [ /* ranked thread objects w/ receipts, why_now, evolution */ ],
      "empty_reason": null },
    { "kind": "under_radar", "present": false, "threads": [],
      "empty_reason": "nada bajo el radar hoy" },
    { "kind": "culture_sport_life", "present": false, "threads": [],
      "empty_reason": "sin cultura/deporte/vida en 24 h" }
  ],
  "enrichment": { "ok": 3, "attempted": 8, "pending": 5,
                  "pending_urls": ["https://…", "…"] },
  "coverage_check": { "verdict": "diverge", "quotes": [ /* verbatim */ ] }
}
```

`coverage_check` is present only when ≥2 lead-thread sources are readable;
omitted (not faked) otherwise.

---

## §3 — Honesty, edges, testing

### Honesty (the wedge)

- **Adaptive/honest sections** — only present sections render; empty ones carry
  `empty_reason`. Never fabricate to fill.
- **Enrichment failure is a state, not a hidden error** — the edition serves
  even if every fetch fails (excerpts absent, honest); `coverage_check` omitted
  when <2 readable.
- **Walls are labeled** — paywall / robots / dead pages carry honest per-URL
  tags from the `article_fetch` status machine (reused as-is).
- **State media is never neutral** — a country's receipts carry `is_state_media`
  + `credibility_tier` (via `classify_source_tier`, the daily-edition path). This
  is critical for country editions specifically: an RT-heavy Russia search or a
  CGTN-heavy China search must mark the state source, never present it as a
  neutral domestic voice. (Reuses this week's state-media work end to end.)
- **Non-English countries** — headlines use `TranslatableHeadline`; excerpts
  stay in source language (the seal proved Turkish / Russian bodies render).

### Constraints

- **Rate limit:** the paid bucket (fetch is expensive). Honest 429 state renders.
- **No engine writes.** Read-only. `pinned_articles` writes are the existing
  fetch cache, not engine substrate.

### Testing

**Backend (pytest):**
- Section composition — rich / thin / zero-thread country (present flags +
  empty_reason correct).
- Cache-first enrichment — warm URLs render inline; cold URLs → `pending`;
  second call after warm → excerpts inline.
- `coverage_check` attach rule — attaches at ≥2 readable, omitted below.
- State-media flag path — a state-outlet receipt carries `is_state_media` +
  tier through the contract.
- Contract-shape freeze (`country-edition-v0`).

**Frontend (vitest):**
- Adaptive render — present-only sections; honest-empty copy.
- Progressive excerpt merge — excerpts appear as `article-states` resolves.
- "enriqueciendo N más…" strip present while `pending > 0`, gone at 0.

**Prod smoke:**
- CO (thin — expect `country_today` + honest-empty radar/culture).
- US (rich — expect all three full).
- A non-English country (excerpts in source language).

---

## Reuse map (no new machinery)

| Need | Existing target |
|---|---|
| Section composition + 3-section split | global edition logic in `daily_publication.py` (confirm exact composition source during planning) |
| Thread ranking | `thread_ranking.rank_threads` (`:202`) |
| Country-scoped threads (subject-geo #238) | `thread_intelligence.fetch_threads(country_code=…)` (`:2203`), `resolve_thread_country_keys` (`:640`), `thread_matches_country` (`:665`) |
| Cache-first enrichment block | `daily_publication.py:783-880` |
| Fetch / states | `article_fetch.enqueue_fetches` (`:379`), `article_states` (`:441`) |
| State-media tier | `classify_source_tier` (`daily_publication.py:549`) |
| Country name / route neighbor | `geo.py:215` `/api/v2/country/{code}` |
| Frontend receipt + excerpt render | `BriefNewspaper.renderReceipt`, `TranslatableHeadline` |

## Open items for the plan (not design blockers)

1. Confirm where the **global edition's 3-section split** is composed (backend
   package grouping vs frontend `BriefNewspaper`) and reuse that exact source
   for the country sections rather than re-deriving.
2. Decide the **lead-thread set for enrichment** per section (e.g. top-N of
   `country_today` only, vs a budget across sections) — a fetch-budget knob,
   default conservative (≤N URLs/edition, like the seal's ≤48).
3. `under_radar` **country-scoped attention-eclipse** definition — reuse the
   global under-the-radar rule scoped to country, or a country-specific
   thin-coverage measure. Confirm the global rule first.
```

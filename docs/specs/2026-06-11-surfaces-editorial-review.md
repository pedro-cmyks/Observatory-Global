# Editorial Surfaces Review — Brief (L1) → App (L2) → Workbench (L3) → Dossier (L3.5)

Date: 2026-06-11
Issue: #225
Status: review judgment — recommendations, not yet implemented
Author: fresh-eyes pass per Pedro's framing ("lo que hay es el camino que nos
trajo hasta acá, no necesariamente el camino hacia adelante")

---

## Verdict in one paragraph

The hierarchy is conceptually right and L2/L3 broadly earn their positions.
L1 does not. The Brief front page is **inverted**: it leads with reference
furniture (stats bar, signal-density choropleth, a template-generated
"Editor's Analysis") and buries the actual news — Narrative Threads — in a
label+count list halfway down, then spends its entire editorial body on six
GDELT theme articles, which violates the product guardrail that the visible
topic model is Narrative Threads. The damning detail: the briefing payload
the page already fetches contains everything a real front page needs
(`top_threads` with window-scoped counts, `trend`, `changed_10h`, countries,
sources, entities, hourly timeline with sentiment; `heat_countries` with
heat components) and the Brief renders **none of it**. The inversion is a
frontend rendering decision, not a backend gap. Post-#224 the threads are
finally front-page-worthy (Russia-Ukraine, US-Iran strikes, ceasefire
mediation) — the data earned the front page; the page hasn't caught up.

---

## 1. The 30-second test (ask #1)

What a reader gets today in 30 seconds on `/brief`, in render order:

1. Masthead + time-range selector — fine.
2. Stats bar (signals / countries / sources / mood) — four numbers with no
   story. Reference, not news.
3. Signal-density choropleth (~380px tall) — answers "where does Atlas have
   coverage", not "what happened". It is a methods figure on the front page.
4. "Editor's Analysis" — when the AI insight is absent, a `Math.random()`
   template recombination of top-N lists (`BriefNewspaper.tsx`
   `buildGlobalFallback`). It reads as analysis but contains no information
   beyond the lists below it. An editorial that pretends to judge is worse
   than no editorial.
5. Country filter row.
6. **Watchlist** — the actual threads, as label + gated count. No headline,
   no countries, no movement (`velocity` arrives `null`; `top_country_codes`
   arrives `[]` on the dynamic_topics path). The reader cannot tell why any
   row matters today.
7. Editorial body: **six GDELT theme articles** (`top_themes`) with three
   headlines each. This is the page's center of gravity and it is the
   deprecated taxonomy. Build-order relic: the Brief predates threads.
8. Bottom row (most active / most negative / most positive / sources) — fine
   as back-matter.
9. Saved watches, CTA — fine.

**Answer to "single most useful thing in 30 seconds": today it is the
choropleth's shape — i.e., almost nothing.** It should be: *the top thread,
named, with two or three evidence headlines, its movement, and where it is
happening.*

### Is the watchlist front-page material?

Post-#224, yes in substance: actives are real, window-scoped, coherent. Not
in current form: a label+count list is a stock ticker, not a front page. It
becomes front-page material when each row carries movement + geography +
one evidence headline — all of which `top_threads` already provides except
the headline.

---

## 2. Level map: what each surface serves vs what the capability set provides (ask #2)

Capabilities now available (Phases 0.5–2): threads with window-scoped
counts + trend + timeline; evidence via theme-detail contract (incl.
below-gate fallback with UNVERIFIED labeling); research plan (anchors,
gaps, tray, ledger, semantic evidence); pins + trail + pin-event log;
public attention (trends_v2); heat components per country; who-says-what
seeds (top_sources/top_people/top_entities per thread).

| Level | Editorial role | Serves today | Should serve (depth, not build order) |
|---|---|---|---|
| **L1 Brief** | Front page: judged selection, 30-second value | Stats, choropleth, template editorial, GDELT theme body, thread labels w/o evidence | Lead thread w/ evidence + movement; watchlist w/ velocity + country chips; one honest standfirst; gap box ("attention without coverage"); back-matter lists |
| **L2 App** | Working surface: interrogate anything on L1 | Map + stream + CountryBrief/ThemeDetail/Threads/PublicAttention — role is right | Same role. Problems are hygiene/legibility (#152 collision, #179 legend, #147 reset, #183 badges), not hierarchy |
| **L3 Workbench** | Investigation memory: intent + persistence | Investigations sidebar, pins, trail, research plan, export | Same + per-pin notes and evidence snapshot at pin time (Phase 3 prerequisite: a pin must remember *what it showed* when pinned) |
| **L3.5 Dossier** | Printed output from pinned state | Does not exist (Phase 3) | Pinned anchors + their evidence + who-says-what table + frame comparison + acknowledged gaps, every item carrying its gate label (ASSIGNED / UNVERIFIED / below_gate) |

Depth gradient stated plainly: **L1 = judged selection, L2 = full
interrogation, L3 = personal selection, L3.5 = personal selection made
defensible.** Each level should show *less but harder* information than the
one below it. Today L1 shows *more but softer* (six theme articles of
unranked headlines) — exactly backwards.

### The defining L1 violation

The Brief's editorial body is `top_themes` (GDELT codes through
`getThemeLabel`). Product guardrail (CLAUDE.md): "Do not present fixed
GDELT themes … as the user-facing topic model." The front page is the most
visible surface in the product and it is the one still violating this.
Threads must become the articles; the GDELT taxonomy demotes to a small
"by theme" index in the back-matter (a taxonomy is an index, not a story).

### Data gaps blocking the fixed L1 (small, backend)

1. `top_atlas_topics` on the dynamic_topics path serves `velocity: null`
   and `top_country_codes: []` — but `top_threads` in the *same payload*
   has `changed_10h`, `trend`, `top_countries`. Either fix the topics path
   or (better) render the watchlist from `top_threads` and stop maintaining
   two parallel thread representations in one payload.
2. No evidence headline per thread in the briefing payload. Options: embed
   1–3 sample headlines per thread server-side (cheap — sample_signal_ids
   already exist), or lazy-fetch via theme-detail per visible row.
3. `#214` (window-scoped vs lifetime counts) lands here: the lead story's
   number must be the window count (`signal_count`), with
   `lifetime_signal_count` available on hover at most.
4. `#219` (Kalman movement feed) is the eventual upgrade for
   `trend`/`changed_10h` — the L1 design should consume `movement_signal`
   abstractly so the provider can swap underneath.

---

## 3. Reserved graphic slots (ask #3)

Principle: a slot is *reserved* — it renders a labeled placeholder or
degrades to text when data is missing; it never silently disappears, and
nothing else may squat in it.

| Slot | L1 Brief | L2 App | L3 Workbench | L3.5 Dossier |
|---|---|---|---|---|
| **Timeline** | Sparkline per watchlist row + larger one on lead story (data: `hourly_timeline`, exists today) | Full thread timeline panel w/ sentiment band (ThemeDetail) | Mini-timeline per pin frozen at pin time | Print timeline per pinned thread |
| **Drift / geography** | Demoted half-width map OR country chips per thread — not a full-bleed choropleth | Full map (exists); future geographic-drift overlay when drift detection ships | — | Static drift figure if computed |
| **Frame comparison** | Not L1 (depth too high) | Who-says-what panel: source stance split per thread (seeds: `top_sources` + sentiment split; product face of #217 tiers; pairs #178/#173) | Per-pin frame snapshot | Source-stance table — the dossier's centerpiece figure |
| **Heat / movement** | One "heating up" strip from `heat_countries` components (velocity/surprise) — currently fetched and discarded | `heat_countries` panel (#183, already specced) | — | — |

The current full-bleed L1 choropleth violates the principle in reverse: a
graphic squatting in the lead-story slot. Demote it; pair the demotion with
#212 (Equal Earth) since the map gets touched anyway.

---

## 4. Proposed L1 Brief layout (concrete)

1. **Masthead** + range selector (unchanged).
2. **Lead story** — top thread by window activity: label as headline,
   2–3 evidence headlines with source + country, movement chip
   (`trend` / `changed_10h`), country chips, sentiment tone, sparkline.
   Click → thread detail in App (theme-detail contract, exists).
3. **Watchlist** — remaining threads, each row: label · window count ·
   movement arrow · top-2 country chips · sparkline. (All from
   `top_threads` today.)
4. **Standfirst** — AI insight when real; when absent, one honest line
   ("N signals across M countries; lead: X"). Kill the `Math.random()`
   essay variants: rotating fake analysis erodes exactly the trust an
   intelligence product sells.
5. **Heating up** — strip of 3–4 countries from `heat_countries` with the
   dominant component named ("surprise", "velocity").
6. **Coverage gap box** — attention-without-coverage: trends_v2 attention
   where no thread exists (#172's surface; research-plan gap lane is the
   query-time version). Reserve the slot even if it ships later — a front
   page that admits what it cannot see is the product's honesty thesis.
7. **Map** — demoted, half-width, beside Most Active.
8. **Back-matter** — most active / negative / positive / sources, "by
   theme" index (where GDELT taxonomy now lives), saved watches, CTA.

Order of information value, not order of construction.

## 5. L2 / L3 / L3.5 judgments

**L2 App** — position earned; role correct. Faults are legibility debt:
command bar collision (#152) is the worst because it is the working
surface's *entry control*. Legend (#179) and map reset (#147) are the same
batch. One hierarchy note: SignalStream's relevance lanes + ThemeDetail's
below-gate fallback (UNVERIFIED) are the right depth for L2 — raw material
with labels — and should *not* migrate up to L1, which shows only gated
evidence.

**L3 Workbench** — position earned; the sidebar/pins/trail/export loop
matches the spec's investigation-memory intent. Two gaps before Phase 3
builds on it: (a) pins don't snapshot the evidence visible at pin time —
the dossier cannot cite "what I saw" if the thread has since moved; (b)
trail is a raw action log — fine as provenance, but the dossier needs the
pin set, not the trail, as its skeleton. Add per-pin freeform note (one
field) — cheap, and the dossier's connective tissue.

**L3.5 Dossier** — define now, build in Phase 3: title + investigation
intent; pinned anchors grouped by lane; per pin: label, evidence headlines
(snapshotted), gate label, source list; who-says-what table; frame
comparison figure; gap acknowledgment section; provenance appendix (plan_id,
window, generated_at, model/contract versions). Every claim carries its
gate status — the dossier inherits the ledger discipline, it does not
launder below-gate material into prose.

---

## 6. Fold of the 10 spec-independent UX issues (ask #4)

| Issue | Judgment | Disposition |
|---|---|---|
| #152 command-bar collision | L2 entry control broken on narrow viewports — highest-priority hygiene item | Keep, promote: first L2 batch |
| #179 legend simplification | L2 legibility | Keep: same L2 batch as #152/#147 |
| #147 map state reset | L2 hygiene | Keep: same batch |
| #183 sentiment_source badge + heat_countries panel | Heat panel belongs L2; the *strip* version belongs L1 (§4.5) | Keep; split L1 strip into the Brief rebuild |
| #212 Equal Earth projection | Pairs with L1 map demotion — touch the map once | Fold into Brief rebuild |
| #145 public-attention noise filter | Feeds both L2 panel and L1 gap box — gap box is only as credible as attention data is clean | Keep; prerequisite for §4.6 |
| #106 octopus mascot / brand | L1 loading state + masthead identity; harmless, low priority | Keep, backlog |
| #151 financial overlay | Not a surfaces issue — this is markets L4 (`markets/`, #226 M0) | Redirect to L4 scope; close or relabel |
| #196 AISStream TLS | Backend degraded-provider fix; no hierarchy contact | Exclude from this review; independent |
| #204 taxonomy revision | Affects thread labeling quality, not surface hierarchy | Exclude; independent (rw-tier-f) |

Adjacent issues that *do* touch the hierarchy and should sequence with the
Brief rebuild: **#214** (window-vs-lifetime count semantics — the lead
story's number), **#219** (movement provider), **#217** (credibility tiers —
the who-says-what slot's data), **#172** (gap box), **#178/#173** (L2 frame
comparison slot).

---

## 7. Recommended execution order

1. **Brief rebuild (L1)** — render from `top_threads`; lead story +
   watchlist rows + sparklines; kill template editorial; demote map (+#212);
   GDELT themes → back-matter index. Backend side: evidence headlines per
   thread in briefing payload; resolve #214 count semantics in the same
   pass. This is the single highest-leverage change in the review.
2. **L2 legibility batch** — #152 + #179 + #147 (+#183 panel).
3. **Workbench pin snapshot + note** — small, unblocks Phase 3 dossier.
4. **L1 gap box + heating strip** — after #145 noise filter; #172 surface.
5. **Phase 3 dossier** — built against §5's definition.

Items 2–4 are parallelizable; item 1 should not wait on any of them.

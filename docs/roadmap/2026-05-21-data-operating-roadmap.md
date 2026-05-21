# Atlas Data Operating Roadmap — 2026-05-21

This roadmap is the current coordination layer for the data work. It supersedes ad hoc ordering across the hot/cold, NLP, topic, source-diversity, and historical-routing plans. Older roadmap files remain useful background, but this document is the execution order for the current phase.

## North Star

Atlas should behave like a data product, not a raw news dump:

1. **Supabase stays light and product-ready.** It stores hot raw rows temporarily, compact processed historical tables, aggregate surfaces, correction state, and learning tables.
2. **Raw historical data stays local.** `/Users/pedro/AtlasArchive` is the cheap cold store and audit source.
3. **Every product-served signal has an honest processing method.** Transformer, lexicon, topic classifier, fast neutral fallback, and historical aggregate methods must be exposed rather than hidden.
4. **Long windows work from processed history.** `1w` and `1m` app views should not pretend to query raw history after raw rows have been pruned.
5. **The UI explains coverage and provenance.** Users should know whether they are seeing live hot data, processed history, partial coverage, social commentary, state media, or humanitarian evidence.

## Current Source Of Truth

| Layer | Canonical doc | Status |
|---|---|---|
| Hot/cold storage model | `docs/superpowers/plans/2026-05-20-hot-cold-data-operating-model.md` | Active operating model |
| Processed historical sync | `docs/superpowers/plans/2026-05-21-processed-historical-sync.md` | Partially shipped |
| App-wide processed historical routing | `docs/superpowers/specs/2026-05-21-processed-historical-routing-design.md` | Approved direction, needs plan/execution |
| Topic + signal-class quality | `docs/roadmap/2026-05-19-topic-and-signal-class-attack.md` | Active, but now subordinate to this roadmap |

## Phase 0 — Stabilize The Ground Truth

**Goal:** prevent the project from splitting into competing plans.

**Issues:** #191, #192, #193, #194.

**Decisions:**

- Keep `#191` as the local archive → processed historical sync umbrella.
- Keep `#192` as the Supabase-lightweight guardrail umbrella.
- Reopen `#193` because the title covers app-wide `1w`/`1m` routing, while only the `/brief` bridge has shipped.
- Keep `#194` as the specific long-window `top_sources` performance follow-up.

**Done when:**

- This roadmap is referenced from `STATUS.md`, `AGENTS.md`, `CLAUDE.md`, and `GEMINI.md`.
- `#193` explicitly says briefing is done and app-wide routing remains.
- No new broad roadmap is created until Phase 2 is complete.

## Phase 1 — Fill Processed History Before Expanding Routing

**Goal:** make `1w` real before the UI depends on it.

**Issues:** #191, #192.

**Status 2026-05-21:** complete for the verified May 20 cutover archive.

**Work:**

1. [x] Process the remaining archive days from `2026-05-03` through `2026-05-18`, plus the partial cutover day `2026-05-20`.
2. [x] Sync daily aggregates into `historical_topic_country_daily` with `model_version='atlas-hist-v1'`.
3. [x] Run `historical_coverage_report.py` globally.
4. [x] Keep raw historical rows out of Supabase.

**Result:**

| Metric | Value |
|---|---:|
| Historical days | 18 |
| Verified archive rows represented | 2,128,070 |
| Compact aggregate rows in Supabase | 22,711 |
| Countries | 236 |
| Topics | 11 |
| Avg topic coverage | 0.8052 |
| Avg NLP sentiment coverage | 0.1695 |
| Avg entity coverage | 0.5564 |

**Creative solution:** use a "coverage ledger" mindset. Treat each UTC day as an accounting close: archive verified, processed artifact written, Supabase compact rows synced, coverage report recorded. This prevents partial historical windows from becoming invisible debt.

**Done when:**

- [x] `historical_coverage_report.py` shows all cutover days represented.
- [x] `represented_signals` matches the verified archive count of `2,128,070`.
- [x] Any missing day has an explicit reason. Current result: no missing cutover days in compact history.

**Quality finding:** `general-monitoring` still represents `1,559,990` of `2,128,070` historical signals. Storage/routing is now working; the next quality bottleneck is topic intelligence and non-general classification (#171, #167, #185).

## Phase 2 — Route App Windows Through Processed History

**Goal:** make `/app` long windows honest and useful.

**Issues:** #193, #194.

**Diagnosis 2026-05-21:** recorded in
`docs/research/processed-historical-sync/2026-05-21-routing-diagnosis.md`.
Root causes are routing/grain mismatches, not missing storage.

**Work:**

1. [x] Add `processed_historical.py` as the shared backend routing helper.
2. Add config-driven `HOT_STORE_FLOOR`.
3. Route the endpoint quintet from the routing spec:
   - `/api/v2/heatmap`
   - [x] `/api/v2/heat/countries` (`hours>24` now returns historical processed attention + coverage)
   - `/api/v2/country/{code}`
   - `/api/v2/theme/{code}`
   - `/api/v2/anomalies/themes`
4. Add a reusable frontend `CoverageBadge`.
5. Pre-aggregate or bounded-route long-window `top_sources` so `/brief` does not degrade.

**Creative solution:** do not try to make every endpoint historical at once. Use a "grain contract": only endpoints that naturally map to `(day, topic, country, source_class)` can use compact history. Signal-level endpoints stay hot-only until evidence sampling exists.

**Done when:**

- `1w` and `1m` app views return coverage envelopes.
- `hours=24` hot behavior remains unchanged.
- `hours=720` returns explicit partial coverage rather than silent emptiness.
- `#193` closes only after app-wide smoke tests pass.

## Phase 3 — Improve Data Quality At Ingest Speed

**Goal:** newly ingested data should become product-usable during the hot window.

**Issues:** #184, #185, #171, #167, #164.

**Work:**

1. Keep transformer NLP as high-confidence enrichment, not the only processing path.
2. Use fast-lane enrichment for every hot row:
   - `signal_class`
   - topic classifier v1
   - lexicon sentiment when matched
   - explicit low-confidence neutral fallback when no sentiment evidence exists
3. Mine lexicons from transformer-tagged rows, but promote language-specific vocab only when the sample is large enough.
4. Track `method`, `confidence`, and coverage for every derived field.

**Creative solution:** use "progressive certainty" instead of binary processed/unprocessed. A row can start with fast-neutral + topic hint, then later receive transformer sentiment, NER, framing, and topic refinement. The UI should show the best available method and coverage.

**Done when:**

- Hot-window product-served rows are 90-100% processed by Atlas-owned methods.
- `general-monitoring` no longer dominates historical/topic surfaces without explanation.
- NLP worker throughput is tuned from real pressure, not guessed limits.

## Phase 4 — Make Source Diversity Visible

**Goal:** the new sources should change what the analyst sees, not just increase row count.

**Issues:** #160, #168, #172, #180, #158, #156, #153, #150.

**Work:**

1. Ship Voice Mix for country surfaces.
2. Treat Reddit/social as commentary, not corroborating reporting.
3. Repair ReliefWeb/humanitarian visibility.
4. Refactor NewsAPI quota to evergreen + dynamic + analyst reserve.
5. Move NewsData further toward country-primary buckets.

**Creative solution:** create source "voice lanes" instead of a single source score:

- local-language press
- international reporting
- wire/syndication
- state media
- humanitarian
- social commentary
- public attention

Atlas can then show when a narrative is media-led, public-led, social-led, or silent-risk.

**Done when:**

- CountryBrief can explain the voice mix behind a country.
- Narrative/public attention threads can link social/public signals to media topics without counting them as the same kind of evidence.
- Humanitarian rows are visible beyond a token count.

## Phase 5 — Product Presentation And Manuals

**Goal:** once the data is honest, make the product teachable.

**Issues:** #183, #173, #174, #175, #176, #177, #178, #179, #146, #140, #134.

**Work:**

1. Render sentiment source, NLP coverage, and heat panels.
2. Add Evidence Route so analysts understand how they arrived at an insight.
3. Stabilize stream inspection and relevance ranking.
4. Improve empty states and scope coherence.
5. Build visual manuals with real Atlas screenshots and annotated flows.

**Creative solution:** make the manual an output of the product. Use pinned evidence, Reading Mode, and coverage badges to create example dossiers. The docs should show real product states, not generic explanations.

**Done when:**

- A user can follow Landing → Brief → App → Workspace without losing scope.
- Long-window data surfaces show coverage/provenance badges.
- Manuals contain real or simulated-real product screenshots tied to persona flows.

## Parking Lot

These stay open but should not interrupt Phases 1-3 unless they become blockers:

- #151 financial overlays.
- #161 GDELT DOC 2.0 query-time enrichment.
- #159 GDELT Event Mentions propagation research.
- #145 Wikipedia/Public Attention noise filter.
- #152 command bar collision.
- #147 map reset polish.
- #148 publisher expansion.
- #106 mascot, blocked.
- #46 ACLED, blocked.

## Next Execution Order

1. [x] Reopen and clarify `#193`.
2. [x] Finish historical processed backfill for the cutover archive.
3. Turn the routing spec into a focused implementation plan.
4. Execute app-wide routing + coverage badge.
5. Fix `#194` long-window `top_sources`.
6. Return to NLP/topic quality: `#171`, `#167`, `#185`, `#184`.

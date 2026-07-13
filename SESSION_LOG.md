# Atlas — Session Log

## 2026-07-12/13 — Spec-history crosswalk + shared L1/L3 publication foundation

Pedro asked that the latest design not repeat previously documented thinking.
The review crossed the approved Investigation Graph spec against the June 9
Research Workflow/Workbench spec, Living Narrative Threads, dossier v3,
movement/Kalman, relation/corroboration/voice/history contracts, subject
geography, event bindings and the validation/paper route. The crosswalk kept the
new contribution —heterogeneous composition and one `PublicationPackage` for
L1/L3— while rejecting parallel ranking, relation, citation and prose systems.

Implemented with TDD:

- deterministic `atlas-investigation-graph-v1` with typed measured, inferred,
  contextual and analyst edges;
- adapter for the existing `dossier-connections-v1`, correcting shared coverage
  country from “confirmed” to contextual/non-causal;
- deterministic `atlas-publication-package-v1` with numbered receipts, 5W+H,
  narrative spine, who-says-what inputs, gaps, method and reproducibility;
- Workbench pin adapters for stories, evidence, subjects, countries, sources,
  events, anomalies, attention, assets and time slices; unknown research anchors
  remain explicit context;
- visible Workbench editorial-readiness panel and Markdown export block;
- removal of silent six-receipt and enrichment top-N cuts before publication
  prose; all frozen evidence remains addressable;
- explicit operational ledgers for the legacy relation-provider window,
  recent-member sampling and visual neighbors.

The Daily Investigation path now scans the complete active top-level universe,
uses movement/surprise/confidence/evidence/breadth/persistence dimensions with
Pareto fronts, and stores a sealed daily artifact. Content category,
`crisis_relevant` and raw volume contribute zero importance weight. The first
live artifact traversed 458/458 candidates, selected 12 layout slots with 17
current-window receipts and remained honestly degraded because the cutoff was
21.5 hours old, actor identity was missing and causal/subject geography was
partial. L1 was not switched.

A local production-shaped Workbench smoke pinned two real threads. The
constellation rendered both with zero links instead of inventing one from
proximity or coverage. Full verification reached `1274 passed, 6 skipped` in
the backend and `303 passed` in the frontend; the production Vite build passes.
Deploy/editorial gates remain later in this same loop.

Operations audit found the July 12 embed run holding the mutex for about 400
minutes. The bottleneck was HNSW database I/O, not embedding math. The writer
now sweeps retention before index maintenance and guarantees HNSW restoration
from an outer `finally`. No archived or product information was deleted to hide
the capacity problem.

The controlled July 13 follow-up removed HNSW insert waits but stalled after
2,304 rows in a Metal command-buffer synchronization while PostgreSQL was idle.
Cooperative interruption entered the outer `finally` and restored HNSW. The
rebuild itself caused a 15-second production threads timeout on the shared
database. Per-batch MPS cache release was added and #241 reopened; bulk reindex
remains recovery-only, not a cron strategy.

Records:

- `docs/state/2026-07-12-spec-history-crosswalk.md`
- `docs/state/2026-07-13-l0-l3-reliability-matrix.md`
- `docs/superpowers/plans/2026-07-12-investigation-graph-slice-3-daily-publication.md`

---

## 2026-07-12 — L1/L2/L3 Investigation Graph canon + reliability Slice 1

Pedro approved the unifying product model: L1 is a complete-universe 24h
investigation built by the system; L2 is the standalone exploration instrument;
L3 is the editorial studio where heterogeneous pins become a multi-focus graph
and, eventually, a publishable dossier. L1 and L3 share one publication-quality
contract. Search supplies anchors; it does not manufacture the dossier.

The approved architecture is recorded in
`docs/superpowers/specs/2026-07-12-investigation-graph-l2-l3-design.md`.

Reliability Slice 1 was implemented with TDD and deployed:

- removed the discarded atlas-category query from stories-only thread lists;
- preserved category rollback switches and honest short/empty story lists;
- mapped database-owned thread command timeouts to `503 db_busy` without
  mislabeling generic timeouts;
- isolated semantic story-centroid, taxonomy-description, and signal-headline
  failures with component-specific visible gaps;
- removed two stale test assumptions left behind by intentional LLM parser and
  provider-chain changes.

Verification: `1230 passed, 6 skipped, 0 failed`. Production Fly image
`deployment-01KXCRYT1K1VN352NZC04K5Q77` is on app version 398 with its health
check passing. Post-deploy 24h/168h thread lists returned 10/24 rows; NATO 24h
returned a pineable thread with no timeout gap; the Iran case returned 13 thread
anchors, six pin candidates, and a 66-signal detail with 23 evidence receipts.

The slice is `pass_with_caveats`: browser automation could not attach a fresh
tab for the visual walkthrough, and the shared DB still generated handled
timeouts on unrelated anomaly/correlation requests. Full evidence:
`docs/state/2026-07-12-investigation-graph-slice-1-reliability.md`.

Next: typed Investigation Graph foundation and heterogeneous pin resolution,
with no frontend rewrite until the graph forcing case reconciles thread, event,
country, entity, and evidence nodes.

Typed-node Slice 2 then shipped the first executable graph contract. All ten
planned node families now normalize to `atlas-investigation-v2`; frozen pin
state is separated from live enrichment; thread and signal adapters resolve
canonical receipts; unsupported enrichment remains a retryable metadata-only
node. Production version 400 resolved the Iran thread (66 signals) and a real
signal receipt while preserving their frozen snapshots. The smoke caught and
fixed an undeployed-column assumption before the slice was accepted. Full
record: `docs/state/2026-07-12-investigation-graph-slice-2-node-foundation.md`.

---

## 2026-07-12 — Complete-universe subject geography and event map audit

Delivered Stage 1 of #238 without LLM classification or semantic top-N limits.
The new cursor-exhaustive report separates subject from coverage geography,
scores explainable multilingual/NER/consensus/e5/temporal evidence, exposes
provenance and uncertainty, and abstains instead of copying a coverage country.

The live read-only 14-day run reached cursor exhaustion over all 1,442
active/candidate dynamic topics: 502 active, 940 candidate, 29 batches, no
retries or failures. It inferred 140 primary subject countries (9.7%) and
abstained on 1,302; 409 topics had no hot-window evidence members. Component
ablations, structural invariants, weak-proxy disagreements, and the full topic
ledger are in `docs/research/subject-geography/`. Human semantic adjudication
remains deferred to the publishable-dossier validation stage.

The map/thread audit verified that hazards and CAMEO events are attached after
thread formation as movement context, never evidence; baseline spikes remain
derived properties rather than event members. It also found stale bindings
after July 12 snapshot timeouts. GitHub #255 now specifies accessible structured
hover receipts, while #256 isolates binding freshness and resumability.

Execution plan:
`docs/superpowers/plans/2026-07-12-subject-geography-math-first.md`.

---

## 2026-07-12 — Canonical consolidation, shared-DB stability, and C7 pilot

`v3-intel-layer` was reaffirmed as the canonical production/main branch. PRs #118 and #144 were closed as superseded/obsolete; only the explicitly obsolete remote PR branch was deleted. Dirty and host-owned worktrees were preserved.

Delivered:

- corrected P1.1 heavy-job mutex and honest asyncpg degradation;
- bounded candidate-first dynamic-thread SQL, with live read-only EXPLAIN evidence (48.166 ms global, 242.154 ms country-scoped; zero sequential scans);
- nullable measured confidence, neutral non-crisis acceleration, and truthful empty/error states;
- Brief stale-while-revalidate with cached fallback and retry;
- repaired Python Anthropic and Node/ESLint installations;
- C7 read-only voice-asymmetry scorer, tests, and 168h JSON/Markdown artifact.

C7 inspected 100 active non-junk topics: 49 cleared volume/source/attribution floors and 18 crossed the review threshold. The run exposed obvious mismatches in `cluster_primary_coverage_proxy`; this is useful negative evidence. C7 remains a human-review research report and cannot alter lifecycle, ranking, UI, DB state, or cron until semantic subject geography (#238) exists.

Execution plan: `docs/superpowers/plans/2026-07-12-consolidation-stability-c7.md`.

---

## 2026-06-09 — Research Workflow + Workbench investigation spec

Pedro reframed the Iran climate search experiment as a product objective:
Atlas should not merely answer one research question, and it should not pretend
that search instantly builds a finished dossier. It should let any broad,
compound natural query start a guided research workflow where the user opens
Atlas anchors, pins useful items, follows related branches, and lets Workbench
become the investigation memory.

### Forcing case
- Initial query: climate/weather in the Middle East, specifically Iran.
- Required answers: who is talking, what each source/actor says, how frames
  differ, where it is happening, why it is moving now, what countries and actors
  are involved, and how the story evolves.
- Compound branch added by Pedro: relationship between climate/water in Iran,
  attacks on US/allied bases or satellite/communications infrastructure, other
  Middle Eastern countries, and regional water/energy/security routes.

### Web baseline
Manual web research showed the correct research tree is not "climate" alone:
`climate -> drought -> water scarcity -> Tehran reservoirs/rationing ->
agriculture/groundwater -> protests/governance -> conflict damage to
water/electricity infrastructure -> WASH/health -> regional water/energy
security -> US bases/satellite imagery/communications/radar infrastructure`.

Sources/frames found:
- UNICEF: climate as child-rights, water, health, heat, displacement risk.
- Al Jazeera: Tehran dams, rationing, agriculture, sanctions, poor management,
  50C heat, water bankruptcy.
- WRI: water stress plus conflict/security and food/energy/health risk.
- ACAPS: humanitarian/WASH, damaged water and electricity infrastructure,
  displaced people, waterborne disease risk, food inflation.
- Guardian: day-zero, pressure cuts, protests, climate breakdown and
  mismanagement.
- AP/WaPo/OSINT-style reporting: attacks/damage around US/allied bases,
  radars, satellite communications, air-defense equipment, and commercial
  satellite imagery as contested evidence.

### Atlas gap snapshot
- `/api/v2/search/thread?q=Iran climate water drought&hours=168&country_code=IR`
  -> 0 signals.
- Variants `Iran water shortage`, `Iran drought`, `Tehran water`,
  `Iran heatwave`, `Iran dams`, and `Iran water crisis` also returned 0.
- `/api/v2/search/unified` detected country `IR` and suggested climate/water
  concepts, but did not bridge those concepts to evidence.
- `/api/v2/threads?hours=168&country_code=IR` did return country threads,
  including `flood-landslide-disaster--ir`, but
  `/api/v2/theme/flood-landslide-disaster?country_code=IR` returned 0. This is a
  list/detail reconciliation bug class.
- `/api/v2/signals?country_code=IR&sort=relevance` returned geopolitical
  signals mixed with unrelated/noisy rows; retrieval is not intent-aware enough.

### Spec created
- `docs/specs/2026-06-09-research-thread-builder-workbench.md`
- GitHub #213 opened for the implementation track.

Pedro's correction after the first spec pass:
- search returns anchors/options, not a final dossier;
- anchors can be country focus, Narrative Threads, source lanes, public
  attention, coverage gaps, or related branches;
- the user can search `Iran`, `climate`, `climate in Iran`, or the satellite/base
  branch, then pin what matters;
- Workbench emerges from the user's route and pins;
- dossier/export is a later view generated from Workbench state.

Pedro's terminology correction:
- a `thread` is a hilo: a connected line of events, sources, claims, places,
  actors, and evidence that can be followed over time;
- a `dynamic_topic` is a tema dinamico: a changing topic identity that persists
  across snapshots;
- for Atlas product purposes these are the same object. `dynamic_topics` is the
  implementation/lifecycle table behind many user-facing Narrative Threads, not
  a separate product category.

Search architecture correction:
- Atlas should learn from web search by using prepared indexes, fast candidate
  retrieval, and ranking, but rank for Atlas's research job rather than generic
  web relevance.
- The key ranking criterion is investigative usefulness: intent fit, thread
  coherence, evidence strength, answerability, movement, source/actor value,
  geo/entity fit, novelty/gap value, and penalties for noise, unsupported
  claims, or list/detail mismatch.
- Ranking should not become hidden bias. The spec now requires risk-adjustment
  explanations, reason codes, a downranking/omission ledger, and a low-confidence
  tray so users can inspect what was omitted or demoted.
- Normal users search by reformulating, following trails, asking/socially
  checking, and using suggestions. The spec now treats reformulation and
  suggested branches as core workflow, not failure.
- Reddit/forum discussion is added as a public-attention / narrative-discovery
  lane. It can show what people are asking, amplifying, linking, or doubting,
  but it is not verified evidence by default.
- Workbench should support separate saved investigations in a sidebar/history so
  yesterday's pins do not silently mix with today's research.

The spec defines a detailed target:
- natural research intent parser;
- multi-lane anchor discovery;
- thread/country/source/public-attention entry points;
- investigative-usefulness ranking;
- transparent downranking ledger;
- Reddit/public-discussion lane;
- saved investigation sidebar/history;
- who-says-what matrix;
- frame comparison;
- coverage gaps;
- list/detail reconciliation;
- Workbench pinning/add-branch flow;
- optional report/export path from pinned route;
- phased implementation from walkthrough fixture -> read-only research-plan API
  -> Workbench pinning UI.

### Next plan
1. Keep #213 as the dedicated GitHub issue for the corrected workflow frame.
2. Implement Phase 0 walkthrough fixture for the Iran compound case.
3. Build Phase 1 read-only `/api/v2/research/plan` prototype before changing
   the public UI.

## 2026-06-09 — Dynamic-topic Kalman/state pilot

Implemented the first read-only state-tracking pilot for `dynamic_topics`.
Kalman filtering is used only to estimate movement state over snapshot history:
smoothed intensity, velocity, uncertainty, surprise, and trend. It does not
replace semantic classification, does not change lifecycle state, and does not
write to database tables.

### Implementation
- Added `backend/scripts/dynamic_topic_state_report.py`.
- The script reads `dynamic_topics`, `dynamic_topic_members`, and
  `emergent_clusters`, then emits JSON/Markdown reports.
- It models intensity as `log1p(n_signals)` and uses a small constant-velocity
  Kalman filter over each topic's snapshot sequence.
- Recommendations are review hints only:
  `watch_acceleration`, `watch_decay`, `keep_current_lifecycle`,
  `collect_more_history`, `do_not_promote_roundup`, and
  `do_not_promote_high_noise`.
- The report keeps `lifecycle_state` separate from `state_estimate` so the
  existing candidate/active/deprecated state machine remains authoritative.
- Explicit roundup labels are blocked from promotion even when the temporal
  signal is surging.

### Artifacts
- `docs/research/topic-quality/2026-06-09-dynamic-topic-state-pilot.json`
- `docs/research/topic-quality/2026-06-09-dynamic-topic-state-pilot.md`

### Live read-only result
- 12 active/candidate topics reported.
- 6 explicit roundup candidates flagged `do_not_promote_roundup`.
- 2 active topics flagged `watch_acceleration`.
- 2 active topics flagged `watch_decay`.
- 1 high-noise candidate flagged `do_not_promote_high_noise`.

### Verification
- TDD red: new tests first failed on missing module and missing roundup guard.
- `cd backend && .venv/bin/python -m pytest tests/test_dynamic_topic_state_report.py tests/test_project_dynamic_topics.py -q`
  -> 18 passed.
- Live script run used gitignored root `.env` `DATABASE_URL` without printing the
  secret and wrote only local report artifacts.

### Next plan
1. Decide whether state tracking should become a periodic report or remain a
   manual research diagnostic.
2. If recurring, add a local wrapper that writes reports only; defer any DB
   persistence until the signal is useful across multiple days.
3. Keep semantic classification changes separate from this state metric.

## 2026-06-08 — MVP issue closeout and CountryBrief thread truth

Resumed the MVP issue sprint from the uncommitted 2026-06-05 batch. The batch is
now committed, pushed, deployed, and production-smoked as `ca2130b`
(`feat(mvp): align search and country thread truth`).

### State reconstructed
- The batch contains the PolyForm Noncommercial license migration,
  custom query-thread builder (#175), Signal Stream relevance lanes (#177 slice
  1), and docs/roadmap updates.
- Search is now product-framed as a temporary Narrative Thread builder, not a
  curated concept browser. Organic demand tracking remains deferred.
- Signal Stream relevance is deployed and live-smoked. Dedicated public-attention
  / US-domestic / raw-firehose tabs remain future narrower work if needed.
- Secret rotation was deferred by Pedro and remains a separate maintenance pass.

### CountryBrief thread-count fix (#174/#207)
Pedro flagged that opening a country could show "12 themes", which contradicted
the Narrative Threads panel. Root cause: `CountryBrief` built `top_themes` from
recent signal GDELT themes with `topCounts(themeCounts, 12)` and displayed the
length of that forced local slice.

Fix:
- Added `frontend-v2/src/lib/countryBriefThreads.ts` and tests.
- Added `frontend-v2/src/lib/countryBriefFetch.ts` so optional CountryBrief
  fetches cannot blank the whole country panel when one auxiliary endpoint is
  slow or unavailable.
- `CountryBrief` now fetches `/api/v2/threads?hours=<window>&limit=24&country_code=<country>`.
- The top metric now displays the country-scoped Narrative Thread count, labeled
  `threads`.
- The visible section changed from `Top Themes` to `Narrative Threads`, using
  the same country-scoped thread rows. No GDELT fallback is used for the visible
  thread count; if zero threads clear the gate, the count is `0`, not `12`.
- `GET /api/v2/search/thread` now accepts both `country` and `country_code`,
  matching the ThemeDetail fetch convention and preventing the local query-thread
  path from returning a scoped detail error.

### Verification
- `cd frontend-v2 && npm test -- src/lib/countryBriefThreads.test.ts` -> 2
  passed after TDD red/green.
- `cd frontend-v2 && npm test -- src/lib/countryBriefFetch.test.ts src/lib/countryBriefThreads.test.ts`
  -> 2 files passed / 3 tests.
- `cd backend && .venv/bin/python -m pytest tests/test_query_thread.py tests/test_query_thread_router_contract.py tests/test_signals_lane_contract.py tests/test_stream_relevance.py -q`
  -> 29 passed.
- `cd frontend-v2 && npm test -- src/lib/countryBriefThreads.test.ts src/lib/narrativeThreads.test.ts src/lib/themeDetailEmptyState.test.ts src/lib/searchResults.test.ts`
  -> 4 files passed / 8 tests.
- `cd frontend-v2 && npm run build` passed.
- Static preview smoke: `npx vite preview --host 127.0.0.1 --port 4173` served
  `/app` as `200 text/html` with the built `index` bundle. Full automated
  browser interaction was not completed because Playwright is not installed in
  the available Node runtime.
- In-app browser smoke on local backend + Vite dev:
  - `/app` loaded with page title `Atlas - Public Narrative Intelligence Console`.
  - Search for `Colombia` showed the custom query-thread CTA without curated
    concept-map results.
  - Opening that CTA rendered a `Custom thread` panel without `HTTP 404`.
  - `/app?country=CO` rendered CountryBrief with `10 threads`, a `Narrative
    Threads` section, and no `Top Themes` label or `Error: Failed to fetch`.

### Production deploy and issue closeout
- Pushed `ca2130b` to `origin/v3-intel-layer`.
- Deployed Fly backend with `scripts/deploy-fly-api.sh`, which targets only the
  lightweight `api-runtime` image and `app` process group. Fly reported image
  size 259 MB and the API machine in a good state.
- Vercel served the matching built frontend bundle
  `/assets/index-BY2GvIR-.js`.
- Production API smoke:
  - `/health` -> `200`, healthy, `db_ok=true`.
  - `/api/v2/search/thread?q=Colombia&hours=24&country_code=CO` -> `200` after
    previously returning `404`.
  - `/api/v2/threads?hours=24&limit=5&country_code=CO` -> real thread rows.
  - `/api/v2/signals?hours=24&limit=5&sort=relevance&country_code=CO` returned
    signals with `lane=analyst` and `relevanceScore=1.0`.
- Production Playwright smoke:
  - `/app?country=CO` showed `10 THREADS`, no `Top Themes`, no `Failed to fetch`,
    and no console errors.
  - Search for `Colombia` called `/api/v2/search/thread` with `200` responses.
  - Clicking "Build a thread" opened `CUSTOM THREAD` with matching signals and
    no `HTTP 404`.
- Closed GitHub #175 and #177 after production smoke.
- Commented #207 with the country-thread truth smoke and kept it open as the
  Living Narrative Threads umbrella.

### Next plan
1. Rotate keys in a separate maintenance pass before the next credential-bearing
   deploy cycle.
2. Scope a read-only Kalman/state-tracking
   pilot for dynamic topic intensity/velocity/surprise. Keep it out of semantic
   classification.

## 2026-06-05 — Signal Stream relevance lanes (#177, slice 1)

First slice of #177: analyst-grade relevance scoring + lane separation so the
`Notable` stream stops mixing crisis/conflict items with sports and celebrity
noise (e.g. "Vikings 2026 Undrafted Free Agents", "Eurovision Song Contest").

**Approach:** the observed noise carries generic/empty GDELT themes, so the
analyst signal comes from themes (crisis + security/economy/politics
categories) while sports/entertainment are detected from headline keywords.
Analyst themes override headline keywords.

**Backend**
- `backend/app/services/stream_relevance.py` — pure `classify_stream_lane`,
  `stream_relevance_score`, `score_stream_signal`. Lanes:
  analyst|sports|entertainment|general; score 0..1 (analyst base 0.7 + severity
  boost, noise lanes ≤0.15). 11 unit tests.
- `GET /api/v2/signals` now returns `lane` + `relevanceScore` per signal, accepts
  `lane=` filter and `sort=relevance` (widens fetch to 200 then ranks + truncates
  to `limit`). 4 contract tests.

**Frontend**
- `SignalDetailPanel.tsx` — `Signal` type gains `lane`, `relevanceScore`,
  `framing`.
- `SignalStream.tsx` — fetches `sort=relevance`; analyst tabs
  (notable/critical/elevated/trend) exclude sports/entertainment lanes; `notable`
  promotes `lane === 'analyst'`; sports/entertainment items get a lane badge in
  `all`; NOTABLE tab has a tooltip explaining the ranking (acceptance criterion).
- `SignalStream.css` — `.stream-lane-badge` styles.

**Verification:** 28 backend tests (this slice + query-thread) pass; `npm run
build` passes. Live smoke pending.

**Not yet in this slice:** dedicated Public-attention / US-domestic / Raw-firehose
tabs; consuming `signal_topic_assignments` (#167) for domain labels. Lane is
theme+headline heuristic for now.

## 2026-06-05 — License migration + custom query-thread builder (#175)

### License → source-available
- Replaced MIT with **PolyForm Noncommercial License 1.0.0** (verbatim canonical
  text + `Required Notice: Copyright (c) 2025 Pedro Villegas — Observatorio
  Global`). Goal: free read/noncommercial access, IP retained, commercial use
  requires a separate license.
- Updated `LICENSE`, root `README.md` (new License section), `backend/README.md`,
  `frontend-v2/package.json` (`LicenseRef-PolyForm-Noncommercial-1.0.0`), and
  `backend/pyproject.toml`.
- Remaining `MIT` mentions are correct (MIT Media Lab institution; h3-js/deck.gl
  dependency licenses) — left untouched.

### Key rotation plan (deploy day)
- Decision: rotate **all** secrets at next deploy regardless of leak audit
  (audit inconclusive — full-history `git log -S` scans timed out on the 50MB
  pack; `.env` is confirmed gitignored and never tracked on the working branch).
- Rotation targets: `ANTHROPIC_API_KEY`, `OPENAI_API_KEY`, `DEEPSEEK_API_KEY`,
  `MAPBOX_TOKEN`, `OPENSKY_CLIENT_ID/SECRET`, `POSTGRES_PASSWORD`/`DATABASE_URL`,
  Redis creds. Re-set via `fly secrets set` + Vercel env + worker `.env` (600).

### #175 — custom query-thread builder (search becomes a thread creator)
Product reframe: search no longer exposes a curated investigative concept map.
Any query builds a temporary Narrative Thread from direct evidence. This slice
ships that builder end-to-end.

**Decisions (confirmed with Pedro):**
- Matching: **direct only** — headline / themes / persons / source via the
  existing multilingual `build_query_variants`. No GDELT weak-recall expansion.
- Gate: **none** — build from whatever matches; flag sparse results with a
  `coverageTier` ("thin" | "limited" | "ok") so the UI shows a THIN badge like
  country-scoped threads, instead of an empty state.
- Entry UX: search results are the options; a prominent top CTA builds a thread
  for the exact query, and the offered thread is prefetched so the click is
  instant.

**Backend**
- `backend/app/services/query_thread.py` — pure `build_query_thread(rows, query,
  *, hours, country)` wraps the shared `build_thread_packet` into the
  theme-detail contract + `coverageTier` + `query_thread_thin_coverage` warning.
  ASCII slug folds accents. 9 unit tests.
- `GET /api/v2/search/thread` in `backend/app/routers/search.py` — fetches packet
  columns from `signals_v2` (headline/source/themes/persons LIKE ANY the
  multilingual variants), caps at 300 signals, caches 120s. 4 contract tests.
- 0 regression across thread/packet tests.

**Frontend**
- `SearchBar.tsx` — top CTA "Build a thread for «query»" → `onThemeSelect(
  'query-thread::<raw>')`; fires a warm fetch to `/api/v2/search/thread` when
  results load.
- `ThemeDetail.tsx` — detects the `query-thread::<raw>` token, fetches
  `/search/thread` instead of `/theme/<slug>`, guards the theme-code-only
  sub-fetches (trends/wiki/insight), renders a Custom-thread tag + THIN/LIMITED
  badge.
- `App.tsx` — `handleThemeSelect` skips `setTheme` for `query-thread::` tokens so
  the synthetic id never pollutes FocusContext.
- CSS: `.search-query-thread-cta` (SearchBar.css), `.query-thread-tag`
  (ThemeDetail.css). `coverage-badge--thin/limited` reused (global CSS).

**Verification:** backend tests + `npm run build` pass (observed). Live smoke
pending — needs running backend + DB; deferred to Pedro's manual / video pass.

**Not yet shipped (next #175 slice):** organic demand tracking — a concept list
that grows from repeated searches / query volume / multilingual variants /
signal support. Parked per roadmap.

**State:** uncommitted on `v3-intel-layer`; batched for deploy day with key
rotation and the license change. Full detail in
`docs/state/2026-06-05-query-thread-builder.md`.

## 2026-06-04 — MVP thread-volume and issue sprint design

### What happened
- Reframed the next work block around MVP readiness for next week: recover useful
  Narrative Thread volume first, then clean up the stale GitHub issue backlog.
- Wrote `docs/superpowers/specs/2026-06-04-mvp-thread-volume-and-issue-sprint-design.md`.
- Documented GDELT themes as weak, bias-measured support signals, not final
  Atlas classifiers or proof of significance.
- Added explicit bias diagnostics for Western/global-north, language,
  source-family, and syndicated-source skew.
- Updated roadmaps so Paper 1 remains active refinement but no longer blocks the
  MVP sprint.

### Follow-up
- Added `docs/roadmap/2026-06-04-mvp-issue-triage.md` after reviewing the 42
  open GitHub issues. Active MVP order is: close #146, implement #174/#175 as a
  scope/empty-state pass, smoke #193, then return to Signal Stream relevance
  and GDELT weak-recall review mechanics.
- Updated `NarrativeThreads` country-scoped empty state so it explains thread
  quality gates and provides a "Show global threads" reset instead of implying
  the panel is broken.
- Closed #146 after the fix was pushed.
- Started #174 with a Source Integrity scope-truth slice: the panel now names
  country/theme/person scopes when FocusData is scoped, and labels unscoped
  metrics as `Global background` when the center panel is focused on a thread,
  public-attention item, or chokepoint.
- Started #175 with a ThemeDetail coverage-gate empty state: zero-result
  thread/topic details now explain that no scoped evidence cleared the current
  quality gate and provide a return action instead of rendering empty stats and
  graph sections.
- Started #193 app-window routing fix: live smoke showed briefing long windows
  already use `historical_topic_country_daily`, but `/api/v2/nodes?range=1w`
  and `range=1m` returned the same hot-rollup-style totals. Updated `nodes` to
  use `query_historical_country_attention` plus `build_historical_coverage` for
  non-focused long windows.
- Deployed the #193 API fix to Fly. Production smoke now shows:
  - `nodes?range=24h`: `source=hourly_rollup`, `totalSignals=173,566`;
  - `nodes?range=1w`: `source=historical_topic_country_daily`,
    `coverage.source=historical_processed`, `totalSignals=1,009,607`;
  - `nodes?range=1m`: `source=historical_topic_country_daily`,
    `coverage.source=historical_processed`, `totalSignals=4,332,735`.
  Added the remaining `/app` coverage cue: `FocusDataContext` now carries
  `nodes.source`/`nodes.coverage`, and the command-bar stats show a
  `Historical processed` badge for long windows served from compact aggregates.
- Closed #193 after Vercel served the new `/app` bundle.
- Continued #174/#175 with a scope/stale-response slice:
  - `FocusDataContext` now keys requests by active range + focus and discards
    stale responses, so old global/scoped fetches cannot overwrite the current
    map/panel scope after rapid navigation.
  - `PublicAttentionPanel` now shows whether it is comparing global media
    matches or was opened from a country origin.
  - `AnomalyPanel` passes the active country origin into Public Attention
    selections when available.
- Reframed Search/Investigative Concepts:
  - `INVESTIGATIVE CONCEPT MAP` is not the desired user-facing model. It is a
    legacy curated map and should not be force-fed into arbitrary searches.
  - Search should evolve into a custom query-thread builder: the user enters a
    phrase in any language, Atlas searches evidence across signals/people/
    countries/public attention, and assembles a temporary thread for that query.
  - Any future concept list should be demand/evidence driven: generated from
    repeated searches, query volume, and matched signal support, not manually
    curated suggestions.
  - The SearchBar now hides curated concept-map results, related concept
    suggestions, and the old "Save as investigative concept" CTA.

### Validation
- Spec self-review found no placeholder TODO/TBD markers.
- Obsidian wikilinks in the spec resolve.
- `git diff --check` passed.
- `cd frontend-v2 && npm test -- src/lib/narrativeThreads.test.ts` passed.
- `cd frontend-v2 && npm test -- src/lib/sourceIntegrityScope.test.ts src/lib/narrativeThreads.test.ts` passed.
- `cd frontend-v2 && npm test -- src/lib/themeDetailEmptyState.test.ts src/lib/sourceIntegrityScope.test.ts src/lib/narrativeThreads.test.ts` passed.
- `cd frontend-v2 && npm run build` passed.
- `cd backend && .venv/bin/python -m pytest tests/test_processed_historical_routing.py tests/test_briefing_performance_shape.py tests/test_historical_processing.py -q`
  passed (`40 passed`).
- `cd frontend-v2 && npm test -- src/lib/historicalCoverageCue.test.ts src/lib/themeDetailEmptyState.test.ts src/lib/sourceIntegrityScope.test.ts src/lib/narrativeThreads.test.ts`
  passed.
- `cd frontend-v2 && npm test -- src/lib/publicAttentionScope.test.ts src/lib/focusRequestKey.test.ts src/lib/publicAttention.test.ts src/lib/sourceIntegrityScope.test.ts`
  passed.
- `cd frontend-v2 && npm run build` passed after the Public Attention and
  stale-response slice.
- Local `/app` smoke returned HTTP 200.
- `cd backend && .venv/bin/python -m pytest tests/test_search_concept_suggestions.py tests/test_search_performance_shape.py tests/test_search_normalization.py -q`
  passed.
- Production smoke for `Ivan cepeda` returned direct media evidence and
  `concept_suggestions: []`.
- `cd frontend-v2 && npm test -- src/lib/searchResults.test.ts` passed.
- `cd frontend-v2 && npm run build` passed after removing curated concept
  results from the SearchBar.

## 2026-06-04 — GDELT weak-support audit implemented

### What happened
- Added `backend/scripts/gdelt_weak_support_audit.py`, a read-only audit over
  active `dynamic_topics`.
- Added helper metrics for GDELT domain mapping, expected-domain inference from
  thread labels, normalized theme entropy, support/contradiction rates, and bias
  slices by source language, source family, and global-north vs other country
  group.
- Generated first live artifact:
  `docs/research/topic-quality/gdelt-weak-support/2026-06-04-live.json`.
- Fixed a scoring bug found by the live audit: `TAX_WORLDLANGUAGES_*` themes are
  metadata and must not become domain evidence merely because they contain
  words like Russia or Ukrainian.

### Validation
- TDD red: `test_theme_domains_ignores_language_metadata_themes` failed before
  the metadata guard.
- `cd backend && .venv/bin/python -m pytest tests/test_gdelt_weak_support_audit.py -v`
  -> `5 passed`.
- Live read-only run returned `schema_version=atlas-gdelt-weak-support-v1`,
  `thread_count=8`.
- Initial findings: `Russia-Ukraine War Updates` has high weak support
  (`0.8992`) but high entropy (`0.8846`), suggesting a real but mixed/splittable
  thread. `Virginia Bus Crash` has low support (`0.1667`) and high contradiction
  (`0.6667`), making it a review/split/suppress candidate.

## 2026-06-04 — GDELT weak-support recall pilot implemented

### What happened
- Added `backend/scripts/gdelt_weak_recall_pilot.py`, a read-only pilot that
  asks how many additional recent signals compatible GDELT themes could surface
  for manual review.
- Added conservative safeguards after the first live run surfaced noisy
  expansion:
  - reject over-broad expansion themes (`GENERAL_*`, `TAX_FNCACT_*`,
    `TAX_WORLDLANGUAGES_*`, generic CrisisLex safety);
  - do not treat every `UNGP_*` code as policy/rights;
  - require label anchor terms such as `russia`/`ukraine`;
  - skip generic labels such as `Local News and Politics` until label review.
- Generated `docs/research/topic-quality/gdelt-weak-support/2026-06-04-recall-pilot.json`.

### Validation
- `cd backend && .venv/bin/python -m pytest tests/test_gdelt_weak_recall_pilot.py tests/test_gdelt_weak_support_audit.py -v`
  -> `12 passed`.
- Live pilot with `--candidate-limit 500` returned 33 conservative added
  candidates for `Russia-Ukraine War Updates`.
- Other active threads did not expand because they lacked compatible themes,
  had generic labels, or were already flagged by the audit as review/split
  candidates. This is acceptable for the first MVP-safe pilot: recover volume
  only where GDELT support plus label anchors agree.

## 2026-06-04 — Unified thread detail shell started

### What happened
- Corrected the F5 frontend direction: resolvable Narrative Threads now open the
  existing `ThemeDetail` shell instead of the parallel `ThreadFocusPanel`.
- Added `resolveThreadThemeTarget` to route dynamic threads to
  `dynamic-topic-<id>`, atlas threads to their anchor topic, and keep
  emergent-only threads on the old ThreadFocusPanel fallback until ThemeDetail
  supports that prefix.
- Embedded the thread `narrative_note` at the top of `ThemeDetail` when the
  panel was opened from a Narrative Thread, preserving the richer ThemeDetail
  interactions (Evolution Graph, country cards, right-panel country edge,
  source/person/theme actions).
- Renamed the fallback ThreadFocusPanel's vague `Movement` section to
  `10h Signal Change`.
- Follow-up UI fix from live review: `ThemeDetail` now prefers backend
  `data.label` over formatting raw slugs, so `dynamic-topic-10` renders as the
  actual thread label instead of `Dynamic Topic 10`.
- `ThemeDetail` now falls back from empty `countryFraming` to `countryBreakdown`
  for dynamic topics, restoring the country-card/edge interaction even when the
  backend only has preview-grade country aggregates.
- Related-topic copy now names those chips as co-occurring GDELT themes, not
  source-family categories.

### Validation
- `cd frontend-v2 && npm run build` passed.
- Direct helper smoke passed via Node type stripping.
- Local proxy returned 200 for `/api/v2/threads`, `/api/v2/theme/dynamic-topic-17`,
  and `/api/v2/theme/election-legitimacy-dispute?country_code=CO`.
- Local smoke for `/api/v2/theme/dynamic-topic-10?hours=24` returned
  `label=Russia-Ukraine War Updates`, `countryBreakdown=15`, and
  `countryFraming=0`, matching the frontend fallback.
- Vitest currently hangs even on an existing unrelated test in this local
  session; kept the new unit test file in place but did not rely on Vitest as a
  completion gate.

## 2026-06-04 — Thread Intelligence Packet (F5) shipped

### What happened
- Built a shared `backend/app/services/thread_packet.py` `build_thread_packet(rows,
  own_topic)` that aggregates a thread's sample signals into country edges,
  source/social lanes, sentiment timeline, top sources (+family), top persons,
  related themes, and a public_attention slot.
- Attached `packet` to all three thread-detail paths (atlas/emergent/dynamic) in
  `thread_intelligence.py`; added `themes` to the sample SQL (and `themes`+`persons`
  to the atlas evidence SQL).
- `public_attention`: best-effort, reuses the trends/wiki theme-match SQL keyed on
  the thread's top GDELT theme; fully isolated (any failure → None).
- Refactored `themes.py` `_dynamic_topic_detail`/`_emergent_cluster_detail` to reuse
  the same builder (DRY, −106 lines), ThemeDetail contract unchanged.
- `ThreadFocusPanel` renders 5 packet sections (timeline, country breakdown, source
  lanes, related topics, public attention), null-safe, reusing ThemeDetail patterns.
- Also closed F3 loose end: snippet confirmed persisting live (independent 127/143,
  api 47/47, gdelt 0).

### Validation
- 44 backend tests pass; frontend `npm run build` clean.
- Prod smoke: dynamic-topic-10 packet populated (countryBreakdown 6, topSources 12,
  timeline 8, lanes media 12, relatedThemes 10); emergent path returns null-safe
  empty packet on a drifted sample. Fly `/health` healthy.

### Decision
Packet shipped (server-side, one contract, all thread types). `classify_source`
returns "independent" for reddit, so lanes use a domain set (`_SOCIAL_DOMAINS`) to
route social. public_attention is live but often null (theme-match miss) — acceptable.
Caveat: packet aggregates over `sample_signal_ids` (~8-24), preview-grade; bumping the
snapshot sample cap is an optional follow-up.

## 2026-06-04 — DeepSeek thread-note pilot and country thread alignment

### What happened
- Added optional DeepSeek synthesis for opened thread details:
  `/api/v2/threads/{thread_id}?llm=1`.
- Kept the deterministic `extractive-v1` note as the fallback and accepted only
  strict JSON from DeepSeek.
- Added `country_code` to `/api/v2/threads` and updated `NarrativeThreads` to
  request country-scoped threads from the backend instead of filtering global
  results client-side.
- Documented the current DeepSeek model selection:
  `deepseek-v4-flash` by default, `deepseek-v4-pro` via
  `DEEPSEEK_THREAD_NOTE_MODEL`.

### Validation
- Backend: `34 passed` across DeepSeek narrative, router contract, thread
  intelligence, and emergent/dynamic shape tests.
- Frontend: `npm run build` passed.

### Decision
Themes and Narrative Threads should be one product concept. The immediate fix is
country-scoped thread retrieval; the next architectural fix is a shared Thread
Intelligence Packet so `ThreadFocusPanel` inherits graph, country-edge,
source-lane, social/Reddit, and sentiment-history data instead of diverging from
`ThemeDetail`.

## 2026-06-04 — Narrative Note synthesis shipped

### What happened
- Implemented the first read-only Narrative Note increment from
  `docs/superpowers/specs/2026-06-04-narrative-note-synthesis-design.md`.
- Added `backend/app/services/narrative_note.py`, a deterministic/extractive
  note builder with no LLM calls and no new persistence.
- Wired `narrative_note` into atlas-topic, emergent-cluster, and dynamic-topic
  thread assemblies in `thread_intelligence.py`.
- Updated `ThreadFocusPanel` so an opened thread starts with prose (`lede`,
  movement, evidence, caveat) before metrics/evidence lists. The old `why_now`
  paragraph remains the fallback when the backend field is absent.

### Validation
- Backend: `36 passed` across narrative note, thread intelligence, emergent
  shape, and snippet evidence contract tests.
- Frontend: `npm run build` passed.
- Direct local-code smoke against Supabase returned `dynamic-topic-17` with
  `narrative_note.source="extractive-v1"`.
- Deployed backend to Fly with `scripts/deploy-fly-api.sh`; app machine reached
  good state and `/health` returned healthy.
- Fly and localhost proxy both returned `/api/v2/threads?hours=24&limit=1` with
  `narrative_note.source="extractive-v1"`.

### Decision
Thread-level narrative prose is now the first reading layer. It remains
extractive and provisional by design; LLM synthesis and country-scoped notes are
separate follow-up increments.

## 2026-06-04 — F3 signal snippet enrichment shipped and verified

### What happened
- Continued from the F3 handoff after context loss and validated the real repo
  state first. The feature was already merged on `v3-intel-layer` at
  `87c98dc merge: signal snippet enrichment (F3)`.
- Confirmed migration 052 adds nullable `signals_v2.snippet`, and the Supabase
  column exists as `text`.
- Confirmed source text is wired through `clean_snippet` for Reddit, NewsAPI,
  RSS, NewsData, MediaStack, and ReliefWeb. GDELT remains NULL by design.
- Confirmed `/api/v2/signals` returns `snippet` for `SignalDetailPanel`, and
  thread evidence serialization carries `snippet` as data for future narrative
  synthesis.
- Confirmed localhost is connected to production data by default through the
  Vite proxy to `https://atlas-api-pedro.fly.dev`; local frontend changes render
  against the same signals as production unless `VITE_LOCAL_API` is set.

### Validation
- Backend focused tests:
  `.venv/bin/python -m pytest tests/test_signal_text.py tests/test_ingest_snippet_wiring.py tests/test_snippet_evidence_contract.py -v`
  -> `9 passed`.
- Frontend: `npm run build` passed.
- Fly `/health` and localhost `/health` returned matching production state
  (`status=healthy`, `db_ok=true`, `total_signals=343493`, ingest lag `2.5`
  minutes during smoke).
- `/api/v2/signals?hours=24&limit=5` on both Fly and localhost returned the
  `snippet` key without contract errors.
- Live DB showed `with_snippet=0` in the current 24h window, but post-deploy
  inserts since `2026-06-04T14:25:00Z` were GDELT-only. That is expected because
  GDELT has no body text. The next non-GDELT ingest cycle is the real persistence
  smoke.

### Decision
F3 is shipped as a foundation: persist snippets when source text exists, expose
them as data, and render raw text only in the clicked single-signal detail panel.
Do not render raw snippets under every theme/thread headline; the stronger use
is a follow-up narrative-note synthesis layer.

## 2026-06-03 — Workbench early-access waitlist gate shipped

### What happened
- Reframed the production focus around the Workbench as the public MVP lead
  surface (information-disorder sensemaking pivot). Chose Option A: keep the
  Workbench gated, make the gate interactive.
- Synced production first: pushed 37 unpushed commits + committed/pushed the
  Jun-3 smoke follow-up work so GitHub matched Fly (Fly was already current).
- Brainstormed → spec'd → planned → executed via subagent-driven development on
  branch `feat/workbench-waitlist` (6 implementation commits, one per task).
- Migration 051 `workbench_waitlist` (RLS), backend `/api/v2/waitlist` +
  `/api/v2/waitlist/count`, frontend `lib/waitlist.ts` +
  `WorkbenchWaitlistGate.tsx` replacing the static mailto overlay.
- Final review caught 3 blockers (spoofable rate limit, unbounded rate-log,
  submit stuck on network error) + 2 minor; all fixed and re-verified.
- Merged to `v3-intel-layer` (`1af31fa`), deployed backend to Fly, pushed to
  trigger Vercel.

### Validation
- Backend: 16/16 waitlist tests; two clean `npm run build` runs.
- Production smoke: count `0 → POST → 1`; honeypot wrote no row; invalid email
  `422`; DB row verified then cleaned. Vercel bundle confirmed to contain the
  new overlay copy and `/api/v2/waitlist/count` resolves through the proxy.

### Decision
The waitlist gate is shipped. Counter uses real data only (threshold 25, else
qualitative copy) — no fabricated numbers, consistent with the anti-disinformation
stance. Next product track is a dedicated platform-wide language/positioning
coherence pass (landing + walkthrough + microcopy), specced separately.

## 2026-06-03 — Research-to-product roadmap clarified

### What happened
- Documented the current route in
  `docs/roadmap/2026-06-03-research-model-product-roadmap.md`.
- Added `docs/research/atlas-paper/2026-06-03-paper-1-result-skeleton.md` so
  Paper 1 has a draft-ready results structure instead of only an outline.
- Clarified that Paper 1 is not closed as a manuscript, but RQ1 is measured at
  sufficient scale to guide the model-improvement roadmap.
- Updated the Paper 1 outline, master paper plan, validation README, Obsidian
  index, Narrative Intelligence MOC, Validation/Paper MOC, production-cycle
  roadmap, and narrative-intelligence framework.
- Captured Atlas's product purpose as information-disorder sensemaking: show how
  narratives move, which sources amplify them, what evidence supports them, and
  what should be treated as context or noise.

### Decision
- Finish the Paper 1 documentation/result skeleton first.
- Then deploy the backend canonical `dynamic_topics` cutover and run the full
  browser smoke through `/brief`, Watchlist clicks, Narrative Threads, and
  ThreadFocusPanel.

## 2026-06-03 — Dynamic topics deployed and product-smoked

### What happened
- Ran focused backend tests from `backend/`: `63 passed` across thread,
  briefing, theme slug, and dynamic-topic lifecycle guardrails.
- Deployed the backend with `scripts/deploy-fly-api.sh`; image size `259 MB`,
  deployed only process group `app` (`1/3` machines), machine
  `d8d2e46fe07e78` healthy.
- Fly `/health` returned healthy with DB ok and fresh ingest.
- API smokes confirmed `dynamic_topics` canonical reads:
  `/api/v2/threads` top rows are `dynamic-topic-*`;
  `/api/v2/briefing?hours=24` returned
  `top_atlas_topics_source=dynamic_topics`; `/api/v2/theme/dynamic-topic-10`
  returned `source=dynamic_topics`, `total=313`, `signalSample=76`.
- Browser-smoked the deployed frontend:
  `/brief` rendered dynamic Watchlist rows; clicking a Watchlist row opened
  `/app?theme=dynamic-topic-10&entry=brief`; clicking Narrative Threads opened
  ThreadFocusPanel with `350` signals, `5` countries, `11` sources, movement,
  and evidence.
- Saved smoke report:
  `docs/research/topic-quality/2026-06-03-dynamic-topics-product-smoke.md`.

### Follow-up findings
- ThemeDetail `HOT WINDOW` copy contradicted the dynamic topic signal count by
  saying there was no measurable coverage while the panel showed `313` signals.
- ThreadFocusPanel duplicated country chip codes visually (`IDID`, `BRBR`, ...).
- Dynamic topic entity labels still include raw/repeated strings.
- The onboarding tour appeared over the first `/app` entry and had to be
  dismissed for a clean smoke screenshot.

### Decision
The dynamic-topic backend/product contract cutover is shipped. Next work should
be a focused UI/data-quality pass on contradictory insight copy, country chip
rendering, and entity hygiene.

## 2026-06-03 — Dynamic topics smoke follow-up fixes

### What happened
- Fixed dynamic-topic ThemeDetail insight copy locally. For
  `dynamic-topic-*`, the component now skips the static GDELT-theme insight
  endpoint and builds the `HOT WINDOW` summary from the same dynamic-topic
  detail payload that drives totals, countries, sources, sentiment, and evidence.
- Fixed duplicated dynamic-thread country chips locally. Dynamic-thread backend
  payloads no longer send country codes as `top_country_names`, so the frontend
  country resolver does not render `IDID`, `BRBR`, etc.
- Added a backend regression test for the country-name payload behavior and a
  frontend source-shape test documenting the dynamic-topic insight branch.
- Updated the product smoke report with fixed vs still-open findings.

### Validation
- Focused backend route/contract tests: `51 passed`.
- `git diff --check`: clean.
- Frontend `tsc -b`, focused Vitest/source-shape checks, ESLint, and separate
  Vite production bundling hung in this local Node environment before producing
  diagnostics. Frontend build/browser re-smoke remains pending before deploy.

### Decision
The contradictory dynamic-topic insight copy and duplicated country chips are
fixed locally. Raw/repeated entity strings remain open for the Entity
Focus/model-quality lane.

## 2026-06-03 — Frontend surface/data map

### What happened
- Regenerated `docs/state/PROJECT_INVENTORY.md` with `python3
  scripts/project_inventory.py` so endpoint, frontend-callsite, cron, and recent
  commit maps reflect the current repo.
- Audited `frontend-v2` routes, `App.tsx` mounted panels, fetch callsites,
  context providers, and unmounted/legacy components.
- Added `docs/frontend/2026-06-03-frontend-surface-data-map.md` as the human
  operating map for visible surfaces, hidden/partial surfaces, dynamic-topic
  connection points, and contract ownership.
- Linked the new map from `docs/maps/Frontend Product Surfaces.md` and
  `docs/000-INDEX.md`.

### Findings
- Dynamic topics now feed the main product through Brief Watchlist,
  NarrativeThreads, ThreadFocusPanel, and ThemeDetail dynamic branches.
- Globe/country heat, CorrelationMatrix, AnomalyPanel, and SourceIntegrity are
  adjacent evidence/context surfaces, not dynamic-topic ownership surfaces.
- `/brief` Watchlist rows are dynamic-topic aware, but headline snippets still
  fetch `/api/v2/signals?theme=<slug>`; for `dynamic-topic-*`, that should move
  to `/api/v2/theme/dynamic-topic-*` samples.
- Several components exist but are not mounted in the current product path:
  `DiscoveryPanel`, `AtlasHeatList`, `CrisisDashboard`, `CrisisToggle`,
  `FocusSummaryPanel`, and placeholder panels.

### Decision
Use the frontend surface/data map before wiring new model outputs. The next
frontend contract fix should be dynamic-topic snippets in `/brief`, followed by
a stable frontend build/browser re-smoke and then Entity Focus hygiene.

## 2026-06-03 — MVP Workbench public preview gate

### What happened
- Added a production-only public preview lock for the Workbench. In production,
  outside localhost, opening the workspace now shows the board blurred with a
  "Coming soon" panel, a `Request early access` mailto CTA, and a secondary
  `Support Atlas` CTA.
- Kept the Workbench fully usable for local development and data validation on
  localhost. The production gate can also be bypassed with
  `VITE_ENABLE_WORKBENCH=true` for controlled previews.
- Documented the Workbench's MVP status in the frontend surface/data map.

### Decision
For the next MVP launch, ship Atlas with Brief, Globe, Narrative Threads,
ThreadFocusPanel, ThemeDetail, Source Integrity, and public attention surfaces
available. Treat Workbench as the product's strongest future investigation
surface, but do not expose the raw full interaction publicly until the workflow
is understandable and stable. Use early-access clicks/emails as a lean
validation signal for whether to prioritize the Workbench next.

## 2026-06-02 — Phase 6 backend canonical cutover

### What happened
- Moved the backend read path from shadow-only `dynamic_topics` to canonical
  fallback-first product reads:
  `/api/v2/threads` prefers active `dynamic_topics`; raw emergent clusters and
  atlas-topic threads remain fallbacks.
- Updated `/api/v2/briefing.top_atlas_topics` to prefer `dynamic_topics`
  (`source_table=dynamic_topics`, `model_version=dynamic-topics-v1`,
  `noise_rate`) before raw `emergent_clusters` and static atlas assignments.
- Added `/api/v2/theme/dynamic-topic-<id>` so existing Watchlist clicks still
  open `ThemeDetail`; the detail payload is built from member
  `emergent_clusters.sample_signal_ids` and does not call paid APIs.
- Fixed the dynamic detail branch against the real migration schema:
  `dynamic_topic_members.dynamic_topic_id` +
  `dynamic_topic_members.emergent_cluster_id`.

### Validation
- Focused backend tests: 63 passed across threads, briefing shape, theme slug
  guardrails, and dynamic topic lifecycle tests.
- Live local smokes against Supabase through the worker `.env`:
  `/api/v2/threads?hours=24&limit=5` returned only `dynamic-topic-*` rows at
  the top; `/api/v2/briefing?hours=24` returned
  `top_atlas_topics_source=dynamic_topics`; `/api/v2/theme/dynamic-topic-10`
  returned label "Russia Warns on Baltic and Zaporizhzhia",
  `source=dynamic_topics`, `total=287`, and `signalSample=141`.

### Decision
Backend canonical cutover is implemented locally but not yet deployed. Next
step is backend deploy plus frontend/browser smoke through `/brief`,
Watchlist clicks, Narrative Threads, and ThreadFocusPanel. The only degraded
briefing segment observed in smoke was `theme_country`, a separate pre-existing
section issue.

## 2026-06-02 — Phase 6 dynamic_topics self-curation

### What happened
- Continued Phase 6 after the student noise-rate gate and incremental cron
  wiring.
- Completed merge/dedup as a conservative `--rebuild` consolidation step in
  `backend/scripts/project_dynamic_topics.py`. The first centroid-only
  single-linkage design was rejected by dry-run evidence because Atlas
  emergent centroids are dense: unrelated real topics and roundup artifacts
  can sit above cosine 0.90 and chain-collapse.
- Final merge rule requires centroid similarity plus compatible normalized
  labels, and excludes roundups from merge participation so grab-bags cannot
  absorb real topics.
- Applied a shadow rebuild with the guarded merge: 101 clusters / 9 snapshots
  -> 21 dynamic topics, `n_merged_topics=0`, 6 active / 12 candidate /
  3 deprecated, 5 roundups, 1 high-noise topic, 101 member rows.
- Verified the live cron path remains idempotent after rebuild: incremental
  run reported `n_new_clusters=0`, `inserted=0`, `updated=0`, `members=0`.

### Decision
The self-curating lifecycle now runs after each emergent snapshot with $0 API
inference, caches per-cluster student noise, and has a safe rebuild-only dedup
path. This section was originally shadow-only; the later 2026-06-02 backend
canonical cutover above is the current read-path state.

## 2026-06-02 — Local Ollama validation route deprecated

### What happened
- Documented and tested `backend/scripts/atlas_ollama_pilot.py`, a read-only
  local Ollama benchmark runner that writes separate `ollama_*` fields and
  resolved `gold_*` comparison fields without mutating review templates.
- Logged the 2026-06-02 `llama3.2:1b` pilot against 20 reviewed batch 02 rows:
  decision accuracy 25%, scope accuracy 25%, evidence-role accuracy 11.76%,
  with 3 invalid prediction rows after tolerant parsing.
- Updated the validation README, experiment log, Obsidian validation map, and
  status docs so this route is not rediscovered as an open opportunity.

### Decision
Local Ollama on Pedro's current M1 is deprecated for Atlas judging, teacher
labels, reviewer substitution, assistant hints, and gold generation. Keep the
script and artifacts only for reproducibility or low-stakes prompt/JSON plumbing
tests.

## 2026-06-01/02 — RQ1 at scale + thread-label fix + venv off iCloud

### What happened
- **Thread label fix** (`6370bcf`): dropped the redundant momentum verb
  (`intensifies`/`continues`) from `build_thread_label`; the trend pill
  (accelerating/stable/fading) is now the sole momentum signal. Removed the
  unused `changed_10h` param. 20/20 thread tests pass.
- **osiris cloned** to `Cursos/osiris` as a reference repo (data-aggregation
  patterns), alongside `worldmonitor`. Not wired into Atlas.
- **Lexicon recall baseline** (`77828cd`): `lexicon_recall_baseline.py` turns
  the coverage diagnosis into a standing metric. 8.9% overall candidate recall,
  6.6% on primary_evidence; noise recall (13.2%) > primary_evidence.
- **RQ1 answered at scale** (`73b08a2` + this commit): 691-row stratified
  benchmark (batch-03) → 3-vendor LLM-annotator panel (deepseek-chat, gpt-4.1,
  claude-sonnet-4-6), 691/691 each → majority-vote consensus gold (660 usable,
  Fleiss kappa 0.625) via new `build_annotator_consensus_gold.py` → LLM
  zero/few-shot classifier (1382 predictions) → `llm_baseline_compare`.
  Result: Atlas v2 **41.6%** vs LLM zero-shot **78.6%** / few-shot **81.1%**,
  Wilson CIs ~±4pts (vs ±12 at n=61). Thesis holds with statistical force.
- **Infra**: moved LLM/heavy-import work off the iCloud-synced repo `.venv`
  (eviction stalls; anthropic import once took 505s) to a dedicated local venv
  `/Users/pedro/AtlasLocalWorker/atlasvenv`. Repair if evicted:
  `pip install --force-reinstall --no-deps <pkg>`.
- **RQ1 improvement methods (all 4 measured/built)**: M1 scope gate 41%→70%
  precision (`score_gold_gate.py`); M2 evidence-role student v1 primary precision
  78% + v2 DB-features near-null (lever is gold+cluster purity, not features);
  M1↔M2 bridge: 90% of gate-kept errors are recoverable evidence; M3 theme-hint
  tail 20% precision, drop→48% (`topic_remediation_report.py`). Improvement doc:
  `docs/research/atlas-paper/phase-1-validation/2026-06-02-rq1-improvement-methods.md`.
- **3-vendor calibration cron** `com.atlas.threevendor-calibration` (03:00 daily)
  installed: runner + plist + additive installer; worker `.env` gained OpenAI +
  Anthropic keys (mode 600); smoke run Fleiss kappa 0.520 (n=67), rc=0.

## 2026-05-22 to 2026-05-31 (sessions 19-31 — Data quality, narrative threads, validation, emergent layer)

### Session type: Data operations, taxonomy quality, research validation, production wiring, documentation hygiene

### What happened
This block summarizes the intense late-May work that previously lived mostly in
`CLAUDE.md`, handoff docs, commit history, and research artifacts.

**2026-05-22 — hot/cold automation + NLP coverage**
- Automated the local hot/cold catch-up flow around
  `backend/scripts/local_hot_cold_catchup.py`, with launchd-safe execution from
  `/Users/pedro/AtlasLocalWorker` instead of the Desktop checkout.
- Added effective NLP coverage reporting and confidence-weighted sentiment
  fusion across hot pre-aggregates.
- Fixed HTML entity decoding and `xx` language handling in lexicon mining and
  scoring paths.

**2026-05-23 — Atlas topic classifier v2 and multilingual Path A**
- Promoted the bulk SQL atlas-topic classifier v2 path:
  `backend/scripts/backfill_lexicon_topics.py`, `signal_topic_assignments`, and
  `/api/v2/briefing.top_atlas_topics`.
- Applied migrations 034-035b to prune noisy GDELT hints, expand precise
  lexicons, and restore disease-outbreak medical hints after sample checks.
- Started AI-assisted taxonomy Path A with migration 036 for
  `election-legitimacy-dispute`.

**2026-05-24 — Living Narrative Threads becomes product canon**
- Completed Path A multilingual rollout with migration 038 and closed the first
  atlas-topic lexicon expansion track.
- Implemented the Living Narrative Threads beta:
  `backend/app/routers/threads.py`,
  `backend/app/services/thread_intelligence.py`, and the `/api/v2/threads`
  contract.
- Wired `frontend-v2/src/components/NarrativeThreads.tsx` and
  `ThreadFocusPanel.tsx` to the thread contract so the visible panel no longer
  routes through static theme detail by default.
- Canonized the backlog-first production cycle: frontend work interrupts only
  when the UI contradicts the data or breaks a contract.

**2026-05-25 to 2026-05-26 — Path B/Path C validation workflow**
- Corrected the mining/resource safety anchor with migration 039 while keeping
  slug compatibility.
- Audited all 30 atlas topics and tightened noisy terms/hints through
  migrations 040-041.
- Built `backend/scripts/topic_benchmark_harness.py` and moved the benchmark
  schema toward answerability, semantic scope, evidence role, and parent/child
  thread candidates.
- Started the Atlas paper/validation track: labeling guide, stratified sample,
  review packets, review templates, local review UI, and visual validation
  reports.

**2026-05-27 — paper track and rule-edit ceiling**
- Built LLM annotator tooling, kappa/agreement tools, bootstrap confidence
  intervals, and Sonnet baseline comparisons.
- Applied migration 042 from LLM multilingual vocab mining, then measured that
  broad lexicon additions did not improve precision.
- Wrote the paper master plan and methodology-paper outline. The operating
  conclusion: do not write the final paper before evidence, baselines, and
  ablations exist.

**2026-05-28 — multi-vendor consensus and precision roadmap**
- Expanded validation to a multi-vendor annotator panel across Claude, OpenAI,
  DeepSeek, and Pedro labels.
- Documented the main finding: Atlas static topic precision was around the
  42-51% band under full-taxonomy consensus, and remaining errors were mainly
  scope mismatch, not missing vocabulary.
- Applied migrations 043-044 for gold-guided precision removals; rule edits
  helped but hit a ceiling. The next architecture became a learned scope gate.

**2026-05-29 — learned scope gate shipped to production**
- Built and deployed a scope-aware keep/abstain classifier over
  `[sentence embedding || atlas confidence || matched terms]`.
- Production encoder is local `intfloat/multilingual-e5-base`, running from
  `/Users/pedro/AtlasLocalWorker/mlvenv` at `$0/signal`.
- Applied migration 045 (`gate_score`, `gate_kept`, `gate_model`) and wired
  gated counts into `/api/v2/briefing`.
- Closed #203 with the gate live in production.

**2026-05-30 — emergent topic discovery and context-gap diagnosis**
- Built the emergent topic discovery POC and production path:
  `backend/scripts/snapshot_emergent_topics.py`,
  `backend/migrations/046_emergent_clusters.sql`, `/api/v2/emergent`, and
  `cluster-<id>` theme detail routing.
- Wired emergent clusters into the Brief Watchlist first.
- Pedro identified the context miss: the primary visible app surface was
  `NarrativeThreads.tsx` via `/api/v2/threads`, not the Brief Watchlist. This
  triggered the explicit context-gap diagnosis and inventory proposal.

**2026-05-31 — threads/emergent completion + translation layer**
- Augmented `/api/v2/threads` with emergent cluster rows and added detail
  dispatch for `emergent-cluster-<id>`.
- Added lazy headline translation with `backend/migrations/047_signal_translations.sql`,
  `/api/v2/translate`, `/api/v2/translate/batch`, and bilingual evidence in
  `ThreadFocusPanel`.
- Closed the threads-wiring milestone in `CLAUDE.md`.

**2026-06-01 documentation hygiene follow-up**
- Compacted `CLAUDE.md` and archived older chronological blocks into
  `docs/state/archive/CLAUDE-history-2026-05.md`.
- Added `scripts/project_inventory.py` and generated
  `docs/state/PROJECT_INVENTORY.md`.
- Replaced the old architecture doc with `docs/ARCHITECTURE.md` and added
  `docs/000-INDEX.md` as the Obsidian vault entry point.
- Moved Atlas cold archive storage to the external disk at
  `/Volumes/Ext/Atlas/Archive`, keeping `/Users/pedro/AtlasArchive` as a
  symlink for compatibility.
- Updated the hot/cold runner so archive writes default to the external disk,
  processed historical outputs default to `/Volumes/Ext/Atlas/Processed`, and a
  missing external mount fails loudly instead of filling the internal disk.
- Verified all `59` archive manifest directories through the symlink:
  `272` manifest records and `3,947,759` represented rows.
- Added `backend/scripts/gate_coverage_report.py` so gate quality can be tracked
  as precision plus coverage/abstention, not precision alone.
- First 24h live report saved under
  `docs/research/atlas-paper/phase-1-validation/reports/gate-coverage/`:
  `16,878` assignments, `16,878` scored, `2,999` kept, `13,879` abstained,
  kept rate `17.77%`, unscored `0`.
- Started the Narrative Cluster Evidence Roles pilot plan: teacher LLMs provide
  roles, rationales, and reason codes offline; a local student model is the
  intended production classifier. The pilot explicitly separates `verified`,
  `candidate`, `context_rich`, and `suppressed` tiers so coverage can improve
  without lowering the verified precision target.
- Ran the first three-vendor evidence-role smoke over 10 sampled cluster
  signals using DeepSeek, OpenAI, and Anthropic. The consensus builder produced
  10 gold rows and 0 disagreements; student readiness remains
  `needs_more_labels` until the pilot has at least 100 consensus rows.
- Switched the evidence-role sampler to a multi-snapshot window: `--since-days`
  + `(cluster_label, signal_id)` dedup across all `emergent_clusters` snapshots
  in the window. Packet grew from `133` to `646` rows on the existing data,
  and will keep accumulating from the 4x/day cron toward the 1,000-1,500 target.
- Ran the full three-vendor teacher pass over the 646-row packet (DeepSeek,
  OpenAI gpt-4.1, Anthropic claude-sonnet-4-6). Consensus produced 605 gold
  rows and 41 disagreements (93.7% agreement); the student readiness report
  flipped from `needs_more_labels` to `ready_for_student_training`. Role mix:
  288 primary_evidence, 227 noise, 54 context, 23 reaction, 11 analysis,
  2 entity_reference. The 37.5% noise share quantifies off-topic membership
  inside emergent clusters and motivates the role layer as a precision filter.

### Key conclusion
Atlas moved from a static-topic dashboard toward a narrative-intelligence
system with three linked layers:

1. curated atlas-topic anchors,
2. learned precision gates over evidence,
3. emergent clusters and Living Narrative Threads as the user-facing model.

The documentation system now needs to behave like an operating map, not a
chronological scrapbook.

### Current documentation map
- `docs/000-INDEX.md` — Obsidian entry point.
- `docs/ARCHITECTURE.md` — human-maintained system diagram.
- `docs/state/PROJECT_INVENTORY.md` — machine-generated endpoint/API/table/cron
  inventory.
- `docs/state/archive/CLAUDE-history-2026-05.md` — archived session context.
- `docs/maps/` — human-curated Obsidian MOCs for data ops, narrative
  intelligence, validation/paper work, and frontend surfaces.

### Next
Keep the hygiene loop small: after meaningful changes, regenerate
`PROJECT_INVENTORY.md`, update the affected MOC, and keep `CLAUDE.md` focused
on current state plus pointers.

---

## 2026-05-16 (session 18 — Video UX review + productization roadmap)

### Session type: UX research, issue triage, roadmap planning

### What happened
Reviewed the three owner walkthrough videos through local transcripts and extracted visual frames:

- Landing walkthrough: `docs/research/ux-video-evaluation/transcripts/Screen Recording 2026-05-14 at 21.40.47.txt`
- Brief walkthrough: `docs/research/ux-video-evaluation/transcripts/Screen Recording 2026-05-14 at 21.53.02.txt`
- App walkthrough: `docs/research/ux-video-evaluation/transcripts/Screen Recording 2026-05-16 at 09.25.31.txt`
- App YouTube captions: `docs/research/ux-video-evaluation/transcripts/youtube-app-x8qlx2cijEE-es-auto.txt`

Added:

- `docs/research/ux-video-evaluation/2026-05-16-atlas-video-review.md`
- `docs/superpowers/specs/2026-05-16-atlas-productization-design.md`
- `docs/roadmap/2026-05-16-productization-roadmap.md`

### Key conclusion
The correct flow remains `Landing -> Brief -> App`, but Atlas needs a productization pass before more advanced features. The next product theme is:

**Make Atlas teachable, persistent, and exportable.**

### Issue work
Reopened with new video evidence:

- #56 Day/Night overlay + Settings utility
- #69 Spanish-language routing + multilingual query expansion
- #104 Google Trends missing/stale data
- #124 Saved watches / persistent alerts
- #128 Workspace viewport + Trail/Pinned graph clarity

Created:

- #135 Landing live stats + clickable docs/use-case cards
- #136 Landing -> Brief -> App prefetch/loading states
- #137 Methodology/editorial explanation
- #138 Investigation context persistence
- #139 Time range beyond 24h + Live/Pause semantics
- #140 Visual use-case manual with real Atlas screenshots
- #141 Reading Mode / investigation newspaper from pinned evidence
- #142 Public Attention scoping and actionability
- #143 Map layer explanation and decluttering

Expanded:

- #133 Workspace dossier should become the evidence foundation for Reading Mode.
- #134 Use cases should be visual and product-grounded, not text-only.

### Next
Start with P0 trust/continuity issues: #136, #137, #138, #128, #104/#142, and #69. After that, build the visual manual (#140/#134/#135), then Workspace Dossier and Reading Mode (#133/#141).

---

## 2026-05-14 (session 17 — Remaining closable issues closed)

### Session type: Issue closure + branch synchronization

### What happened
Started from the session 16 handoff and verified GitHub open issues. Found that local `v3-intel-layer` was 10 commits ahead of `origin/v3-intel-layer`; ran `npm run build`, committed the remaining-issues plan, and pushed `origin/v3-intel-layer` to match local before new work.

**Closed issues:**
- `220b91f` **#82** Temporal Narrative Graph selected bucket can now be pinned as a `temporal_snapshot` workspace node, with graph relationships to theme, countries, sources, people, and related themes.
- `7fb5eaa` **#61** Added shared `CompareDashboard` shell; ThemeCompare and PersonCompare now use one reusable 50/50 comparison overlay.
- `ea6c2ce` **#105** Safely ported only `backend/app/services/ingest_rss.py` from candidate branch; RSS registry now has 50 curated feeds across LATAM, MENA, Sub-Saharan Africa, and Southeast Asia.
- `2d3b2aa` **#70** Added frontend-only theme hierarchy: 7 clusters, 79 mapped codes, grouped EntityPanel related themes, and NarrativeThreads cluster labels.

**Blocked issues documented:**
- **#46** ACLED remains open with `blocked` label; needs real ACLED API access and credentials.
- **#106** Octopus mascot remains open with `blocked` label; needs designer SVG assets before implementation.

### Validation
- `cd frontend-v2 && npm run test` → 26 passed.
- `cd frontend-v2 && npm run build` → passed; existing large chunk warning only.
- `python3 -m py_compile backend/app/services/ingest_rss.py` → passed.
- `backend/.venv/bin/python -m pytest backend/tests/test_health.py -q` → 2 passed.
- Production Fly `/health` → 200 healthy after `82e2e77`.
- Production Fly and Vercel `/api/v2/narratives?hours=24&limit=3` → 200 JSON after `6e8e0df`.
- Production Vercel `/api/v2/stats` → 200 JSON.

### Production hotfixes
- `82e2e77` restored missing `datetime/timezone/asyncio` imports in `backend/app/routers/stats.py`; fixed `/health` 500 after deploy.
- `6e8e0df` restored missing runtime imports across split routers; fixed `/api/v2/narratives` 500 and prevented similar `app.state.redis`, `json`, and `datetime/timezone` failures in adjacent endpoints.

### Next
Production is deployed and smoke-tested on `v3-intel-layer`. Remaining open GitHub issues are blocked externally: #46 needs ACLED credentials, #106 needs designer SVG assets. Keep production on `v3-intel-layer` unless a separate branch-migration decision is made.

---

## 2026-05-14 (session 16 — Tier 5 sweep: 10 issues closed)

### Session type: Issue closure + feature work

### What happened
Continued from session 15. Triaged all 12 remaining open issues by effort, picked path of least resistance, closed 10 in one session.

**Verified already-implemented (3):**
- `#80` — Session graph: trackVisit, Trail tab, promote-to-pin all shipped in session 12
- `#79` — Public Attention AEIL: pin support, workspace node type, graph relationships, navigate-back all implemented
- `#114` — Workspace audit: wrote `docs/research/workspace-expert-audit.md` (synthetic expert walkthrough, drug-trafficking topic, 28-min session, 9 gaps documented, 4 new issues recommended)

**Bug fixes (3):**
- `2f97f19` **#129** Onboarding tour writes `localStorage` on mount → navigating away before Skip/Done no longer re-triggers tour
- `5e2499b` **#130** SourceIntegrityPanel: `filter.theme` routed through `getThemeLabel()`, raw GDELT codes gone
- `f5e4383` **#132** Workspace graph: compact dot + type initial when nodeCount ≥ 20 and globalScale < 1.2; full labels return on zoom

**Features (4):**
- `09d24be` **#131** Custom investigative concepts: `useCustomConcepts` hook (localStorage), `CustomConceptModal` (label + description + debounced theme search picker), SearchBar shows "My Concepts" section + "Save as concept" CTA
- `1888800` **#111** StreamLevel added to FocusContext GlobalFilter; SignalStream writes it on every tab click; AnomalyPanel shows THREAD/STREAM context badge; SourceIntegrityPanel shows level pill
- `37aaf0b` **#124** Saved watches: `useSavedWatches` hook, WATCH button (gold, toolbar, only when filter active), name dialog, watches section in /brief with Open-in-Atlas deep-link
- `3f42949` **#109** Evolution Graph: degree-1 nodes render at 55% radius + hide label below zoom 1.4; "⊞ Workspace" button pins theme + opens WorkspaceBoard

**Untracked audit fixes:**
- `21fa9d0` NarrativeThreads country pips → clickable buttons (setCountry + fly + onCountrySelect); thread click auto-opens CountryBrief for top country

**Documentation:**
- `#106` scoped in issue comment: needs designer SVG assets (3 poses, 3 costume overlays) before dev starts
- `1b2b35c` `docs/research/workspace-expert-audit.md` added

### Build status
`npm run build` passed (11s). 6 open issues remain — all L/research/blocked.

### Open issues after session
#82 (temporal+workspace), #61 (compare engine), #105 (RSS), #70 (theme clustering), #46 (ACLED, blocked), #106 (needs designer)

### Next
#82 is the highest-value remaining item — temporal narrative graph integration with WorkspaceBoard. Requires rethinking the bucket model.

---

## 2026-05-14 (session 15 — Issue blitz: Tiers 1–4 closed)

### Session type: Systematic issue closure

### What happened
Reviewed all 26 open issues, categorized into 4 tiers by impact/effort, and closed 14 in one session.

**Tier 1 — Already implemented, code-verified and closed (7):**
#108, #119, #120, #121, #122, #123, #127

**Tier 2 — Bug fixes (2):**
- `9a0cb5d` **#128** Workspace: Trail and Pinned are now separate graph modes; header fixed; charge strength auto-scales
- `9a0cb5d` **#110** Top Sources LIMIT 10 → 20 in backend theme endpoint

**Tier 3 — UX polish (3):**
- `c265c77` **#126** TemporalNarrativeGraph hover dims unconnected nodes/links (refs pattern for frame stability)
- `cbd58b2` **#112** Related Topics compare button: VS → icon + tooltip + CSS class + overflow fix
- `9eadc3f` **#113** Signal Stream entry: green flash + left border glow animation (650ms, live-arrival feel)

**Tier 4 — Tech debt (2):**
- `547db58` **#107** PanelSkeleton shimmer component; stale-while-revalidate in ThemeDetail; skeletons in NarrativeDrift + FocusSummaryPanel
- `bf037cf` **#125** Backend split: main_v2.py 4958→120 lines, 12 APIRouter files, app/db.py, app/utils.py

### New issues opened during session
- **#129** Guided tour re-triggers every visit (bug — should be localStorage-gated)
- **#130** Raw GDELT code `CRISISLEX_CRISISLEXREC` visible in Source Integrity panel
- **#131** Custom investigative concepts (feat)
- **#132** Workspace graph label overlap at 26+ nodes

### Build status
`npm run build` passed (15s). All 43 backend routes import-verified with `.venv` Python.

### Next
#129 (guided tour bug) + #130 (raw code bug) — both small, high-visibility.

---

## 2026-05-14 (session 14 — UX Panel Evaluation Ronda 2)

### Session Type: Documentation & UX Research (no code shipped)

### Context
Between sessions 12 and 14, significant work was done by Claude Code (sessions 10–13), shipping 14 of the 16 issues identified in our first evaluation. This session re-evaluates Atlas against the same 5-persona panel to measure progress.

### UX Panel Evaluation Ronda 2 (5-persona re-audit)
Re-evaluated against production (observatory-global.vercel.app):

| Evaluator | Sesión 12 | Sesión 14 | Delta |
|-----------|:---------:|:---------:|:-----:|
| **Investor (VC)** | 7/10 | 8/10 | **+1** |
| **CTO** | 7.5/10 | 8.5/10 | **+1** |
| **Journalist** | 7/10 | 8/10 | **+1** |
| **Product (UX)** | 7/10 | 8.5/10 | **+1.5** |
| **Intelligence Analyst** | 8/10 | 8.5/10 | **+0.5** |
| **PROMEDIO** | **7.3** | **8.3** | **+1.0** |

### Issues Verified as Resolved (from Session 12 → closed by Claude Code)
#108, #112, #113, #119, #120, #121, #122, #123, #125, #126, #127, #128, #107

### New Issues Created (from Ronda 2 findings)
- **#129** — Guided tour re-triggers on every console visit ← bug, should only show first time
- **#130** — Raw theme code `CRISISLEX_CRISISLEXREC` visible in Source Integrity ← `getThemeLabel()` rule violation
- **#131** — Allow users to create custom investigative concepts ← owner-endorsed scope expansion
- **#132** — Workspace graph label overlap with 26+ nodes ← follow-up to #128

### Owner Notes
- Custom investigative concepts (#131) endorsed as an important scope problem — the 6 fixed concepts demonstrate the engine's power but limit the analytical lens.

---

## 2026-05-12 (session 12 — UX audit, panel evaluation, documentation)

### Session Type: Documentation & UX Research (no code shipped)

### Added
- **Ephemeral Session Trail (#63)** — `WorkspaceContext` now tracks up to 20 visited items per session. `workspaceGraph.ts` generates chronological `session-trail` links. `InteractiveWorkspace` renders session nodes with dashed borders and includes a "Show Session Trail" toggle. `App.tsx` auto-tracks visits to countries, themes, sources, persons, and public attention items.
- **CompareSearchModal integration** — rescued from Claude Code worktree (`competent-maxwell-4eb03c`) and integrated into EntityPanel.
- **Z-score heat map logic** — backend `/api/v2/nodes` now uses statistical z-score instead of absolute counts for anomaly heat representation.
- **Google Trends expansion** — coverage expanded from 30 to 84 countries (commit `7594cb3`).

### UX Panel Evaluation (5-persona audit)
Conducted a rigorous multi-persona UX audit against production (observatory-global.vercel.app):

| Evaluator | Verdict | Key Finding |
|-----------|---------|-------------|
| **Investor (VC)** | 7/10 | `/brief` is the killer feature — lead with it. No clear ICP yet. |
| **CTO** | 7.5/10 | `main_v2.py` monolith (4,100 lines) is tech debt #1. Error boundaries are excellent. |
| **Journalist** | 7/10 | Source Family badges are powerful. Signal Stream is noise — needs editorial default. |
| **Product (UX)** | 7/10 | Dashboard default is overwhelming. "CF CF" country name bug found in production. |
| **Intelligence Analyst** | 8/10 | 4-source cross-correlation is unique. English-language bias needs disclaimer. |

**Overall: 7.3/10** — "Atlas doesn't need more features. It needs to decide who its #1 user is."

### Issues Created (from audit findings)
- **#119** — Brief country filter should include ALL countries (not just highlighted) ← owner-reported
- **#120** — Default Signal Stream to NOTABLE/CRITICAL, not ALL ← relates to #111, #113
- **#121** — Add coverage bias disclaimer to dashboard ← relates to #105, #91, #70
- **#122** — Country Brief shows "CF CF" instead of full name ← bug
- **#123** — Make Workspace tab more discoverable ← relates to #114, #80
- **#124** — Saved searches / persistent alerts for investigative patterns ← relates to #61, #80
- **#125** — Refactor main_v2.py into APIRouter modules ← relates to #107, #73
- **#126** — TemporalNarrativeGraph hover-to-focus (dim unselected) ← relates to #82, #109
- **#127** — Filter entertainment from Public Attention panel ← relates to #78, #85

### Cross-reference with existing open issues
| Existing Issue | Audit Finding |
|---------------|--------------|
| #111 (Stream filter accessibility) | Confirmed: ALL default is wrong. → #120 created |
| #113 (Stream show volume) | Confirmed: volume metric exists but doesn't help curation |
| #114 (WorkspaceBoard UX research) | Confirmed: workspace is hard to find → #123 created |
| #109 (Evolution Graph interactions) | Confirmed: spaghetti effect → #126 created |
| #107 (perf audit) | Confirmed: would benefit from router split → #125 created |
| #105 (RSS feed expansion) | Confirmed: bias is structural, not just volume → #121 created |
| #82 (Temporal graph integration) | Confirmed: needs hover-to-focus → #126 created |

### Owner Notes
- Monetization: owner prefers Wikipedia-style donation model (free for the world). Not pursuing SaaS.
- Philosophy: Atlas exists to help users escape algorithmic echo chambers and see beyond their local information bubble.

---

## 2026-04-24 (session 2)

### Added
- **EntityPanel component** — right panel for person/keyword search results. Shows: trust indicators (source diversity, countries, global sentiment), coverage by country (bar chart colored by sentiment), related themes (clickable chips → ThemeDetail), top sources with sentiment, recent headlines. Opens automatically when `focus.type === 'person'`.
- **Keyword search fully connected** — SearchBar now triggers map fly + correct panel for all result types:
  - Country result → fly + CountryBrief
  - Theme result → fly to top country + ThemeDetail + arcs
  - Person result → fly to top country + EntityPanel (person-filtered map)
- **FocusContext: person as first-class focus type** — added `person: string | null` to `GlobalFilter`, `setPerson()` method, `focus.type` now returns `'person'`. Previously `setFocus('person',...)` called `clearFilter()` silently.
- **Search endpoint enriched** — themes and persons now return `total_signals` + `top_countries [{code, name, count}]` (needed for map fly). TAX_* and WORLDLANGUAGES_* themes excluded from results. Redis cache 2 min.
- **Search dropdown redesigned** — country tag (blue), person tag (violet), signal count + top country codes in meta. ESC closes, × button clears.

### Fixed
- `setFocus('person', ...)` was silently calling `clearFilter()` — EntityPanel never rendered
- Country click inside EntityPanel now calls `clearFocus()` first so CountryBrief can take over
- Theme search was matching GDELT taxonomy codes (TAX_WORLDFISH_TRUMPETER for "trump") — filtered

### Known issues / Roadmap
- AI insight: account needs Anthropic credits (key is loaded, auth works)
- Person click inside CountryBrief/ThemeDetail pill → still no action (separate from search)
- Aircraft: still amber dots, needs intelligence-value filter (military/diplomatic callsigns)
- Maritime vessels: AISStream Phase 3C, not started
- Globe 3D: deferred

### Next session
- Sort/rank for article coverage in ThemeDetail (currently timestamp, consider relevance)
- Hosting: move off local Mac → Fly.io (backend) + Vercel (frontend)
- Aircraft intel layer: filter by military/diplomatic callsigns (ADSBExchange)
- Maritime layer design + implementation

---

## 2026-04-24

### Added
- **Country territory click** — Mapbox fill layer (`country-heat-fill`) click handler replaces node dot clicks. Clicking anywhere on a country's geography fires `handleCountryClick`. Includes `ISO_TO_GDELT` mapping for code mismatches (ID→RI, RS→RB, XK→KV, etc.)
- **Node dots removed** — `nodes-core` ScatterplotLayer deleted. Territory click handles selection. Anomaly pulse rings (red circles for crisis countries) preserved.
- **NODES toggle button removed** — was controlling the now-deleted dots layer.
- **AI insight error codes** — backend now returns `insight_no_credits` (vs `insight_unavailable`) when the Anthropic API rejects due to low balance. ThemeDetail shows actionable message: "Anthropic account has no credits (top up at console.anthropic.com)"
- **Insight model fix** — model name corrected from `claude-haiku-4-5` → `claude-haiku-4-5-20251001`
- **CorrelationMatrix parse error fix** — removed IIFE pattern `(() => { ... })()` inside JSX ternary (Babel parser incompatible). Refactored normalization into a plain variable block before the return.

### Known issues / Roadmap
- **AI insight**: `ANTHROPIC_API_KEY` is loaded and auth works, but account has no API credits — add funds at console.anthropic.com to activate
- People Mentioned: pills shown but person click → no action yet
- Keyword/company search: SearchBar exists but free-text search not connected to backend
- Aircraft icon: still amber dot, real plane SVG shape deferred
- Maritime vessel layer (AISStream): Phase 3C, not started
- Globe 3D: deferred

### Next session
- Signal stream sort order — review how articles are ordered inside ThemeDetail recent coverage (currently by timestamp, consider by relevance/sentiment)
- Person click → search/filter view
- Keyword search → backend `/api/v2/search?q=` endpoint
- Aircraft icon → real plane SVG shape

---

## 2026-04-23 (session 2)

### Added
- `COUNTRY_COORDS` static coordinate table in App.tsx — map fly now works for countries without active signals (Slovenia, Tanzania, Albania, etc.)
- `CountryThemePanel` component — right panel showing a country's specific coverage of a theme (timeline, sources, articles, related topics). Positioned at right:0, z-index 500
- ThemeDetail `hasRightPanel` prop — shifts overlay left (padding-right: 420px) so it doesn't cover CountryThemePanel
- ThemeDetail `onCountryCardClick` prop — "How It's Covered" cards now update the right CountryThemePanel instead of drilling in center
- ThemeDetail `originCountry` — origin country appears first in "How It's Covered" grid with blue highlight
- `rightPanelThemeCountry` state in App.tsx — manages which country+theme to show in right panel
- Backend: `load_dotenv()` added to main_v2.py to auto-load root `.env` (fixes ANTHROPIC_API_KEY not found)
- Better insight error message: "AI analysis not configured — add ANTHROPIC_API_KEY to .env and restart the backend"
- Welcome card switched from `localStorage` to `sessionStorage` — shows on every new session, not once ever
- AnomalyPanel now calls `setFocus('country', code)` + `setMapFlyCountry(code)` — map flies on anomaly click
- CountryBrief: `useCrisis()` anomaly lookup — shows `▲ Nx above 7-day baseline` badge + spike indicator on top theme
- CountryBrief: `WORLDLANGUAGES_` and `TAX_WORLDLANGUAGES_` themes filtered from top themes (GDELT language metadata, not actual topics)
- Help mode toggle (`?` button in toolbar) — cursor changes, `[data-help]` hover tooltips enabled globally
- `data-help` attributes on ThemeDetail section headers

### Fixed
- AnomalyAlert click had no map fly (used `setCountry` not `setFocus`)
- CountryBrief theme click opened ThemeDetail without country context or map fly
- ThemeDetail showed "Coverage analysis unavailable" without explanation
- Welcome card never showed again after first dismiss
- ThemeDetail auto-drilled into country (reverted) — now always shows global view
- "Language: Slovenian" no longer appears in top themes (GDELT language tag, not topic)

### Known issues / Roadmap
- ANTHROPIC_API_KEY: backend must be restarted after adding key to .env
- People Mentioned: pills shown but person click → no action yet (search/filter by person not implemented)
- Keyword/company search: SearchBar exists but free-text topic search not yet connected to backend
- Aircraft icon: still amber dot, real plane shape deferred
- Maritime vessel layer (AISStream): Phase 3C, not started
- Globe 3D: deferred to later phase
- OpenSky free tier: ~1 req/60s rate limit

### Next session
- Person click → search/filter view
- Keyword search → backend `/api/v2/search?q=` endpoint
- Maritime vessel layer (AISStream Phase 3C)
- Aircraft icon → real plane SVG shape
- UX: first-minute experience / onboarding improvements

---

## 2026-04-23

### Added
- AI Coverage Insight endpoint: `GET /api/v2/theme/{theme_code}/insight` (Claude Haiku, Redis-cached 15 min, Ollama fallback)
- `anthropic>=0.40.0` added to backend/pyproject.toml
- `.env.example` updated with `ANTHROPIC_API_KEY`, `INSIGHT_PROVIDER`, `OLLAMA_HOST`, `OLLAMA_MODEL`
- ThemeDetail: async insight block, person pills, 2-col related grid, source-filter for Recent Coverage
- FocusContext: `mapFlyCountry` state + `setMapFlyCountry()` for cross-component fly-to hints
- App.tsx: 4 new effects — map fly from Correlation Matrix, fly from NarrativeThreads hint, open ThemeDetail on filter.theme change, close CountryBrief on external country clear
- ESC handler and close callbacks now call `clearFocus()` consistently
- ArcLayer now renders on theme focus; `filter.theme` added to layers useMemo deps

### Fixed
- CountryBrief re-open bug (close was being overridden by focus sync)
- NarrativeThreads theme click only showed pill — ThemeDetail never opened
- Country click in Correlation Matrix did not animate map

### Activate insight feature
Add `ANTHROPIC_API_KEY=sk-ant-...` to `.env`. Without it the endpoint returns `insight: null` gracefully.

### Known issues
- OpenSky free tier rate limits (~1 req/60s recommended)
- Globe 3D deferred to later phase
- Some GDELT theme codes still not in manual label dictionary

### Next session
- UX first minute experience (auto-focus, welcome card)
- Maritime vessel layer (AISStream Phase 3C)
- Aircraft icon → real plane shape

---

## 2026-04-20

### Added
- Aircraft layer: OpenSky integration, amber dots, PLANE toggle
- Graceful degradation for API rate limits (no fake data)
- ThemeDetail framing section promoted to top
- Correlation Matrix → CountryBrief click navigation
- Source Integrity: real domain names from backend (extract_domain)
- GDELT theme label improvements (regex cleanup in themeLabels.ts)
- README rewritten for Atlas public launch
- CONTRIBUTING.md added

### Known issues
- OpenSky free tier rate limits (~1 req/60s recommended)
- Globe 3D deferred to later phase
- Some GDELT theme codes still not in manual label dictionary

### Next session
- UX first minute experience (auto-focus, welcome card)
- Maritime vessel layer (AISStream Phase 3C)
- Aircraft icon → real plane shape

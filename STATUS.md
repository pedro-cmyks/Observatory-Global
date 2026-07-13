# Atlas — Session Status
**Branch:** `v3-intel-layer` (canonical production/main) | **Updated:** 2026-07-13

## Current handoff — Spec reconciliation + shared publication foundation

- The July 12 Investigation Graph spec was crossed against the June Workbench
  workflow, Living Narrative Threads, movement/Kalman, dossier v3,
  corroboration, event bindings, voice, history, subject geography and
  paper-validation records. The result is recorded in
  `docs/state/2026-07-12-spec-history-crosswalk.md`: the graph is a needed
  composition contract, not permission to rebuild existing measurement brains.
- New deterministic contracts are implemented locally:
  `atlas-investigation-graph-v1` and `atlas-publication-package-v1`. Coverage
  geography is contextual, semantic proximity is inferred, distinctive actor
  overlap/exact receipts are measured, and analyst edges remain separately
  typed. The package inventories 5W+H, receipts, gaps, method and
  reproducibility without an LLM.
- Workbench now maps every heterogeneous pin into the typed graph and renders
  `who / what / when / where / how / why` as ready, partial or missing. Unknown
  anchor types remain explicit context instead of being guessed into entity or
  story identity. All frozen pins and receipts reach the publication/synthesis
  input; inherited six-receipt and enrichment top-N cuts were removed.
- A complete-universe Daily Investigation builder traversed 458/458 top-level
  topics and stored one sealed `atlas_daily_editions` artifact. Serving is a
  single compact indexed-row read. L1 now reads that shared package, but only
  promotes it when the artifact is `ready`, its contracts match, its complete
  candidate universe is disclosed and story nodes exist. The current artifact
  remains deliberately `degraded`, so production displays the visible live
  fallback instead of presenting it as a publishable edition.
- The L1 selector uses per-topic movement/surprise/evidence/persistence state,
  Pareto fronts and equal percentile aggregation. Raw volume, crisis status and
  content category have zero importance weight. Twelve slots are newspaper
  layout only; all 458 selection rows remain in the ledger.
- The old relation provider's 64-story operational window no longer silently
  takes a prefix: the typed graph still processes the full set with exact and
  contextual engines and marks the legacy provider unavailable for that run.
  Its recent-member sample and visual-neighbor selection now disclose method,
  size and truncation metadata.
- Reliability truth is summarized in
  `docs/state/2026-07-13-l0-l3-reliability-matrix.md`. L2 is the strongest
  standalone surface. L1 is a useful front door but not yet the new publishable
  package. L3 has the adapter/readiness foundation but still needs the full
  heterogeneous Iran forcing-case pass.
- Current verification: backend `1285 passed, 6 skipped`; frontend `306 passed`;
  production Vite build passes. The Fly backend is deployed and health,
  Research Plan, and stored Daily Publication smokes pass.
- During verification, the recurring embed writer held the heavy mutex for
  about 400 minutes because writes thrashed the shared 1 GB database's HNSW
  index. The live writer was allowed to finish its downstream chain after stuck
  transactional inserts were cancelled. The maintenance path now sweeps before
  index work and restores HNSW from an outer `finally`; a controlled bulk-index
  measurement found a second MPS command-buffer stall after 2,304 rows and
  confirmed that index rebuild I/O can time out production threads. HNSW builds
  at `m=16/8/4` could not stay inside the shared instance envelope, so the hot
  corpus was cut over to IVFFlat (`327` lists). At probes 20, a dispersed
  20-query benchmark reached recall@10 `1.000` with 130.97 ms mean latency, and
  a rolled-back 256-row insert took 172.429 ms. Serving now sets probes 20
  explicitly. #241 stays open through the first complete recurring pipeline;
  P1.2 isolation remains the architectural cure.
- The production smoke also proved a pipeline-order defect: raw ingest was
  fresh while typed memberships were stale. The scoped runner now projects
  `topic_members` and recomputes movement after fresh thread identities and
  before event binding/daily sealing. A first live recovery attempt was stopped
  after 6/136 countries because the sequential country loop degraded serving;
  its 139 unprojected cluster rows were removed by exact snapshot id. The next
  operation is an atomic/staged runner redesign, not a blind rerun.
- A separate production paint-budget failure was isolated: the legacy
  `top_sources` and `theme_country` sections each consumed their full optional
  database timeout, taking `/api/v2/briefing` to about 19.2 seconds and beyond
  the client's 12-second budget. Those optional sections now fail fast at 1.5
  seconds while core sections retain their 8-second budget. A warm production
  response measured 6.47 seconds and rendered L1 with both gaps disclosed.
  Availability is restored; editorial quality is still red because several
  visible thread labels do not match their current evidence.
- The abandoned 139-row partial snapshot was removed by exact snapshot id. The
  last complete snapshot was reprojected through `topic_members`, movement,
  event/disaster bindings and daily sealing. The new artifact reconciles
  546 candidates, 12 layout stories and 71 frozen receipts at 5.4 hours lag.
  Current-cluster labels replace stale lifecycle labels only for the edition;
  stable topic identity remains separately receipted.
- Publication evidence fit is now measured over the complete eligible
  single-cluster universe with `text-embedding-3-small`. A bivariate low-tail
  rule (pair median + label median, q=0.10) downranked 7/150 incoherent
  candidates, including the mixed Lindsey Graham cluster, without deleting
  them from L2 or the ledger. The rule is provisional and not paper-grade gold.
- The scoped snapshot runner stages every country and commits one snapshot only
  after all scopes finish. Production defaults no longer cap per-country input
  or retained clusters; diagnostic caps remain explicit opt-ins. Projection is
  skipped if staging fails, so a partial snapshot cannot become product state.
- Workbench Research Plan no longer asks the volume-ranked top 24 or retains
  only three weak supports. It evaluates the complete current thread universe,
  keeps every candidate accessible, and reserves the primary tray for direct
  or contextual matches. Coverage geography is explicitly not subject
  geography. The first deployed pass still promoted unrelated German, Russian
  and Ukrainian rows through generic topic vocabulary. The corrected gate now
  requires an explicit target label or visible coverage-country connection for
  geo-scoped primary context, and exact current-label duplicates remain
  accessible but do not repeat in the primary tray. A live production-shaped
  Iran query evaluated 581 candidates with embeddings: 11 primary, 570
  low-confidence, 0 omitted; no unrelated geo rows or duplicate labels remained.
- Current verification: backend `1306 passed, 6 skipped`; frontend `308 passed`;
  production Vite build passes.

Primary records:

- `docs/state/2026-07-12-spec-history-crosswalk.md`
- `docs/state/2026-07-13-l0-l3-reliability-matrix.md`
- `docs/state/2026-07-13-ann-index-recovery.md`
- `docs/research/atlas-paper/phase-1-validation/reports/2026-07-13-publication-evidence-fit.md`
- `docs/superpowers/plans/2026-07-12-investigation-graph-slice-3-daily-publication.md`

## Current handoff — Shared L1/L2/L3 Investigation Graph

- Pedro approved the product architecture in
  `docs/superpowers/specs/2026-07-12-investigation-graph-l2-l3-design.md`.
  L1 is a system-built 24h investigation, L2 is the standalone single-focus
  exploration instrument, and L3 is the multi-focus editorial composition
  studio. L1 and L3 must emit the same publication-grade `PublicationPackage`.
- Reliability Slice 1 is deployed. The default stories-only Narrative Threads
  path no longer runs the atlas-category query it discards; database-owned
  command timeouts return honest `503 db_busy`; semantic centroid, taxonomy,
  and headline retrieval now degrade independently.
- Fresh backend verification: `1230 passed, 6 skipped, 0 failed`. Fly API image
  `deployment-01KXCRYT1K1VN352NZC04K5Q77`, app machine version `398`, health
  `1/1 passing`.
- Post-deploy production: threads returned `10` rows at 24h and `24` at 168h;
  NATO 24h returned one pineable thread without a timeout gap; the Iran case
  returned 13 thread anchors / 6 pin candidates and opened a 66-signal detail
  with 23 evidence receipts.
- Delivery is graded `pass_with_caveats`: the integrated browser controller
  could not attach a fresh tab for the visual smoke, and unrelated
  anomaly/correlation queries still show handled shared-DB timeouts. P1.2
  serving/batch isolation remains necessary.
- Typed-node Slice 2 is now deployed: `atlas-investigation-v2`, stable identity,
  immutable snapshot/live reference separation, ten accepted node families,
  canonical thread/signal enrichment, and stateless
  `POST /api/v2/investigation/resolve-node`. Other families pin honestly as
  metadata-only until their canonical adapters land.
- Next executable slice: stateless graph assembly + typed edge receipts, proven
  by a multi-object Iran forcing case before changing UI.

Primary records:

- `docs/superpowers/plans/2026-07-12-investigation-graph-slice-1-reliability.md`
- `docs/state/2026-07-12-investigation-graph-slice-1-reliability.md`
- `docs/state/2026-07-12-investigation-graph-slice-2-node-foundation.md`

---

## Current handoff — Subject geography Stage 1 + event relationship audit

- #238 Stage 1 is delivered as a deterministic, read-only complete-universe
  report. It uses multilingual headline patterns, NER/gazetteer evidence,
  member consensus, persisted e5 similarity, source breadth, temporal stability,
  explicit uncertainty, and abstention. Coverage geography cannot create a
  subject candidate; no LLM classification or database write occurs.
- Live 14-day run exhausted all `active,candidate` rows: `1,442/1,442` topics in
  29 cursor batches, 0 retries/failures. `140` inferred a primary subject
  country and `1,302` abstained; `409` had no hot-window evidence members.
- Full ledgers and ablations are under `docs/research/subject-geography/`.
  Archive comparison is labeled a weak lexical proxy because its OpenAI 1536-d
  vectors are incompatible with the dynamic-topic e5 768-d space; proxy
  disagreement is not called an error.
- Event/thread truth was verified: hazard and CAMEO events attach after thread
  formation as `role='movement'` context and do not increase evidence/confidence.
  Baseline spikes are derived movement properties, not topic members.
- #255 tracks structured, accessible hover receipts for hazard/conflict/anomaly
  markers using official USGS/GDACS structured APIs and explicit external links.
- #256 tracks stale event-to-thread bindings: ingest is current, but
  `disaster-v1` and `movement-v1` bindings lag after snapshot timeouts.

Primary execution record:
`docs/superpowers/plans/2026-07-12-subject-geography-math-first.md`.

---

## Current handoff — Consolidation, stability, and C7

- Canonical GitHub cleanup: obsolete PRs #118 and #144 closed; legacy `main` retained only as history, not as the active merge target.
- P1.1 landed with one heavy-job owner, owner TTL metadata, no eviction of a live overdue PID, and explicit asyncpg-only `db_busy` degradation.
- `/api/v2/threads` bounds dynamic candidates before correlated member aggregation. Read-only production EXPLAIN: 48.166 ms global and 242.154 ms country-scoped, with no sequential scans in either plan.
- Dynamic-topic confidence is nullable and labeled measured/unscored; non-crisis acceleration is neutral, not red.
- Brief uses stale-while-revalidate for up to 24 hours and retains cached content on refresh failure with a visible notice/retry path.
- Python/Node installations were repaired; duplicate `orjson` manifest entry removed.
- C7 voice-asymmetry pilot is delivered under `docs/research/voice-asymmetry/`. Live 168h run: 100 topics, 49 eligible, 18 review hits. Stage 1 of #238 now supplies a conservative subject-country candidate ledger, but C7 remains read-only and must not enter UI/ranking/cron before joint validation.
- Dirty and Codex-host-owned worktrees were deliberately preserved; no user work was deleted.

Primary execution record: `docs/superpowers/plans/2026-07-12-consolidation-stability-c7.md`.

---

## Historical handoff (2026-06-09) — Dynamic-topic state pilot

---

Implemented the first read-only Kalman/state-tracking pilot for
`dynamic_topics`. This is **not** a semantic classifier and does not write to
production tables.

Shipped locally:

- `backend/scripts/dynamic_topic_state_report.py` estimates smoothed intensity,
  velocity, uncertainty, surprise, and trend from each topic's
  `dynamic_topic_members` / `emergent_clusters` snapshot history.
- The report preserves the existing lifecycle state separately from the Kalman
  reading, so `active/candidate/deprecated` remains the source-of-truth lifecycle
  decision.
- Explicit `News Roundup` / `Mixed News` labels are marked
  `do_not_promote_roundup`, even if their movement signal is surging.
- High-noise topics remain `do_not_promote_high_noise`.
- Generated artifacts:
  - `docs/research/topic-quality/2026-06-09-dynamic-topic-state-pilot.json`
  - `docs/research/topic-quality/2026-06-09-dynamic-topic-state-pilot.md`

Live read-only result over active/candidate topics:

- 12 topics reported.
- 6 explicit roundup candidates flagged `do_not_promote_roundup`.
- 2 active topics flagged `watch_acceleration`.
- 2 active topics flagged `watch_decay`.
- 1 high-noise candidate flagged `do_not_promote_high_noise`.

Verification:

- `cd backend && .venv/bin/python -m pytest tests/test_dynamic_topic_state_report.py tests/test_project_dynamic_topics.py -q`
  -> `18 passed`.
- Live script run used the gitignored root `.env` `DATABASE_URL`; it wrote only
  the JSON/Markdown report artifacts under `docs/research/topic-quality/`.

Next order:

1. Review whether the `watch_acceleration` / `watch_decay` rows should become a
   recurring monitoring report or stay as manual research.
2. If useful, add a dry-run cron/report wrapper; do not write Kalman estimates to
   DB until the metric proves useful across several snapshots.
3. Rotate secrets in a separate maintenance pass before the next
   credential-bearing deploy cycle.

---

## Current product target (2026-06-09) — Research Workflow + Workbench

The next major product objective is no longer a one-off Iran climate search. It
is a general Atlas investigation workflow for natural compound searches.

New design spec:

- `docs/specs/2026-06-09-research-thread-builder-workbench.md`
- GitHub: #213 (`feat(search/workbench): support research workflow from natural
  search to pinned investigation`)

Forcing case:

- "climate/water in Iran and the Middle East";
- plus a related branch for attacks on US/allied bases, satellite imagery,
  communications/radar infrastructure, and regional water/energy security.

Product correction from Pedro:

- Search should not directly create a finished dossier.
- Search should generate useful anchors/options: country focus, Narrative
  Threads, source lanes, public-attention lanes, coverage gaps, and related
  branches.
- The user investigates naturally inside Atlas by opening those anchors and
  pinning useful items.
- Workbench emerges as the memory/organizer of the route and can later generate
  a report/dossier from pinned evidence.
- `dynamic_topics` and Narrative Threads should not be treated as separate
  product concepts. `dynamic_topics` is the current implementation/lifecycle
  backing for many user-facing threads.
- The key ranking problem is investigative usefulness: Atlas should rank
  anchors by intent fit, thread coherence, evidence strength, answerability,
  movement, source/actor value, geo/entity fit, novelty/gap value, and penalties
  for noise, unsupported claims, or list/detail mismatch.
- Ranking/downranking must be transparent and reversible. Atlas should expose a
  downranking ledger with reason codes instead of silently hiding candidate
  information.
- Search should support how people actually search: reformulating queries,
  following trails, inspecting social/public discussion, and saving separate
  investigations over time.
- Reddit/forum discussion is a public-attention and narrative-discovery lane,
  not verified evidence by default.

The spec defines the expected product outcome:

- natural query interpretation and anchor options;
- thread/country/source/public-attention entry points;
- investigative-usefulness ranking;
- ranking explanations and downranking ledger;
- Reddit/public-discussion lane;
- saved investigations/sidebar model for Workbench;
- who-says-what source/actor matrix;
- frame comparison;
- coverage gaps;
- list/detail reconciliation;
- Workbench pinning, route memory, and optional report/export path.

Current Atlas gap found during the experiment:

- Atlas detects Iran and can suggest climate/water concepts, but direct
  query-thread searches for `Iran climate water drought`, `Iran water shortage`,
  `Iran drought`, `Tehran water`, `Iran heatwave`, `Iran dams`, and
  `Iran water crisis` returned 0 signals.
- `/api/v2/threads?country_code=IR&hours=168` did return Iran threads, including
  `flood-landslide-disaster--ir`, but scoped theme detail for the same apparent
  story returned 0. The builder must reconcile list/detail contradictions.
- Signal Stream for Iran returned relevant geopolitical signals mixed with
  unrelated/noisy rows; intent-aware stream retrieval is required.

Next implementation should start with Phase 0/1 from the spec: create the Iran
compound walkthrough fixture, then build a read-only `/api/v2/research/plan`
prototype before changing public UI.

---

## Current handoff (2026-06-08/09) — MVP issue closeout shipped

Current repo state: `v3-intel-layer` is aligned with `origin/v3-intel-layer`.
Commit `ca2130b` (`feat(mvp): align search and country thread truth`) has been
pushed, the Fly API process has been deployed with the API-only lightweight
target, and the Vercel frontend is serving the matching build bundle.

What shipped:

- **Search becomes a thread creator (#175 slice):** `GET /api/v2/search/thread`
  builds a temporary `query-thread::<raw query>` detail packet from direct
  evidence. The old curated concept-map suggestions remain hidden from the
  user-facing search flow.
- **Signal Stream relevance (#177 slice 1):** `/api/v2/signals` returns
  `lane` and `relevanceScore`, supports `lane=` and `sort=relevance`, and the
  frontend separates analyst-relevant items from sports/entertainment noise in
  the Notable/Critical/Elevated/Trend tabs.
- **CountryBrief thread count fix (#174/#207):** the CountryBrief metric no
  longer counts a local `topCounts(..., 12)` slice of GDELT themes as visible
  "themes". It fetches `/api/v2/threads?country_code=<country>` and displays
  that country-scoped Narrative Thread count and rows. If no thread clears the
  gate, the visible count is `0`, not a forced `12`.
- **CountryBrief resilience:** optional side fetches for indicators, trends,
  wiki, nodes, and threads no longer blank the whole country panel if one request
  fails. Country signals remain the critical fetch.
- **Query-thread country alias:** `/api/v2/search/thread` now accepts
  `country_code` as well as `country`, matching ThemeDetail's scoped fetch
  convention.
- **License batch:** source-available migration to PolyForm Noncommercial
  shipped with the MVP closeout commit.

Verification on 2026-06-08:

- `cd backend && .venv/bin/python -m pytest tests/test_query_thread.py tests/test_query_thread_router_contract.py tests/test_signals_lane_contract.py tests/test_stream_relevance.py -q`
  -> `29 passed`.
- `cd frontend-v2 && npm test -- src/lib/countryBriefFetch.test.ts src/lib/countryBriefThreads.test.ts`
  -> `2 files passed / 3 tests`.
- `cd frontend-v2 && npm test -- src/lib/countryBriefThreads.test.ts src/lib/narrativeThreads.test.ts src/lib/themeDetailEmptyState.test.ts src/lib/searchResults.test.ts`
  -> `4 passed / 8 tests`.
- `cd frontend-v2 && npm run build` passed.
- In-app browser smoke on local backend + Vite dev passed the target flows:
  query-thread CTA opens without `HTTP 404`; `/app?country=CO` renders
  CountryBrief with `10 threads`, a `Narrative Threads` section, and no `Top
  Themes` fallback.

Production deployment and smoke on 2026-06-08/09:

- `git push origin v3-intel-layer` pushed `ca2130b`.
- `scripts/deploy-fly-api.sh` deployed only Fly process group `app` with
  `--build-target api-runtime`; image size was 259 MB and Fly reported the API
  machine in a good state.
- `https://atlas-api-pedro.fly.dev/health` returned `200`, `status=healthy`,
  `db_ok=true`, and fresh ingest activity.
- `GET /api/v2/search/thread?q=Colombia&hours=24&country_code=CO` returned
  `200` in production; this endpoint had returned `404` before deploy.
- `GET /api/v2/threads?hours=24&limit=5&country_code=CO` returned real
  country-scoped thread rows.
- Vercel served the matching `frontend-v2/dist` bundle
  (`/assets/index-BY2GvIR-.js`).
- Playwright production smoke on
  `https://observatory-global.vercel.app/app?country=CO` showed `10 THREADS`,
  no `Top Themes`, no `Failed to fetch`, and no console errors.
- Playwright production search smoke for `Colombia` called
  `/api/v2/search/thread` with `200` responses; clicking "Build a thread"
  opened `CUSTOM THREAD` with matching signals and no `HTTP 404`.
- GitHub #175 and #177 were closed after production smoke. #207 remains open as
  the Living Narrative Threads umbrella.

Next closeout order:

1. Rotate secrets in a separate maintenance pass before the next deploy cycle
   that changes credentials.
2. Start the read-only Kalman/state
   tracking pilot for dynamic topics.

---

## Current handoff (2026-06-04) — Unified thread detail shell

Corrected the F5 frontend architecture after product review: Narrative Threads
and Theme Detail are not separate concepts in the visible product. Resolvable
threads now open the existing `ThemeDetail` shell, with the thread
`narrative_note` embedded at the top, so the richer intelligence surface remains
intact: Evolution Graph, country breakdown, right-panel country edge, sources,
persons, public-attention affordances, and related-theme actions.

Implemented:

- `resolveThreadThemeTarget` routes `dynamic-topic-*` threads directly to the
  dynamic ThemeDetail slug and atlas-backed threads to their anchor topic.
- `emergent-cluster-*` threads remain on `ThreadFocusPanel` as a fallback until
  ThemeDetail supports that prefix.
- `ThemeDetail` accepts optional thread context and fetches
  `/api/v2/threads/{thread_id}?llm=1` only when opened from a Narrative Thread,
  then renders the note above dense metrics.
- The fallback `ThreadFocusPanel` section label changed from vague `Movement` to
  `10h Signal Change` because the metric is an absolute 10-hour signal delta.

Validation:

- `cd frontend-v2 && npm run build` passed.
- Direct helper smoke passed via Node type stripping.
- Local proxy returned 200 for `/api/v2/threads`,
  `/api/v2/theme/dynamic-topic-17`, and
  `/api/v2/theme/election-legitimacy-dispute?country_code=CO`.
- Vitest currently hangs even on an existing unrelated local test in this
  session; the unit test file exists, but Vitest was not used as the completion
  gate.

Next product step: browser-smoke the unified panel on localhost/prod after merge
and remove or further narrow `ThreadFocusPanel` once emergent-only threads have a
ThemeDetail-compatible route.

---

## Current handoff (2026-06-04) — DeepSeek thread-note pilot + country alignment

Implemented a follow-up to the Narrative Note work:

- `/api/v2/threads/{thread_id}` accepts `llm=1` and tries DeepSeek-backed
  `narrative_note` synthesis for opened thread details only.
- The LLM path is grounded in the existing thread packet and evidence samples,
  requires strict JSON, and falls back to the existing `extractive-v1` note on
  missing key, provider error, or invalid output.
- DeepSeek default model is `deepseek-v4-flash`; `deepseek-v4-pro` is selectable
  with `DEEPSEEK_THREAD_NOTE_MODEL`.
- `/api/v2/threads` accepts `country_code`, and `NarrativeThreads` now requests
  country-scoped threads from the backend instead of filtering global threads in
  the client. This addresses the country brief vs Narrative Threads mismatch
  where a country could show active themes while the threads panel showed none.

Verification before deploy:

- Backend focused suite:
  `cd backend && .venv/bin/python -m pytest tests/test_deepseek_narrative.py tests/test_threads_router_contract.py tests/test_thread_intelligence.py tests/test_threads_emergent_augment_shape.py -v`
  -> `34 passed`.
- Frontend: `cd frontend-v2 && npm run build` passed.

Follow-up product work moved to the unified shell: keep `ThemeDetail` as the
canonical reader and add a ThemeDetail-compatible route for emergent-only
threads so the fallback `ThreadFocusPanel` can shrink further or disappear.

---

## Current handoff (2026-06-04) — Narrative Note synthesis shipped

The first read-only Narrative Note increment is implemented on `v3-intel-layer`.
It adds deterministic/extractive thread prose without an LLM, then renders it at
the top of `ThreadFocusPanel` before dense metrics.

Shipped:

- **Spec + plan**:
  `docs/superpowers/specs/2026-06-04-narrative-note-synthesis-design.md` and
  `docs/superpowers/plans/2026-06-04-narrative-note-synthesis.md`.
- **Backend service** `backend/app/services/narrative_note.py` builds
  `narrative_note` with `lede`, `movement`, `evidence`, `caveat`, `quality`, and
  `source="extractive-v1"`.
- **Thread contract** now includes `narrative_note` for atlas-topic,
  emergent-cluster, and dynamic-topic thread assemblies; atlas detail refreshes
  the note after loading detail evidence.
- **Frontend** `ThreadFocusPanel` renders the note as the first reading block,
  with fallback to the previous `why_now` paragraph when the field is absent.

Verification on 2026-06-04:

- Backend focused suite:
  `cd backend && .venv/bin/python -m pytest tests/test_narrative_note.py tests/test_thread_intelligence.py tests/test_threads_emergent_augment_shape.py tests/test_snippet_evidence_contract.py -v`
  -> `36 passed`.
- Frontend: `cd frontend-v2 && npm run build` passed.
- Direct local-code smoke against Supabase returned `dynamic-topic-17` with
  `narrative_note.source="extractive-v1"`.
- Backend deployed with `bash scripts/deploy-fly-api.sh`; Fly machine
  `d8d2e46fe07e78` reached good state.
- Fly `/health` after deploy returned `status=healthy`, `db_ok=true`,
  `total_signals=350853`.
- Fly and localhost proxy both returned `/api/v2/threads?hours=24&limit=1` with
  `narrative_note.source="extractive-v1"` and lede
  `Infrastructure and Public Services is moving across ID, BR, and CA.`

Next product step: use the same note service shape for country-scoped narrative
assembly (F2/F4), after this thread-level reading block is reviewed in the UI.

---

## Current handoff (2026-06-04) — F3 signal snippet enrichment shipped

F3 is implemented on production branch `v3-intel-layer` at merge commit
`87c98dc merge: signal snippet enrichment (F3)`. The repo is clean and aligned
with `origin/v3-intel-layer`.

Shipped:

- **Migration 052** `signals_v2.snippet TEXT` (nullable, no backfill) is present
  in Supabase.
- **Ingestion wiring** persists source-provided body text through
  `clean_snippet` for Reddit, NewsAPI, RSS, NewsData, MediaStack, and ReliefWeb.
  GDELT intentionally leaves `snippet` NULL because it does not provide body
  text.
- **Backend exposure** adds `snippet` to `/api/v2/signals` for the clicked
  single-signal detail panel, and to thread evidence serialization as data for
  future narrative-note synthesis.
- **Frontend exposure** renders `snippet` only in
  `SignalDetailPanel` when present. It is not rendered as a raw extra line under
  every thread/theme headline.
- **Localhost data connection** is corrected: `frontend-v2/vite.config.ts`
  proxies `/api` and `/health` to `https://atlas-api-pedro.fly.dev` by default,
  so `localhost:3000` uses production data while keeping local frontend code.
  Set `VITE_LOCAL_API=http://localhost:8000` only when intentionally targeting a
  local backend.

Verification on 2026-06-04:

- `cd backend && .venv/bin/python -m pytest tests/test_signal_text.py tests/test_ingest_snippet_wiring.py tests/test_snippet_evidence_contract.py -v`
  -> `9 passed`.
- `cd frontend-v2 && npm run build` -> Vite build passed.
- Fly `/health` and localhost `/health` both returned the same production data:
  `status=healthy`, `db_ok=true`, `total_signals=343493`, ingest lag `2.5`
  minutes at the time of smoke.
- Supabase column check returned `snippet | text`.
- `/api/v2/signals?hours=24&limit=5` on both Fly and localhost returned the
  `snippet` key without contract errors.
- Since the app deploy at `2026-06-04T14:25:00Z`, only GDELT rows had been
  inserted (`gdelt_gkg` / `gdelt_gkg_translated`), so current post-deploy
  `with_snippet=0` is expected until the next non-GDELT RSS/API/Reddit/ReliefWeb
  insert lands.

Spec: `docs/superpowers/specs/2026-06-04-signal-snippet-enrichment-design.md`.
Plan: `docs/superpowers/plans/2026-06-04-signal-snippet-enrichment.md`.

Next verification checkpoint: after the next non-GDELT ingest cycle, confirm
`created_at > deploy_time` rows for `rss_feed`, `newsdata_api`,
`mediastack_api`, `newsapi_api`, `reddit_public`, or `reliefweb_api` have
`snippet IS NOT NULL`. Do not judge F3 from GDELT-only windows.

---

## Current handoff (2026-06-03) — Workbench early-access waitlist gate (shipped)

Product pivot context: Atlas leads the public MVP with the Workbench
(investigation workspace), framed as information-disorder sensemaking — expose
how narratives move/change, not classify true/false. The Workbench stays gated
(Option A); the gate itself became interactive.

Shipped this session (branch `feat/workbench-waitlist` merged to
`v3-intel-layer` at merge commit `1af31fa`, feature branch deleted):

- **Migration 051** `workbench_waitlist` (RLS-locked, `email` + `use_case` +
  server-derived `referrer`, `UNIQUE(email)`). Applied + verified in Supabase.
- **Backend** `backend/app/routers/waitlist.py`: `POST /api/v2/waitlist`
  (Pydantic, honeypot `company` field → silent success, soft per-IP rate limit
  keyed on **Fly-Client-IP** with idle-IP eviction, `is_valid_email` +
  `normalize_email`, idempotent `ON CONFLICT (email) DO NOTHING`,
  `to_regclass` guard, never reveals existence) and
  `GET /api/v2/waitlist/count` (aggregate `COUNT(*)` only — never returns
  emails). Registered in `main_v2.py`. Tests: `test_waitlist_email_validation`
  (8) + `test_waitlist_router_shape` (8), 16/16.
- **Frontend** `lib/waitlist.ts` (`postWaitlist`/`getWaitlistCount`, relative
  `/api/v2` fetch — no supabase-js) + `WorkbenchWaitlistGate.tsx` interactive
  overlay (email + optional use_case, hidden honeypot, success/error/submitting
  states with try/catch, **real-data counter**: shows `Ya van N` only at N≥25
  else qualitative copy — no fabricated numbers, anti-disinformation stance,
  separate `Apoyar Atlas` ko-fi CTA, `mailto:` removed). Replaced the static
  overlay block in `InteractiveWorkspace.tsx`; styles in
  `InvestigationWorkspace.css`.
- **Review loop:** final security/privacy review found 3 blockers
  (spoofable X-Forwarded-For rate limit, unbounded `_rate_log`, submit stuck on
  network error) + 2 minor — all fixed and re-verified.

Deploy + production smoke (2026-06-03):
- Backend deployed via `scripts/deploy-fly-api.sh` (app group), Fly `/health`
  healthy, db_ok.
- API smoke: count `0 → POST {ok:true} → 1`; honeypot POST returns `{ok:true}`
  and wrote **no** row; invalid email → `422`; smoke row verified in DB then
  deleted (table back to 0).
- Frontend on Vercel (`observatory-global.vercel.app`): served bundle's
  `InteractiveWorkspace` chunk contains the new overlay copy
  (`Pedir acceso`, `beta privada`, `primeros en usarlo`, `waitlist/count`);
  `/api/v2/waitlist/count` resolves through the Vercel `/api/*` rewrite.

Spec: `docs/superpowers/specs/2026-06-03-workbench-waitlist-gate-design.md`.
Plan: `docs/superpowers/plans/2026-06-03-workbench-waitlist-gate.md`.

Next product track (deferred, its own brainstorm/spec): platform-wide
language/positioning coherence pass — align landing + walkthrough + microcopy to
the single thesis (see where information comes from, how it moves, what changes;
see outside your bubble). Not blended into this gate work.

---

## Current handoff (2026-06-01) — external storage, emergent cron, and documentation hygiene

The repo is still on `v3-intel-layer`. The latest documented hygiene commit is
`955f8da docs(obsidian): add session hygiene maps`.

Operational changes now verified:

- Duplicate invalid Git refs created by iCloud-style filename suffixes were
  moved to `.git/refs-invalid-backup/2026-06-01/`; `git status`, `git log`, and
  `git show-ref` work again.
- `SESSION_LOG.md` now has a 2026-05-22 through 2026-05-31 summary block.
- Obsidian MOCs now live under `docs/maps/` and are linked from
  `docs/000-INDEX.md`.
- `scripts/run-emergent-snapshot.sh`,
  `scripts/install-emergent-snapshot-launchd.sh`, and
  `infra/launchd/com.atlas.emergent-snapshot.plist` are versioned.
- `com.atlas.emergent-snapshot` now runs from `/Users/pedro/AtlasLocalWorker`
  and reads credentials from `/Users/pedro/AtlasLocalWorker/.env` (mode `600`),
  not from the Desktop repo `.env`.
- Verification run on 2026-06-01: the emergent cron pulled 15,000 signals,
  deduped to 13,031 headlines, found 12 raw HDBSCAN clusters, kept 9 after the
  precision gate, labeled via DeepSeek, wrote 9 `emergent_clusters` rows, and
  exited with `LastExitStatus = 0`.
- `docs/state/PROJECT_INVENTORY.md` was regenerated after the cron fix. Its
  cron row for `com.atlas.emergent-snapshot` now points to the worker runner
  with a fresh log timestamp instead of the old Desktop `.env` permission
  error.
- Raw archive storage now lives on the external 2TB disk at
  `/Volumes/Ext/Atlas/Archive`; `/Users/pedro/AtlasArchive` is a symlink kept
  for compatibility with existing scripts.
- `scripts/run-local-hot-cold-catchup.sh` and the installed worker copy now
  default archive writes to `/Volumes/Ext/Atlas/Archive` and processed-history
  artifacts to `/Volumes/Ext/Atlas/Processed`.
- The hot/cold runner now refuses to run if the external `/Volumes/Ext` mount is
  missing, preventing accidental fallback writes to the internal disk.
- External archive verification on 2026-06-01 passed for `59` manifest
  directories, `272` manifest records, and `3,947,759` represented rows.
- Scope-gate coverage telemetry is now explicit via
  `backend/scripts/gate_coverage_report.py`. First saved 24h report:
  `docs/research/atlas-paper/phase-1-validation/reports/gate-coverage/2026-06-01-gate-coverage-24h.json`
  (`16,878` assignments, `100%` scored, `2,999` kept, `13,879`
  abstained, kept rate `17.77%`). This confirms the next quality problem is
  coverage/abstention, not scoring freshness.
- Evidence-role pilot Task 1/2 is underway to address coverage without lowering
  the 90% precision bar. `backend/scripts/evidence_role_schema.py` defines the
  teacher label contract, and `backend/scripts/evidence_role_sampler.py` samples
  read-only `(cluster, signal)` rows from the latest `emergent_clusters`
  snapshot for offline teacher labeling.
- Evidence-role teacher-student pilot started from
  `docs/superpowers/specs/2026-06-01-narrative-cluster-evidence-roles-design.md`.
  The goal is to keep `verified` claims at `>=90%` precision while recovering
  `>=80%` visible coverage through `candidate` and `context_rich` tiers.
- Evidence-role teacher packet regenerated with a multi-snapshot window:
  `backend/scripts/evidence_role_sampler.py` now takes `--since-days N`
  (default `7`) and dedups by `(cluster_label, signal_id)` across all
  snapshots in the window, instead of only reading the latest snapshot.
  Current packet at
  `docs/research/atlas-paper/phase-1-validation/evidence-role/teacher-packets/2026-06-01-evidence-role-teacher-packet.jsonl`
  contains `646` rows (was `133` from a single snapshot), comfortably above
  the 300-row planning threshold. The 4x/day cron keeps growing this pool
  toward the 1,000-1,500 row target without requiring HDBSCAN parameter
  changes.
- Evidence-role teacher smoke now has three vendors: DeepSeek
  (`deepseek-chat`), OpenAI (`gpt-4.1`), and Anthropic
  (`claude-sonnet-4-6`). OpenAI/Anthropic keys were found in the root `.env`
  and used for this manual run; `/Users/pedro/AtlasLocalWorker/.env` still only
  has DeepSeek because that worker is intentionally separated from the
  iCloud-backed repo/Torch environment.
- Multi-vendor evidence-role consensus over the full `646`-row packet
  (DeepSeek + OpenAI `gpt-4.1` + Anthropic `claude-sonnet-4-6`) produced
  `605` gold rows and `41` disagreements (`93.7%` 3-vendor agreement) under
  `docs/research/atlas-paper/phase-1-validation/labels/evidence-role-consensus/2026-06-01-consensus.jsonl`.
  The student readiness report
  `docs/research/atlas-paper/phase-1-validation/reports/evidence-role/2026-06-01-student-readiness.json`
  now reports `605` training rows and status `ready_for_student_training`.
  Role distribution: `primary_evidence 288` (47.6%), `noise 227` (37.5%),
  `context 54`, `reaction 23`, `analysis 11`, `entity_reference 2`.
- Key finding: ~`37.5%` of sampled emergent-cluster signals are `noise` under
  3-vendor consensus. This quantifies that emergent clusters carry significant
  off-topic membership, and supports the role layer as a coverage/precision
  filter rather than trusting raw cluster membership.
- The `41` disagreements are mostly 3-way splits (`context`/`noise`/
  `primary_evidence`, `25` of `41`) — the borderline evidence-vs-context-vs-
  noise cases the student will either learn or abstain on.
- Evidence-role pilot verification (plan Task 7): focused unit tests pass
  (`18` passed across schema/sampler/teacher/consensus/student), `py_compile`
  clean on all five scripts, no secrets found in generated artifacts, and
  `git diff --check` reports no whitespace errors. Current student status is
  `ready_for_student_training`.

- Coverage root-cause diagnosis (read-only, no gate changes):
  `docs/research/topic-quality/2026-06-01-coverage-root-cause-lexicon-recall.md`.
  The `17.77%` kept rate is not gate over-abstention. Decile 1 (`gate_score`
  0.0-0.1) is ~75% of scored volume at avg score `0.013` — genuine
  near-zero-confidence lexicon noise, correctly abstained. Cross-checking the
  `605`-row evidence-role gold set: `551/605` (`91.1%`) gold rows and
  `269/288` (`93.4%`) true `primary_evidence` rows have **no lexicon
  assignment at all**. The bottleneck is candidate recall, not the gate.
  Lowering the threshold cannot recover the 91% of real evidence that never
  enters the pipeline. Coverage and the evidence-role pilot are the same
  problem; the emergent-cluster + evidence-role student path is the coverage
  engine, not a separate paper track.

- Standing lexicon-recall baseline (read-only):
  `backend/scripts/lexicon_recall_baseline.py` →
  `reports/evidence-role/2026-06-01-lexicon-recall-baseline.json`. Against the
  605-row gold set: `8.9%` overall candidate recall, `6.6%` on
  `primary_evidence`. Sharper finding: lexicon recall on `noise` (`13.2%`) is
  **higher** than on `primary_evidence` (`6.6%`) — the generator is biased
  toward off-topic candidates. The embedding cluster-membership generator must
  beat `6.6%` primary_evidence recall without regressing verified precision.

- **RQ1 answered at scale (2026-06-02).** Paper 1 RQ1 (hand-crafted GDELT
  classifier vs LLM zero/few-shot) re-run on a 691-row stratified benchmark
  (batch-03, 7d window) with a 3-vendor LLM-annotator consensus gold
  (deepseek-chat, gpt-4.1, claude-sonnet-4-6; Fleiss kappa `0.625`,
  660 usable / 31 ties). Precision: Atlas v2 **41.6%** [37.8, 45.5];
  LLM zero-shot **78.6%** [75.3, 81.7]; LLM few-shot **81.1%** [77.7, 84.0].
  CIs tightened from ~±12pts (n=61 pilot) to ~±4pts. The single-layer
  classifier roughly halves achievable precision — the paper's thesis holds
  with statistical force. Honest caveat: LLM fell from the pilot's 95% to ~80%
  on the larger/harder sample; none pass the 90% gate. Artifacts:
  `reports/llm-baseline/2026-06-02-comparison-atlas-vs-llm-n660.{json,md,svg}`,
  gold `labels/2026-06-02-atlas-v2-batch-03.consensus-gold.jsonl`,
  builder `backend/scripts/build_annotator_consensus_gold.py`.

- **Research-to-product roadmap clarified (2026-06-03).** Paper 1 is not closed
  as a manuscript, but RQ1 is now strong enough to guide the model roadmap. The
  current sequence is: finish the Paper 1 documentation/result skeleton, then
  deploy and browser-smoke the dynamic-topic product cutover. Atlas's product
  purpose is now documented as information-disorder sensemaking: show narrative
  movement, source amplification, evidence, context, and noise so raw volume is
  not mistaken for truth. Roadmap:
  `docs/roadmap/2026-06-03-research-model-product-roadmap.md`.

- **Dynamic topics product cutover deployed and smoked (2026-06-03).**
  `scripts/deploy-fly-api.sh` deployed the API-only image (`259 MB`) to the
  `app` process group only (`1/3` machines); the NLP worker was not redeployed.
  Fly health was healthy. Production API smokes confirmed
  `/api/v2/threads` returns `dynamic-topic-*`,
  `/api/v2/briefing?hours=24` returns
  `top_atlas_topics_source=dynamic_topics`, and
  `/api/v2/theme/dynamic-topic-10?hours=24` returns
  `source=dynamic_topics`, `total=313`, `signalSample=76`. Browser smoke passed
  through `/brief`, Watchlist click, Narrative Threads, and ThreadFocusPanel.
  Follow-up product issues: ThemeDetail insight copy contradicted the signal
  count, country chips duplicated codes (`IDID`), and dynamic topic entities
  still show raw/repeated strings. Smoke report:
  `docs/research/topic-quality/2026-06-03-dynamic-topics-product-smoke.md`.

- **Dynamic topics smoke follow-up fixes (2026-06-03).** Two product-quality
  findings from the browser smoke are fixed locally: dynamic-topic ThemeDetail
  now builds its `HOT WINDOW` copy from the dynamic-topic detail payload instead
  of the static GDELT insight endpoint, and dynamic-thread backend payloads no
  longer send country codes as display names. Focused backend route/contract
  verification passed (`51` tests) and `git diff --check` is clean. Frontend
  `tsc`/Vitest/ESLint/Vite commands hung in the local Node environment before
  diagnostics, so frontend build/browser re-smoke remains pending before deploy.
  Raw/repeated dynamic-topic entity strings remain open for the Entity
  Focus/model-quality lane.

- **Frontend surface/data map added (2026-06-03).** The current
  frontend-to-data ownership map now lives at
  `docs/frontend/2026-06-03-frontend-surface-data-map.md` and is linked from the
  Frontend Product Surfaces MOC plus `docs/000-INDEX.md`. `docs/state/PROJECT_INVENTORY.md`
  was regenerated with `python3 scripts/project_inventory.py`. Main finding:
  dynamic topics feed Brief Watchlist, NarrativeThreads, ThreadFocusPanel, and
  ThemeDetail dynamic branches; Globe, CorrelationMatrix, AnomalyPanel, and
  SourceIntegrity remain adjacent context/evidence surfaces. Next contract fix:
  `/brief` dynamic-topic headline snippets should use `/api/v2/theme/dynamic-topic-*`
  samples instead of `/api/v2/signals?theme=dynamic-topic-*`.

- **MVP Workbench public preview gate (2026-06-03).** The Workbench remains
  fully usable locally for development against real data, but production now
  gates it behind a blurred "Coming soon" preview with a `Request early access`
  mailto CTA plus a secondary `Support Atlas` CTA.
  The gate applies only in production outside localhost and can be bypassed for
  controlled previews with `VITE_ENABLE_WORKBENCH=true`. Product rationale:
  Workbench is likely Atlas's strongest investigation surface, but it is still
  too raw for the first public MVP; early-access emails become the lean
  validation signal for whether to prioritize it next.

- **Infra: LLM/heavy-import venv moved off iCloud.** The repo `.venv` lives on
  the iCloud-synced Desktop; large packages (anthropic, openai) get evicted and
  first use stalls minutes (anthropic import once took `505s`) or throws
  `No module named anthropic.types.model`. Durable fix: dedicated local venv at
  `/Users/pedro/AtlasLocalWorker/atlasvenv` (Python 3.12; anthropic 0.96,
  openai 2.38, asyncpg, numpy). Use it for all LLM/annotator/baseline jobs;
  keep repo `.venv` for pytest only. Quick repair if iCloud evicts a package:
  `pip install --force-reinstall --no-deps <pkg>`.

- **RQ1 improvement methods documented (2026-06-02).** Each paper must propose
  how to raise the measured number, not just report it. Failure anatomy of the
  334 incorrect rows: `off_topic` 41.6%, `scope_mismatch` 28.1%, and classic
  `substring_noise` only **0.6%** — the failure is semantic, not lexical. Levers:
  M1 learned scope gate abstains off_topic (biggest bucket); M2 evidence-role
  layer re-types scope_mismatch as graded context; M3 per-topic remediation for
  the 0%-precision tail (fuel-subsidy-unrest, mining-royalty-risk, …). Doc:
  `docs/research/atlas-paper/phase-1-validation/2026-06-02-rq1-improvement-methods.md`;
  composition artifact `reports/llm-baseline/2026-06-02-rq1-error-composition.json`.
  **M1 quantified (2026-06-02):** scoring the 660-row gold through the scope gate
  offline (`score_gold_gate.py`, e5-base, no DB writes) lifts precision
  **40.9% → 70.3%** at 37.3% coverage (and 78.3% @ 27.3% at threshold 0.95). The
  gate is confirmed as the dominant precision lever; residual gap to the LLM
  upper bound is `scope_mismatch` (M2's target). Artifact:
  `reports/llm-baseline/2026-06-02-rq1-gate-precision-coverage.json`.

- **M2 student v1 trained (2026-06-02).** `train_evidence_role_student.py` now
  trains a real local multinomial-logistic student (e5-base headline embedding +
  headline↔cluster_label cosine; no LLM at inference) on the 603-row evidence-role
  consensus gold, evaluated by honest stratified 5-fold CV. primary_evidence
  precision **78.2%** / recall 77.4%; noise recall **71.4%**; accuracy 70.6%,
  macro-F1 0.59. `context`/`analysis` weak (small support). Below the 90% verified
  target at signal level, but the `verified` tier needs ≥2 strong primaries per
  cluster. Path to 90%: v2 features (centroid/gate_score/source/country),
  role-score calibration, more gold. Artifacts:
  `reports/evidence-role/2026-06-02-student-v1-eval.json`,
  `models/2026-06-02-evidence-role-student-v1.json`.

- **M1↔M2 bridge measured (2026-06-02).** `bridge_gate_student_scope.py` scores
  batch-03 with both gate + student. Of the 73 rows the gate keeps but consensus
  marks incorrect, the student types **90.4% as non-noise** (60 primary_evidence)
  — the residual gate errors are recoverable evidence at wrong granularity, not
  garbage. scope_mismatch rows: 90.4% non-noise. Honest limit: off_topic still
  71% non-noise (headline-only student over-assigns primary; off_topic is the
  gate's job, and student v2 needs cluster-membership features). Artifact:
  `reports/llm-baseline/2026-06-02-gate-student-bridge.json`.

- **M3 remediation measured (2026-06-02).** `topic_remediation_report.py`
  confirms the off_topic tail is GDELT-theme-hint driven: `theme_only` matches
  (lex_count=0, theme_hits>0) precision **20.2%** vs lex_backed ~48%. M3a:
  dropping theme_only lifts precision **40.9% → 48.3%** at 74% coverage (no
  model). M3b: retire/gate the 0%-precision topics (mining-royalty-risk 0%,
  fuel-subsidy-unrest 2.8%, humanitarian-access 4.5%, election-legitimacy 8.6%).
  Durable fix = Phase 6 dynamic_topics + emergent self-curation (remove the
  theme-hint lexicon at the source). Artifact:
  `reports/llm-baseline/2026-06-02-rq1-topic-remediation.json`.

- **Student v2 (DB-enriched) — near-null result (2026-06-02).**
  `train_evidence_role_student_v2.py` adds cluster cosine(label/description/centroid_vec),
  cohesion, log n_signals, country_match, source_family, is_english (782 feats, 29
  clusters joined). vs v1: primary precision **flat at 78.2%**, noise recall
  +1.3pts, accuracy +0.7pts, macro-F1 slightly down. Centroid cosine is a weak
  discriminator because noise members sit inside the same cluster. Lever to 90% is
  more gold + cleaner clusters (M4), not per-row features. Artifact:
  `reports/evidence-role/2026-06-02-student-v2-eval.json`.

- **Phase 6 Sub-A' — emergent topic identity validated (2026-06-02).**
  `emergent_topic_identity_resolver.py` (read-only) groups the 81
  `emergent_clusters` across 7 snapshots into stable topic identities by
  centroid cosine (sequential time-ordered linking, threshold sweep). Result:
  **15 recurring topics, threshold-robust** across 0.70–0.90 → cross-snapshot
  identity is coherent. Operating threshold **0.85** (knee). Identity signal:
  centroid primary, label confirmatory (cos ~0.83), member-overlap discarded
  (Jaccard 0.0 cross-snapshot). 15 recurring emergent topics vs **30 active
  `atlas_topics`** → static taxonomy ~2× bloated (ties to M3 dead topics). Some
  persistent identities are roundup artifacts → lifecycle must still suppress
  them. Decision: proceed to Sub-A schema (keyed on stable id + persistence +
  roundup flag). Spec: `docs/superpowers/specs/2026-06-02-emergent-topic-identity-resolver-design.md`;
  report: `docs/research/topic-quality/2026-06-02-emergent-topic-identity.{json,md}`.

- **Phase 6 Sub-A — dynamic_topics shadow lifecycle built (2026-06-02).**
  Migration `048_dynamic_topics.sql` applied (dynamic_topics + members, RLS
  locked). `project_dynamic_topics.py --rebuild` collapses emergent_clusters
  across snapshots into stable identities (centroid ≥0.85, running-mean) and
  runs a quality-gated state machine (candidate→active needs persist≥2 +
  cohesion≥0.5 + signals≥30 + not-roundup; roundups never promoted; stale→
  deprecated→retired). 9 unit tests. Shadow rebuild (89 clusters, 8 snapshots):
  5 active / 11 candidate (5 roundup) / 5 deprecated. Findings: mechanism works;
  label-regex roundup gate is weak (catches explicit grab-bags, generic-broad
  slip); cohesion ~0.95 everywhere so it can't discriminate; **robust gate =
  evidence-role student noise rate (next increment)**. ~half the persistent
  emergent identities are geographic "X News Roundup" artifacts. Spec:
  `docs/superpowers/specs/2026-06-02-emergent-topic-identity-resolver-design.md`;
  result: `docs/research/topic-quality/2026-06-02-dynamic-topics-shadow-result.md`.
  SHADOW only — no product read path.

- **Phase 6 quality gate v2 — student noise rate (2026-06-02).** Migration
  `049` adds `dynamic_topics.noise_rate`; `project_dynamic_topics.py --student-model`
  scores each topic's member sample headlines through the evidence-role student
  (mean `noise` fraction) and gates promotion on `noise_rate < 0.50`. Validated
  complementary to the label regex: the student caught **"Economic and Social
  Trends" (n=770, noise 0.82)** — the largest cluster, an unlabeled grab-bag no
  regex would flag — while the regex still catches explicitly-labeled roundups
  with low noise ("Mixed News Headlines" 0.08). Result: **4 active** (all noise
  ≤0.39) / 12 candidate / 5 deprecated.

- **Phase 6 incremental cron wiring (2026-06-02).** `project_dynamic_topics.py`
  now hydrates existing topics from the DB (replays members) and processes only
  not-yet-ingested snapshots — default mode is incremental; `--rebuild` is the
  full shadow rebuild. Wired into `run-emergent-snapshot.sh` as a guarded tail
  step (`|| true`), so the lifecycle folds each new snapshot in right after it is
  written. **Cost control:** the whole lifecycle is $0 API — student + e5 are
  local; per-cluster noise is cached in `emergent_clusters.role_noise_rate`
  (migration 050) and scored exactly once, never recomputed. Worker deploy via
  the emergent installer (now additive on `.env`, never clobbers calibration
  keys; copies the student model). Verified idempotent no-op on the worker
  (n_new=0 → 0 writes).

- **Phase 6 merge/dedup refinement (2026-06-02).** Merge is wired only into the
  `--rebuild` consolidation path, not the live incremental cron. A naive
  centroid-only single-linkage merge at 0.90 was rejected after dry-run evidence
  showed dense centroids chain-collapse unrelated topics and roundups. The final
  merge requires centroid similarity **and** compatible labels, and excludes
  roundups from merge participation so grab-bags cannot absorb real topics.
  Verified rebuild with 101 clusters / 9 snapshots: 21 topics, `n_merged_topics=0`,
  6 active / 12 candidate / 3 deprecated, 5 roundups, 1 high-noise topic.
  Follow-up complete below: backend product reads now prefer dynamic topics.

- **Phase 6 backend canonical read path (2026-06-02).** `/api/v2/threads`
  now treats active `dynamic_topics` as canonical when available; atlas/static
  and raw emergent rows remain fallback sources. `/api/v2/briefing.top_atlas_topics`
  now prefers `dynamic_topics` and exposes `source_table="dynamic_topics"`,
  `model_version="dynamic-topics-v1"`, and `noise_rate`. Watchlist slugs are
  `dynamic-topic-<id>` and `/api/v2/theme/dynamic-topic-<id>` resolves them
  through member emergent-cluster samples so existing `ThemeDetail` clicks keep
  working without frontend contract changes. Local live smoke, sourced from the
  worker `.env`, returned `dynamic-topic-10` ("Russia Warns on Baltic and
  Zaporizhzhia") as top thread/watchlist item: `signal_count=287`,
  `noise_rate=0.0218`, detail `source=dynamic_topics`, `signalSample=141`.
  `/api/v2/briefing` still reports degraded segment `theme_country`, which is a
  separate pre-existing briefing section issue, not the dynamic-topic cutover.
  Remaining before calling product fully shipped: deploy backend and do a
  frontend/browser smoke through the Watchlist and Narrative Threads panels.

- **Local Ollama validation route deprecated (2026-06-02).**
  `backend/scripts/atlas_ollama_pilot.py` remains as a reproducibility runner
  only. It writes separate `ollama_*` fields and resolved `gold_*` comparison
  fields without mutating review templates. The `llama3.2:1b` M1 pilot on 20
  reviewed batch 02 rows scored 25% decision accuracy, 25% scope accuracy, and
  11.76% evidence-role accuracy, so local Ollama must not be used as an Atlas
  judge, label teacher, reviewer substitute, assistant hint source, or gold
  generator.

- Cron health (verified 2026-06-02): `com.atlas.emergent-snapshot` running 4x/day
  (snapshots at 05:00/11:00 today, 17:00/23:00 yesterday; 81 cluster rows / 7
  snapshots). Evidence-role gold held at 605 (no new teacher pass this cycle).

- Cron issue to triage before product cutover: `com.atlas.local-hot-cold-catchup`
  is loaded but has `last exit code = 1`; the 2026-06-02 00:10 run failed with
  `asyncpg.exceptions.ConnectionDoesNotExistError: connection was closed in the
  middle of operation` during `archive_export`. External disk mount is present
  (`/Volumes/Ext`). Patch applied 2026-06-02: archive export batches now retry
  transient DB connection loss up to 3 attempts with exponential backoff, and
  `/Users/pedro/AtlasLocalWorker/backend/scripts/` was synced manually without
  kickstarting the prune runner. Worker-layout dry-run passed (`planned_rows=8`,
  execute=false). Pending: verify the next scheduled overnight run resets
  launchd `last exit code` to 0.

- **3-vendor calibration cron installed (2026-06-02).** Daily 03:00 launchd agent
  `com.atlas.threevendor-calibration` samples a fresh atlas-v2 benchmark slice,
  runs the deepseek-chat/gpt-4.1/claude-sonnet-4-6 annotator panel, and writes an
  inter-annotator agreement report (drift monitor). Repo: `scripts/run-3vendor-calibration.sh`,
  `scripts/install-3vendor-calibration-launchd.sh`,
  `infra/launchd/com.atlas.threevendor-calibration.plist`. Worker `.env` now holds
  all three vendor keys + DATABASE_URL (mode 600, off-iCloud); runner uses the
  off-iCloud `atlasvenv`. Reports land in `/Users/pedro/AtlasLocalWorker/calibration/`
  (outside the repo). Smoke run 2026-06-02 (n=67): Fleiss kappa 0.520, pairwise
  0.48–0.61, rc=0. The installer is additive on the worker `.env` (appends only
  missing keys — never clobbers, unlike the emergent installer).

Next operational work:
- Do NOT lower the scope-gate threshold to chase coverage; the gate is well
  calibrated on what it receives. Treat the emergent-cluster + evidence-role
  path as the coverage engine instead.
- Deploy the backend canonical dynamic-topic read path and run frontend/browser
  smokes through `/brief`, Watchlist clicks, Narrative Threads, and
  ThreadFocusPanel.
- Continue the evidence-role pilot with teacher labeling, consensus, and local
  student evaluation before promoting broader coverage changes.
- Decide whether to copy OpenAI/Anthropic keys into the local worker env for
  scheduled evidence-role calibration, or keep multi-vendor teacher runs as
  manual repo-local jobs sourced from root `.env`.
- Watch external disk availability before hot/cold catch-up runs; if the disk is
  unplugged, the runner should fail loudly instead of filling the internal
  drive.
- Decide whether to tune the emergent cron size after a few runs; this run spent
  several minutes in HDBSCAN with 13,031 deduped headlines, which is acceptable
  but worth watching.
- Keep the docs hygiene loop small: regenerate `PROJECT_INVENTORY.md`, update
  the affected MOC, and keep `CLAUDE.md` as current-state pointers.

---

## Current handoff (2026-05-25) — backlog-first production cycle

The repo is on `v3-intel-layer`. The latest pushed production commit before the
Path B harness work is `99af056 feat(taxonomy): audit and tighten topic
quality`.

New operating canon:

- Roadmap: `docs/roadmap/2026-05-25-production-cycle-and-backlog.md`.
- The UI is now treated as a detector of contract/data-quality failures, not as
  an invitation to open ad hoc polish issues.
- Frontend work interrupts the data backlog only when the visible product is
  contradicting itself or misrepresenting data.
- Visual feedback should be batched from recorded walkthroughs: video -> issue
  batch -> focused UX PR.
- The active work block is data/product backlog. Path C first-pass taxonomy
  cleanup is shipped; Path B now has a read-only benchmark harness, first
  103-row priority sample, first labeled score, and v2 semantic/evidence-role
  label schema.
- Equal Earth / equal-area projection is now tracked separately as #212 and
  ADR-0005. It is important for Atlas's worldview, but parked outside the
  current data sprint.

Current data/product state:

- Local hot/cold automation is installed and verified through
  `com.atlas.local-hot-cold-catchup`; last recorded LaunchAgent exit code was `0`.
- Hot store validation after automation: `signals_v2` had `173,925` rows,
  compact historical tables represented `2,412,591` signals through `2026-05-21`,
  and only `7` older-than-24h residual rows remained at the moving cutoff.
- App-wide long-window routing is implemented, but `#193` should remain open
  until deployed frontend visual smoke tests pass.
- Storage/routing is no longer the blocker. The active bottleneck is topic
  intelligence quality: too much historical volume still falls into
  `general-monitoring`, and low-lex topics depend too heavily on GDELT theme
  hints.
- Product direction has shifted from "display better fixed topics" to
  **Living Narrative Threads**. `atlas_topics` remains the internal anchor
  vocabulary for measurement, backfills, benchmarks, and precision gates, but
  the user-facing UI should show natural, evidence-backed threads that can
  split, merge, fade, and connect to related threads.
- Production now exposes living threads in the visible Narrative Threads panel:
  `frontend-v2/src/components/NarrativeThreads.tsx` consumes `/api/v2/threads`,
  and selected rows open `ThreadFocusPanel`, which consumes
  `/api/v2/threads/{thread_id}`. This fixed the prior mismatch where a row could
  show hundreds of signals while `ThemeDetail` showed `0`.
- Remaining thread quality issue: current live evidence shows
  `mining-royalty-risk` is capturing a coal-mine-disaster cluster. This is a
  Path C taxonomy problem, not a UI problem.
- Path C first slice is documented in
  `docs/research/2026-05-25-path-c-mining-resource-taxonomy-audit.md`.
  Migration `039_mining_resource_safety_label.sql` keeps slug compatibility but
  updates the human-facing label/description to mining/resource safety crisis.
- Full all-topic quality audit is documented in
  `docs/research/topic-quality/2026-05-25-atlas-topic-quality-audit.md`.
  It audits all 30 active atlas topics with a repeatable script and applies
  migrations 040-041 to prefer smaller, lex-supported topics over broad noisy
  theme-driven volume.
- Path B benchmark harness is documented in
  `docs/research/topic-quality/2026-05-25-path-b-benchmark-harness.md`.
  The new read-only script `backend/scripts/topic_benchmark_harness.py`
  generates label-ready JSONL and scores labeled rows against the 85% minimum /
  90% target precision gate. The harness schema is now
  `atlas-topic-benchmark-v2`, adding `gold_scope`, `gold_evidence_role`,
  parent/child thread candidates, and `gold_supported_questions` so the
  benchmark can measure semantic role and answerability, not only topic
  correctness. First sample artifact:
  `docs/research/topic-quality/benchmark-samples/2026-05-25-path-b-priority-topics.jsonl`
  with 103 rows across seven priority topics.
- First Path B labels are documented in
  `docs/research/topic-quality/2026-05-25-path-b-priority-label-results.md`.
  Overall precision was `80.85%`, below the 85% floor. `disease-outbreak`
  (`100%`) and `food-price-stress` (`90%`) passed target; armed conflict,
  forced displacement, gender violence, labor strikes, and transport corridors
  failed. The important product finding is typed failure: some rows are true
  substring/off-topic noise, but others are parent-thread candidates or scope
  mismatches that should feed nested Narrative Threads rather than be deleted.
- Root cause audit is documented in
  `docs/research/topic-quality/2026-05-25-narrative-classification-root-cause-audit.md`.
  The core diagnosis is model-level: Atlas is asking one internal assignment
  layer to represent domains, parent threads, child threads, entity threads,
  evidence rows, and contextual mentions at the same time. Further work should
  evaluate semantic role and evidence level before making topic-specific
  repairs.
- Market/product quality review is documented in
  `docs/research/topic-quality/2026-05-25-atlas-quality-models-market-and-product.md`.
  Atlas quality should be answerability-first: measure whether the system can
  answer the seven Atlas questions with relevant evidence, correct semantic
  scope, enough coverage, and clear uncertainty.
- External field review is documented in
  `docs/research/topic-quality/2026-05-25-narrative-intelligence-field-review.md`.
  Adjacent models include event-centric narrative graphs, narrative maps,
  dynamic topic modeling, topic tracking, media framing, Media Cloud-style
  attention analysis, StoryAtlas-style visualization, and interactive narrative
  analytics.
- The active Atlas model canon is now
  `docs/specs/2026-05-25-atlas-narrative-intelligence-framework.md`.
  Atlas is defined as a live narrative intelligence model and visualizer:
  signals -> evidence -> parent/child/entity threads -> relations -> quality
  envelope -> product surfaces. The next Path B step is semantic/evidence-role
  labeling and a read-only Narrative Thread Graph report, not another
  topic-specific patch.
- The research-paper track has started in
  `docs/research/atlas-paper/2026-05-25-atlas-narrative-intelligence-state-of-art-and-validation-plan.md`.
  This is not a paper draft yet. It is the state-of-the-art and validation plan:
  related work, research thesis, research questions, hypotheses, baselines,
  ablations, data/label plan, metrics, and evidence required before writing a
  publishable manuscript.
- Phase 1 validation artifacts now exist:
  - Labeling guide:
    `docs/research/atlas-paper/2026-05-25-atlas-v2-labeling-guide.md`.
  - Unlabeled stratified sample:
    `docs/research/topic-quality/benchmark-samples/2026-05-25-atlas-v2-stratified-sample.jsonl`.
  - Sample manifest:
    `docs/research/topic-quality/benchmark-samples/2026-05-25-atlas-v2-stratified-sample.md`.
  The sample has `256` rows across all `30` active topics and four buckets:
  `lex_high_conf`, `lex_low_conf`, `theme_high_conf`, and `theme_low_conf`.
- Phase 1 validation workspace:
  `docs/research/atlas-paper/phase-1-validation/README.md`.
  The 256-row sample is split into 8 raw batches. Batch 01 has assistant-pilot
  labels and a score report, but those labels are explicitly not gold labels
  until reviewed/adjudicated.
- Batch 01 now has a human review/adjudication packet:
  `docs/research/atlas-paper/phase-1-validation/review-packets/2026-05-25-atlas-v2-stratified-batch-01.review.md`.
  It joins raw evidence with assistant-pilot suggestions and blank reviewer
  fields for decision, semantic scope, evidence role, parent/child thread,
  supported questions, and notes.
- Batch 01 also has a machine-editable review template:
  `docs/research/atlas-paper/phase-1-validation/review-templates/2026-05-25-atlas-v2-stratified-batch-01.review-template.jsonl`.
  It keeps `assistant_*` suggestions separate from blank `reviewer_*` fields so
  pilot labels cannot accidentally become gold evidence.
- Review progress/finalization is now scripted:
  `backend/scripts/atlas_label_workflow.py review-progress` and
  `finalize-review`. Current batch 01 progress is recorded at
  `docs/research/atlas-paper/phase-1-validation/progress-review-batch-01.json`.
- Batch 01 Markdown adjudication was applied on 2026-05-26 with
  `apply-review-packet`. Current status is `32/32` rows ready: `23` accepted
  assistant suggestions and `9` reviewer-corrected rows. Normalization report:
  `docs/research/atlas-paper/phase-1-validation/reports/batch-01-md-review-normalization.json`
  with `7` warnings.
- Batch 01 reviewed score:
  `docs/research/atlas-paper/phase-1-validation/reports/reviewed-batch-01-score.json`.
  Overall precision is `53.33%` (`16` correct, `14` incorrect, `2` unclear,
  denominator `30`), below the `85%` minimum gate. Treat this as reviewed
  internal evidence, not paper-grade gold.
- Batch 02 is prepared for adjudication with assistant hints:
  `docs/research/atlas-paper/phase-1-validation/labels/assistant-pilot/2026-05-25-atlas-v2-stratified-batch-02.assistant-pilot.jsonl`,
  `docs/research/atlas-paper/phase-1-validation/review-packets/2026-05-25-atlas-v2-stratified-batch-02.review.md`,
  and
  `docs/research/atlas-paper/phase-1-validation/review-templates/2026-05-25-atlas-v2-stratified-batch-02.review-template.jsonl`.
  Current progress is `0/32` ready at
  `docs/research/atlas-paper/phase-1-validation/progress-review-batch-02.json`.
- Local adjudication UI exists at `backend/scripts/atlas_review_server.py`.
  Start it with the batch 02 template and open `http://127.0.0.1:8765`.
  It shows one row at a time, displays assistant hints, and writes reviewer
  fields directly to the JSONL template.
- Report visuals are now generated outside the product UI by
  `backend/scripts/atlas_validation_report.py`. The first visual report is
  `docs/research/atlas-paper/phase-1-validation/reports/assistant-pilot-batch-01/assistant-pilot-batch-01.md`
  with SVG charts for semantic scope, evidence role, supported questions, and
  per-topic precision.

Living Threads canon:

- Spec: `docs/specs/2026-05-24-living-narrative-threads.md`.
- Panel audit: `docs/research/2026-05-24-app-panel-thread-audit.md`.
- Open-issue triage: `docs/roadmap/2026-05-24-open-issues-thread-triage.md`.
- Technical plan: `docs/superpowers/plans/2026-05-24-living-narrative-threads.md`.
- GitHub umbrella: #207 (`feat(threads): introduce living Narrative Threads data contract`).
- The seven Atlas questions are now the product contract: why this is moving
  now, what changed in the last 10h, where it is concentrated, which
  subthreads are forming, which sources are driving it, what evidence supports
  it, and what related thread it connects to.
- First implementation should be a read-only beta thread assembler above
  existing data (`signal_topic_assignments`, `atlas_topics`, `signals_v2`,
  aggregates, source mix, and related-topic co-occurrence), exposed as
  `/api/v2/threads` before any major UI redesign.
- Backend beta is now implemented in code as `living-narrative-threads-v0`:
  `/api/v2/threads` returns top thread candidates and
  `/api/v2/threads/{thread_id}` returns detail with representative evidence.
  It is read-only and uses existing hot-window data; no migration was added.

Atlas-topic taxonomy state:

- `docs/specs/2026-05-23-ai-assisted-taxonomy.md` is now partially implemented,
  not just a spec. Path A shipped in migration 036 for
  `election-legitimacy-dispute` and migration 037 for
  `armed-conflict-escalation`.
- Pilot result: lex_pct `6.3% -> 31.6%`, high_conf `5 -> 27`, and multilingual
  terms drove `74%` of lex-match volume. This validates the SQL-driven workflow:
  sample positives/negatives, propose terms from real headlines, verify volume
  and precision via SQL, migrate only accepted terms, purge/re-backfill the topic,
  then measure lift.
- Migration 037 for `armed-conflict-escalation` was precision-first. It removed
  noisy broad terms (`clashes`, `offensive`, `shelling`) and rejected broad
  armed-incident terms after spot checks (`shots fired`, `opening fire`,
  `firing at`, `ataque armado`, `battlefield`). Live purge + 24h re-backfill:
  lex_pct `2.10% -> 6.56%`, high_conf `22 -> 85`, global v2 coverage `17.22%`.
  This does not clear the 30% Path A gate, but avoids inflating conflict with
  local crime, sports, entertainment, and metaphorical usage.
- Migration 038 finished the remaining low-lex Path A rollout:
  - `fuel-subsidy-unrest`: lex_pct `5.20% -> 37.12%`, high_conf `2 -> 136`.
    Gate cleared cleanly on fuel price/fuel rate/petrol/diesel terms.
  - `food-price-stress`: lex_pct `17.52% -> 4.63%`, high_conf `7 -> 10`.
    This is a precision cleanup, not a recall win; removed noisy `shortage` and
    `hunger` terms that matched non-food shortages and charity-drive headlines.
  - `housing-cost-pressure`: lex_pct `10.16% -> 8.20%`, high_conf `0 -> 2`.
    This is also precision-first; removed `mortgage` and `eviction` because
    they matched tickers and non-household legal/land stories. Spanish housing
    pressure terms are now present.
  - `mining-royalty-risk`: lex_pct `12.33% -> 78.99%`, high_conf `0 -> 100`.
    Gate cleared, but the live evidence is a coal-mine-disaster cluster, so
    Path C first-pass migration 039 keeps slug compatibility while correcting
    the visible anchor label/description to mining/resource safety crisis.
- Global v2 topic coverage after full Path A rollout: `18.47%` of 24h eligible
  signals.
- Path C quality pass after all-topic audit:
  - Added `backend/scripts/topic_quality_audit.py` for repeatable read-only
    topic quality audits.
  - Migration 040 pruned broad/noisy hints and terms on gender violence, labor
    strikes, transport corridors, disease outbreak, food prices, displacement,
    humanitarian access, disinformation, and migration/border pressure.
  - Migration 041 made labor, transport, forced displacement, and water stress
    lex-first after post-040 validation showed theme-only volume still leaking.
  - Final post-041 notable improvements: `gender-violence-rights` moved from
    1,266 mostly noisy rows at 0.08% lex to 261 rows at 100% lex;
    `disease-outbreak` moved from 2,687 mixed rows at 9.83% lex to 830 rows at
    94.46% lex. Several topics intentionally became `thin` rather than noisy:
    `food-price-stress`, `transport-corridor-disruption`, and
    `forced-displacement`.
  - Residual risk: `armed-conflict-escalation` remains large and theme-heavy,
    but sampled evidence is mostly real conflict; route it to Path B benchmark
    labels or a dedicated multilingual conflict pass, not blind suppression.
- Path B encoder classifier stays in design/shadow mode. The benchmark harness
  now exists, but no encoder score or ranking change should ship until labeled
  samples show at least `85%` precision; `90%` is the product target. Recall
  does not justify promotion below that floor.
- Path C taxonomy revision stays later/periodic. Do not build a user-facing
  "this topic is wrong" correction affordance yet; use controlled benchmark
  labels and SQL sample review first.

Sentiment decision from analyst review:

- Normal UI should expose one value: Atlas sentiment.
- GDELT Tone remains useful as fallback, calibration input, benchmark, and
  provenance, but should not appear as a competing product metric beside Atlas
  sentiment.
- Backend/source labels such as `gdelt`, `nlp`, and `nlp_weighted` can remain for
  traceability and debugging; product copy should avoid making users compare
  incompatible-looking systems.

Next execution order:

1. Upgrade the benchmark/model audit from topic correctness to semantic role
   and answerability:
   domain, parent thread, child thread, entity thread, evidence, context signal,
   noise, and which Atlas questions the row/thread can support.
2. Extend the Path B harness schema with `gold_scope`, `gold_evidence_role`,
   parent/child thread candidates, and supported Atlas questions.
3. Adjudicate the batch 01 review packet, then continue labeling batches 02-08.
   Keep `assistant-pilot`, `reviewed`, and `gold` label quality separate.
4. Prototype a read-only Narrative Thread Graph report above existing data
   before adding persistent tables or training an encoder.
5. Keep encoder/ranking promotion blocked until the benchmark clears the 85%
   floor, with 90% as the product target.
6. Run deployed app-wide long-window smoke tests before closing `#193`.
7. Normalize product sentiment presentation around one Atlas sentiment under
   `#183`.
8. Evolve Entity Focus into thread participation, not raw mention display.

---

## Confidence-weighted sentiment fusion (2026-05-22, migration 033)

Follow-up to the lexicon HTML entity fix. Empirical benchmark on 5,000 random
transformer-tagged rows showed 29.2% sign disagreement between transformer
and lexicon sentiment in the same headlines (mean |diff| = 2.02 on the
raw -5..+5 scale). Briefing's flat `AVG(nlp_sentiment) FILTER (...)` was
therefore mixing high-confidence transformer rows (avg confidence 0.64)
with low-confidence lexicon (~0.31) and `fast_neutral` (~0.01) rows at
equal per-row weight, diluting the transformer signal exactly where it
disagrees with the lexicon.

Migration 033 adds confidence-weighted sums to the three hot pre-aggregates:

- `theme_hourly_v2` (regular table, ADD COLUMN)
- `theme_country_hourly_v2` (regular table, ADD COLUMN)
- `country_hourly_v2` (matview — build-populate-rename swap)

New columns per bucket:

- `nlp_sentiment_weight_sum` = `SUM(nlp_sentiment * nlp_confidence) FILTER (...)`
- `nlp_confidence_sum`       = `SUM(nlp_confidence) FILTER (...)`

Downstream computes `weighted_avg = weight_sum / NULLIF(conf_sum, 0)` and the
`choose_sentiment_weighted` helper in `app/services/sentiment_fusion.py`
picks it over the legacy `avg_nlp_sentiment` whenever it is available.

Production validation right after the swap, top 10 countries by 24h volume:

| CC | Vol | Flat | Weighted | Delta |
|----|----:|-----:|---------:|------:|
| US | 25,868 | -1.24 | **-2.20** | -0.96 |
| GB |  9,882 | -1.21 | -2.18 | -0.97 |
| CN |  8,611 | -0.55 | -1.83 | **-1.28** |
| IN |  7,428 | -1.34 | -2.32 | -0.97 |
| IT |  6,871 | -1.48 | -2.37 | -0.89 |
| RU |  6,260 | -3.75 | -4.25 | -0.50 |
| CA |  5,115 | -0.77 | -1.58 | -0.80 |
| DE |  4,925 | -1.73 | -2.77 | -1.05 |
| ES |  4,470 | -2.92 | -3.74 | -0.81 |
| TR |  4,389 | -3.63 | -4.07 | -0.44 |

Every top-10 country shifts more negative because the lexicon hits were
under-reporting magnitude. CN moves furthest (-1.28) because lexicon
coverage on Chinese-language headlines was weakest, so transformer rows
carry disproportionately more signal in that bucket.

Migration application order (Supabase MCP, statement-level):

1. `033a` — `ALTER TABLE` on theme_hourly_v2 + theme_country_hourly_v2.
2. Backfill 24h windows in chunks (6h × 3) to avoid MCP query timeouts.
3. `033b` — `CREATE MATERIALIZED VIEW country_hourly_v2_new WITH NO DATA`
   plus unique + secondary indexes.
4. `REFRESH MATERIALIZED VIEW country_hourly_v2_new` via `execute_sql`
   because REFRESH cannot run inside a transaction block.
5. `033c` — `BEGIN; RENAME swap; COMMIT;` for matview + 4 indexes.
6. `033d` — `DROP MATERIALIZED VIEW country_hourly_v2_old CASCADE`.

Code changes:

- `app/services/sentiment_fusion.py`: new `_weighted_nlp_raw` +
  `choose_sentiment_weighted` helpers, plus `serialize_country_row`
  auto-detecting weighted columns. Legacy `choose_sentiment` preserved.
- `app/services/ingest_v2.py`: theme_hourly_v2 + theme_country_hourly_v2
  INSERT...ON CONFLICT extended to write the weighted sums on every
  2-hour refresh cycle.
- `app/routers/briefing.py`: three country queries (top_countries,
  negative_sentiment, positive_sentiment) and the global stats query now
  select the weighted columns. `chosen_sentiment_raw` ORDER BY prefers
  `(weight_sum / conf_sum)` and falls through to legacy `nlp_avg` then
  GDELT. Global stats consume `choose_sentiment_weighted`.

Tests: 298 passed, 6 skipped. New coverage:

- `tests/test_briefing_sentiment_fusion.py`: 9 cases for
  `_weighted_nlp_raw` + `choose_sentiment_weighted` including the
  transformer-vs-lexicon dilution scenario from the production benchmark.
- `tests/test_ingest_pre_agg_nlp_coverage.py`: relaxed whitespace
  matching and added two shape tests for the new INSERT columns.

Deployment:

- DB is live with the new schema and backfilled 24h of weighted sums.
- Backend API still serves the legacy `sentiment_source = "nlp"` path
  until `scripts/deploy-fly-api.sh` ships the new code. The current API
  reads the new matview transparently because old columns still exist;
  no degradation in the meantime.
- After deploy the briefing response carries
  `sentiment_source = "nlp_weighted"` whenever the bucket has any
  confidence mass. UI label work to expose the new source label is a
  follow-up under #183.

Out of scope for migration 033:

- `historical_topic_country_daily` does not carry per-row
  `nlp_confidence`, so historical day cells stay on flat
  `sentiment_coverage` until `historical_process_partition.py` is
  extended to emit weighted sums and the existing 18 cutover days are
  reprocessed.

---

## Lexicon mining + scoring quality fix (2026-05-22)

Following the local hot/cold automation, a quality audit produced two
findings that reframe the next NLP work:

1. **Effective NLP coverage in product cells is already near 100% in the
   hot window** (`country_hourly_v2`: 221/221 cells qualify for fusion;
   `theme_country_hourly_v2`: 103,256/104,295 cells qualify). The
   widely-cited "4% transformer" figure is the raw row share, not the
   product-cell share. Baseline saved at
   `docs/research/nlp-coverage/2026-05-22-effective-coverage-baseline.{json,md}`.
2. **The real dilution lever is the 11.5% `fast_neutral` share**, not the
   transformer-row gap. New helper:
   `backend/scripts/nlp_coverage_report.py` measures this directly against
   `country_hourly_v2`, `theme_country_hourly_v2`, and
   `historical_topic_country_daily`.

Two bugs were unblocking the lexicon path (#185):

- **HTML entity decode.** Headlines from upstream feeds contain numeric
  references (`&#xE4;`) that the tokenizer fractured into junk tokens
  (`verk` + `xe4` + `ndet`). `html.unescape` is now applied in both the
  runtime scorer (`enrichment/lexicon_sentiment.py`) and the miner
  (`scripts/mine_lexicon_vocab.py`). 22.6% of sampled `fast_neutral` rows
  from the last 24h contain such entities; 3.5% would now flip to lexicon.
- **`xx` rows ignored.** The XLM multilingual NLP pipeline stamps
  `source_lang='xx'` on 82% of transformer-tagged rows. The miner
  previously discarded them. It now runs `langdetect.detect_langs` on the
  cleaned headline (seed 0; min confidence 0.85) and projects onto the
  supported set.

Live mine results (min_freq=10, min_abs_mean=0.4) after both fixes:

| Lang | Before | After (merged) |
|------|-------:|---------------:|
| en   |  1,920 |          1,923 |
| es   |      7 |             81 |
| it   |      0 |             34 |
| de   |      0 |             18 |
| pt   |      2 |             11 |
| ar   |      2 |              7 |
| fr   |      0 |              2 |

The miner now defaults to merge mode and writes `<lang>.mined.json.bak`
before overwriting. `--replace` opts into hard overwrite. `--no-langdetect`
restores the prior xx-skipping behavior.

Tests: 62 passed across `tests/test_lexicon_sentiment.py`,
`tests/test_lexicon_mining.py`, `tests/test_fast_lane.py`,
`tests/test_archive_common.py`, `tests/test_historical_processing.py`.
Three regression tests pin the HTML entity decode behavior.

Deployment notes:

- Runtime change to `lexicon_sentiment.py` requires NLP worker redeploy
  (`scripts/deploy-fly-nlp-worker.sh`) before existing `fast_neutral` rows
  improve. New rows ingested by the redeployed worker score correctly.
- Re-mining schedule: rerun
  `python -m scripts.mine_lexicon_vocab --min-freq 10` after every few
  thousand new transformer rows. Future: tie to `nlp_progress` checkpoints.
- Aggressive thresholds (min_freq=5, min_abs_mean=0.3) yield ~700 non-EN
  terms but accept noisier surface forms (entity names, short articles);
  hold for a second-pass after measuring ROI of the conservative cut.

Commits:

- `5b02e7c feat(nlp): add product-cell effective coverage report + baseline`
- `6c6b253 fix(lexicon): decode HTML entities + langdetect xx rows in mining + scorer`

---

## Current coordination layer (2026-05-21)

Use `docs/roadmap/2026-05-21-data-operating-roadmap.md` as the active execution order for the current data phase. It organizes the open work into five layers:

1. Stabilize ground truth and issue scope.
2. Fill processed historical tables from the verified local archive.
3. Route `/app` long windows through processed history with explicit coverage.
4. Improve hot-window NLP/topic/source quality at ingest speed.
5. Present the improved data with coverage/provenance UI and visual manuals.

The older roadmap files remain useful background, but they are now subordinate to this coordination roadmap:

- `docs/roadmap/2026-05-16-productization-roadmap.md` — product/UX direction.
- `docs/roadmap/2026-05-19-topic-and-signal-class-attack.md` — detailed topic/source-quality plan.

### Routing scope correction

`docs/superpowers/specs/2026-05-21-processed-historical-routing-design.md` is now explicitly scoped as **app-wide processed historical routing**, not merely the shipped `/brief` bridge.

Already shipped:

- `/api/v2/briefing?hours>24` routes `top_themes` to `historical_topic_country_daily`.
- `/api/v2/briefing?hours>24` routes `top_sources` to `historical_source_daily` (#194 fix).
- `/brief` shows historical processed coverage metadata.
- Full verified cutover archive backfill is synced to Supabase compact history:
  `18` days, `2,128,070` represented signals, `22,711` compact aggregate rows,
  `236` countries, `11` topics, model `atlas-hist-v1`.
- Source aggregate backfill is synced to Supabase compact history:
  `18` days, `2,128,070` represented signals, `161,871` daily source aggregate rows,
  model `atlas-hist-v1`; live `top_sources` historical query is ~40 ms with index-only scan.
- `/api/v2/heat/countries`, `/api/v2/country/{code}`, `/api/v2/theme/{topic_slug}`,
  and `/api/v2/anomalies/themes` route long windows through processed history with coverage metadata.
- Reusable frontend `CoverageBadge` is wired into Heat and Theme Detail.

Still pending:

- Visual app-wide smoke test through the deployed frontend before closing `#193`.
- Continue hot-window data quality and throughput work: `#171`, `#167`, `#185`, `#184`.
- Continue hot-window data quality and throughput work: `#171`, `#167`, `#185`, `#184`.
- Handle AISStream expired TLS as a degraded provider (#196).

Infrastructure shipped:

- Fly image split (#195) is implemented and production-verified.
- `scripts/deploy-fly-api.sh` deploys `api-runtime` only to process group `app`; verified image size `257 MB`.
- `scripts/deploy-fly-nlp-worker.sh` deploys `nlp-runtime` only to process group `nlp_worker`.
- Current production has mixed images by design: `app` on lightweight API image, `nlp_worker` on heavy model image.

### Incremental catch-up after local outage (2026-05-22)

Pedro's computer was off during the intended `00:00-06:00 America/Bogota`
maintenance window, so no local archive/backlog job ran automatically. The manual
catch-up below cleared that gap, and a local `launchd` automation is now installed
to keep the hot store light going forward.

Manual catch-up completed on 2026-05-22:

- Planned hot rows older than 24h: `279,555`.
- Exported archive: `/Users/pedro/AtlasArchive/incremental/2026-05-22-catchup`.
- Archive verification: `8` manifest records, `279,555` rows, `0` failures, `0` overlaps.
- Recomputed compact history by combining the original cutover archive with the incremental archive for overlapping days `2026-05-14` through `2026-05-20`, plus new day `2026-05-21`.
- Historical processed totals after sync:
  - `historical_topic_country_daily`: `25,187` rows, `2,407,625` represented signals, `2026-05-03` through `2026-05-21`.
  - `historical_source_daily`: `179,253` rows, `2,407,625` represented signals, `2026-05-03` through `2026-05-21`.
- Prune dry-run parity: `archive_rows=279,555`, `db_candidate_rows=279,555`.
- Live prune completed: `deleted_rows=279,555`, `elapsed_seconds=29.31`.
- Post-prune `VACUUM (ANALYZE) public.signals_v2` completed.
- Post-prune verification:
  - `signals_v2`: `176,636` rows, min timestamp `2026-05-21T12:33:32Z`.
  - Catch-up archive ranges remaining in `signals_v2`: `0`.
  - `/health`: healthy; `rows_ingested_last_15m=890`; `nlp.unprocessed_total≈168.6k`.
  - Local SLA report for 24h: `100%` Atlas-owned enrichment (`168,573` fast-lane rows, `8,021` transformer rows).

Follow-up automation shipped on 2026-05-22:

- New runner: `backend/scripts/local_hot_cold_catchup.py`.
- Launch wrapper: `scripts/run-local-hot-cold-catchup.sh`.
- Installer: `scripts/install-local-hot-cold-launchd.sh`.
- LaunchAgent template: `infra/launchd/com.atlas.local-hot-cold-catchup.plist`.
- Runtime home: `/Users/pedro/AtlasLocalWorker` because macOS blocks launchd execution from Desktop-protected paths.
- Schedule: `00:10`, `01:10`, `02:10`, `03:10`, `04:10`, `05:10` local time, plus `RunAtLoad`.
- Behavior: dry-run by code default, but installed wrapper runs live export + verified sync + verified prune. It only runs outside the window when catch-up rows exceed the threshold.
- Safety gates: archive verification must pass; prune dry-run must match exported rows and DB candidate rows; live prune requires `--i-understand-irreversible-delete`; `VACUUM (ANALYZE) public.signals_v2` runs after prune.
- LaunchAgent verification: installed and `last exit code = 0`.

Validation after automation install:

- Launchd catch-up exported/verified/pruned an additional `3,645` rows.
- `signals_v2`: `173,925` rows, min timestamp `2026-05-21T13:16:07Z`.
- `historical_topic_country_daily`: `2,412,591` represented signals, `2026-05-03` through `2026-05-21`.
- `historical_source_daily`: `2,412,591` represented signals, `2026-05-03` through `2026-05-21`.
- `archive_plan --older-than-hours 24`: `7` residual moving-cutoff rows.
- Local SLA report for 24h: `100%` Atlas-owned enrichment (`165,818` fast-lane rows, `8,104` transformer rows).

Issue `#193` should remain open until app-wide routing is shipped and smoke-tested. The briefing bridge is complete but not the full app-window routing scope.

Quality finding: historical compact storage is complete for the cutover, but
`general-monitoring` still represents `1,559,990` of `2,128,070` signals. That
makes #171/#167/#185 the next quality bottleneck after app-wide routing.

---

## Current handoff (2026-05-21) — Processed Historical Sync

Production branch remains `v3-intel-layer`. The hot/cold cutover is complete; the current implementation direction is to make the local archive useful by syncing processed historical outputs back to Supabase without reloading raw history.

### Processed Historical Sync direction (2026-05-21)

Canonical decision: Supabase should serve processed historical product surfaces,
not raw historical rows. Raw historical signals live in the local archive; the
local processor turns archive partitions into compact processed outputs and syncs
only those product-ready tables to Supabase.

New docs:

- Spec: `docs/superpowers/specs/2026-05-21-processed-historical-sync-design.md`
- Plan: `docs/superpowers/plans/2026-05-21-processed-historical-sync.md`

New tracking issues:

- #191 — local processed historical sync from archive to Supabase.
- #192 — processed-only historical tables and Supabase lightweight guardrails.
- #193 — route `1w`/`1m` app windows to processed historical tables.

Related issues commented with integration note: #164, #167, #171, #184, #185.

Operational rule:

- Fly owns hot-window SLA and fresh processing.
- Local machine owns historical/backlog processing.
- Supabase stores hot raw rows temporarily, plus compact processed aggregates,
  evidence samples, coverage metadata, topic/entity/narrative indexes, and
  correction/learning state.
- Supabase should not receive a raw historical copy of `signals_v2`.

Implementation started:

- Added `backend/migrations/029_historical_processed_tables.sql` for compact historical processed tables.
- Added `backend/scripts/historical_process_partition.py` to convert local archive partitions into daily topic/country aggregates.
- Added `backend/scripts/historical_sync.py` for idempotent upsert payloads and dry-run/live sync.
- Added `backend/tests/test_historical_processing.py`.
- Smoke processed archive day `2026-05-19`: `185,163` archived rows -> `1,728` processed aggregate rows.
- Smoke artifact: `docs/research/processed-historical-sync/2026-05-19-topic-country.json`.
- Validation: `cd backend && .venv/bin/python -m pytest tests/test_historical_processing.py tests/test_archive_common.py -q` -> `18 passed`.
- Validation: `cd backend && .venv/bin/python -m scripts.historical_sync --artifact ../docs/research/processed-historical-sync/2026-05-19-topic-country.json --dry-run` -> `{"dry_run": true, "rows": 1728}`.
- Supabase MCP configured and OAuth login completed. Migration `029` applied through Supabase MCP.
- Live sync completed using Fly runtime `DATABASE_URL`: `{"dry_run": false, "rows": 1728}`.
- Supabase verification for `day='2026-05-19'`, `model_version='atlas-hist-v1'`: `1,728` rows, `185,163` summed `signal_count`.
- Top synced bucket: `general-monitoring` / `US` / `gdelt` / `reporting` with `20,960` signals. This confirms the historical path works and also shows Topic Intelligence needs better non-general coverage.
- API bridge implemented for #193: `/api/v2/briefing?hours>24` now routes `top_themes` to `historical_topic_country_daily` when available and returns `top_themes_source` plus `historical_coverage` metadata.
- Frontend `/brief` displays a compact historical processed coverage note for long-window briefs.
- Added `backend/scripts/historical_coverage_report.py`. Live report baseline: `1,728` aggregate rows, `185,163` represented signals, `226` countries, `11` topics, avg topic coverage `0.7703`, avg sentiment coverage `0.1384`.
- Validation: backend full suite -> `271 passed, 6 skipped`; frontend `npm run build` passed; archive verify passed (`18/18` records, `2,128,070` rows, `0` failures).

### Hot/cold retention cutover state

- Local archive root: `/Users/pedro/AtlasArchive`.
- Clean cutover archive: `/Users/pedro/AtlasArchive/cutovers/2026-05-20`.
- Export source: Fly app machine `d8d2e46fe07e78`, Supabase `signals_v2`.
- Export window: `2026-05-03T00:00:00Z` through `2026-05-20T03:33:29Z`.
- Exported partitions: `18` UTC date-sized JSONL gzip files.
- Verified rows: `2,128,070`.
- Local compressed size: `~368M`.
- Manifest verification: `18/18` records OK, `0` failed, `0` overlaps.

Smoke queries against the local archive:

| Query | Result |
|-------|--------|
| Date `2026-05-19` | `185,163` rows |
| Country `CO` | `13,654` rows |
| Source family `social` | `485` rows |
| Topic/headline substring `energy` | `92,005` rows |

Safety tooling added:

- `backend/scripts/archive_verify.py` — verifies manifest row counts, SHA256 digests, compressed byte sizes, and overlapping ranges.
- `backend/scripts/archive_plan.py` — plans daily cold-export batches from Supabase.
- `backend/scripts/prune_archived_signals.py` — dry-run by default; live delete requires `--execute --i-understand-irreversible-delete` and only prunes `signals_v2` rows covered by verified manifest ranges.

Validation:

- `cd backend && .venv/bin/python -m pytest tests/test_archive_common.py -q` → `10 passed`.
- `cd backend && .venv/bin/python -m pytest -q` → `260 passed, 6 skipped`.

Issue state:

- #188 closed: same-day hot-window NLP SLA reached through fast-lane enrichment.
- #189 closed: hot/cold architecture and first archive probe completed.
- #190 active: cutover archive backfill completed; next gate is verified prune dry-run and then explicit live prune decision.
- #190 closed: cutover archive backfill completed; verified prune dry-run passed exactly (`2,128,070` archive rows = `2,128,070` DB candidates); live prune executed after explicit approval.

### Important guardrail

Do not run broad deletes manually. Use `backend/scripts/prune_archived_signals.py` only after `archive_verify.py` passes on a clean archive. The live prune completed from Fly nlp_worker `0803426f142468` with exact parity: `archive_rows=2,128,070`, `db_candidate_rows=2,128,070`, `deleted_rows=2,128,070`, `elapsed_seconds=139.13`. Post-prune verification: archived range remaining `0`, exact `signals_v2` count `259,360`, `ANALYZE signals_v2` completed, and `nlp_progress` recomputed to `unprocessed_total=241,002`. The prune script touched only `signals_v2`; product aggregates, correction tables, topic tables, and NLP audit/progress state were intentionally retained. `/health.total_signals` now represents historical aggregate volume from `country_hourly_v2`, not raw hot-store rows.

---

## Previous handoff (2026-05-20) — Session 19

Production is on `v3-intel-layer` at `763b3c9 feat(lexicon): first mined vocab snapshots from 15K transformer-tagged rows`.

### Production state verified 2026-05-20

- Fly `/health`: healthy.
- `total_signals`: ~2.26M.
- `rows_ingested_last_15m`: ~3K during latest check.
- NLP backlog remains the core constraint:
  - `unprocessed_24h`: ~179K.
  - `unprocessed_total`: ~2.09M.
  - worker is healthy, but current throughput is structurally below ingest velocity.
- `nlp_worker`: Fly process group, `shared-cpu-2x`, 4GB, `NLP_WORKER_LIMIT` still conservative.

### What shipped since the previous status

| Commit | Area | Result |
|--------|------|--------|
| `09b95bb` | Migrations 025 + briefing insight | Pre-aggregates now track NLP coverage columns. |
| `507c395` | Migration 026 | `country_hourly_v2` matview swap with NLP coverage. |
| `70e39c0` | Sentiment fusion | `choose_sentiment()` selects NLP only when coverage is high enough; otherwise honest GDELT fallback. |
| `82c0888` | Lexicon seeds | Expanded EN/ES/PT and added IT/DE seed lexicons; plateau confirmed. |
| `1332a8d` | Briefing sources | Restored `top_sources` from bounded/cached `signals_v2`. |
| `43732a9` | Heat ranking | Added `heat_countries` section; closes #149/#165 product side. |
| `613a21e` + `3e0fce8` | Operational integrity | `nlp_progress` recomputes from ground truth; added `heat_voluminous_countries`. |
| `afc68e5` → `763b3c9` | Lexicon mining | Added corpus miner, Docker script copy, stopword filtering, and first mined snapshots. |

### Issues closed or updated

- Closed: #149, #165, #186, #187.
- Open and current:
  - #183 — frontend must render `sentiment_source`, NLP coverage badge, heat panels.
  - #184 — bump `NLP_WORKER_LIMIT` and measure memory/DB pressure.
  - #185 — corpus mining infrastructure shipped, but quality target remains open. Current snapshots are strong for EN only; non-EN corpus is too small.
  - #188 — define same-day processing SLA for incoming signals.
  - #189 — define hot/cold storage and optional local-worker operating model.
- Still relevant older data/product issues: #154, #157, #162, #164, #167, #171, #180.

### Important findings

1. Atlas has enough raw volume, but not enough normalized/enriched volume.
2. Ingest velocity currently exceeds transformer NLP velocity by a wide margin.
3. Lexicon backfill helps but does not solve multilingual quality by itself:
   - manual seeds plateaued;
   - corpus-mined EN expanded to ~1,920 tokens;
   - non-EN mined snapshots remain tiny because transformer-tagged non-EN sample is too small.
4. Heat ranking works as intended: it surfaces smaller/regional countries that raw volume ranking hides.
5. Supabase IO becomes the limiting factor when we run broad updates or full-table backfills. Avoid all-table mutation patterns.

### Next decision

Before continuing implementation, decide the data operating model:

- **A. Cloud-only acceleration:** increase Fly NLP capacity and keep Supabase as canonical hot+historical store.
- **B. Hot/cold split:** Supabase keeps hot operational data and aggregates; local/cheap storage keeps raw historical archive and offline backfills.
- **C. Hybrid worker:** local machine runs heavy offline NLP/backfill jobs and syncs curated results back to Supabase/Fly.

Recommended direction: **B plus C carefully**. Keep Supabase as the 24h-30d operational surface, but move raw historical/bulk experimentation to local object/archive storage. Do not make the public app depend on the home machine being online.

---

## Previous handoff (2026-05-16) — Session 18

Latest shipped production commit is still `2989dc5 docs: record production hotfix verification`; this session is documentation/research/roadmap only.

### What changed this session

- Generated local transcripts for the three owner walkthrough videos:
  - Landing: `docs/research/ux-video-evaluation/transcripts/Screen Recording 2026-05-14 at 21.40.47.txt`
  - Brief: `docs/research/ux-video-evaluation/transcripts/Screen Recording 2026-05-14 at 21.53.02.txt`
  - App: `docs/research/ux-video-evaluation/transcripts/Screen Recording 2026-05-16 at 09.25.31.txt`
- Added YouTube auto-generated Spanish captions for the App video:
  - `docs/research/ux-video-evaluation/transcripts/youtube-app-x8qlx2cijEE-es-auto.txt`
- Added full review: `docs/research/ux-video-evaluation/2026-05-16-atlas-video-review.md`
- Added productization design spec: `docs/superpowers/specs/2026-05-16-atlas-productization-design.md`
- Added roadmap: `docs/roadmap/2026-05-16-productization-roadmap.md`

### Product direction

Atlas is now in productization mode: make the existing intelligence **teachable, persistent, and exportable**.

- Teachable: explain Brief/App/Workspace methodology with real product screenshots and persona-specific use cases.
- Persistent: preserve investigation context across search, theme, country, source, Public Attention, and Workspace pivots.
- Exportable: convert pinned evidence into dossiers, Reading Mode, and eventually Atlas Daily editions.

### GitHub issues updated from the video review

Reopened with new evidence:

| Issue | Why |
|-------|-----|
| #56 | Day/Night overlay is harsh; Settings value unclear. |
| #69 | Spanish query `conflicto en Colombia` did not route to a useful Colombia/conflict investigation. |
| #104 | Google Trends appears missing/stale in Public Attention. |
| #124 | Watch button is missing/overlapping and not surfaced in walkthrough. |
| #128 | Workspace/Trail/Pinned graph remains hard to use and can leave viewport. |

New issues:

| Issue | What |
|-------|------|
| #135 | Landing live stats + clickable product cards linked to visual docs. |
| #136 | Prefetch and loading states across Landing -> Brief -> App. |
| #137 | Restore/replace editorial analysis and explain mood/tone/sentiment/drift/baseline. |
| #138 | Preserve investigation context across pivots. |
| #139 | Extend console range beyond 24h and clarify Live/Pause. |
| #140 | Visual use-case manual with real Atlas screenshots and annotated flows. |
| #141 | Reading Mode / Atlas investigation newspaper from pinned evidence. |
| #142 | Scope Trends/Wikipedia to active country/topic and make items actionable. |
| #143 | Explain and declutter map layers, ships, geo alerts, arcs, and colors. |

### Recommended next order

1. P0 trust/continuity: #136, #137, #138, #128, #104/#142, #69.
2. P1 visual onboarding: #140, #134, #135.
3. P2 exportable investigation: #133, #141, #124.
4. P3 polish: #139, #143, #56.

Production remains on `v3-intel-layer`. `main` is still abandoned per repo guidance.

---

## Previous handoff (2026-05-14) — Session 17

Latest shipped commit: `6e8e0df fix(api): restore router runtime imports` on `v3-intel-layer`.

### Closable issues closed this session

| Commit | Issue | What |
|--------|-------|------|
| `69d4b93` | docs | Remaining issue closure plan saved in `docs/superpowers/plans/2026-05-14-remaining-issues-closure.md` |
| `220b91f` | #82 | Temporal Graph selected bucket can pin a typed temporal snapshot into Workspace |
| `7fb5eaa` | #61 | Shared `CompareDashboard` shell for ThemeCompare and PersonCompare |
| `ea6c2ce` | #105 | RSS registry expanded to 50 curated feeds; provenance fields preserved |
| `2d3b2aa` | #70 | Frontend theme hierarchy: 7 clusters, 79 mapped codes, EntityPanel grouping, NarrativeThreads cluster label |
| `82e2e77` | hotfix | Restored `/health` imports after production 500 |
| `6e8e0df` | hotfix | Restored router runtime imports after `/api/v2/narratives` production 500 |

### Remaining open issues

| # | Status | Notes |
|---|--------|-------|
| #46 | blocked | ACLED API access required before real integration. Labeled `blocked` and commented. |
| #106 | blocked | Designer SVG mascot assets required before dev. Labeled `blocked` and commented. |

### Validation

- `cd frontend-v2 && npm run test` → 26 passed.
- `cd frontend-v2 && npm run build` → passed after #82, #61, and #70; known large chunk warning remains.
- `python3 -m py_compile backend/app/services/ingest_rss.py` → passed.
- `python3 -m py_compile backend/app/routers/*.py` targeted hotfix set → passed.
- `backend/.venv/bin/python -m pytest backend/tests/test_health.py -q` → 2 passed.
- Production Fly `/health` → 200 healthy, checks passing on machine `d8d2e46fe07e78` version 112.
- Production Fly and Vercel rewrite `/api/v2/narratives?hours=24&limit=3` → 200 JSON.
- Production Vercel rewrite `/api/v2/stats` → 200 JSON.
- `origin/v3-intel-layer` is pushed through `6e8e0df`.

### Branch recommendation

Production is currently verified on `v3-intel-layer`. Do not repoint production to `main` in the next handoff; current repo guidance marks `main` as abandoned for now, so any branch migration should be a separate controlled decision.

---

## Previous handoff (2026-05-14) — Session 16

Latest shipped commit: `3f42949 feat: Evolution Graph — leaf node treatment + Open in Workspace (#109)` on `v3-intel-layer`.

### 10 issues closed this session

| Commit | Issue | What |
|--------|-------|------|
| `2f97f19` | #129 | Onboarding tour: write localStorage on mount → no re-trigger on nav-away |
| `5e2499b` | #130 | SourceIntegrityPanel: `filter.theme` → `getThemeLabel()`, no raw GDELT codes |
| `f5e4383` | #132 | Workspace graph: compact dot mode at 20+ nodes / zoom < 1.2 |
| `09d24be` | #131 | Custom investigative concepts: `useCustomConcepts` hook, `CustomConceptModal`, SearchBar integration |
| code verified | #80 | Session graph already fully implemented (trackVisit, trail tab, promote-to-pin) |
| `1888800` | #111 | StreamLevel in FocusContext; SignalStream writes it; AnomalyPanel + SourceIntegrity show context badges |
| `1b2b35c` | #114 | Workspace expert analyst audit → `docs/research/workspace-expert-audit.md` |
| code verified | #79 | Public Attention AEIL pin + workspace node + graph relationships already implemented |
| `37aaf0b` | #124 | Saved watches: `useSavedWatches` hook, WATCH button in toolbar, watches section in /brief |
| `3f42949` | #109 | Evolution Graph: leaf node treatment (55% radius, hide label <1.4 zoom); "⊞ Workspace" button |

### Untracked fixes (from workspace-expert-audit.md)
- `21fa9d0` — NarrativeThreads country pips → interactive buttons; thread click auto-opens CountryBrief for top country

### Open issues (6 remaining)

| # | Type | Notes |
|---|------|-------|
| #82 | L | Temporal narrative graph + workspace integration |
| #61 | L | Compare engine UI |
| #105 | data | RSS feed expansion |
| #70 | L | Theme clustering over GDELT taxonomy |
| #46 | blocked | ACLED API access (external) |
| #106 | needs designer | Octopus mascot — scope documented in issue comment |

### Architecture note — backend routers
`backend/app/main_v2.py` is now the slim entrypoint. All routes live in `backend/app/routers/`. DB pool exposed via `backend/app/db.py` (`db.pool`, set on startup). Shared helpers in `backend/app/utils.py`.

### New hooks added this session
- `frontend-v2/src/hooks/useCustomConcepts.ts` — localStorage CRUD for user-defined investigative concepts
- `frontend-v2/src/hooks/useSavedWatches.ts` — localStorage CRUD for named filter watches
- `frontend-v2/src/components/CustomConceptModal.tsx` — create/edit modal with live theme search picker

---

## Previous handoff (2026-05-14)

What changed:
- Public Attention now behaves as a people-side enrichment layer, not a separate destination. Clicking a Public Attention topic can open a narrative thread while preserving the originating attention context.
- `ThemeDetail` shows `opened from Public Attention: <topic>` and adds a Public Attention Context block when opened from an attention item.
- `CountryBrief` now fetches country-scoped Google Trends and Wikipedia proxies, and its analysis copy reads more like `/brief` while staying inside the console panel.
- Workspace now exposes a visible `Trail` tab using existing `sessionItems`; the trail records investigation pivots and can pin/open trail points.
- First-run walkthrough advanced to `atlas_onboarding_v3` and now explains Anomaly/Public Attention as the second lens next to Signal Stream.

Validated:
- `cd frontend-v2 && npm run test` → 25 tests passed.
- `cd frontend-v2 && npm run build` → passed; known large chunk warning remains for MapLibre/main bundle.
- `cd frontend-v2 && npm run lint` → 0 errors, 37 existing warnings.
- Browser QA local verified `/app?attention=ShinyHunters`, `/app?theme=TAX_FNCACT_CYBER_ATTACK&attention=ShinyHunters`, visible Public Attention context, and Workspace Trail. Local backend was not running, so API-backed content was empty/500 during UI verification.

New issue created:
- **#128** — `ux(workspace): keep board in viewport and separate Trail graph from Pinned graph`
  - Workspace modal can exceed laptop/browser bounds, hiding close/actions.
  - Trail and Pinned need distinct visual modes; Trail should show an ordered investigation path, Pinned should remain the evidence relationship board.
  - Force graph physics need tuning for 40-60 node sessions; current clusters can collapse into overlapping labels.

Recommended next order:
1. Fix **#128** before deeper Workspace graph work. This is a usability blocker now that Trail is visible.
2. Close/review implemented UX issues: #108, #119, #120, #121, #123, #127 after production visual QA.
3. Continue #80/#82 with the distinction that Trail ≠ Pinned graph.
4. Then return to #107 slow panels and #110 visible correctness.

---

## Current UX direction (2026-05-12)

Atlas is now positioned as a **public narrative intelligence console**, not a GDELT wrapper.
The preferred first user path is `/brief` for orientation, with `/app` as the full analyst console.

This session implements:
- Landing copy refresh: Atlas = daily brief + live map + country context + anomaly alerts + investigation workspace.
- SEO baseline in `frontend-v2/index.html`: descriptive title, meta description, canonical, Open Graph, Twitter card metadata, and `WebApplication` JSON-LD.
- Interactive guided tour v2: highlights Search, Globe, Signal Stream, Narrative Threads, Workspace, and Brief instead of showing passive text only.
- Command-bar discoverability: visible `WORKSPACE` button with pinned/session count and visible `TOUR` restart button.
- Coverage-bias correction in `/app`: map heat and hot-spot focus use country-baseline deviation; raw volume is framed as evidence density, not importance.
- `/brief` country selector now includes all known countries and shows an empty state when the selected country has no current-window theme cluster.
- Signal Stream defaults to `NOTABLE`, not `ALL`.
- Public Attention lists filter obvious entertainment/sports/lifestyle noise before rendering.

Issue mapping:
- `#108`, `#113`, `#119`, `#120`, `#121`, `#123`, `#127`.

Documentation:
- `docs/demos/2026-05-12-ux-onboarding-brand-refresh.md`

---

## Production hotfix (2026-05-13)

Root cause for the “no data / slow brief” incident was a frontend request storm, not missing production data.
The old deployed app repeatedly called `/api/v2/country/CO?hours=24` and `/api/v2/theme/WB_507_ENERGY_AND_EXTRACTIVES?hours=24` while a country and workspace session trail were active, pushing the single Fly machine to its 100 concurrent-connection hard limit and making `/health` degrade with `pool busy`.

Changes shipped in `7ac9500`:
- Stabilized `WorkspaceContext` callbacks with `useCallback`, especially `trackVisit`, so session tracking no longer retriggers on every render.
- Removed the `/api/v2/country/{code}` fetch from the country click path in `/app`.
- Rebuilt `CountryBrief` from lighter `/api/v2/nodes?focus_type=country...` and `/api/v2/signals?country_code=...` calls, deriving top themes, sources, people, sentiment, and recent signals client-side.
- Changed the coverage-bias disclaimer from fixed overlay to in-flow layout so it no longer covers panel controls/back affordances.
- `BRIEF` navigation now preserves context: `/brief?range=<range>&country=<code>`.

Production actions and verification:
- Pushed `7ac9500` to `origin/v3-intel-layer`; Vercel deployed the frontend.
- Restarted Fly machine `d8d2e46fe07e78` to clear saturated in-flight requests.
- Verified Fly `/health` recovered to `healthy` with ~1.57M total signals.
- Verified `https://observatory-global.vercel.app/app?country=CO` loaded Colombia with 736 signals and source integrity populated.
- Verified `https://observatory-global.vercel.app/brief?range=24h&country=CO` loaded Colombia themes instead of an empty country state.

Follow-up backend hygiene:
- `/api/v2/stats` still logged one statement-timeout during recovery; harden that endpoint further if it recurs under ingest load.
- `/health` reported a future `last_ingest_ts` and negative `ingest_lag_minutes`; inspect timestamp normalization in ingest/health separately.
- Consider short TTL caching or request coalescing for heavy detail endpoints before opening the app to broader demos.

---

## Brief-to-console flow pass (2026-05-13)

Implemented the first slice of #111-style panel orchestration:
- `/brief` now treats country filters as first-class context: the top stat bar, analysis copy, and map emphasis switch from global to selected-country mode.
- The brief minimap remains global by default, but clicking a country selects it; when a country is selected, other countries dim and the selected country receives the strongest emphasis.
- Brief theme CTAs now deep-link to `/app?theme=<theme>&country=<country>` when country context exists, so a topic like Public Sector opens directly as a country-scoped ThemeDetail in the console.
- `/app` no longer auto-flies to the highest-volume/baseline country on initial load; the globe starts global and the hotspot fly-to remains available through the reset/hotspot button.
- ThemeDetail preserves country-scoped pivots from Brief/CountryBrief via `initialDrillCountry`.
- Related theme navigation now maintains a small in-panel back stack, so clicking a related topic no longer strands the analyst without a way back to the previous narrative.
- CountryBrief source lists now prefer the focus summary top sources when available, instead of relying only on the first 500 recent signals.

Related issues:
- #111 — Signal Stream/filter as global panel motor.
- #107 — remaining slow-panel work: add SWR/cache and richer skeletons.
- #112 — related-topic clarity remains open for deeper Related Investigations copy and behavior.

Production verification after `366db9b`:
- Verified `https://observatory-global.vercel.app/brief?range=24h&country=CO&v=366db9b` serves the new brief flow: Colombia has selected-country stats, the minimap dims the world and highlights Colombia, and the analysis block switches to `COUNTRY ANALYSIS`.
- Verified a brief theme CTA opens `/app?theme=WB_696_PUBLIC_SECTOR_MANAGEMENT&country=CO`, keeps ThemeDetail as the center panel, and loads Colombia-scoped Public Sector data.
- Verified `/app?v=366db9b` no longer auto-flies to the United States on initial load.
- During verification, found a backend correctness bug in `/api/v2/narratives`: `theme_hourly_v2.country_count` was summed across hourly buckets, inflating narrative country counts and geographic spread above 100%.

Backend follow-up shipped after verification:
- `/api/v2/narratives` now computes per-theme distinct `country_count` and `source_count` from the selected signal window for the top themes, then derives `spread_pct` from that distinct country count.
- Deployed backend to Fly after correcting the production column name to `source_name`.
- Validation: `python3 -m py_compile backend/app/main_v2.py` passed. Backend pytest could not run in this shell because `poetry` is not installed.
- Production API validation: `/health` returned `healthy`; `/api/v2/narratives?hours=24&limit=20` returned no error and top narrative spread values below 100% (`Environment 87.6`, `US Politics 80.2`, `Public Sector 84.8`).

---

## What we built (sessions 1–9)

### Core infrastructure (sessions 1–3)
- PostgreSQL schema: `signals_v2`, `events_v2`, aggregation materialized views
- FastAPI backend on Fly.io — 30+ API endpoints under `/api/v2/` and `/api/v3/`
- GDELT 2.0 ingest pipeline (`ingest_v2.py`) polling every 15 min
- Vercel frontend with Mapbox GL / MapLibre GL + DeckGL v9
- Redis-free architecture — direct DB queries with pg connection pool

### Intelligence features (sessions 3–5)
- **Narrative Drift chart** — 14-day sentiment trajectory line chart per topic
- **NarrativeThreads** — macro topic view: sparklines, spread bars, sentiment dots, trend labels
- **ThemeDetail** — full topic breakdown: country cards, drift chart, spikes, comparison
- **CountryBrief** — country snapshot: top themes, key people, sentiment, signal count
- **EntityPanel** — person-focus view: coverage by country, related themes
- **Comparative engine** — PersonCompare / ThemeCompare side-by-side charts
- **AnomalyPanel** — spike detection vs 7-day baseline + Wikipedia public attention
- **SourceIntegrityPanel** — source diversity score per context
- **CorrelationMatrix** — country/narrative overlap heatmap

### Investigation workspace (session 6)
- `InteractiveWorkspace.tsx` — react-force-graph-2d canvas, lazy-loaded (~188KB chunk)
- `InvestigationWorkspace.tsx` — shell with `React.lazy()` + `PanelErrorBoundary`
- `workspaceGraph.ts` — two-pass graph builder (pinned nodes always succeed; edges per-item try/catch)
- Three-layer error boundary: `RootErrorBoundary` → `PanelErrorBoundary` → `MapErrorBoundary`

### UX + quality fixes (sessions 5–8)
- Theme label formatter: all raw GDELT codes → human-readable names via `getThemeLabel()`
- Country key people: `CountryBrief` shows clickable person chips from `keyPersons`
- Signal Stream restored as blank state (eliminates duplicate content with NarrativeThreads)
- Graceful drift fallback: API failure → "No drift data" instead of red error
- Workspace node spread: D3 charge=-320, link distance=110, edge labels at zoom > 1.2
- Onboarding coachmark: 3-step overlay on first visit (localStorage-gated)
- Pin discoverability: workspace tab pulses when empty, empty state shows inline Pin icon

### Search, source integrity, and terminal UX (session 9)
- **Spanish-language search routing (#69)** — multilingual aliases and country extraction for compound queries like `conflicto Colombia`, `elecciones Colombia`, `violencia Mexico`, `petro colombia`.
- **Concept endpoint stability (#71)** — production now returns quickly by degrading long lookbacks to `effective_hours: 24`; true 168h aggregates are tracked separately in #73.
- **Source-family classification (#68)** — backend classifies theme top sources as `state`, `wire`, or `independent`; ThemeDetail now renders source-family badges in Top Sources.
- **Export findings (#66)** — ThemeDetail exports CSV/Markdown/PNG, CountryBrief exports Markdown, and Workspace export includes fetched investigation details where available.
- **Terminal dashboard polish** — compact Signal Stream rows, LIVE pill, UTC clock, map status bar, gradient Narrative Threads, A-XXX anomaly labels, improved entity headlines.

---

## Recent changes (session 10 - UX/QA hardening, 2026-05-12)

- **Brand narrative refresh** — landing now positions Atlas as a public narrative intelligence console, not a GDELT wrapper.
- **Interactive onboarding** — first-run guide now points users through Search, Globe, Signal Stream, Narrative Threads, Workspace, and Daily Brief instead of showing a passive text card.
- **Daily Brief UX** — `/brief` supports an all-country selector, empty country states, invalid range fallback, and optional insight fetch handling.
- **Noise filtering** — shared public-attention filter removes obvious entertainment/sports/lifestyle noise from affected UI surfaces.
- **Backend QA unblockers** — `/api/v2/stats`, `/api/v2/signals`, `/api/v2/anomalies`, and `/api/v2/briefing` now tolerate the current local Docker DB without timing out or failing on schema drift.
- **Backend pytest restored** — stale `app.main`/hexmap imports fixed, `HexmapGenerator` compatibility layer restored, GDELT parser aliases added, and network integration tests now require `--run-integration`; local suite is `139 passed, 6 skipped`.
- **Country Brief name fallback (#122)** — country panel headers now resolve ISO-only API names through shared `resolveCountryName`, avoiding duplicate labels like `CF CF`.
- **Browser QA completed** — Browser plugin verified landing, `/app`, guided tour steps, workspace entry, `/app?country=CF`, and `/brief?range=record` by DOM/console. Screenshot capture timed out, but recent browser console errors were clean.
- **Narratives local fallback** — `/api/v2/narratives` now falls back when local Docker DB lacks `theme_hourly_v2`, avoiding noisy traceback logs during QA.
- **Country code polish** — added GDELT/FIPS display mappings for `HO`, `PC`, and `NF` so record-range briefs do not show raw codes in top sentiment lists.
- **Known local data limitation** — local DB newest signal is `2026-04-27T20:30:00+00:00`; on `2026-05-12`, 24h/7d views render empty/stalled by design. Use `record`/8760h for local content QA or connect to a DB with current ingest.
- **Validation doc** — see `docs/demos/2026-05-12-ux-onboarding-brand-refresh.md`.

## Recent changes (session 9)

| Commit | What it does |
|--------|-------------|
| `3098b59` | **#66 closed**: country and workspace Markdown exports; hardened ThemeDetail export |
| `a6e7eab` | Refresh Atlas session status |
| `ddf338c` | **#68 closed**: source-family badges in ThemeDetail Top Sources |
| `7e405cf` | UX fixes: live stream, map reset, country cap, entity headlines |
| `7cb6b2c` | UX fixes: map reset, search quality, signal drip, anomaly layout, blood diamonds |
| `0c31e9e` | Compact signal rows, LIVE pill, UTC clock, map status bar |
| `2a88d98` | Workspace tab position, wiki search, source metrics, thread scroll |
| `ad0300f` | Terminal aesthetic: relative timestamps, filter tabs, gradient threads, A-XXX anomalies |
| `a9c9f8a` | **#68 backend**: classify source families in theme API |
| `572275d` | **#69 closed**: apply detected country to unified search |
| `76dbba1` | **#69**: extract country from multilingual queries |
| `b161ecf` | **#69**: add multilingual concept aliases |

**Issues closed recently:** #66, #68, #69, #71  
**Issue opened recently:** #73 (`perf(concepts): support true 168h concept aggregates without timeout`)

---

## Deploy status

Fly.io backend is deployed with the #69 search routing, #68 source-family field, and #71 concept fallback fixes.

Verified production examples:
- `/api/v2/concept/blood-diamonds?hours=168` returns HTTP 200 with `effective_hours: 24`.
- `/api/v2/search/unified?q=conflicto%20Colombia&hours=168` returns Colombia-scoped concepts/themes.
- `/api/v2/theme/ARMEDCONFLICT?hours=24` returns `topSources[].family`.

Vercel production deploy follows pushes to `v3-intel-layer`; verify `https://observatory-global.vercel.app/app` after frontend changes.

---

## Open issues (25 open as of 2026-05-12)

### Current UX/QA cluster
| # | Title | Status |
|---|-------|--------|
| **#127** | Public Attention filter out entertainment/actors | Implemented locally; ready to close after review |
| **#128** | Workspace bounds + distinct Trail/Pinned graph modes | New QA issue from 2026-05-14; next Workspace target |
| **#126** | TemporalNarrativeGraph hover-to-focus | Next small UX target |
| **#124** | Saved searches / persistent alerts | Next product feature after QA stabilization |
| **#123** | Workspace discoverability | Implemented locally; ready to close after review |
| **#122** | Country Brief ISO code header | Implemented locally; ready to close after review |
| **#121** | Coverage bias correction | Implemented locally; ready to close after review |
| **#120** | Signal Stream default to NOTABLE/CRITICAL | Implemented locally; ready to close after review |
| **#119** | Brief country filter includes all countries | Implemented locally; ready to close after review |
| **#113** | Signal Stream entry moment | Partially covered by revised cadence language; animation still separate |
| **#108** | Landing `/app` link + brief loading coherence | Implemented locally; ready to close after review |

### Larger roadmap
| # | Title | Notes |
|---|-------|-------|
| **#125** | Split `main_v2.py` into APIRouter modules | Backend tech debt; increasingly important after QA patches |
| **#114** | WorkspaceBoard usage audit | User research / workflow validation |
| **#112** | Related Topics versus column clarity | UX polish |
| **#111** | Signal Stream filter as global panel motor | Bigger interaction model |
| **#110** | Top Sources cap + source-click no recent signals | Backend/frontend bug |
| **#109** | Evolution Graph to Workspace | Graph roadmap |
| **#107** | Slow-loading panels: SWR + skeleton states | Performance polish |
| **#106** | Brand loading animation | Brand identity; defer until product narrative stabilizes |
| **#105** | Expand curated RSS feeds | Data coverage |
| **#82** | Temporal narrative graph + workspace relationships | Graph roadmap |
| **#80** | Session graph auto-build from navigation | Graph/workspace roadmap |
| **#79** | Entity Intelligence layout + workspace graph | Graph/workspace roadmap |
| **#70** | Theme clustering hierarchy layer | Backend research |
| **#61** | Comparative engine UI | Large product surface |
| **#46** | ACLED API access | Blocked externally |

---

## Recommended next order

1. **Close the implemented UX batch** — review and close #108, #119, #120, #121, #123, and #127 after visual QA. #121 now includes baseline-normalized hot-spot behavior, not only disclaimer copy.
2. **Fix local QA hygiene** — apply or backfill missing local migrations, especially `theme_country_hourly_v2` and NLP columns, then rerun backend tests.
3. **#122 / #110** — clean visible correctness bugs before adding new surfaces.
4. **#126 / #112 / #107** — small UX/performance polish while the redesign is still active.
5. **#128 / #80 / #82** — fix Workspace shell/graph usability first, then move toward guided investigation memory: saved searches, session graph, and temporal graph integration.

---

## Architecture snapshot

```
Vercel (frontend)          Fly.io (backend)             Supabase (DB)
─────────────────          ────────────────             ────────────
frontend-v2/               backend/start.sh             signals_v2
  App.tsx                    ingest watchdog             events_v2
  40+ .tsx components        main_v2.py API              trends_v2
  MapLibre GL                ingest_loop.py              wiki_pageviews_v2
  DeckGL v9                  GDELT: 15min                country_hourly_v2
  react-force-graph-2d       Google Trends RSS: 30min    country_daily_v2
                             RSS curated: 60min         theme_country_hourly_v2
                             ReliefWeb/OCHA: 60min      country_baseline_stats
                             ACLED: 60min               aggregates_*
                             Wikipedia: 24h
                             NLP enrichment: background
                             Fly machine: iad
```

### Critical rules (don't break these)
- **CSS**: Vanilla CSS everywhere EXCEPT `Landing.tsx` which uses Tailwind
- **Tooltips**: `data-tip="text"` only — never native `title=` attribute
- **Theme labels**: always `getThemeLabel(theme_code)` — never trust the API `label` field
- **Build**: always `npm run build` (not `tsc --noEmit`) before pushing
- **Workspace lazy load**: `InteractiveWorkspace` is lazy-loaded via `React.lazy()` in `InvestigationWorkspace` — do NOT import it directly
- **Graph library**: `react-force-graph-2d` only — never `react-force-graph` (3D version pulls AFRAME, crashes the app)
- **Onboarding key**: `atlas_onboarding_v1` in localStorage — increment suffix if you need to re-show it to existing users

---

## How to evaluate what's working

| Area | How to check |
|------|-------------|
| Onboarding | Delete `atlas_onboarding_v3` from localStorage → reload `/app` → guided overlay appears, including Anomaly/Public Attention |
| Signal Stream | Left panel shows live GDELT articles with timestamps |
| Narrative Threads | Right panel — 5 topics with sparklines, spread bars, trend arrows |
| Theme detail | Click any theme → stats + country cards + drift chart (or "No drift data for this period") |
| Country brief | Click any country → top themes + clickable person chips |
| Workspace board | Pin 3+ items → folder tab pulses green when empty → click it → nodes spread, edge labels at zoom-in |
| Public Attention | Bottom-right of Anomaly panel → shows top Wikipedia articles by pageview |
| Concept endpoint | `/api/v2/concept/blood-diamonds?hours=168` → returns JSON with `effective_hours: 24` until #73 |
| Search | Top bar → try "conflicto Colombia", "elecciones Colombia", "violencia Mexico", "petro colombia" |
| Source family | Open a ThemeDetail → Top Sources should show `State`, `Wire`, or `Independent` badges |
| Export | ThemeDetail Export menu downloads CSV/Markdown; CountryBrief Export downloads Markdown; Workspace export includes details for fetched pinned items |

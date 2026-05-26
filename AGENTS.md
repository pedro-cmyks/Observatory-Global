# Repository Guidelines

## Project Structure & Module Organization
`backend/` hosts the FastAPI service (APIs, services, NLP logic) and pytest suites under `tests/`. The active React + Vite client lives in `frontend-v2/` (`src/pages`, `src/components`, `src/lib`, `src/App.tsx`). The `frontend/` directory is DEPRECATED — do not touch it. Docker/Compose exists for local dev only; production runs on Vercel (frontend) + Fly.io (backend). ADRs, demos, and decision logs go in `docs/`; keep environment templates in `.env.example`. MCP server configuration lives in `.mcp.json` (supabase + stitch). Design assets exported from Google Stitch live in `stitch_atlas_landing_experience_redesign/`.

Key files added in session 15 (multi-source ingestion + NLP stabilization — 2026-05-19):
- `backend/app/services/ingest_newsdata.py` — NewsData.io multilingual ingestion. 7 country-primary buckets after post-commit edit: ES/PT LatAm split (CO/MX/BR/AR/VE + PE/CL/EC/BO/CU), AR MENA, FR West/Central Africa, SW/AM East Africa, SE Asia, S Asia. Page size 10, 7-day fetch window. Called every 4th cycle. Env: `NEWSDATA_API_KEY`. `source_family="api"`, `attribution_method="newsdata_api"`, `geo_confidence=0.7`.
- `backend/app/services/ingest_mediastack.py` — MediaStack ES/PT supplement. 17 LatAm countries, 100 articles/run, every 8th cycle (~2h). Env: `MEDIASTACK_API_KEY`. Free 500 req/month. `geo_confidence=0.65`.
- `backend/app/services/ingest_newsapi.py` — NewsAPI.org crisis queries. 8 EN queries (Colombia, Venezuela, Myanmar, Sudan, Gaza, Haiti, Sahel, Congo M23) with 7-day window + `searchIn=title,description` + `sortBy=publishedAt`. Every 8th cycle, offset by 4 from MediaStack. Env: `NEWSAPI_KEY`. Dev plan 100 req/day.
- `backend/app/services/ingest_reddit.py` — Reddit public API. 14 subreddits: worldnews, geopolitics, GlobalNews, colombia, Venezuela, ukraine, MiddleEast, Turkey, Nigeria, myanmar, haiti, CredibleDefense, SyrianCivilWar, PakistanPolitics. No API key needed. `source_family="social"`, `attribution_method="reddit_public"`, `geo_confidence=0.5`. Commentary layer — NOT peer to wire services.
- `backend/.env.example` — all backend env vars documented: `DATABASE_URL`, `NEWSDATA_API_KEY`, `MEDIASTACK_API_KEY`, `NEWSAPI_KEY`, `ACLED_API_KEY`, `ACLED_EMAIL`, `INGEST_INTERVAL_SECONDS`, `REDIS_URL`.
- `backend/migrations/019_atlas_topic_intelligence.sql` — Topic Intelligence schema (Codex track). Tables: `atlas_topics`, `signal_topic_assignments`, `topic_learning_examples`. 30 seed topics.
- `backend/migrations/020_nlp_progress_indexes.sql` — indexes for NLP worker progress math (Codex track). Avoids full-scan on signals_v2.

Key files added in session 20 (hot/cold retention cutover — 2026-05-20):
- `backend/scripts/archive_verify.py` — verifies local archive manifest row counts, SHA256 digests, compressed byte sizes, and overlapping time ranges.
- `backend/scripts/archive_plan.py` — plans daily `signals_v2` cold-export batches from Supabase without writing archive files.
- `backend/scripts/prune_archived_signals.py` — dry-run-first prune for `signals_v2`; live deletion requires `--execute --i-understand-irreversible-delete` and only applies to verified manifest ranges.

Key docs added in session 21 (processed historical sync — 2026-05-21):
- `docs/superpowers/specs/2026-05-21-processed-historical-sync-design.md` — canonical design: Supabase serves processed historical product surfaces, not raw historical rows.
- `docs/superpowers/plans/2026-05-21-processed-historical-sync.md` — implementation plan for historical processed schema, local archive processor, idempotent sync, long-window API bridge, and coverage reporting.
- `docs/superpowers/specs/2026-05-21-processed-historical-routing-design.md` — pending app-wide long-window routing design. The `/brief` bridge is done, but this spec covers `/app` endpoints and should not be considered complete until the endpoint quintet returns coverage envelopes.
- `docs/roadmap/2026-05-21-data-operating-roadmap.md` — current execution-order roadmap for data work. It coordinates hot/cold storage, processed historical sync, app-wide routing, NLP/topic/source quality, and later coverage/provenance UI.

Key files added in session 21 (processed historical sync — 2026-05-21):
- `backend/migrations/029_historical_processed_tables.sql` — compact processed historical tables: runs, topic/country daily aggregates, evidence samples, and archive coverage. Applied to Supabase through Supabase MCP after OAuth setup.
- `backend/scripts/historical_process_partition.py` — local archive partition processor. First smoke: 2026-05-19 archive partition, 185,163 rows -> 1,728 aggregate rows.
- `backend/scripts/historical_sync.py` — dry-run/live idempotent sync into `historical_topic_country_daily`.
- `backend/scripts/historical_backfill.py` — idempotent cutover backfill orchestrator. Discovers verified manifest records, writes missing daily artifacts, and can sync existing artifacts with `--sync-existing --execute-sync`.
- `backend/scripts/historical_coverage_report.py` — Supabase budget/coverage report for compact processed history.
- `backend/tests/test_historical_processing.py` — migration shape, topic inference, aggregate, and sync payload tests.
- `docs/research/processed-historical-sync/2026-05-19-topic-country.json` — first processed historical artifact.
- `backend/migrations/032_historical_source_daily.sql` — compact daily source-domain aggregate for long-window briefing `top_sources`.
- `backend/scripts/local_hot_cold_catchup.py` — end-to-end local catch-up runner. It plans rows older than 24h, exports to local archive, verifies the manifest, recomputes compact historical days from all archive roots, syncs processed aggregates, then prunes only after dry-run parity.
- `scripts/run-local-hot-cold-catchup.sh` — launchd-safe wrapper. It fetches `DATABASE_URL` from Fly if absent and writes processed artifacts under `/Users/pedro/AtlasArchive/processed-historical-sync`.
- `scripts/install-local-hot-cold-launchd.sh` — installs a minimal runtime under `/Users/pedro/AtlasLocalWorker` and loads `com.atlas.local-hot-cold-catchup`.
- `infra/launchd/com.atlas.local-hot-cold-catchup.plist` — LaunchAgent schedule for `00:10` through `05:10` local time plus `RunAtLoad`.

Key docs/files changed in session 22 (atlas-topic taxonomy quality — 2026-05-23/24):
- `docs/specs/2026-05-23-ai-assisted-taxonomy.md` — AI-assisted taxonomy plan. Path A pilot is implemented; Paths B/C remain specs. Product decisions: one Atlas sentiment in the UI, GDELT Tone as fallback/calibration/provenance, Path B precision gate 85% minimum / 90% target, no user-facing topic-correction UI for now.
- `backend/migrations/036_election_legitimacy_multilingual_lex.sql` — Path A pilot for `election-legitimacy-dispute`; lexicon terms expanded from 5 English terms to 43 multilingual terms after SQL volume checks and sample precision checks. Reject noisy stems like `scrutin`.
- `backend/migrations/037_armed_conflict_multilingual_lex.sql` — precision-first Path A pass for `armed-conflict-escalation`; removed noisy broad terms (`clashes`, `offensive`, `shelling`) and added precise multilingual conflict terms. Did not clear the 30% lex_pct gate, but high_conf improved `22 -> 85`.
- `backend/migrations/038_remaining_low_lex_multilingual_terms.sql` — completed Path A rollout for `fuel-subsidy-unrest`, `food-price-stress`, `housing-cost-pressure`, and `mining-royalty-risk`. Fuel and mining cleared the 30% gate; food/housing were precision cleanups.
- `docs/roadmap/2026-05-21-data-operating-roadmap.md` — current execution order now routes next work to Path A rollout before Path B encoder work.

Key docs added in session 23 (Living Narrative Threads canon — 2026-05-24):
- `docs/specs/2026-05-24-living-narrative-threads.md` — product/data canon: user-facing Atlas should expose living Narrative Threads; `atlas_topics` is internal anchor vocabulary, not the visible taxonomy.
- `docs/research/2026-05-24-app-panel-thread-audit.md` — panel-by-panel audit mapping Brief, Globe/Heat, NarrativeThreads, SignalStream, CountryBrief, ThemeDetail, PublicAttention, Workspace, and Search to the seven Atlas thread questions.
- `docs/roadmap/2026-05-24-open-issues-thread-triage.md` — open issue triage into `canon`, `evolve`, `close-after-merge`, `parking`, `blocked`, and `stale-review`.
- `docs/superpowers/plans/2026-05-24-living-narrative-threads.md` — implementation plan for the first read-only `/api/v2/threads` beta and compatible Brief/NarrativeThreads migration.
- GitHub #207 — umbrella issue for the Living Narrative Threads data contract.

Key docs/code changed in session 24 (production-cycle canon — 2026-05-25):
- `docs/roadmap/2026-05-25-production-cycle-and-backlog.md` — active operating canon: backlog/data first, contract smokes second, visual feedback batched from recorded walkthroughs. Frontend work should interrupt only when Atlas is visibly contradicting the data or showing a broken contract.
- `frontend-v2/src/components/NarrativeThreads.tsx` now consumes `/api/v2/threads` for the visible Narrative Threads panel.
- `frontend-v2/src/components/ThreadFocusPanel.tsx` opens selected living threads via `/api/v2/threads/{thread_id}` so row counts, focus counts, countries, sources, movement, and evidence agree.
- `backend/app/services/thread_intelligence.py` parses asyncpg JSONB strings for `hourly_timeline` and `related_threads`; do not regress these fields back to JSON strings.
- Next active work should return to data quality/backlog: Path C taxonomy split/rename for `mining-royalty-risk` vs coal mine disaster, Path B benchmark harness, Entity Focus hygiene, source lanes, and deployed long-window smoke for #193.

Key docs/files changed in session 25 (Path C + projection note — 2026-05-25):
- `docs/adrs/ADR-0005-equal-area-projection-mode.md` — Equal Earth / equal-area projection is product-architecture parking (#212), important to Atlas worldview but not allowed to interrupt the current data-quality sprint.
- `docs/research/2026-05-25-path-c-mining-resource-taxonomy-audit.md` — live Path C audit: `mining-royalty-risk` is a coherent high-confidence mining safety/resource-disaster cluster, not primarily royalty/concession evidence.
- `backend/migrations/039_mining_resource_safety_label.sql` — conservative Path C first migration: keep slug `mining-royalty-risk` stable for API/history compatibility, update label/description toward mining/resource safety crisis.
- `backend/scripts/topic_quality_audit.py` — repeatable read-only all-topic quality audit. Outputs JSON artifacts with volume, lex_pct, theme-only share, confidence, source/country breadth, top terms, evidence samples, and coarse risk flags.
- `docs/research/topic-quality/2026-05-25-atlas-topic-quality-audit.md` — all 30 active atlas topics audited over live 24h assignments. Product principle: prefer smaller precise topics over broad noisy topics because errors compound through threads/focus/entities/sentiment.
- `backend/migrations/040_topic_quality_precision_pass.sql` — pruned broad/noisy hints and terms for gender violence, labor strikes, transport corridors, disease outbreak, food prices, displacement, humanitarian access, disinformation, and migration/border pressure.
- `backend/migrations/041_topic_quality_lex_first_followup.sql` — made labor, transport, forced displacement, and water stress lex-first after post-040 validation showed theme-only leakage remained.
- `backend/scripts/topic_benchmark_harness.py` — Path B read-only benchmark harness. `sample` generates label-ready JSONL from production assignments; `score` reports overall/per-topic precision with gates.
- `backend/tests/test_topic_benchmark_harness.py` — harness unit tests for label schema, JSONL scoring, and precision gates.
- `docs/research/topic-quality/2026-05-25-path-b-benchmark-harness.md` — Path B harness documentation and first sample plan.
- `docs/research/topic-quality/benchmark-samples/2026-05-25-path-b-priority-topics.jsonl` — first 103-row priority sample across seven risky/recently changed topics.
- `docs/research/topic-quality/benchmark-samples/2026-05-25-path-b-priority-topics-labeled.jsonl` — first labeled Path B sample.
- `docs/research/topic-quality/benchmark-scores/2026-05-25-path-b-priority-topics-score.json` — first score: overall precision `80.85%`, below the 85% floor.
- `docs/research/topic-quality/2026-05-25-path-b-priority-label-results.md` — analysis of typed failures: substring noise, scope mismatch, parent-thread candidate, primary-context mismatch, insufficient context, off-topic.
- `docs/research/topic-quality/2026-05-25-narrative-classification-root-cause-audit.md` — model-level diagnosis: current assignment layer collapses domains, parent threads, child threads, entity threads, evidence rows, and contextual mentions.
- `docs/research/topic-quality/2026-05-25-atlas-quality-models-market-and-product.md` — market/repo review of quality metrics; recommends answerability-first Atlas quality around the seven product questions.
- `docs/research/topic-quality/2026-05-25-narrative-intelligence-field-review.md` — external field review of event-centric narrative graphs, narrative maps, dynamic topic modeling, topic tracking, media framing, attention platforms, StoryAtlas-style visualization, and interactive narrative analytics.
- `docs/specs/2026-05-25-atlas-narrative-intelligence-framework.md` — active model canon: Atlas is both narrative intelligence model and visualizer; next work is semantic/evidence-role labels plus a read-only Narrative Thread Graph report before persistent tables or encoder promotion.
- `docs/research/atlas-paper/2026-05-25-atlas-narrative-intelligence-state-of-art-and-validation-plan.md` — research-paper track: state of the art, thesis, research questions, hypotheses, baselines, ablations, data/label plan, metrics, and evidence required before writing a publishable paper.
- `docs/research/atlas-paper/2026-05-25-atlas-v2-labeling-guide.md` — Phase 1 label guide for `atlas-topic-benchmark-v2`.
- `docs/research/atlas-paper/phase-1-validation/README.md` — Phase 1 workspace route: raw batches, pilot labels, future gold labels, reports, and progress snapshots.
- `docs/research/atlas-paper/phase-1-validation/review-packets/2026-05-25-atlas-v2-stratified-batch-01.review.md` — human adjudication packet joining raw batch 01 evidence with assistant-pilot suggestions and reviewer fields.
- `docs/research/atlas-paper/phase-1-validation/review-templates/2026-05-25-atlas-v2-stratified-batch-01.review-template.jsonl` — machine-editable review template with `assistant_*` suggestions and blank `reviewer_*` fields.
- `docs/research/atlas-paper/phase-1-validation/progress-review-batch-01.json` — review progress snapshot; current batch 01 state is `32/32` ready after Markdown adjudication.
- `docs/research/atlas-paper/phase-1-validation/reports/batch-01-md-review-normalization.json` — normalization report after applying Pedro's Markdown review answers; current warning count is 7.
- `docs/research/atlas-paper/phase-1-validation/reports/reviewed-batch-01-score.json` — first reviewed score: `53.33%` precision, below the 85% minimum gate.
- `docs/research/atlas-paper/phase-1-validation/labels/assistant-pilot/2026-05-25-atlas-v2-stratified-batch-02.assistant-pilot.jsonl` — assistant hints for batch 02, used for model/user comparison.
- `docs/research/atlas-paper/phase-1-validation/review-templates/2026-05-25-atlas-v2-stratified-batch-02.review-template.jsonl` — batch 02 adjudication template, currently `0/32` ready.
- `backend/scripts/atlas_label_workflow.py` — Phase 1 file workflow helper. Modes: `split`, `progress`, `merge`, `review-packet`, `review-template`, `review-progress`, `finalize-review`, and `apply-review-packet`.
- `backend/scripts/atlas_review_server.py` — local one-row-at-a-time adjudication UI for review templates. Use for batch 02 and later batches.
- `backend/scripts/atlas_validation_report.py` — renders benchmark score JSON into Markdown plus SVG report charts for the paper/validation track.
- `docs/research/topic-quality/benchmark-samples/2026-05-25-atlas-v2-stratified-sample.jsonl` — first v2 stratified sample, 256 rows across 30 active topics and four buckets.
- `docs/research/topic-quality/benchmark-samples/2026-05-25-atlas-v2-stratified-sample.md` — manifest for the first v2 stratified sample.

Session 22 topic taxonomy state:
- Path A pilot result: `election-legitimacy-dispute` lex_pct `6.3% -> 31.6%`, high_conf `5 -> 27`, multilingual terms drove `74%` of lex-match volume; global coverage moved `13.08% -> 13.35%`.
- Armed-conflict partial result: lex_pct `2.10% -> 6.56%`, high_conf `22 -> 85`, global v2 coverage after re-backfill `17.22%`. Treat as partial because the 30% gate did not clear; do not re-add broad armed-incident terms just to raise recall.
- Final Path A rollout result after migration 038: `fuel-subsidy-unrest` lex_pct `5.20% -> 37.12%`, high_conf `2 -> 136`; `food-price-stress` lex_pct `17.52% -> 4.63%`, high_conf `7 -> 10` after removing noisy `shortage`/`hunger`; `housing-cost-pressure` lex_pct `10.16% -> 8.20%`, high_conf `0 -> 2` after removing noisy `mortgage`/`eviction`; `mining-royalty-risk` lex_pct `12.33% -> 78.99%`, high_conf `0 -> 100` driven by a coal-mine-disaster cluster.
- Global v2 topic coverage after full Path A rollout: `18.47%` of 24h eligible signals.
- Open issues: #203 Path B and #204 Path C. #202 is closed after migrations 036-038.
- Next taxonomy step: use Path B labels and broader Path C samples to decide whether royalty/concession deserves a separate anchor from mining/resource safety crisis. Migration 039 already corrected the visible mining/resource safety label while keeping slug compatibility.
- Path B current step: use the first labeled score to separate mechanical precision repairs from parent/child Narrative Thread hierarchy work; do not promote encoder or ranking changes until measured precision clears the 85% floor, with 90% as product target.
- Path B harness schema is now `atlas-topic-benchmark-v2`. New samples include `gold_scope`, `gold_evidence_role`, `gold_parent_thread`, `gold_child_thread`, and `gold_supported_questions`; old v1 JSONL remains score-compatible.
- Path B nuance: do not delete broad concepts just because they fail a specific child assignment. `Panama Canal` can be a valid parent/entity thread, but it is only `transport-corridor-disruption` evidence when the headline shows closure, drought, blockade, delay, shipping disruption, or operational impact.
- Root-cause guardrail: do not keep solving benchmark failures topic-by-topic before modeling semantic role. Future labels should distinguish `domain`, `parent_thread`, `child_thread`, `entity_thread`, `evidence`, `context_signal`, and `noise`.
- Quality-model guardrail: metrics should trace to the seven Atlas questions. Assignment precision alone is insufficient; Atlas quality should combine answerability, evidence, scope, source, movement, and coverage.
- Narrative-intelligence framework guardrail: Atlas is not a fixed topic dashboard or pure topic model. Treat `atlas_topics` as internal anchors; expose living parent/child/entity Narrative Threads with typed relations, movement drivers, evidence roles, and quality envelopes.
- Paper-track guardrail: do not write a final paper before evidence exists. The next work is v2 label guide, stratified benchmark, baseline comparisons, ablations, read-only thread graph report, and reviewer usefulness/error-discovery validation.
- Phase 1 guardrail: the first v2 sample is unlabeled. Do not draw model-quality conclusions from it until labels are filled and scored.
- Assistant-pilot label guardrail: labels under `phase-1-validation/labels/assistant-pilot/` are for workflow testing only. Use review packets to adjudicate them; do not cite them as gold/paper-grade evidence before human review/adjudication.
- Review-template guardrail: do not run `finalize-review` without human-filled `reviewer_*` fields or explicit `accept_assistant_label=true`; use `--require-complete` before paper-grade scoring.
- Markdown-review guardrail: `apply-review-packet` may normalize human text such as multi-value fields; review the normalization report before treating the output as `gold`.
- Local-review UI guardrail: assistant hints are for comparison, not truth. The UI writes to `reviewer_*`; do not score assistant hints as reviewer decisions unless the row has `accept_assistant_label=true`.
- Visual-report guardrail: keep research charts in `docs/research/atlas-paper/phase-1-validation/reports/`; do not promote them to the production UI until reviewed/gold labels show stable model value.
- Quality guardrail: do not treat assignment volume as product quality. After migrations 040-041, several topics intentionally became thin (`food-price-stress`, `transport-corridor-disruption`, `forced-displacement`) rather than noisy. Keep them available as evidence-backed anchors, but do not promote them visually until volume/sample precision improves.
- Theme/topic guardrail: do not trust GDELT theme classification alone as proof of a significant Atlas topic. Topic changes must be validated against real headlines, lex_pct/high_conf movement, and precision spot checks.

Session 23 Living Narrative Threads direction:
- Atlas topics are internal anchors for measurement, backfills, precision gates, and benchmarks. Do not design the user-facing product around a fixed table of 10/30/130 topics.
- The visible product model is living Narrative Threads: natural-language clusters that can emerge, split, merge, fade, and connect to related threads as evidence changes.
- Every thread-capable surface should answer at least one of the seven Atlas questions: why this is moving now, what changed in the last 10h, where it is concentrated, which subthreads are forming, which sources are driving it, what evidence supports it, and what related thread it connects to.
- First technical increment should be read-only and additive: build `/api/v2/threads` above existing `signal_topic_assignments`, `atlas_topics`, `signals_v2`, aggregate tables, source mix, and related-topic co-occurrence. Keep current theme-based UI fallbacks until smoke-tested.
- Backend beta exists as `living-narrative-threads-v0`: `/api/v2/threads` and `/api/v2/threads/{thread_id}` in `backend/app/routers/threads.py`, assembled by `backend/app/services/thread_intelligence.py`. Review live output quality before wiring frontend panels.
- Do not add user-facing topic correction UI yet. Controlled SQL review, benchmark labels, and precision gates remain the validation path.

Session 24 production-cycle direction:
- Do not turn every visual issue into immediate frontend work. The UI is a detector of data/contract problems, but the current priority is closing backlog and improving data quality.
- Immediate frontend fixes are appropriate only when the app is lying or contradicting itself, such as a thread row showing hundreds of signals while the focus panel shows zero.
- Pure visual polish should be batched after Pedro records review videos. Convert the video into a short issue batch and implement it as a focused UX PR.
- Before starting a major work block, re-check open GitHub issues and classify them as `active-now`, `close/update`, `parking`, `blocked`, or `superseded`.

Session 20 data state:
- Local archive root: `/Users/pedro/AtlasArchive`.
- Clean cutover archive: `/Users/pedro/AtlasArchive/cutovers/2026-05-20`.
- Verified export window: `2026-05-03T00:00:00Z` through `2026-05-20T03:33:29Z`.
- Verified archive: 18 manifest records, 2,128,070 rows, ~368M local compressed size, 0 checksum failures, 0 overlaps.
- Smoke queries passed: date `2026-05-19` = 185,163 rows; country `CO` = 13,654; source_family `social` = 485; topic/headline `energy` = 92,005.
- Live prune completed after explicit approval: 2,128,070 rows deleted from `signals_v2` in 139.13s; archived range remaining 0; exact `signals_v2` count 259,360; `ANALYZE signals_v2` completed; `nlp_progress` recomputed to `unprocessed_total=241,002`.
- Guardrail: do NOT manually delete historical rows. Use `archive_verify.py` first, then `prune_archived_signals.py` dry-run. Keep product aggregate tables, correction tables, topic tables, and NLP audit/progress tables in Supabase. `/health.total_signals` reflects historical aggregate volume, not raw hot-store row count.

Session 21 processed historical sync direction:
- Raw historical archive remains local at `/Users/pedro/AtlasArchive`; do not rehydrate full raw history into Supabase.
- Supabase should store compact processed historical outputs: daily topic/country/source aggregates, coverage metadata, run metadata, and small evidence samples.
- Fly handles hot 24h ingestion/enrichment SLA. Pedro's local machine handles historical/backlog processing and syncs compact outputs back to Supabase.
- Tracking issues: #191 (local archive -> processed historical sync), #192 (processed-only historical tables), #193 (route `1w`/`1m` app windows to processed historical tables). Related issues commented: #164, #167, #171, #184, #185.
- First implementation should start with migration `029_historical_processed_tables.sql`, then `backend/scripts/historical_process_partition.py`, then `backend/scripts/historical_sync.py`.
- Current implementation status: migration 029 applied; first `historical_sync.py` live run inserted/upserted `1,728` rows for `2026-05-19` / `atlas-hist-v1`, summing to `185,163` signals. Next step is API bridge for long-window reads.
- Full cutover backfill status: `historical_backfill.py` processed/synced `2026-05-03` through partial `2026-05-20`: `18` historical days, `22,711` compact rows, and `2,128,070` represented signals, exactly matching the verified local archive.
- Long-window API bridge status: `/api/v2/briefing?hours>24` routes `top_themes` to `historical_topic_country_daily` and `/brief` renders historical processed coverage metadata. Current coverage report after full backfill: `22,711` aggregate rows, `2,128,070` represented signals, `236` countries, `11` topics, avg topic coverage `0.8052`, avg NLP sentiment coverage `0.1695`.
- App-wide routing status: `/api/v2/heat/countries`, `/api/v2/country/{code}`, `/api/v2/theme/{topic_slug}`, and `/api/v2/anomalies/themes` route long windows through processed history with coverage metadata; `/api/v2/heatmap` is explicitly deprecated in favor of `/api/v2/heat/countries`; frontend `CoverageBadge` is wired into Heat and Theme Detail.
- Long-window briefing source status (#194): `/api/v2/briefing?hours>24` routes `top_sources` to `historical_source_daily`. Full source backfill synced `161,871` daily source aggregate rows representing `2,128,070` archived signals. Live query plan after `VACUUM`: ~40 ms, index-only scan, `Heap Fetches: 0`.
- Local hot/cold automation status: installed LaunchAgent `com.atlas.local-hot-cold-catchup` runs from `/Users/pedro/AtlasLocalWorker`, not the Desktop repo, because macOS blocks launchd access to Desktop-protected paths. Last verified install exited `0`; after incremental catch-up, `signals_v2` had `173,925` hot rows and compact historical tables represented `2,412,591` signals through `2026-05-21`.
- Scope correction: do not close #193 based only on backend/API work. #193 remains open until app-wide visual smoke tests pass through the deployed frontend.
- Quality finding: `general-monitoring` represents `1,559,990` of `2,128,070` historical signals, so storage is no longer the blocker; topic intelligence quality (#171/#167/#185) is.

Key files changed in session 15:
- `backend/app/services/ingest_loop.py` — wired 4 new ingestion services. `ingest_newsdata` + `ingest_reddit` at `cycle%4`. `ingest_mediastack` at `cycle%8`. `ingest_newsapi` at `cycle%8+4` (offset to spread load).

Fly.io infra changes session 15 (Codex track):
- `nlp_worker` machine: `shared-cpu-2x:4096MB` (raised from undersized config to fix OOM)
- Standby worker stopped (single-worker mode)
- `NLP_SAMPLE_REFRESH_EVERY=0` env — heavy refresh explicitly OFF
- `NLP_SAMPLE_CLEANUP_LIMIT=50` env — bounded queue cleanup
- Fly secrets set: `NEWSDATA_API_KEY`, `MEDIASTACK_API_KEY`, `NEWSAPI_KEY`
- Deployment ID: `01KS0EG5FJAY5507G729FNVACQ`

Fly.io image split (session 21, #195):
- `Dockerfile` has two deploy targets: `api-runtime` (FastAPI/ingestion, no Torch/Transformers/model cache) and `nlp-runtime` (heavy NLP worker with Torch/Transformers/spaCy/HF cache).
- Use `scripts/deploy-fly-api.sh` for API-only changes. It runs `fly deploy --build-target api-runtime --process-groups app` and should update only the `app` machine.
- Use `scripts/deploy-fly-nlp-worker.sh` for NLP/model changes. It runs `fly deploy --build-target nlp-runtime --process-groups nlp_worker`.
- Production verification: API-only deploy created a `257 MB` image and updated `1/3` machines; `nlp_worker` stayed on the heavy image and continued `Sentiment[xlm-v1]`, `NER[xlm-v1]`, `Framing[xlm-v1]`.
- Do not use bare `fly deploy --config fly.toml` for routine API work; it can rebuild/push the heavy model image.

Multilingual NLP confirmed: logs show `Sentiment[xlm-v1]`, `NER[xlm-v1]`, `Framing[xlm-v1]`. Cycle duration 231.5s, error=no. Throughput stable at 25 rows/cycle — do NOT raise to 100/200 until DB pressure observed over hours.

Known operational debt for next session:
- HuggingFace tokenizer warning on `twitter-xlm-roberta-base-sentiment` — validate before trusting multilingual quality
- `country_heat_v2` refresh hit timeout once — operational item
- NewsAPI design weak (8 hardcoded EN queries on zones GDELT covers in EN) — refactor to 6 evergreen + 2 dynamic from GDELT spikes + 36 req/day analyst reserve
- Reddit needs `signal_class="commentary"` field (migration 021) before counting in #149 source-diversity scoring

Key files added in session 14 (P1 pass — 2026-05-18):
- `frontend-v2/src/components/ReadingMode.tsx` — newspaper-style right panel showing signal cards per pinned item. Opens via BookOpen icon in Workspace. Escape/scrim dismiss; Export .md button.
- `frontend-v2/src/components/ReadingMode.css` — styles for ReadingMode overlay, signal card grid, sentiment indicator, source badges.

Key files changed in session 14:
- `frontend-v2/src/lib/exportFormatters.ts` — added `DossierSignal`, `DossierSection` types; `fetchItemSignals(item)` calls `/api/v2/signals`; `buildDossierMarkdown(sections)` formats with headline/source/URL/sentiment.
- `frontend-v2/src/contexts/WorkspaceContext.tsx` — added `exportDossier()` (fetches signals, downloads markdown); exposed in context value.
- `frontend-v2/src/components/InteractiveWorkspace.tsx` — BookOpen (Reading Mode) + Download (Dossier) buttons replace old single export button; `readingMode` state; `ReadingMode` rendered at component end.
- `frontend-v2/src/hooks/useSavedWatches.ts` — added `lastSeenAt`/`lastSeenCount` to `SavedWatch`; `markSeen(id, count)`; `fetchWatchCount(filter)` and `buildWatchParams(filter)` exported utilities.
- `frontend-v2/src/pages/BriefNewspaper.tsx` — `watchCounts` state; parallel fetch of signal counts per watch; card shows count pill + delta badge (↑/↓); `markSeen` called on "Open in Atlas →".
- `frontend-v2/src/pages/BriefNewspaper.css` — `.brief-watch-stats`, `.brief-watch-count`, `.brief-watch-delta.up/.down/.neutral` classes.
- `frontend-v2/src/layers/TerminatorLayer.ts` — `calculateTerminatorPolygon` accepts `lngOffsetDeg`; `createTerminatorLayer` returns `PolygonLayer[]` (5 bands, opacity gradient).
- `frontend-v2/src/components/SettingsPanel.tsx` — Day/Night label → "Day/Night Shadow (experimental)" with description.
- `frontend-v2/src/App.tsx` — `...terminatorLayers` spread (was single nullable layer); country param in search URL.
- `frontend-v2/src/components/Legend.tsx` — full rewrite; context banner; per-layer keys; collapsible.
- `frontend-v2/src/components/SearchBar.tsx` — `countryParam` in backend search URL; `onThemeSelect` passes countryCode for compound queries.
- `frontend-v2/src/pages/Landing.tsx` — live signal count via `/health`; navigable BentoCards; `formatSignalCount()`.
- `backend/app/services/ingest_acled.py` — docstring clarifies optional status.

Key files added in session 15 (multi-source ingestion — 2026-05-18):
- `backend/app/services/ingest_newsdata.py` — NewsData.io multilingual ingestion every 4th GDELT cycle; currently language/country batches with `geo_confidence=0.7`.
- `backend/app/services/ingest_mediastack.py` — MediaStack ES/PT LatAm supplement every 8th GDELT cycle; conservative quota use.
- `backend/app/services/ingest_newsapi.py` — NewsAPI targeted crisis queries every 8th GDELT cycle offset; current 8 queries x 12/day = 96 req/day.
- `backend/app/services/ingest_reddit.py` — Reddit public API social/commentary ingestion every 4th GDELT cycle; writes `source_family="social"` and `attribution_method="reddit_public"`.
- `backend/.env.example` — documents `NEWSDATA_API_KEY`, `MEDIASTACK_API_KEY`, `NEWSAPI_KEY`.

Session 15 validation note:
- The new sources are live, but the blocker is enrichment quality/capacity. `nlp_pipeline.py` is English-first (`cardiffnlp/twitter-roberta-base-sentiment-latest`, `spacy en_core_web_sm`, English NLI framing) and `ingest_loop.py` currently runs NLP with `limit=100` per 15-min cycle. Do not build source-weighted scoring or Voice Mix assumptions until NLP backlog and multilingual behavior are measured.
- Next migration is 013 and should add `signal_class` before #149 scoring. Recommended classes: `reporting`, `wire`, `state_media`, `humanitarian`, `social_commentary`, `public_attention`, `unknown`. Clustering should come later, after provider attribution and NLP quality are measured.
- Implementation plan: `docs/superpowers/plans/2026-05-18-multisource-intelligence-hardening.md`.

Key files added in session 13 (P0 productization pass — PR #144):
- `frontend-v2/src/lib/briefingPrefetch.ts` — sessionStorage-backed briefing prefetch cache (4-min TTL).
- `backend/app/routers/narratives.py` — narrative detail window capped at 48h; returns `effective_hours`.

Key files changed in session 13:
- `frontend-v2/src/components/AnomalyPanel.tsx` — Trends + Wiki merged into PUBLIC ATTENTION; staleness badge; deduplication.
- `frontend-v2/src/components/NarrativeThreads.tsx` — capped-window notice when `effectiveHours` < requested hours.
- `frontend-v2/src/components/InteractiveWorkspace.tsx` — Trail and Pinned split into two independent ForceGraph2D instances.
- `frontend-v2/src/components/InvestigationWorkspace.css` — `.workspace-graph-slot` and `.workspace-graph-slot.hidden` rules.
- `frontend-v2/src/pages/BriefNewspaper.tsx` — Editor's Analysis fallbacks; `resolveCountryName` everywhere.
- `frontend-v2/src/App.tsx` — `prevStreamCtx` union extended with `country` type; back-nav wiring.
- `frontend-v2/src/lib/publicAttention.ts` — `Math.max(hours, 72)` floor for Trends window.
- `backend/app/services/ingest_trends.py` — shuffle + retry pass + batch 5→3.

Key files added in session 6:
- `frontend-v2/src/components/InteractiveWorkspace.tsx` — force-graph canvas (react-force-graph-2d). MUST be lazy-loaded only.
- `frontend-v2/src/components/InvestigationWorkspace.tsx` — lazy shell + PanelErrorBoundary wrapper.
- `frontend-v2/src/lib/workspaceGraph.ts` — two-pass graph builder (pinned nodes + edges with per-item try/catch).
- `frontend-v2/src/contexts/WorkspaceContext.tsx` — workspace state (pinned items, graph useMemo, detail fetching).

Key files added in session 7:
- `frontend-v2/src/components/PublicAttentionPanel.tsx` — Google Trends + Wikipedia public-attention feed. Item clicks open investigation panel (no external navigation).
- `frontend-v2/src/components/TemporalNarrativeGraph.tsx` — timeline of narrative coverage + sentiment shift over time. In ThemeDetail. Workspace integration pending (#82).
- `frontend-v2/src/components/OnboardingCoachmark.tsx` — first-run onboarding overlay.
- `backend/app/services/ingest_rss.py` — RSS curated feed ingestion (Wave 1 + Wave 3).
- `backend/app/services/ingest_reliefweb.py` — ReliefWeb/OCHA humanitarian feeds (Wave 2, 19 crisis countries, geo_confidence=0.92).
- `backend/migrations/008_source_provenance.sql` — source_family, source_lang, geo_confidence, attribution_method, is_state_media fields.
- `backend/migrations/009_trends_v2_constraint.sql` — trends_v2 hour_bucket UNIQUE constraint.
- `backend/migrations/010_theme_country_hourly.sql` — theme_country_hourly_v2 pre-agg table.

Key files changed in session 8:
- `backend/app/services/ingest_loop.py` — NLP as non-blocking background task (`asyncio.create_task`), weekly 90-day retention cleanup for unprocessed signals.
- `backend/Dockerfile` — HF_HOME and TRANSFORMERS_CACHE env vars placed before pre-bake RUN; offline env vars placed after. Fixes OOM on Fly.io.
- `backend/enrichment/nlp_pipeline.py` — three-phase NLP pipeline (sentiment, NER, framing). Called by ingest_loop background task.
- `backend/migrations/011_nlp_columns.sql` — NLP columns on signals_v2 (APPLIED).
- `frontend-v2/src/App.tsx` — data coverage badge: fetches oldest_signal from /api/v2/stats, shows FROM [DATE] pill.
- `frontend-v2/src/App.css` — `.data-since-pill` CSS class.

## Build, Test, and Development Commands
Local backend: `cd backend && poetry run uvicorn app.main_v2:app --reload --port 8000`. Local frontend: `cd frontend-v2 && npm run dev`. Fly.io deploy: `fly deploy` from repo root. Lint via `poetry run ruff check`, `poetry run mypy app`, `npm run lint`. Run `npm run build` before every PR — TypeScript/Vite errors must be zero. DO NOT rely on `tsc --noEmit` alone: Vite's build uses `tsc -b` (project references mode), which is stricter and catches errors like TS6133 (unused imports) that `tsc --noEmit` silently ignores. A green `tsc --noEmit` does not guarantee a passing Vercel build. Pytest: `cd backend && poetry run pytest`. Migrations are raw `.sql` files run from the Supabase SQL editor dashboard (NOT via alembic, NOT via the connection pooler).

## Coding Style & Naming Conventions
Python targets 3.11, 4-space indentation, 100-char lines (Black/Ruff). Favor pydantic models in `app/models`, keep modules snake_case, and expose FastAPI routes under `/api/v2/...` (NOT `/v1/` — all active endpoints are v2). TypeScript uses 2-space indentation, PascalCase components, camelCase hooks/store setters, and colocated styles only when needed. Run Ruff, Mypy, ESLint, and `tsc` before committing; never commit generated OpenAPI artifacts or `node_modules`. Tooltip system: use `data-tip="text"` on any element — never use native `title=` attributes.

Additional frontend conventions (session 6):
- Theme names: always call `getThemeLabel(theme_code)` from `lib/themeLabels.tsx`. Do NOT use the `label` field from API responses — it may contain raw GDELT code strings.
- Graph library: use `react-force-graph-2d` only. The 3D variant (`react-force-graph`) imports AFRAME and crashes the app.
- Lazy-load heavy components: any component importing large visualization libraries must be wrapped in `React.lazy()` + `Suspense` to keep the main bundle lean.
- Error boundaries: wrap any panel that loads async data in `PanelErrorBoundary`. The `RootErrorBoundary` in `main.tsx` is the final fallback only.

Additional frontend conventions (session 7):
- Sentiment display: all API endpoints return sentiment in ÷10 normalized range. Frontend thresholds: ±0.1 neutral, beyond = positive/negative. Do NOT divide again on the frontend.
- Coverage confidence badges: when signal count n<10 render an orange "thin" badge; 10≤n<50 render a yellow "limited" badge; n≥50 no badge. Apply in any component displaying per-country/per-source metrics (CountryBrief, NarrativeThreads, ChokepointPanel pattern).
- PublicAttentionPanel item clicks: must open InvestigationWorkspace (internal), never navigate to external URL.
- Component count: 45 .tsx components in `frontend-v2/src/components/` as of 2026-05-17.

Additional frontend conventions (session 13):
- Country names: always call `resolveCountryName(code, name)` — never use the raw `name` field from API country objects. The raw field may be FIPS or incomplete.
- Theme signal anchors: do NOT use `themeSignals[theme][0]` as a headline anchor. Signals are frequently misclassified and the first result is unreliable.
- Trends API response field: use `d?.trending ?? []` not `d?.trends`. The field name on the response object is `trending`.
- Two ForceGraph2D instances pattern: when Trail and Pinned graph modes need to coexist, mount both ForceGraph2D instances and toggle visibility via CSS `visibility: hidden`. This preserves the d3 simulation (layout) — unmounting destroys it.
- Briefing prefetch: use `briefingPrefetch.ts` cache before making API calls in BriefNewspaper. Landing prefetches on mount via the same module.

Backend conventions (session 7):
- All new ingestion services must set `source_family`, `source_lang`, `geo_confidence`, `attribution_method`, and `is_state_media` on every inserted row.
- Concept endpoint hours>24 must query `theme_country_hourly_v2`, not `signals_v2`. Do not re-add the `effective_hours` cap.

Backend conventions (session 8):
- Migrations 007–012 are all applied. Next migration will be 013.
- NLP pipeline runs as a background task in `ingest_loop.py` — do not make it blocking.
- Dockerfile: `ENV HF_HOME=/app/hf_cache` and `ENV TRANSFORMERS_CACHE=/app/hf_cache` MUST appear before the pre-bake RUN step. `ENV TRANSFORMERS_OFFLINE=1` and `ENV HF_DATASETS_OFFLINE=1` MUST appear after. Do not reorder — this is the OOM fix.
- Data retention: unprocessed signals (nlp_processed_at IS NULL) are deleted after 90 days. NLP-processed signals are kept indefinitely.
- Branch: `v3-intel-layer` is production. `main` is abandoned — do not merge into it.

Backend conventions (session 13):
- Narrative detail window cap: `detail_hours = min(hours, 48)` in `narratives.py` for Phase 2 (signals_v2 unnest scan). Phase 1 (theme_hourly_v2) uses the full requested hours. Always return `effective_hours` in the result dict so the frontend can display the actual window.
- Google Trends ingestion: shuffle country list per run, batch size max 3 countries, delay 2s between batches, run a retry pass for failed countries at end of cycle. These are anti-rate-limit measures — do not revert to batch=5 or delay=1s.
- Trends staleness threshold: frontend shows stale badge when data is >25h old. The `publicAttention.ts` helper enforces a 72h floor on the `hours` param to avoid fetching empty windows.

Backend conventions (session 15):
- New API/social sources must continue setting `source_family`, `source_lang`, `geo_confidence`, `attribution_method`, and `is_state_media`.
- Treat `source_family="social"` / `attribution_method="reddit_public"` as commentary. It can support early-signal detection but must not count as independent news corroboration.
- NewsAPI quota math matters: the current 8-query/every-2h schedule spends about 96/100 req/day. Any analyst-query reserve requires a changed cadence or explicit daily quota budget.
- NewsData should move toward country-primary buckets before using it for high-confidence country scoring.

## Testing Guidelines
Backend tests live in `backend/tests/test_*.py` per `pyproject.toml`. New services need fixtures for flow/heat math and regression coverage for service clients; mock external providers through the client layer rather than hitting the network. Treat the coverage report from `make test-backend` as a gate and keep touched modules above the current baseline. Frontend work that touches the map or API should include Vitest/React Testing Library smoke tests or, at minimum, refreshed manual steps and screenshots in `docs/demos/`.

## Commit & Pull Request Guidelines
Commits follow Conventional Commits (`feat(flow): ...`, `docs: ...`, `revert: ...`) on focused branches such as `feat/frontend-map/...`. PRs should reuse the `PR_DESCRIPTION.md` structure: short summary, bullet list of file-level work, explicit test commands with results, and references to agent specs or ADRs. Attach screenshots or shell snippets for user-visible work, link relevant issues, and call out env or migration steps before requesting review.

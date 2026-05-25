# Atlas — Session Status
**Branch:** `v3-intel-layer` | **Updated:** 2026-05-25 (production-cycle canon + backlog restart)

---

## Current handoff (2026-05-25) — backlog-first production cycle

The repo is clean on `v3-intel-layer`. The latest production code before this
documentation pass is `d568772 fix(frontend): open living thread focus from
narratives`.

New operating canon:

- Roadmap: `docs/roadmap/2026-05-25-production-cycle-and-backlog.md`.
- The UI is now treated as a detector of contract/data-quality failures, not as
  an invitation to open ad hoc polish issues.
- Frontend work interrupts the data backlog only when the visible product is
  contradicting itself or misrepresenting data.
- Visual feedback should be batched from recorded walkthroughs: video -> issue
  batch -> focused UX PR.
- The next active work block is data/product backlog, starting with Path C
  taxonomy quality and live thread-evidence mismatches.

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
    Path C should revisit whether this topic should become broader
    mining/resource risk or split royalty/concession risk from mine disasters.
- Global v2 topic coverage after full Path A rollout: `18.47%` of 24h eligible
  signals.
- Path B encoder classifier stays in design/shadow mode until a benchmark shows
  at least `85%` precision; `90%` is the product target. Recall does not justify
  promotion below that floor.
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

1. Close or update stale issue state from the production-cycle canon.
2. Start Path C taxonomy quality with live thread-evidence mismatches:
   `mining-royalty-risk` vs coal mine disaster is the first candidate.
3. Build the Path B benchmark/precision harness before any encoder promotion.
4. Run deployed app-wide long-window smoke tests before closing `#193`.
5. Normalize product sentiment presentation around one Atlas sentiment under
   `#183`.
6. Evolve Entity Focus into thread participation, not raw mention display.

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

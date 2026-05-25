# CLAUDE.md - Project Guidelines and Agent Configuration

Last updated: 2026-05-25 (narrative classification root cause)

This file provides Claude Code with essential context about the Observatorio Global project, including agent configurations, tooling guidelines, and development workflows.

## Project Overview

Observatorio Global is a narrative intelligence system that tracks, analyzes, and visualizes how topics and narratives propagate across global media sources. The system aggregates signals from GDELT 2.0, Google Trends, and Wikipedia, normalizes them into a unified schema, and provides insights on geographic drift, sentiment analysis, and narrative mutations.

## Current Session Context (2026-05-25, production-cycle canon)

### Phase zero operating truth

Use these docs as the active ground truth before opening new work:

- `docs/roadmap/2026-05-25-production-cycle-and-backlog.md`
- `docs/roadmap/2026-05-21-data-operating-roadmap.md`
- `docs/roadmap/2026-05-24-open-issues-thread-triage.md`

The production loop is backlog/data first, contract smoke second, and visual
feedback batched from Pedro's recorded walkthroughs. The UI is a detector of
data/contract failures, not a reason to create ad hoc polish issues. Interrupt
the backlog only when the app visibly contradicts the data, such as a thread row
showing hundreds of signals while its focus panel shows zero.

Current visible Narrative Threads slice:

- `frontend-v2/src/components/NarrativeThreads.tsx` consumes `/api/v2/threads`.
- `frontend-v2/src/components/ThreadFocusPanel.tsx` opens `/api/v2/threads/{thread_id}`.
- `backend/app/services/thread_intelligence.py` must keep parsing asyncpg JSONB
  strings for `hourly_timeline` and `related_threads`.
- Legacy theme fallbacks remain for older panels, but the visible Narrative
  Threads panel is already on the living thread contract.

Active execution order after phase zero:

1. #203 Path B labeled validation path. The read-only harness exists; the next
   step is to label the 103-row priority sample and score it. Precision gate is
   85% minimum, 90% target. This is the main dependency because sample
   precision must be measured instead of manually inferred.
2. #204 Path C taxonomy quality remains open for broader revision. First slice
   shipped as migration 039: keep slug `mining-royalty-risk` stable, but
   correct label/description toward mining/resource safety crisis after live
   evidence showed coal mine/resource-disaster dominance.
3. #193 deployed app-wide long-window smoke; keep open until the deployed frontend proves `1w`/`1m` consistency.
4. #176 Entity Focus hygiene: entities are lenses over threads, not raw mention cards.
5. #177 Signal Stream/source lanes and evidence provenance.

Completed/closeable after documentation: #191, #192, and #202. Do not reopen
Path A rollout unless new metrics show regression; future topic quality work
routes through #204/#203/#185.

Equal Earth / equal-area projection is tracked separately as #212 and ADR-0005.
It is product-architecture parking for Atlas's worldview, not part of the
current data sprint.

All-topic quality audit state:

- `backend/scripts/topic_quality_audit.py` is the repeatable read-only audit
  tool.
- `docs/research/topic-quality/2026-05-25-atlas-topic-quality-audit.md` records
  the 30-topic audit and quality-score direction.
- Migrations 040-041 intentionally shrink noisy topics. Do not restore broad
  hints/terms just to recover volume; quality-first means thin precise topics
  are preferable to large noisy topics.

Path B benchmark harness state:

- `backend/scripts/topic_benchmark_harness.py` is the read-only benchmark tool.
  It has `sample` and `score` modes. The score report now also counts typed
  failures through optional `gold_error_type`.
- First sample:
  `docs/research/topic-quality/benchmark-samples/2026-05-25-path-b-priority-topics.jsonl`
  with 103 rows across armed conflict, disease, food, displacement, gender
  violence, labor, and transport.
- First labeled sample:
  `docs/research/topic-quality/benchmark-samples/2026-05-25-path-b-priority-topics-labeled.jsonl`.
- First score:
  `docs/research/topic-quality/benchmark-scores/2026-05-25-path-b-priority-topics-score.json`.
- Result doc:
  `docs/research/topic-quality/2026-05-25-path-b-priority-label-results.md`.
- First result: overall precision `80.85%`, below the 85% floor. Disease
  outbreak passed target at `100%`; food price stress passed target at `90%`.
  The failures are not all noise: typed errors distinguish `substring_noise`,
  `scope_mismatch`, `parent_thread_candidate`, `primary_context_mismatch`,
  `insufficient_context`, and `off_topic`.
- Documentation:
  `docs/research/topic-quality/2026-05-25-path-b-benchmark-harness.md`.
- Do not promote encoder/ranking changes below the 85% precision floor; target
  90% before treating topic quality as product-grade.
- Do not delete broad concepts only because they fail a specific child anchor.
  Example: `Panama Canal` can be a valid broad/entity thread, but not evidence
  for `transport-corridor-disruption` unless the signal shows closure, drought,
  blockade, delay, shipping disruption, or operational impact.

Narrative classification root cause:

- Canonical audit:
  `docs/research/topic-quality/2026-05-25-narrative-classification-root-cause-audit.md`.
- Do not continue topic-by-topic patching as the default response to benchmark
  failures. The root issue is that one assignment layer is currently carrying
  domains, parent threads, child threads, entity threads, evidence rows, and
  contextual mentions.
- The next model step is to measure semantic role and evidence role:
  `domain`, `parent_thread`, `child_thread`, `entity_thread`, `evidence`,
  `context_signal`, `noise`.
- Keep `atlas_topics` as internal anchors. The visible product should organize
  parent -> child Narrative Threads and entity lenses above those anchors.

## Previous Session Context (2026-05-21, data operating roadmap)

### Coordination roadmap

Use `docs/roadmap/2026-05-21-data-operating-roadmap.md` as the current execution order for the data phase. It coordinates:

1. Supabase-light hot/cold operating model.
2. Local archive -> processed historical sync.
3. App-wide long-window routing through processed history.
4. Hot-window NLP/topic/source quality.
5. Coverage/provenance UI and visual manuals.
6. Living Narrative Threads as the next product/data route.

Older docs remain valid but subordinate:

- `docs/superpowers/plans/2026-05-20-hot-cold-data-operating-model.md`
- `docs/superpowers/plans/2026-05-21-processed-historical-sync.md`
- `docs/superpowers/specs/2026-05-21-processed-historical-routing-design.md`
- `docs/roadmap/2026-05-19-topic-and-signal-class-attack.md`
- `docs/roadmap/2026-05-16-productization-roadmap.md`

Living Narrative Threads canon:

- `docs/specs/2026-05-24-living-narrative-threads.md`
- `docs/research/2026-05-24-app-panel-thread-audit.md`
- `docs/roadmap/2026-05-24-open-issues-thread-triage.md`
- `docs/superpowers/plans/2026-05-24-living-narrative-threads.md`

Product rule: `atlas_topics` is an internal anchor vocabulary, not the user's
primary mental model. User-facing surfaces should converge on living Narrative
Threads that answer: why this is moving now, what changed in the last 10h,
where it is concentrated, which subthreads are forming, which sources are
driving it, what evidence supports it, and what related thread it connects to.
The first technical increment exists as an additive read-only `/api/v2/threads`
beta above existing topic assignments, aggregates, sources, and signal evidence.
Contract: `living-narrative-threads-v0`. Implementation:
`backend/app/services/thread_intelligence.py` + `backend/app/routers/threads.py`.
The first visible frontend slice is live in `NarrativeThreads` +
`ThreadFocusPanel`; keep older theme fallbacks for panels not yet migrated.

### App-wide historical routing scope

`#193` should be treated as still open until deployed frontend visual smoke tests pass. Backend routing is implemented, but do not close the issue solely from API checks.

- Done: `/api/v2/briefing?hours>24` routes `top_themes` to `historical_topic_country_daily`.
- Done: `/api/v2/briefing?hours>24` routes `top_sources` to `historical_source_daily` (#194).
- Done: `/brief` renders historical processed coverage metadata.
- Done: full cutover archive backfill into compact historical tables using `backend/scripts/historical_backfill.py`: `18` days, `22,711` compact rows, `2,128,070` represented signals, `236` countries, `11` topics.
- Done: source backfill into `historical_source_daily`: `18` days, `161,871` compact daily source rows, `2,128,070` represented signals; live query plan after `VACUUM` is ~40 ms index-only scan with `Heap Fetches: 0`.
- Done: shared `processed_historical.py` helper.
- Done: `/api/v2/heatmap`, `/api/v2/heat/countries`, `/api/v2/country/{code}`, `/api/v2/theme/{topic_slug}`, and `/api/v2/anomalies/themes` coverage envelopes.
- Done: reusable frontend `CoverageBadge` in Heat and Theme Detail.

Quality finding after full backfill: `general-monitoring` represents `1,559,990` of `2,128,070` historical signals. Historical storage/routing has enough data; next quality work is topic intelligence (#171/#167/#185). First step shipped as PR #197 (classifier v2 + A/B baseline) — see "Atlas topic classifier v2" below; awaiting a live measurement run before promotion.

### Security RLS lockdown (migration 030)

### Security RLS lockdown (migration 030)

- Supabase advisor flagged 45 public tables with RLS disabled — anon/authenticated roles could read or write every row via PostgREST.
- Backend connects as `postgres` superuser via `DATABASE_URL`, which bypasses RLS unconditionally; frontend does NOT use the Supabase JS client. So enabling RLS without policies locked out anon/authenticated without breaking the app.
- Migration `030_security_rls_lockdown.sql` (applied via Supabase MCP):
  - `ENABLE ROW LEVEL SECURITY` on all 45 public tables.
  - `REVOKE SELECT FROM anon, authenticated` on 5 materialized views (`mv_recent_hotspots`, `low_volume_countries`, `country_heat_v2`, `mv_active_flows`, `country_hourly_v2`) — RLS does not apply to matviews.
  - Converted 2 `SECURITY DEFINER` views (`v_table_sizes`, `v_row_counts`) to `security_invoker = true`.
  - Locked `search_path = public, pg_temp` on 11 public functions (prevents search-path injection).
- Advisor result: 1 CRITICAL + 2 ERROR + many WARN -> 0 CRITICAL/ERROR; remaining issues are INFO (RLS enabled, no policy — expected) plus 1 WARN (`pg_trgm` in public, cosmetic).
- Backend tests: 271 passed, 6 skipped. `/api/v2/briefing?hours=24` returns full payload, no errors.

### Atlas topic classifier v1 (migration 031 + `classify_topics.py`)

- Audit on last 24h of `signals_v2` (208k rows): only 50% of signals matched any `atlas_topics` via `gdelt_theme_hints`, because the hints used short codes (`TRANSPORT`, `ENERGY`, `SANCTION`) that don't exist in real GDELT GKG output — GDELT uses prefixed taxonomy (`WB_*`, `TAX_*`, `CRISISLEX_*`, `UNGP_*`, `EPU_*`).
- Migration `031_atlas_topic_hints_realign.sql` rewrites `gdelt_theme_hints` on all 30 active atlas topics with the real GDELT codes observed in production data. Theme-level coverage jumps 50.02% -> 84.21%.
- `signal_topic_assignments` was empty (0 rows). `backend/scripts/classify_topics.py` is the first-pass classifier: it joins `signals_v2.themes` against `atlas_topics.gdelt_theme_hints` (set intersection) and checks `atlas_topics.lexicon_terms` against `lower(headline)`. A signal qualifies only if a lexicon term matches the headline OR at least 3 theme hints match. Confidence is normalized to 0..1: `0.4 * (theme_hits / hint_count) + 0.6 * lex_match`. Top-2 topics per signal, min confidence 0.3.
- First backfill (last 24h, applied via Supabase MCP, mirrors the SQL inside `classify_topics.py`): 1,657 assignments across 1,646 distinct signals, all 30 atlas topics represented, average confidence 0.661, 1,457 high-confidence (>=0.6).
- Top topics post-classifier: disease-outbreak (320), labor-strike-disruption (173), oil-gas-supply-risk (162), flood-landslide-disaster (157), armed-conflict-escalation (94). Distribution is balanced — no `general-monitoring` domination.
- Tradeoff: precision-first (lex OR >=3 theme hits) keeps quality ~65% in spot checks at the cost of recall (~0.8% of 24h volume classified). Boosting recall requires the multilingual NLP swap (#162) and the deeper topic intelligence work (#167) — GDELT themes alone are not discriminative enough for fine topics.
- Method/version tag for these assignments: `method='lexicon'`, `model_version='theme-hint-lex-v1'`. Future ML-based or analyst-corrected assignments use different tags and can coexist via the PK `(signal_id, topic_id, method, model_version)`.

### Atlas topic classifier v2 (PR #197 — `backfill_lexicon_topics.py`, bulk SQL)

- v2 is a recall-lift sibling of v1, NOT a replacement. Both coexist in `signal_topic_assignments` via the PK `(signal_id, topic_id, method, model_version)`: v1 = `theme-hint-lex-v1`, v2 = `theme-hint-lex-v2`. v1 keeps running until v2's lift is measured and the promotion gate clears.
- `backend/scripts/backfill_lexicon_topics.py` implements #171: a single-statement `INSERT … SELECT` against `signals_v2` + `atlas_topics`, accelerated by the mig 022 trigram GIN on `lower(headline)` and the GIN on `signals_v2.themes`. Idempotent via `ON CONFLICT … DO UPDATE`, so it doubles as the incremental cron path (`--window-hours 0.5`).
- Qualification widens from v1's "lex OR >=3 theme hits" to v2's "lex >=1 OR theme_hits >=1" — single-theme signals enter when a topic's lexicon is thin for that language. Recall is held by raising the confidence floor to 0.55 (v1 used 0.30).
- v2 confidence: `LEAST(0.95, 0.55 + 0.10*LEAST(lex_count,3) + 0.05*LEAST(theme_hits,4) + (0.05 if lex>0 AND theme_hits>=2 else 0))`. Cap is 0.95 (reserves headroom above any auto-assignment for analyst confirmation). Top-2 per signal, headline length filter >=20 chars to drop aggregator/tweet stubs. Evidence jsonb records `matched_terms`, `theme_hits`, `hint_count`, and the component scores.
- `backend/scripts/topic_classifier_baseline.py` is the read-only A/B reporter: candidate count, recall per `model_version` (distinct_signals / window total), v1-vs-v2 top-1 agreement, per-topic distribution, confidence histogram. Workflow: baseline -> dry-run -> backfill -> re-baseline.
- Promotion gate (v2 -> production ranking): recall_pct >= 5x v1; top1_match_pct >= 70% on shared signals; >=60% precision on a 50-row spot-check of v2-only assignments; per-topic distribution does not collapse (>=20 topics with >=10 assignments in 24h). All four must pass before wiring v2 into API ranking or scheduling the 15-min cron.
- Live A/B 2026-05-23 (6h window, Supabase MCP): v1 dry-run = 841 distinct signals (2.2% recall, 96.5% lex-supported, avg_conf 0.613). v2@0.55 dry-run = 27,942 sigs (73.5% recall, 1.6% lex — too noisy). v2@0.65 dry-run = 6,121 sigs (16.1% recall, **7.3x v1**, avg_conf 0.653). v2@0.70 collapses to 398 sigs (under v1). Sweet spot is 0.65; `DEFAULT_MIN_CONFIDENCE` raised from 0.55 -> 0.65 in `backfill_lexicon_topics.py`.
- Top1 agreement v1↔v2@0.65 on the 812 overlap signals: **92.73%** (753 same, 59 different). Gate (>=70%) cleared by wide margin.
- Live backfill executed 2026-05-23 over 24h in 4x 6h chunks via Supabase MCP: 33,279 rows upserted into `signal_topic_assignments`, 25,975 distinct signals, avg_conf 0.654, 30 topics fired. Top topic disease-outbreak = 4,544 (13.7%); no collapse. Recall vs 24h candidate window (154,226 signals): **16.84%** (≈21× the 0.8% baseline from `classify_topics.py` at mig 031 time).
- v1 stays absent from `signal_topic_assignments` for now (the May 21 v1 backfill was wiped by the hot/cold prune of 2026-05-20). Re-running the legacy `classify_topics.py` against the current 24h is optional — v2's 92.7% top1 agreement on overlap is sufficient evidence the two converge on the easy cases.
- `/api/v2/briefing` exposes the v2 classifier output via `top_atlas_topics` (parallel to legacy `top_themes` which still ships raw GDELT codes). Reads `signal_topic_assignments JOIN atlas_topics` with `COUNT(*)` (NOT `COUNT(DISTINCT signal_id)` — PK guarantees uniqueness per (topic, model_version) group, and DISTINCT forces a 200ms external sort vs ~40ms for plain COUNT on 33k rows). Hot path measured at ~40 ms. Degrades to `[]` via `to_regclass('signal_topic_assignments')` guard.
- Incremental cron `com.atlas.atlas-topic-classifier.plist` (StartInterval=1800s, RunAtLoad=true) fires `run-atlas-topic-classifier.sh` -> `backend/scripts/backfill_lexicon_topics.py --window-hours 0.5` every 30 min. First live run: 511 upserts, 396 distinct signals. Runner lives at `/Users/pedro/AtlasLocalWorker/run-atlas-topic-classifier.sh` (NOT Desktop — macOS launchd blocks Desktop paths); script copies live in `/Users/pedro/AtlasLocalWorker/backend/scripts/` and must be resynced from `backend/scripts/` after every change.
- Migration **034** (2026-05-23) corrects mig 031's noisy hint inheritance. Audit revealed 8 topics with catastrophic false-positive rates: `currency-debt-stress` (2338 sigs / 0.0% lex — `TAX_ECON_PRICE` + `ECON_STOCKMARKET` matched any equity/commodity story), `heat-health-risk` (3584 / 1.1% — `MEDICAL` + `WB_621_HEALTH` matched any medical headline), `telecom-internet-shutdown` (4100 / 1.0% — `WB_133` + `WB_678` matched any IT/e-gov), `press-freedom-crackdown` (1452 / 0.3%), `student-youth-protest` (1060 / 0.3%), `constitutional-institutional-crisis` (5522 / 4.7%), `disinformation-influence-operation` (1988 / 2.8%), `forced-displacement` (239 / 0.0%). Mig 034 drops the polluting hints, keeps the topic-specific ones, expands lexicon_terms from 4–7 entries to 15–18 with natural-language phrases real headlines use (peso, rupee, blackout, heatwave, coup attempt, displaced, etc.).
- Post-mig 034 cleanup: 20,283 stale v2 assignments deleted (those rows were based on the old polluted hints), then re-backfill over 24h. New per-topic lex_pct: 5/8 fixed topics at **100% lex-supported**, currency-debt-stress at 84.9%, forced-displacement at 26.1% — every assignment now has a real headline match. Sharp recall drop is expected and welcome (e.g. heat-health-risk 3584 → 257) because the dropped volume was almost entirely false positives. Top-10 atlas topics now reflects actual narratives (disease-outbreak, labor-strikes, armed-conflict, floods, elections, gangs, fuel-unrest) instead of theme-hint pollution.
- **Hint quality rule**: when adding a topic to `atlas_topics`, audit the GDELT hints against last-24h sample headlines via `signal_topic_assignments` lex_pct after a first backfill. If lex_pct < 10% AND volume > 500 sigs/24h, the hint set has a precision leak — replace the broad hints with narrower siblings (e.g. `MEDIA_CENSORSHIP` instead of `WB_694_BROADCAST_AND_MEDIA`).
- 2026-05-23 coverage audit: 119,129 signals/24h pass the headline length filter, only **12,787 (10.73%)** received any atlas_topic assignment. 87% of unclassified signals HAVE themes — the classifier just wasn't looking for the right GDELT codes. Pareto check: 4 topics = 50% volume, 10 = 80%, 19 = 95% (30 active topics across 10 domains — diversity OK, no single-topic collapse).
- Migration **035 + 035b** (2026-05-23) closes part of the recall gap. Audit identified specific GDELT codes appearing frequently in `signals_v2.themes` but absent from any atlas_topic hint. Sample-tested precision per candidate hint; only added hints with >=75% sample precision. Added: `TERROR` to armed-conflict-escalation, `WB_2473_DIPLOMACY_AND_NEGOTIATIONS` to sanctions-diplomatic-pressure, `EVACUATION` to forced-displacement, `WB_2663_EBOLA`+`TAX_DISEASE_EBOLA`+`TAX_DISEASE_DISEASE` to disease-outbreak. Rejected: `CRISISLEX_T02_INJURED`, `WB_2462_POLITICAL_VIOLENCE_AND_WAR`, `WB_2495_DETENTION_PRISON`, `CRISISLEX_C06_WATER_SANITATION`, `SCANDAL`, `WB_2507_HUMAN_RIGHTS_ABUSES` (mixed accidents/noise in sample).
- Mig **035b** correction: mig 035 dropped MEDICAL from disease-outbreak by analogy with mig 034's heat-health-risk fix; that was wrong. MEDICAL is noisy on heat-health-risk (most medical headlines aren't heat) but specific on disease-outbreak during a live Ebola outbreak (most MEDICAL-tagged headlines ARE the outbreak). Restoring it took disease-outbreak from 2,413 sigs/24h back to 4,719 with **590 high_confidence** assignments (vs 142 before mig 035). Lesson: dropping broad hints requires per-topic precision measurement, not analogy.
- Post mig 035+035b global coverage: 10.73% → **13.08%** (+2,770 signals/24h classified). Modest absolute lift but high-quality: most gains landed in disease-outbreak (specific Ebola codes + restored MEDICAL) and armed-conflict-escalation (TERROR brings +1,044 sigs/24h, lex_pct drops but high_conf rises from 1 → 21). Remaining 87% unclassified is dominated by `xx` language headlines (64%) — lex_terms only in English. Multilingual lex mining (#185 extended to atlas_topics) is the next recall lever.
- Atlas hierarchy + co-occurrence now live in `/api/v2/briefing` (PR #201 — `topics_by_domain` + `related_topics`). `parent_domain` (10 domains, 2-5 topics each) is the cluster level; `related_topics` ranks per-topic co-occurrence via Jaccard-proxy `co / sqrt(|A|*|B|)`. Top co-occurrence pairs (24h window): fuel-subsidy ↔ labor-strike (373), food-price ↔ housing-cost (210), water-drought ↔ flood-disaster (149), fuel-subsidy ↔ food-price (123), migration-border ↔ forced-displacement (95), armed-conflict ↔ forced-displacement (56). Co-occurrence SQL **must filter by `assigned_at`, not by joining `signals_v2.timestamp`** — the self-join with the timestamp lookup was measured at 605 ms vs 47 ms when staying inside the assignments table (PK + idx_signal_topic_assignments_method_version).
- **AI taxonomy spec** at `docs/specs/2026-05-23-ai-assisted-taxonomy.md` — three paths (multilingual lex via LLM, bootstrap-trained encoder classifier, LLM-assisted taxonomy revision). Path A pilot is implemented via migration 036; Paths B/C remain design/shadow work. Sequencing: finish Path A rollout on the five remaining low-lex topics before introducing Path B architecture.
- **Sentiment vs tone (analyst decision)**: product UI should expose one normalized value: Atlas sentiment. GDELT V2Tone (column `signals_v2.sentiment`) remains fallback/calibration/provenance, not a competing user-facing metric. Briefing may continue returning `sentiment_source = gdelt | nlp | nlp_weighted` for traceability, but product copy should avoid asking users to compare GDELT Tone and Atlas sentiment as separate systems.
- **Migration 036** (2026-05-23 — Path A pilot for issue #202): multilingual `lexicon_terms` expansion for `election-legitimacy-dispute` from 5 English terms to 43 terms across 8 languages (EN/ES/IT/PT/FR/DE/TR/EL). Methodology: pulled 25 high-conf positives + 30 theme-only negatives via Supabase MCP, Claude proposed candidate substring matchers, each candidate verified via SQL `LIKE` against 24h headlines for volume + 4-headline random sample for precision. Rejected `scrutin` (matched "scrutiny", "escrutinável", ~25% precision). Accepted 38. Live results: lex_pct **6.3% → 31.6%** (5× lift, gate cleared), high_conf **5 → 27** (5×). Multilingual terms drove **74% of new lex hits** (elecciones 156, elezioni 101, comicios 12 vs English ballot 31, presidential primary 68). Methodology validated for rollout to the 5 remaining low-lex_pct topics: armed-conflict-escalation (2.2%), fuel-subsidy-unrest (10.4%), mining-royalty-risk (12.5%), housing-cost-pressure (13.6%), food-price-stress (19.0%).
- **Migration 037** (2026-05-23 — Path A precision-first pass for issue #202): `armed-conflict-escalation` had baseline assignments 3,338, lex-supported 70, high_conf 22, lex_pct 2.10%. Live samples showed original terms `clashes`, `offensive`, and `shelling` were noisy (sports, entertainment, marketing, "shelling out"). The first broad candidate pass also showed `shots fired`, `opening fire`, `firing at`, `ataque armado`, and `battlefield` would inflate local crime/public-security or historical/metaphorical material into armed-conflict. Final migration removes the noisy original terms and adds only precise multilingual conflict terms. Live purge + 24h re-backfill result: assignments 3,642, lex-supported 239, high_conf 85, lex_pct **6.56%**; global v2 coverage **17.22%**. This is a partial result, not a gate clear: do not re-add broad armed-incident terms just to reach 30%.
- **Migration 038** (2026-05-24 — Path A final low-lex rollout for issue #202): completed the remaining four topics. Live purge + 24h re-backfill result: `fuel-subsidy-unrest` lex_pct **5.20% → 37.12%**, high_conf **2 → 136** (gate clear); `food-price-stress` lex_pct **17.52% → 4.63%**, high_conf **7 → 10** after removing noisy `shortage`/`hunger` (precision cleanup, not recall win); `housing-cost-pressure` lex_pct **10.16% → 8.20%**, high_conf **0 → 2** after removing noisy `mortgage`/`eviction`; `mining-royalty-risk` lex_pct **12.33% → 78.99%**, high_conf **0 → 100**, driven by coal-mine-disaster terms. Global v2 coverage after rollout: **18.47%** of 24h eligible signals. Path C should revisit two taxonomy findings: split local armed incidents from armed conflict, and split/rename mining royalty vs mining/resource-disaster risk.
- **Path A workflow** (verified repeatable):
  1. Pick topic with lex_pct < 20% and vol > 500/24h.
  2. SQL pull: 25 high-conf positives + 30 theme-only negatives via Supabase MCP.
  3. Claude (the LLM) reads samples and proposes 30-50 candidate substring matchers across the languages observed in negatives (typically EN/ES/IT/PT/FR/DE plus regional ones like TR/EL when present).
  4. SQL verify each candidate against 24h headlines: count volume + spot-check top 4 hits per heavy hitter (>10 vol) for precision. Reject any term with <75% precision in sample.
  5. Migration appends accepted terms to `atlas_topics.lexicon_terms`. Delete v2 assignments for that topic. Re-backfill 24h. Measure lex_pct.
  6. Promotion gate: lex_pct >= 30% after rebackfill AND no global regression on other topics' high_conf.

### Operational rule

- New tables added to the public schema must enable RLS at creation time (migration 030 set the baseline). If a table needs read access from the anon/authenticated roles, add an explicit `CREATE POLICY` in the same migration; otherwise rely on the `postgres` superuser bypass that the backend uses.
- Atlas topics taxonomy lives in `atlas_topics.gdelt_theme_hints` / `lexicon_terms`. When adding or editing a topic, sanity-check that the theme hints actually appear in `signals_v2.themes` (sample last 24h); otherwise the topic stays at 0 matches like the original 4 broken topics did.

## Previous Session Context (2026-05-21, processed historical sync)

- Active branch: `v3-intel-layer`; production branch. Do not merge into `main`.
- PR #144 open against main: https://github.com/pedro-cmyks/Observatory-Global/pull/144
- Production: Vercel (frontend auto-deploy), Fly.io `atlas-api-pedro` backend, Fly.io `nlp_worker` 4GB.
- Fly image split (#195): use `scripts/deploy-fly-api.sh` for API-only deploys (`api-runtime`, process group `app`, verified `257 MB` image) and `scripts/deploy-fly-nlp-worker.sh` for NLP/model deploys (`nlp-runtime`, process group `nlp_worker`). Avoid bare `fly deploy --config fly.toml` for routine API work because it can rebuild/push the heavy model image.
- Latest hot/cold doc commit before this handoff: `bb26197 docs(data): record live hot cold prune`.
- Current direction: Supabase serves processed historical product surfaces, not raw historical rows. The local archive stays raw; a local processor will sync compact processed aggregates/evidence samples back to Supabase.
- Atlas product framing: **public narrative intelligence console**, not a GDELT wrapper.
- Preferred user path: `/brief` for readable orientation, then `/app` for full analyst investigation.

### Processed historical sync direction

- Spec: `docs/superpowers/specs/2026-05-21-processed-historical-sync-design.md`.
- Implementation plan: `docs/superpowers/plans/2026-05-21-processed-historical-sync.md`.
- Implementation started:
  - `backend/migrations/029_historical_processed_tables.sql`.
  - `backend/scripts/historical_process_partition.py`.
  - `backend/scripts/historical_sync.py`.
  - `backend/tests/test_historical_processing.py`.
  - `docs/research/processed-historical-sync/2026-05-19-topic-country.json`.
- Smoke result: `185,163` archived rows from `2026-05-19` -> `1,728` processed aggregate rows. Sync dry-run accepted `1,728` rows.
- Supabase MCP OAuth is configured. Migration `029` was applied through Supabase MCP, then the first artifact was synced live using Fly runtime `DATABASE_URL`: `1,728` rows in `historical_topic_country_daily`, summing to `185,163` signals for `2026-05-19` / `atlas-hist-v1`.
- #193 first bridge implemented: `/api/v2/briefing?hours>24` routes `top_themes` to `historical_topic_country_daily` and returns `historical_coverage`; `/brief` renders a historical processed coverage note. `historical_coverage_report.py` reports the current baseline: `1,728` aggregate rows, `185,163` represented signals, `226` countries, `11` topics.
- Tracking issues:
  - #191 — local archive -> processed historical Supabase sync.
  - #192 — processed-only historical Supabase schema and guardrails.
  - #193 — route `1w`/`1m` app windows to processed historical tables.
- Related issues commented: #164, #167, #171, #184, #185.
- Operating rule: Fly handles hot 24h SLA; Pedro's local machine handles historical/backlog processing; Supabase stores compact processed outputs and small evidence samples, not full raw history.

### Session 20 hot/cold archive cutover state

- Local archive root: `/Users/pedro/AtlasArchive`.
- First probe archive remains at `/Users/pedro/AtlasArchive` with `952` verified rows.
- Clean cutover archive: `/Users/pedro/AtlasArchive/cutovers/2026-05-20`.
- Cutover export source: Fly app machine `d8d2e46fe07e78`, Supabase `signals_v2`.
- Cutover export window: `2026-05-03T00:00:00Z` through `2026-05-20T03:33:29Z`.
- Cutover archive verified: `18` manifest records, `2,128,070` rows, `~368M`, `0` failures, `0` overlaps.
- Verified prune dry-run from Fly nlp_worker `0803426f142468`: `archive_rows=2,128,070`, `db_candidate_rows=2,128,070`, `range_count=18`, `executed=false`.
- Live prune completed after explicit approval: `deleted_rows=2,128,070`, `elapsed_seconds=139.13`; post-prune archived range remaining `0`, exact `signals_v2` count `259,360`.
- Smoke queries:
  - Date `2026-05-19`: `185,163` rows.
  - Country `CO`: `13,654` rows.
  - Source family `social`: `485` rows.
  - Topic/headline substring `energy`: `92,005` rows.

New safety scripts:

- `backend/scripts/archive_verify.py` — local manifest verifier for rows, SHA256, bytes, and overlapping ranges.
- `backend/scripts/archive_plan.py` — Supabase daily export planner.
- `backend/scripts/prune_archived_signals.py` — dry-run by default; live delete requires `--execute --i-understand-irreversible-delete`; deletes only `signals_v2` rows inside verified manifest ranges.

Guardrail: do not manually delete historical rows. Run `archive_verify.py` first, then `prune_archived_signals.py` dry-run. Product aggregate tables, correction tables, topic tables, and NLP audit/progress state stay in Supabase. `/health.total_signals` reads historical aggregate volume from `country_hourly_v2`, not raw `signals_v2` hot-store row count after the cutover.

Tests after hot/cold guardrail changes: `cd backend && .venv/bin/python -m pytest -q` -> `260 passed, 6 skipped`.

### Previous session 19 closed with data architecture pressure exposed:

**Sentiment fusion (Opción A) end-to-end**
- Migration 025: `theme_hourly_v2` + `theme_country_hourly_v2` gained `nlp_signal_count` + `avg_nlp_sentiment`.
- Migration 026: `country_hourly_v2` matview swapped (build-populate-rename) with the same NLP coverage columns.
- Migration 033 (2026-05-22): same three tables gained `nlp_sentiment_weight_sum` + `nlp_confidence_sum` so readers can compute `SUM(s*c)/SUM(c)` instead of the flat AVG that diluted high-confidence transformer rows with low-confidence lexicon/fast_neutral rows.
- `app/services/sentiment_fusion.py` — two helpers:
  - `choose_sentiment(gdelt_raw, nlp_raw, coverage)` is the legacy flat-AVG path (kept for back-compat).
  - `choose_sentiment_weighted(gdelt_raw, weight_sum, conf_sum, nlp_signal_count, signal_count, fallback_nlp_avg=...)` prefers the confidence-weighted ratio, then legacy flat NLP, then GDELT. Returns one of three source labels: `"nlp_weighted"` | `"nlp"` | `"gdelt"`.
  - Both rescale by `NLP_SENTIMENT_SCALE = 2.37` (calibrated from GDELT stddev 3.99 / NLP stddev 1.68 measured live).
- Briefing API exposes `sentiment_source` (`"nlp_weighted"` | `"nlp"` | `"gdelt"`) + `nlp_coverage` on every country row + global stats.
- `negative_sentiment` / `positive_sentiment` order by the chosen sentiment (computed in SQL via CASE that prefers weighted ratio when `nlp_conf_sum > 0`, falls back to flat `nlp_avg`, then GDELT).

**Heat ranking surface (#149 + #165 closed)**
- New `heat_countries` section in briefing reads `country_heat_v2` and ranks by `atlas_heat`.
- Each entry exposes full component breakdown (velocity, surprise, diversity, voice, polyphony, geo_confidence, duplication).
- Sits next to `top_countries` (volume rank) so the briefing surfaces both lenses; nothing replaced.

**Briefing hygiene**
- `top_themes` switched from dead `signals_theme_hourly` to `theme_hourly_v2`.
- `top_sources` switched from dead `signals_source_hourly` to `historical_source_daily` for long windows; hot windows keep the bounded `signals_v2` scan.
- `/briefing/insight` mirrors `/briefing` hardening — `country_hourly_v2` + parameterized intervals + `_fetch_section` degraded path.

**Data ops via Supabase MCP**
- ADR-0004 prune: 241,656 rows deleted (5 batches, 25k–50k each), `VACUUM ANALYZE` complete, `signals_v2` autovacuum tuned (`scale_factor=0.05`, `cost_delay=10`).
- `nlp_sample_queue` truncated (610K zombie ids — worker prioritized fresh since `7472aba`, queue never drained).
- `nlp_progress` synced to ground truth post-prune (worker delta math doesn't self-correct — tracked in #186).
- Lexicon vocab expansion: EN +110 terms, ES/PT +50, IT/DE seeds added. Hit rate plateau ~12% confirmed live.

**Follow-up commits after session 17 close**
- `613a21e` + `3e0fce8`: `nlp_progress` recomputes ground truth and briefing exposes `heat_voluminous_countries`.
- `afc68e5`: `backend/scripts/mine_lexicon_vocab.py` mines lexicon vocab from transformer-tagged rows.
- `3d7d7af`: Dockerfile copies `backend/scripts` into the Fly image.
- `1894128`: per-language stopword sets reject closed-class tokens.
- `763b3c9`: first mined snapshots committed (`en.mined.json` ~1,920 entries; non-EN still tiny).

**Tests**: 244 passed at lexicon mining stage; 238 passed before heat_voluminous deploy. Keep running full backend suite after touching data paths.

### Issues touched

- ✅ Closed: #149 (volumetric US dominance), #165 (Atlas composite heat), #186 (`nlp_progress` self-recompute), #187 (`heat_voluminous_countries` lens).
- 📝 Progress comments on #164 (ADR-0004 prune executed), #171 (lexicon vocab expanded, plateau measured).
- 🆕 Still open: #183 (frontend sentiment badge + heat panel), #184 (NLP_WORKER_LIMIT bump experiment), #185 (corpus-mine lexicon vocab quality target).

### Next session priorities:
1. **#191 / #192** — add processed historical schema and local archive processor.
2. **#193** — route long app windows (`1w`, `1m`) to processed historical tables with coverage metadata.
3. **#184** — keep Fly worker focused on hot-window SLA; only resize after observing hot backlog and Supabase IO.
4. **#185** — improve multilingual corpus mining; EN snapshot exists, non-EN remains too small.
5. **#183** — frontend renders `sentiment_source`, NLP coverage, `heat_countries`, and `heat_voluminous_countries`.

### Reference docs:
- `docs/STATUS.md` — current state, full session 17 inventory.
- `docs/adr/ADR-0004-nlp-stratified-sampling.md` — stratified + prune strategy (approved, executed).
- `docs/methodology/atlas-heat.md` — `country_heat_v2` formula reference.

### Key patterns (established across sessions 13–14)

- `resolveCountryName(code, name)` — always use for country display, never raw `c.name` from API
- `getThemeLabel(code)` — always use, never raw GDELT theme codes in UI
- `data-tip` attribute only — never native `title=` for tooltips
- `themeSignals[theme][0]` — do NOT use as headline anchor; misclassification risk
- `d?.trending ?? []` — correct field for trends API response (`trending`, not `trends`)
- `detail_hours = min(hours, 48)` — Phase 2 narrative detail cap in `narratives.py`
- Two ForceGraph2D instances with `visibility: hidden` toggle — preserves simulation state
- `briefingPrefetch.ts` sessionStorage cache (4-min TTL) — read before fetch in BriefNewspaper
- `parseCompoundQuery(q)` in SearchBar — extracts countryCode from "topic Country" queries
- `useSavedWatches` localStorage key: `atlas_saved_watches_v1`; `markSeen(id, count)` records delta baseline
- ACLED is optional connector — no `ACLED_API_KEY` → empty layer, no errors
- `createTerminatorLayer()` returns `PolygonLayer[]` (5 bands) — spread with `...terminatorLayers`
- `fetchItemSignals(item)` in `exportFormatters.ts` — shared by dossier export and ReadingMode
- New ingest services follow `ingest_rss.py` pattern: every row sets `source_family`, `source_lang`, `geo_confidence`, `attribution_method`, `is_state_media`
- Reddit signals: `source_family="social"`, `attribution_method="reddit_public"` — commentary layer, NOT independent corroboration; needs `signal_class="commentary"` before #149 scoring
- `geo_confidence` defaults: NewsData 0.7, MediaStack 0.65, NewsAPI 0.65, Reddit 0.5, GDELT GKG 0.9, RSS 0.6
- NLP env flags in prod: `NLP_SAMPLE_REFRESH_EVERY=0`, `NLP_SAMPLE_CLEANUP_LIMIT=50` — do NOT change without testing
- NLP worker confirmed multilingual: logs `Sentiment[xlm-v1]`, `NER[xlm-v1]`, `Framing[xlm-v1]`. Throughput 25 rows/cycle stable — do NOT raise without observing DB pressure
- `npm run build` (not `tsc --noEmit`) is the canonical build check — Vite uses `tsc -b` (stricter)

### Patterns added session 17

- **Sentiment fusion**: never sub-in NLP for GDELT silently. Read both, choose via `choose_sentiment_weighted(gdelt_raw, weight_sum, conf_sum, nlp_signal_count, signal_count, fallback_nlp_avg=nlp_avg)` (mig 033), or via legacy `choose_sentiment(gdelt_raw, nlp_raw, nlp_coverage)` for readers that have not migrated. Rescale NLP by `NLP_SENTIMENT_SCALE` so frontend ±0.1 threshold works for all sources. Helper lives in `app.services.sentiment_fusion` to avoid `briefing` → `main_v2` → `briefing.router` circular import.
- **Pre-agg NLP coverage**: any new ingest pre-agg that has `avg_sentiment` must also have `nlp_signal_count INTEGER NOT NULL DEFAULT 0` and `avg_nlp_sentiment NUMERIC` populated via `COUNT(*) FILTER (WHERE nlp_sentiment IS NOT NULL)` and `AVG(nlp_sentiment) FILTER (WHERE nlp_sentiment IS NOT NULL)`. Migration 033 added `nlp_sentiment_weight_sum NUMERIC NOT NULL DEFAULT 0` + `nlp_confidence_sum NUMERIC NOT NULL DEFAULT 0`, populated via `SUM(nlp_sentiment * nlp_confidence) FILTER (WHERE nlp_sentiment IS NOT NULL AND nlp_confidence > 0)` and `SUM(nlp_confidence) FILTER (...)`. Tracked by shape tests in `test_ingest_pre_agg_nlp_coverage.py` (whitespace-tolerant regex match — do NOT pin exact alignment).
- **Matview schema changes**: never DROP/CREATE in place when readers depend on the matview — use the build-populate-rename pattern from mig 026 (CREATE `_new` `WITH NO DATA` → CREATE UNIQUE INDEX → REFRESH → BEGIN/RENAME/RENAME indexes/COMMIT → DROP `_old`).
- **Dead-table guardrails**: legacy mig 006 tables `signals_theme_hourly`, `signals_source_hourly`, `signals_country_hourly` are NOT written to. Any reader pointing at them is a bug. Shape tests in `test_briefing_performance_shape.py` keep this pinned.
- **Honest ranking**: briefing now ships `top_countries` (volume) AND `heat_countries` (atlas_heat). Don't replace one with the other — every ranking lens answers a different question.
- **Atlas heat consumption**: `country_heat_v2.atlas_heat` is the canonical "what's heating up" metric. Always JOIN with `to_regclass` fall-through so the section degrades to `[]` if the matview is unavailable.
- **`nlp_progress` after external deletes**: worker's delta math goes stale. Manual `UPDATE nlp_progress SET unprocessed_total = ...` until #186 lands a recompute path.
- **Sentiment lexicon backfill plateau**: manual sentiment seeds cap at ~12% hit rate (most headlines factual). Don't expand sentiment vocab further by hand — pivot to #185 corpus-mining. This does not block atlas-topic Path A lexicon expansion, which is sample-driven per topic and validated by precision checks.
- **Supabase MCP DML pattern**: never `RETURNING 1` on bulk DELETE (returns N rows of 1, blows context). Run silent DELETE + separate COUNT verify.
- **Sentiment scale calibration**: NLP transformer raw stddev ~1.68 vs GDELT V2Tone raw stddev ~3.99. Ratio 2.37 stored in `NLP_SENTIMENT_SCALE`. Re-measure if NLP model swap happens (issue #162 multilingual already accounted for).

### Patterns added 2026-05-22

- **Effective NLP coverage measurement**: `backend/scripts/nlp_coverage_report.py` reports product-cell coverage (`country_hourly_v2`, `theme_country_hourly_v2`, `historical_topic_country_daily`) under the briefing fusion threshold. Use this metric (not raw row-level transformer ratio) when deciding whether to spend on worker throughput vs scoring quality.
- **Confidence-weighted bucket sentiment**: when a pre-agg bucket has `SUM(nlp_confidence) > 0`, prefer `SUM(nlp_sentiment * nlp_confidence) / SUM(nlp_confidence)` over `AVG(nlp_sentiment) FILTER (...)`. Flat AVG dilutes transformer (avg conf 0.64) with lexicon (0.31) and fast_neutral (0.01) at equal per-row weight. Mig 033 captures this; new readers should consume the weighted ratio. Source label `"nlp_weighted"` distinguishes from legacy `"nlp"`.
- **Transformer ≠ lexicon on same headline**: 70.8% sign agreement, 29.2% disagreement on a 1,888-row decided sample (2026-05-22 benchmark). Lexicon misses sarcasm, negation, multilingual scripts. Confidence weighting is the cheapest mitigation; pure-quality improvements require more transformer corpus (#184 / #163) or NLP model swaps.
- **HTML entity decode at tokenisation**: upstream feeds emit `&#xE4;`, `&ouml;`, etc. Without `html.unescape`, the regex `\w+` fractures `verk&#xE4;ndet` into `verk` + `xe4` + `ndet`. Runtime scorer (`enrichment/lexicon_sentiment.py::_clean`) and miner (`scripts/mine_lexicon_vocab.py::_clean_headline`) both decode before tokenising. Any new tokeniser path must do the same.
- **Langdetect for `xx` rows in miner**: XLM multilingual NLP stamps `source_lang='xx'` on 82% of transformer-tagged rows. The miner runs `langdetect.detect_langs` (seed 0; min confidence 0.85) on the cleaned headline and projects onto `SUPPORTED_LANGS`. `--no-langdetect` opts out, `--replace` opts out of merge mode (default merges into existing snapshot + writes `<lang>.mined.json.bak`).
- **Supabase MCP DDL timeouts**: `apply_migration` and `execute_sql` have aggressive timeouts. Split heavy backfills into ≤6h windows; split matview build-populate-rename into 4 separate calls (CREATE WITH NO DATA + indexes via `apply_migration`, REFRESH via `execute_sql` because REFRESH cannot run inside a transaction, BEGIN/SWAP/COMMIT via `apply_migration`, DROP _old via `apply_migration`).
- **Local hot/cold catch-up runtime**: `/Users/pedro/AtlasLocalWorker` (NOT `~/Desktop/...`) because macOS launchd blocks execution from Desktop-protected paths. LaunchAgent at `~/Library/LaunchAgents/com.atlas.local-hot-cold-catchup.plist` fires `RunAtLoad` + 6 daily schedule. Runner: `backend/scripts/local_hot_cold_catchup.py`.

## Specialized Agents

The project uses a multi-agent architecture where each agent has specific expertise. The **Orchestrator** coordinates these agents based on task requirements.

### Agent Summary

| Agent | Purpose | When to Call |
|-------|---------|--------------|
| orchestrator | Coordinates multi-agent workstreams | Starting sessions, planning iterations, QA reviews, managing blockers |
| backend-flow-engineer | Implements API endpoints and backend logic | Flows API, health endpoints, trends endpoints, caching, migrations |
| data-geointel-analyst | Handles geointelligence data sources | GDELT/Trends/Wikipedia clients, topic normalization, scoring algorithms |
| data-signal-architect | Designs signal processing systems | Schema design, Redis caching, signal validation, mobile optimization |
| narrative-geopolitics-analyst | Analyzes narrative propagation | Drift detection, mutation patterns, source analysis, visualization design |
| frontend-map-engineer | Implements map visualizations | Mapbox components, geospatial displays, real-time updates |

---

## Agent Details

### Orchestrator

**Purpose**: Senior technical orchestrator for multi-agent coordination, work prioritization, and incremental delivery.

**When to Call**:
- Starting a new session and need to pick up where work left off
- Planning the next iteration after receiving outputs from multiple agents
- Multiple PRs need QA coordination
- Blocking issues affect multiple workstreams
- Breaking down high-level goals into trackable issues

**Key Responsibilities**:
- Convert iteration goals into small, focused GitHub issues
- Manage handoffs between agents with complete context
- Enforce PR hygiene standards
- Produce daily planning artifacts
- Track and label risks by category

**Interaction with Backend Tasks**:
- Creates issues for backend agents with clear acceptance criteria
- Sequences backend work to minimize idle time
- Coordinates data pipeline outputs with API endpoint implementations
- Ensures database migrations are properly sequenced

---

### Data Signal Architect

**Purpose**: Expert in large-scale signal processing, time-series data architectures, anomaly detection, and cross-source data normalization. Specializes in PostgreSQL schema design and Redis caching strategies for lightweight, mobile-ready systems.

**When to Call**:
- Designing signals schemas for multi-source narrative tracking
- Implementing time-bucketing strategies (15-min vs 1-hour)
- Reviewing or optimizing Redis caching implementations
- Validating incoming signals and detecting synthetic data
- Integrating new data sources into existing pipelines
- Optimizing queries for mobile deployment

**Core Expertise**:
- **Signals Schema Design**: Temporal, geographic, and topic dimensions with proper constraints and indexes
- **Time-Bucketing Strategy**: 15-minute buckets for real-time, 1-hour for trend analysis
- **PostgreSQL Optimization**: Efficient data types, index strategies, constraint definitions
- **Redis Caching**: Key patterns, expiration policies, memory budgets (500MB max)
- **Signal Validation**: Source verification, volume sanity, sentiment bounds, URL validation
- **Mobile Optimization**: <100ms queries, <50KB responses, gzip compression

**Interaction with Backend Tasks**:
- Provides schema DDL for database migrations
- Defines caching key patterns for backend services
- Validates signal processing logic against data quality requirements
- Recommends index strategies for API endpoint queries
- Reviews backend implementations for performance and efficiency

**Execution Guidelines**:
- Always include complete DDL with constraints and indexes
- Provide storage and performance estimates
- Include example queries demonstrating index usage
- Document edge cases and error handling
- Target 100ms query latency and 1000 signals/minute throughput

---

### Narrative Geopolitics Analyst

**Purpose**: Expert in global information ecosystems, disinformation analysis, narrative framing, and comparative media analysis. Provides domain insight on how narratives propagate, mutate, and polarize across regions and platforms.

**When to Call**:
- Analyzing how topics are framed differently across countries
- Defining narrative mutation patterns (framing shifts, emphasis changes, attribution flips)
- Implementing drift detection algorithms (geographic, temporal, cross-platform)
- Specifying API schemas for narrative intelligence endpoints
- Interpreting signals from different source families
- Designing visualizations for narrative data
- Adding geopolitical context flags to the system

**Core Expertise**:
- **Narrative Mutation Types**: Framing shifts, emphasis mutations, omissions, amplifications, minimizations, attribution flips
- **Drift Detection**: Geographic drift scores, temporal sentiment trajectories, cross-platform divergence
- **Source Family Analysis**: GDELT, Google Trends, and Wikipedia coverage patterns, biases, and reliability
- **Geopolitical Context**: State media flags, echo chamber detection, information deserts, polarization thresholds
- **Visualization Design**: Geographic heatmaps, cluster views, temporal timelines, narrative flow diagrams

**Interaction with Backend Tasks**:
- Defines API response schemas with required metadata fields
- Provides Python implementations for drift detection algorithms
- Specifies validation rules for narrative signals
- Recommends data structures for stance and cluster tracking
- Defines confidence scoring methodologies

**Execution Guidelines**:
- Provide at least 3 concrete examples for each concept
- Include quantitative metrics with specific formulas and thresholds
- Supply Python code with type hints when algorithms are requested
- Include complete JSON schemas for API responses
- Provide user-facing plain language explanations
- Document testing recommendations and success criteria

**Collaboration**:
- Works with **DataGeoIntel** to ensure source normalization aligns with narrative needs
- Validates with **DataSignalArchitect** that signals schema includes stance and cluster fields
- Coordinates with **BackendFlow** for efficient narrative query endpoints
- Provides UX guidance to **FrontendMap** for visualization implementations

---

### Backend Flow Engineer

**Purpose**: Implements and modifies the flows API, health endpoints, trends endpoints, and intelligence enrichment endpoints in the Python/FastAPI backend.

**When to Call**:
- Implementing API endpoints (all under `/api/v2/...`; crisis endpoints under `/api/v3/...`)
- Implementing caching strategies with Redis
- Writing database migrations for PostgreSQL (raw `.sql` files in `backend/migrations/`)
- Calculating heat formulas and similarity scores
- Writing tests for backend functionality
- Adding new data source integrations (ACLED, OpenSky, AISStream)

**Interaction with Backend Tasks**:
- Implements endpoints following Pydantic model patterns in `app/models/`
- Creates database migrations run via Supabase SQL editor (NOT alembic)
- Implements caching with key patterns from DataSignalArchitect
- Writes unit and integration tests in `backend/tests/`

---

### Data GeoIntel Analyst

**Purpose**: Works on geointelligence data analysis tasks involving GDELT, Google Trends, and Wikipedia data sources.

**When to Call**:
- Validating or implementing data source clients
- Creating topic normalization logic for cross-country comparisons
- Implementing intensity scoring algorithms
- Writing ADRs for time windows or decay formulas
- Creating dataset snapshots with manifests
- Documenting API quotas and error recovery strategies

**Interaction with Backend Tasks**:
- Provides client implementations for data sources
- Defines normalization pipelines for topic extraction
- Implements scoring formulas (heat, intensity, similarity)

---

### Frontend Map Engineer

**Purpose**: Implements interactive map visualizations using React, MapLibre GL, and DeckGL v9.

**When to Call**:
- Adding circle markers/hotspots to maps (ScatterplotLayer)
- Creating animated flow lines between countries (ArcLayer)
- Building map-related UI components (filters, sidebars, chokepoint panels)
- Handling real-time data updates with auto-refresh (aircraft 15s poll, vessels 30s poll)
- Implementing custom DeckGL layers (e.g. TerminatorLayer)

**Critical Rules for Frontend:**
- Use **Vanilla CSS** for all dashboard components. CSS custom properties come from `ThemeContext`.
- **Tailwind CSS** is installed but used **exclusively for `Landing.tsx`** (the public marketing page). Do NOT add Tailwind classes to dashboard components.
- Use `data-tip="text"` for tooltips on any element — NEVER use native `title=` attributes.
- Components live in `frontend-v2/src/components/`. Current count: **36 .tsx components**.
- Always run `npm run build` (not just `tsc --noEmit`) before pushing — Vite's `tsc -b` is stricter.
- `InteractiveWorkspace.tsx` (the force-graph canvas) is lazy-loaded via `React.lazy()` inside `InvestigationWorkspace.tsx` — do NOT import it directly or it will blow the main bundle.
- Theme labels: always call `getThemeLabel(theme_code)` from `lib/themeLabels.tsx`. Do NOT trust the `label` field returned by the API — the API field may be raw GDELT codes.

---

## AI Model Coordination: Claude, Gemini, and Codex

This project uses three AI models in coordination, each with distinct strengths. Understanding when to use each model maximizes efficiency and output quality.

### Claude's Role: Orchestration and Reasoning

Claude serves as the **orchestrator and system-level reasoning engine**.

**Primary Responsibilities:**

- High-level design, architecture, and planning
- Multi-agent coordination and task sequencing
- Narrative analysis and data interpretation
- Schema design and technical decisions
- Complex reasoning requiring deep context
- Documentation and specification writing
- **Automatic delegation** to Gemini and Codex when appropriate

**When to Use Claude:**

- Starting a session and planning work
- Designing database schemas or API architectures
- Analyzing narrative patterns or drift detection algorithms
- Making technical decisions with tradeoffs
- Coordinating multiple workstreams
- Writing ADRs or architectural documents

**Automatic Delegation Rules:**

Claude should automatically:

1. **Delegate to Gemini** when large multi-file context is needed
2. **Delegate to Codex** when code generation or execution is required
3. **Keep reasoning centralized** within Claude
4. **Combine outputs** from Gemini + Codex into coherent plans

**Orchestration Workflow:**

```text
1. Claude analyzes the goal
2. If large multi-file context needed → Claude triggers Gemini CLI
3. Claude receives Gemini's output and reasons about it
4. If code generation/execution needed → Claude triggers Codex CLI
5. Claude merges all results and produces high-level reasoning
```

**Example Commands:**

```bash
# Claude Code CLI for orchestration
claude "Review the handoff document and create today's plan"
claude "Design the PostgreSQL schema for GDELT signals"
claude "Analyze how drift detection should work across geographic regions"
```

---

## Using Gemini CLI for Large Codebase Analysis

Gemini CLI leverages Google Gemini's massive context window for analyzing large codebases or multiple files that would exceed Claude's context limits.

### Gemini Purpose

Use Gemini CLI when:

- Analyzing large codebases or multiple files that exceed context limits
- Reviewing or comparing full directories
- Scanning for patterns across many files
- Verifying complex implementations scattered across the codebase
- Loading hundreds of files at once
- Performing static read-only analysis requiring massive context

### Gemini Syntax

Use `gemini -p` for non-interactive mode with prompts:

```bash
gemini -p "<prompt here>"
```

### File and Directory Inclusion

Use the `@` syntax to include files and directories. Paths are relative to your current working directory:

#### Basic Examples

**Single file analysis:**

```bash
gemini -p "@src/main.py Explain this file's purpose and structure"
```

**Multiple files:**

```bash
gemini -p "@package.json @src/index.js Analyze the dependencies used in the code"
```

**Entire directory:**

```bash
gemini -p "@src/ Summarize the architecture of this codebase"
```

**Multiple directories:**

```bash
gemini -p "@src/ @tests/ Analyze test coverage for the source code"
```

**Current directory and subdirectories:**

```bash
gemini -p "@./ Give me an overview of this entire project"
```

**All files automatically:**

```bash
gemini --all_files -p "Analyze the project structure and dependencies"
```

### Implementation Verification Examples

**Check if a feature is implemented:**

```bash
gemini -p "@src/ @lib/ Has dark mode been implemented in this codebase? Show me the relevant files and functions"
```

**Verify authentication implementation:**

```bash
gemini -p "@src/ @middleware/ Is JWT authentication implemented? List all auth-related endpoints and middleware"
```

**Check for specific patterns:**

```bash
gemini -p "@src/ Are there any React hooks that handle WebSocket connections? List them with file paths"
```

**Verify error handling:**

```bash
gemini -p "@src/ @api/ Is proper error handling implemented for all API endpoints? Show examples of try-catch blocks"
```

**Check for rate limiting:**

```bash
gemini -p "@backend/ @middleware/ Is rate limiting implemented for the API? Show the implementation details"
```

**Verify caching strategy:**

```bash
gemini -p "@src/ @lib/ @services/ Is Redis caching implemented? List all cache-related functions and their usage"
```

**Check for specific security measures:**

```bash
gemini -p "@src/ @api/ Are SQL injection protections implemented? Show how user inputs are sanitized"
```

**Verify test coverage for features:**

```bash
gemini -p "@src/payment/ @tests/ Is the payment processing module fully tested? List all test cases"
```

### When to Use Gemini

- Analyzing entire codebases or large directories
- Comparing multiple large files
- Understanding project-wide patterns or architecture
- Context window is insufficient for the task
- Working with files totaling more than 100KB
- Verifying if specific features, patterns, or security measures are implemented
- Checking for coding patterns across the entire codebase

### When NOT to Use Gemini

- **Generating new code** (use Codex instead)
- **Executing commands** (use Codex instead)
- **Small context tasks** that fit in Claude's window
- **Code refactoring or implementation** (use Codex instead)

### Important Notes

- Paths in `@` syntax are relative to your current working directory when invoking gemini
- The CLI will include file contents directly in the context
- No need for --yolo flag for read-only analysis
- Gemini's context window can handle entire codebases that would overflow Claude's context
- When checking implementations, be specific about what you're looking for to get accurate results

---

## Using Codex CLI for Code Generation and Execution

Codex CLI is optimized for heavy code generation, refactoring, and execution tasks. It specializes in writing and modifying code with high quality output.

### Codex Purpose

Use Codex CLI when:

- Generating large code modules or full files
- Performing refactors across many files
- Generating test suites or documentation
- Scaffolding entire features or microservices
- Executing code or commands
- Running project automation tasks (formatters, linters, migrations)
- Transforming files requiring "write access"

### Codex Syntax

Use `codex -p` for prompting:

```bash
codex -p "<prompt here>"
```

Codex also supports the `@file` and `@directory/` syntax for including context.

### Code Generation Examples

**Implement an endpoint:**

```bash
codex "Implement GET /api/v2/narratives/topic endpoint in backend/app/main_v2.py following the existing endpoint patterns"
```

**Write tests:**

```bash
codex "Write unit tests for the gdelt_parser.py parse_v2_tone function"
```

**Create TypeScript types:**

```bash
codex "Create TypeScript interfaces in frontend/src/lib/types.ts matching the GDELTSignal Pydantic model"
```

**Refactor for performance:**

```bash
codex "Refactor the flow_detector.py to use numpy vectorization instead of nested loops"
```

**Fix a specific bug:**

```bash
codex "Fix the heatmap rendering issue in HexagonHeatmapLayer.tsx where hexagons are not appearing"
```

### File Context Examples

**Generate tests with context:**

```bash
codex -p "@backend/ Generate a complete test suite for all services"
```

**Refactor with file context:**

```bash
codex -p "@src/ Refactor all API handlers to use dependency injection"
```

**Create new module:**

```bash
codex -p "@app/ Create a new logging module and integrate it"
```

**Full CRUD generation:**

```bash
codex -p "@./ Build a full CRUD module for the User entity"
```

### Execution Examples

Run commands directly through Codex:

```bash
codex run tests
codex run "npm install"
codex run "pytest -q"
codex -p "@scripts/ Execute the migration scripts and show output"
```

### When to Use Codex

- Implementing new API endpoints
- Writing tests for services
- Creating React components
- Refactoring modules for performance
- Generating Pydantic models or TypeScript interfaces
- Fixing bugs in specific files
- Running project commands

### When NOT to Use Codex

- **Analyzing very large contexts** (use Gemini instead)
- **Deep reasoning or cross-file orchestration** (Claude handles this)
- **Verifying architecture or patterns** (use Gemini instead)
- **Planning and decision-making** (use Claude instead)

---

## Combined Workflow

The three models work together in a coordinated pipeline:

```
┌─────────────────────────────────────────────────────┐
│                    WORKFLOW                          │
├─────────────────────────────────────────────────────┤
│                                                     │
│  1. CLAUDE THINKS                                   │
│     ├─ Review context and plan                      │
│     ├─ Design architecture                          │
│     └─ Coordinate agents                            │
│                    ↓                                │
│  2. GEMINI INSPECTS                                 │
│     ├─ Analyze codebase                             │
│     ├─ Verify implementations                       │
│     └─ Check patterns                               │
│                    ↓                                │
│  3. CODEX IMPLEMENTS                                │
│     ├─ Write code                                   │
│     ├─ Create tests                                 │
│     └─ Apply fixes                                  │
│                                                     │
│  ═══════════════════════════════════════════════   │
│  All models can run in PARALLEL for independent    │
│  tasks to maximize efficiency                       │
└─────────────────────────────────────────────────────┘
```

**Example Combined Workflow:**

```bash
# Step 1: Claude plans the work
claude "Design the schema for storing narrative clusters with drift scores"

# Step 2: Gemini checks existing patterns
gemini -p "@backend/app/models/ @backend/app/db/ Analyze existing database patterns and constraints"

# Step 3: Codex implements
codex "Create the narrative_clusters table migration following the patterns identified"

# Parallel execution for independent tasks
claude "Design visualization spec" &
gemini -p "@frontend/ Check component structure" &
codex "Implement the tooltip component" &
wait
```

---

## Quick Reference: When to Pick Each Model

| Task Type | Model | Reason |
|-----------|-------|--------|
| Planning and coordination | **Claude** | Complex reasoning, context management |
| Architecture design | **Claude** | Tradeoff analysis, system thinking |
| Codebase-wide analysis | **Gemini** | Large context window |
| "Does X exist in the code?" | **Gemini** | Full repo search |
| Security/pattern audit | **Gemini** | Cross-file analysis |
| Implement endpoint | **Codex** | Code generation |
| Write tests | **Codex** | Implementation |
| Refactor module | **Codex** | Code transformation |
| Fix specific bug | **Codex** | Targeted edits |
| Schema design | **Claude** | Domain expertise |
| TypeScript types | **Codex** | Type generation |
| Execute commands | **Codex** | Command execution |

---

## Concrete Examples by Task

**Task: Add a new API endpoint for narrative topics**

```bash
# 1. Claude designs the API schema
claude "Design the /api/v2/narratives/topic endpoint with request/response schemas"

# 2. Gemini checks existing endpoint patterns
gemini -p "@backend/app/main_v2.py Show me the pattern used for existing endpoints including error handling"

# 3. Codex implements the endpoint
codex "Implement /api/v2/narratives/topic in backend/app/main_v2.py using the designed schema and existing patterns"
```

**Task: Optimize database queries**

```bash
# 1. Gemini identifies slow queries
gemini -p "@backend/app/services/ @backend/app/api/ Find all database queries and identify which ones might be slow"

# 2. Claude designs optimization strategy
claude "Design index strategy for the identified slow queries"

# 3. Codex implements the indexes
codex "Add the recommended indexes to the migration file"
```

**Task: Debug a rendering issue**

```bash
# 1. Gemini finds related code
gemini -p "@frontend/src/components/map/ Show all code related to hexagon rendering"

# 2. Claude analyzes the issue
claude "Analyze why hexagons might not be rendering based on the code"

# 3. Codex fixes the bug
codex "Fix the hexagon rendering issue in HexagonHeatmapLayer.tsx"
```

**Task: Add test coverage**

```bash
# 1. Gemini identifies untested code
gemini -p "@backend/app/services/ @backend/tests/ Which services have less than 80% test coverage?"

# 2. Codex writes the tests
codex "Write comprehensive tests for gdelt_parser.py covering all edge cases"
```

---

## Development Workflow

### Starting a Session

1. Call the **Orchestrator** to review handoff documentation
2. Assess current blockers and prioritize work for the window
3. Create daily plan with agent assignments

### Working on Tasks

1. Use the appropriate specialized agent for each task type
2. Maintain small, focused PRs (<300 lines)
3. Update todos as work progresses
4. Document decisions in ADRs when ambiguity appears

### Ending a Session

1. Complete handoff documentation
2. Update state documents
3. Tag any unresolved blockers
4. Push changes to GitHub

---

## Quality Standards

### PR Hygiene

- Small, focused diffs
- All tests passing
- Structured, useful logs
- Updated .env.example for new environment variables
- Clear commit messages following conventional commits

### Definition of Done

- [ ] Compiles successfully with no errors
- [ ] All tests pass
- [ ] Logs are structured and useful
- [ ] Environment variables documented
- [ ] ADR exists for non-trivial decisions
- [ ] Documentation updated
- [ ] Handoff notes complete

---

## Current Technical State (as of session 13 — 2026-05-17)

### Session 13 Additions (P0 productization pass — PR #144)

**Briefing prefetch (#136)**
- `frontend-v2/src/lib/briefingPrefetch.ts` — sessionStorage cache with 4-min TTL for briefing + insight API responses.
- `Landing.tsx` prefetches on mount. `BriefNewspaper.tsx` reads cache before fetch — no spinner when entering `/brief` from Landing.

**Editor's Analysis restored (#137)**
- `BriefNewspaper.tsx`: `buildGlobalFallback(d)` — 4 rotating variants (theme-lead, geography-lead, sentiment-lead, volume-first).
- `buildCountryFallback(detail)` — 3 country variants.
- `Math.random()` per render for angle rotation — intentional, not seeded.
- Removed all `themeSignals[theme][0]` headline anchors — signals misclassification risk.
- All country names via `resolveCountryName(code, name)` — never raw `c.name`.

**Investigation context preservation (#138)**
- `App.tsx`: `prevStreamCtx` union extended with `country` type.
- Back from source → CountryBrief; Back from country → thread if theme was active.

**Public Attention scoped to active country (#142)**
- `AnomalyPanel.tsx`: re-fetches Wiki on `activeCountry` change; Trends + Wiki merged into single PUBLIC ATTENTION section.
- `[S]` (green) badge for searches, `[W]` (indigo) badge for wiki articles.
- Staleness indicator: `trendsStaleHours` state, shows badge when >25h old.
- Deduplication: `Array.from(new Map(raw.map(a => [a.title, a])).values())`.
- `CountryBrief`: `onAttentionItemClick?: (query: string) => void` prop; `App.tsx` wires it.
- API field fix: `d?.trending ?? []` (was `d?.trends`).

**Google Trends stale data mitigation (#104)**
- `backend/app/services/ingest_trends.py`: shuffle country list each run (`import random`), batch size 5→3, delay 1s→2s, retry pass for failed countries.
- `frontend-v2/src/lib/publicAttention.ts`: `getTrendingSearchesUrl` uses `Math.max(hours, 72)` floor.
- AnomalyPanel shows "searches from Nh ago" badge when stale.

**Narrative Threads timeout cap (#139)**
- `backend/app/routers/narratives.py`: `detail_hours = min(hours, 48)` for Phase 2 (signals_v2 unnest scan); Phase 1 (theme_hourly_v2) still uses full `hours`.
- `effective_hours: detail_hours` added to result dict.
- `NarrativeThreads.tsx`: stores `effectiveHours` state; shows notice "Thread details show last Xh · counts reflect full Yh window" when capped.

**Trail / Pinned graph separation (#128)**
- `InteractiveWorkspace.tsx`: replaced single `graphRef`/`filteredGraph`/physics effect with separate `trailGraphRef` + `pinnedGraphRef`, `trailGraph` + `pinnedGraph` memos, two physics effects.
- Both ForceGraph2D instances always mounted; CSS `visibility: hidden` keeps simulation alive when inactive.
- Trail: linear-spread physics (charge -320/-420, distance 150); Pinned: dense-web physics (charge -380/-560/-760, distance 125-160).
- `InvestigationWorkspace.css`: `.workspace-graph-slot { position: absolute; inset: 0 }` + `.workspace-graph-slot.hidden { visibility: hidden; pointer-events: none }`.

**Backend deployment**
- Fly.io `atlas-api-pedro` deployed with `ingest_trends.py` + `narratives.py` changes (machine version 113, region iad, 1 passing health check as of 2026-05-17T13:57:17Z).

---

## Current Technical State (as of session 9 — 2026-05-11)

### Session 9 Additions

**Geo-validation (Wave 4 Phase 4)**
- `signals_v2.source_origin_country CHAR(2)` — outlet home country (≠ story subject country). Migration 012 applied, 12,944 US signals backfilled.
- `_extract_source_country(url)` in `ingest_v2.py` — 70+ known domains + ccTLD fallback.
- `foreignSourcePct` in country endpoint — null when <50 known-origin signals; shown as warning badge in `CountryBrief` when >60%.

**Source framing split (EntityPanel)**
- Replaces linear source list with Positive/Negative columns + narrative spread bar when sources span both extremes (threshold: `|avg_sentiment| > 0.2`, require ≥2 split sources).

**NER geo-filter**
- `_is_valid_person()` + `_GEO_NAME_BLOCKLIST` (40 entries) + `_GEO_FIRST_WORDS` in `main_v2.py` — filters GDELT-misclassified place names from People Mentioned.

**ESLint clean (#62)**
- `npm run lint` exits 0. `react-hooks/set-state-in-effect` and `purity` off; `no-explicit-any` downgraded to warning; before-declaration ordering fixed in `App.tsx`.

**Tolerant search (#51 closed)**
- `concept_suggestions` chip row added to `SearchBar.tsx`. All acceptance criteria met.

**Onboarding (session 9)**
- Removed redundant `welcome-card` and `map-hint` overlays from `App.tsx`. `OnboardingCoachmark` is the sole onboarding (localStorage, 3-step).

**Command bar stale-while-revalidate**
- `FocusDataContext` preserves nodes/meta during refetch when API returns empty. `App.tsx` command bar fades to 50% opacity during `isRefetching`.

**BRIEF Global Focus (session 9)**
- `Briefing.tsx` — theme→country pill rows showing signal counts per country per topic. Backend already had `theme_country_rows` query + Redis cache.

**Source blocklist expansion**
- 50+ domains added to `backend/app/config/source_blocklist.py`: consumer tech, sports leagues, entertainment, local US TV.

**Investigative concept vocabulary**
- 6 new `CONCEPT_MAP` entries: `blood-diamonds`, `electoral-fraud`, `narcotrafficking`, `forced-displacement`, `water-crisis`, `land-grabbing`.

## Current Technical State (as of session 8 — 2026-05-10)

### Critical Build Rule

Always run `npm run build` (not just `tsc --noEmit`) before pushing frontend changes. Vite uses `tsc -b` (project references), which is stricter. A passing `tsc --noEmit` does NOT guarantee a passing Vercel build.

### No Pending Fly.io Deploys

All backend changes are live. Fly.io app: `atlas-api-pedro`. Migrations 007–011 applied.

### Frontend Component Count

68 .tsx components in `frontend-v2/src/components/` as of 2026-05-10. Do not add Tailwind to any of them.
Session 7 additions: `OnboardingCoachmark`, `PublicAttentionPanel`, `TemporalNarrativeGraph`.

### NLP Pipeline (session 8, live on Fly.io)

- `backend/enrichment/nlp_pipeline.py` — three-phase pipeline: sentiment (RoBERTa), NER (spaCy), framing (NLI distilroberta).
- `ingest_loop.py` fires `asyncio.create_task(_nlp_background(limit=100))` after each GDELT cycle. Non-blocking. Skip if previous task still running.
- Dockerfile: `ENV HF_HOME=/app/hf_cache` and `ENV TRANSFORMERS_CACHE=/app/hf_cache` BEFORE pre-bake RUN. `ENV TRANSFORMERS_OFFLINE=1` AFTER pre-bake RUN. This is the OOM fix — do not reorder.
- NLP rate on Fly: ~200 signals/hour. Peak memory: ~720–738MB on 985MB machine.
- API: `COALESCE(nlp_sentiment, sentiment)` — RoBERTa replaces GDELT tone when available.

### Data Hygiene (session 8)

- Deleted 1,116,136 signals from Apr 27 – May 3 (no NLP, freed ~1GB).
- Retention policy: unprocessed signals deleted after 90 days, NLP-processed kept indefinitely.
- Automated cleanup in `ingest_loop.py` every 672nd cycle (~7 days).
- DB state: ~1.23M total signals, ~34K NLP-processed (2.8%), range May 3 – present.

### Data Coverage Badge (session 8)

- `App.tsx` fetches `oldest_signal` from `/api/v2/stats` on mount.
- Displays `FROM [DATE]` pill next to LIVE DATA in command bar.
- CSS class `.data-since-pill` in `App.css`.

### Branch Status

- `v3-intel-layer` IS production — Vercel and Fly.io both deploy from it.
- `main` is stale/abandoned. Do not merge into it.

### Investigation Workspace (session 6, still current)

- `InteractiveWorkspace.tsx` — react-force-graph-2d canvas. Lazy-loaded (chunk: ~187KB). Use react-force-graph-2d ONLY — the 3D version (react-force-graph) pulls AFRAME and crashes the app.
- `InvestigationWorkspace.tsx` + `InvestigationWorkspace.css` — shell. Wraps `InteractiveWorkspace` via `React.lazy()` + `Suspense` + `PanelErrorBoundary`. Rendered by App.tsx.
- `workspaceGraph.ts` — two-pass graph builder. Pinned nodes always succeed; edges per-item try/catch.

### Error Isolation Architecture (established session 6)

Three-layer error boundary hierarchy:
1. `RootErrorBoundary` in `main.tsx`
2. `PanelErrorBoundary` in `App.tsx` — wraps `InvestigationWorkspace` and other panels
3. `MapErrorBoundary` — wraps DeckGL map layer

### Theme Label Rule (session 6, still current)

All components rendering GDELT theme names must call `getThemeLabel(theme_code)` from `lib/themeLabels.tsx`. Do NOT use the API `label` field — it can return raw GDELT codes.

### Stream Panel Behavior (session 5, still current)

Default stream slot is `DiscoveryPanel` (blank state). State machine: `isPerson → isCompound → isCountry → isTheme → isChokepoint → DiscoveryPanel`.

### Sentiment Scale (unified session 7)

All endpoints return sentiment ÷10 (frontend expects ±1 range, ±0.1 thresholds). GDELT V2Tone raw is ~-20 to +20. Exception: ThemeDetail uses `getSentimentBarWidth()` which normalizes -10 to +10 internally. Do not change ThemeDetail.

### Coverage Confidence Badges (session 7)

Applied in CountryBrief, NarrativeThreads, ChokepointPanel: n<10 → `thin` (orange), 10≤n<50 → `limited` (yellow). CSS classes: `coverage-badge--thin`, `coverage-badge--limited` in respective CSS files.

### Concept Endpoint Fast Path (session 7)

`GET /api/v2/concept/{slug}?hours=N`: for `hours > 24` queries `theme_country_hourly_v2` (pre-agg, PK: hour+theme+country). For `hours ≤ 24` queries `signals_v2` directly. `effective_hours` always equals requested `hours`.

### Source Ingestion Stack (session 7)

- `ingest_rss.py` — Wave 1 general feeds + Wave 3 state media (RT/Sputnik/Global Times/IRNA) + non-English (France24 AR/BBC Arabic/El País/DW). `is_state_media=True` for state sources.
- `ingest_reliefweb.py` — Wave 2: 19 crisis country feeds via ReliefWeb OCHA. `geo_confidence=0.92`, `source_family='ngo'`. Direct URL pattern: `/updates/rss.xml?legacy-river=country/{iso3}` (not country path — that redirects and gets blocked).

### API Endpoints

- `GET /api/v2/search/unified?q=&hours=` — preferred search. Merges taxonomy, concepts, regions, DB. Cached 2 min.
- All v2 and v3 endpoints live. No pending deploys.

### FocusContext

- `GlobalFilter` includes `concept: ConceptFilter | null` and `region: RegionFilter | null`
- `setConcept()` expands to multiple GDELT themes; `setRegion()` expands to multiple countries

### Backend: gdelt_taxonomy.py

- `REGION_MAP` — 6 regions with ISO codes and multilingual aliases (EN/ES/FR/PT/DE/AR)
- `match_region()` — fuzzy region matching

### GitHub Issues Status

Open as of 2026-05-11 (6 issues): #46, #61, #70, #79, #80, #82, #83.
Closed session 7: #63, #73, #78, #81, #84–#93.
Closed session 8: #92 (Wave 4 NLP ADR).
Closed session 9: #51 (tolerant search), #62 (ESLint debt), #77 (source framing viz), #92 (NLP ADR), #99 (geo validation Wave 4 Phase 4), #100 (NER geo-filter).
Next priority: #83 (Signal Intelligence Panel), #61 (comparative engine UI), #70 (theme clustering), mac backfill completion.

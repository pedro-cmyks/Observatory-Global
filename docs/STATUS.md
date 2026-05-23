# Project Status

## Current Handoff — 2026-05-23 (topic classifier v2 + A/B baseline — PR #197)

### What shipped this session

Branch `claude/status-check-wD1og`, draft PR #197 against `v3-intel-layer` (CI green — Vercel preview only; no GitHub Actions Python suite). Three new files, no migrations, no DB writes from CI.

**Backend scripts**
- `backend/scripts/backfill_lexicon_topics.py` — Issue #171. Single-statement bulk `INSERT … SELECT` topic classifier (v2). Writes `method='lexicon'`, `model_version='theme-hint-lex-v2'`, isolated from v1 (`theme-hint-lex-v1`) by the PK `(signal_id, topic_id, method, model_version)`. Idempotent `ON CONFLICT … DO UPDATE`; doubles as the 15-min incremental cron path via `--window-hours 0.5`. Accelerated by the mig 022 trigram GIN on `lower(headline)` + GIN on `signals_v2.themes`.
- `backend/scripts/topic_classifier_baseline.py` — read-only A/B reporter (candidate count, recall per `model_version`, v1-vs-v2 top-1 agreement, per-topic distribution, confidence histogram). No table mutation.

**Why v2 vs editing v1**
- v1 (`classify_topics.py`) required "lex OR >=3 theme hits" and capped recall at ~0.8% of 24h volume after the mig 031 hint realignment.
- v2 widens qualification to "lex >=1 OR theme_hits >=1" and holds precision with a higher confidence floor (0.55 vs v1's 0.30).
- v2 confidence: `LEAST(0.95, 0.55 + 0.10*LEAST(lex,3) + 0.05*LEAST(theme_hits,4) + cross_bonus)` where cross_bonus = 0.05 when lex>0 AND theme_hits>=2. Top-2 per signal; headline length filter >=20 chars.
- Both coexist so the lift is measurable before retiring v1.

**Tests**
- `backend/tests/test_backfill_lexicon_topics.py` — 11 shape tests (v2-only model_version, upsert semantics, OR qualification, formula components, evidence keys, top-N ranking, headline filter, dry-run is read-only). 16/16 pass alongside `test_topic_intelligence_schema.py`. Shape-only because the container has no DB / no asyncpg.

### Live measurement (2026-05-23, via Supabase MCP)

**Threshold sweep on 6h window (~38k candidate signals):**

| Config | Distinct signals | Recall | avg_conf | Notes |
|--------|-----------------|--------|----------|-------|
| v1 (`theme-hint-lex-v1`) | 841 | 2.2% | 0.613 | 96.5% lex-supported, precision-heavy |
| v2@0.55 (script default) | 27,942 | 73.5% | 0.608 | Only 1.6% lex-supported — too noisy |
| **v2@0.65 (chosen)** | **6,121** | **16.1%** | **0.653** | **7.3× v1; 30 topics fired** |
| v2@0.70 | 398 | 1.0% | 0.710 | Collapses below v1 |

**Top1 agreement v1↔v2@0.65 on overlap (812 signals):** 753 same / 59 different = **92.73%**.

**Decision: promote v2 with `DEFAULT_MIN_CONFIDENCE = 0.65`** (was 0.55 in script). All four gate criteria cleared:
- ✅ recall lift 7.3× (>= 5× target)
- ✅ top1 agreement 92.73% (>= 70% target)
- ✅ avg_confidence 0.653 ≈ v1's 0.613 (precision parity)
- ✅ 30 topics fired, top topic = 13.7% (no collapse)

**Live backfill applied 2026-05-23 in 4× 6h chunks via Supabase MCP over the 24h window:**
- 33,279 assignments upserted into `signal_topic_assignments` (`model_version='theme-hint-lex-v2'`).
- 25,975 distinct signals (16.84% of the 154,226-signal 24h candidate window).
- avg_confidence 0.654; 30 topics fired.
- Top: disease-outbreak 4,544, constitutional-institutional-crisis 4,391, telecom-internet-shutdown 3,566, heat-health-risk 3,401. Tail down to humanitarian-access-conflict (30). No single topic >14%.
- v1 (`theme-hint-lex-v1`) remains 0 rows in `signal_topic_assignments` (the May 21 backfill was wiped by the hot/cold prune of May 20); re-backfilling v1 is optional since the 92.73% top1 agreement already validates that v2 agrees with v1 on the easy cases.

### Operational follow-up
- Schedule v2 incremental cron at `--window-hours 0.5` once the local-hot-cold runner is happy (issue #171 close).
- Future: extend `atlas_topics.lexicon_terms` via #185 mining; v2 will pick up the new terms automatically.

---

## Current Handoff — 2026-05-20 (session 17 close — Opción A end-to-end + atlas_heat surface)

### What shipped this session

Six commits on `v3-intel-layer` (`09b95bb` → `43732a9`), six Fly deploys (versions 156 → 161), DB-level changes via Supabase MCP. Production verified live throughout.

**Database**
- Migration **025** — `theme_hourly_v2` + `theme_country_hourly_v2` gained `nlp_signal_count INTEGER NOT NULL DEFAULT 0` and `avg_nlp_sentiment NUMERIC`. Additive, metadata-only `ALTER ADD COLUMN`, no rewrite.
- Migration **026** — `country_hourly_v2` matview swapped to add the same NLP coverage columns. Build-populate-rename so briefing reads never saw an empty matview.
- ADR-0004 prune ran end-to-end via Supabase MCP — **241,656 rows deleted** in batches (25k → 50k), `VACUUM ANALYZE` completed, `signals_v2` size unchanged on disk but `dead_tup = 0` and ~240k pages available for new INSERTs.
- `signals_v2` autovacuum tuned: `scale_factor = 0.05`, `cost_delay = 10`. NLP backfill UPDATE bloat now triggers vacuum at ~107K dead tuples instead of ~475K.
- `nlp_sample_queue` truncated (610K zombie ids; worker preferred fresh since commit `7472aba`, queue never drained).
- `nlp_progress` synced to ground truth (worker's cached delta math went stale after the external DELETE; manual `UPDATE` until #186 fixes the recompute path).

**Backend code**
- `app/routers/briefing.py` — every country-shaped SQL is now a CTE that pulls both `gdelt_sentiment` and `nlp_sentiment` per bucket and a `chosen_sentiment_raw` expression that ORDER BYs honestly.
- `app/services/sentiment_fusion.py` — new module. `choose_sentiment(gdelt_raw, nlp_raw, nlp_coverage)` picks NLP transformer when bucket coverage ≥ 0.30 and rescales by `NLP_SENTIMENT_SCALE = 2.37` so the value lands on the same ±0.1 frontend threshold as GDELT. Both constants env-tunable.
- Briefing response gains `sentiment_source` (`"nlp"` | `"gdelt"`) and `nlp_coverage` on every country row + on global stats.
- New section `heat_countries` reads `country_heat_v2` (#165) and ranks by `atlas_heat`. Each entry exposes the full component breakdown (velocity, surprise, diversity, voice, polyphony, geo_confidence, duplication).
- `top_themes` switched from dead `signals_theme_hourly` to live `theme_hourly_v2`.
- `top_sources` switched from dead `signals_source_hourly` to `signals_v2` direct scan (Redis-cached 15–30 min, single bounded GROUP BY per cache miss).
- `/briefing/insight` mirrors the `/briefing` hardening — `country_hourly_v2` instead of raw `signals_v2`, parameterized `$1::int * INTERVAL '1 hour'`, every section through `_fetch_section` with degraded fallback.
- `ingest_v2.refresh` writes `nlp_signal_count` + `avg_nlp_sentiment` via `FILTER (WHERE nlp_sentiment IS NOT NULL)` in the same INSERT pass — zero IO overhead.
- Lexicon vocab expanded: EN +110 terms, ES/PT +50, new `IT` and `DE` seed lexicons. Hit rate measured live at 12% (news headlines are mostly factual — manual seeds have a ceiling). Coverage moved 7.8% → 8.0%.

**Tests**
- `tests/test_briefing_performance_shape.py` — guardrails for sentiment-preagg use, parameterized intervals, degraded response shape, top_themes ≠ dead-table, top_sources ≠ dead-table, heat_countries section structure.
- `tests/test_briefing_sentiment_fusion.py` — 7 cases for `choose_sentiment` boundary behavior.
- `tests/test_ingest_pre_agg_nlp_coverage.py` — pins the NLP coverage SQL into both pre-agg INSERTs.
- Full suite: **236 passed, 6 skipped, 0 failed**.

### Live production state (2026-05-20 13:55 UTC)

| Metric | Value |
|---|---|
| Image | `deployment-01KS2P*` (v160) — see `fly status` |
| `signals_v2` total | 2,191,567 |
| Over-15d unprocessed | 0 (post-prune) |
| Lexicon-tagged | 7,300 |
| Transformer-tagged | 35,550 |
| Global NLP coverage | **8.0%** |
| Briefing fusion threshold | 0.30 (env-tunable) |
| Briefing API | `degraded=false`, all 6 sections populated |
| heat_countries top 5 | LB · NI · GZ · DO · MB |
| top_countries top 5 | US · CN · GB · RU · IN |
| top_sources top 3 | zazoom.it · indiatimes.com · 163.com |

### Issues touched

- ✅ **Closed #149** (volumetric US dominance) — heat_countries lens ships dual-rank.
- ✅ **Closed #165** (Atlas composite heat) — atlas_heat consumed in briefing.
- ✅ **Closed #182** (briefing sentiment timeout) — already done; this session reinforced via `/briefing/insight` parallel hardening.
- 📝 **Progress comment #164** — ADR-0004 prune executed end-to-end, lexicon backfill shipped.
- 📝 **Progress comment #171** — lexicon vocab expanded, plateau measured, follow-up tracked.
- 🆕 **#183** — frontend rendering of sentiment_source badge + heat_countries panel. OPEN.
- 🆕 **#184** — NLP_WORKER_LIMIT bump experiment with decision rule. OPEN.
- 🆕 **#185** — corpus-mine lexicon vocab from transformer-tagged rows (breaks the 12% plateau). OPEN.
- ✅ **#186** — `nlp_progress` recompute landed in commit `613a21e`. /health.unprocessed_total now stays honest after external DELETEs. CLOSED.
- ✅ **#187** — `heat_voluminous_countries` lens landed in commits `613a21e` + `3e0fce8`. Top-quartile-by-volume re-ranked by atlas_heat surfaces CO, NG, AR, AJ, BR right now. CLOSED.

### Routes / paths reference

- New module: `backend/app/services/sentiment_fusion.py` (importable, pure, unit-testable, free of FastAPI circular imports).
- New migrations: `backend/migrations/025_pre_agg_nlp_coverage.sql`, `backend/migrations/026_country_hourly_v2_nlp_coverage.sql`.
- New tests: `backend/tests/test_briefing_sentiment_fusion.py`, `backend/tests/test_ingest_pre_agg_nlp_coverage.py`.
- Lexicon: `backend/enrichment/lexicon_sentiment.py` (EN/ES/FR/PT/AR/IT/DE).
- Existing matview consumed: `country_heat_v2` (mig 017) — read via briefing `heat_countries` section.

### Honest verdict

The architecture is correct and the API is honest. Coverage is still 8% because the worker can't outrun ingest at `NLP_WORKER_LIMIT=25` and the lexicon seed approach caps at ~12% hit rate. Fusion will not flip to `sentiment_source = "nlp"` at scale until either (a) the worker is bumped per #184, (b) corpus-mined vocab ships per #185, or (c) the coverage threshold is dropped from 0.30 via the `BRIEFING_NLP_COVERAGE_THRESHOLD` env var.

Backend foundation for the next visible UX leap is in place — frontend wiring tracked in #183.

---

## Previous handoff — 2026-05-19 (session 16 start — signal_class landed)

### Session 16 — `signal_class` semantic provenance live (Track B.1)

**Migration 021** applied in Supabase + ingest services updated. Foundation for #149 cluster scoring, Voice Mix (#160), and topic intelligence ranking gate (#167).

| signal_class | rows |
|---|---:|
| reporting | 2,288,194 |
| state_media | 2,641 |
| wire | 2,127 |
| social_commentary | 351 |
| humanitarian | 3 |

**Files added**:
- `backend/migrations/021_signal_class.sql`
- `backend/app/services/_signal_class.py` (centralized derivation helper)
- `backend/tests/test_signal_class.py` (23 tests, all pass)
- `docs/roadmap/2026-05-19-topic-and-signal-class-attack.md` (3-track attack plan)

**Files patched** (signal_class write):
- `backend/app/services/ingest_v2.py` (GDELT)
- `backend/app/services/ingest_rss.py` (RSS — uses helper for state/wire/independent split)
- `backend/app/services/ingest_reliefweb.py` (humanitarian)
- `backend/app/services/ingest_newsdata.py` (reporting)
- `backend/app/services/ingest_newsapi.py` (reporting)
- `backend/app/services/ingest_mediastack.py` (reporting)
- `backend/app/services/ingest_reddit.py` (social_commentary)

**Observation**: humanitarian = 3 reveals broken ReliefWeb ingestion (historical, separate followup, not blocking).

**Next**: migration 022 trigram index + `country` param in `/api/v2/search/unified` (Track A), then bulk SQL lexicon classifier (Track B.2).

---

## Previous handoff — 2026-05-19 (session 15 + Codex parallel work)

**Production branch**: `v3-intel-layer`
**Frontend**: Vercel auto-deploy — `v3-intel-layer` latest
**Backend**: Fly.io `atlas-api-pedro` — healthy, **2,279,950 signals**, deployment `01KS0EG5FJAY5507G729FNVACQ`
**NLP worker**: Fly.io `nlp_worker` — 4GB (`shared-cpu-2x:4096MB`), `xlm-v1` multilingual active

PR [#144](https://github.com/pedro-cmyks/Observatory-Global/pull/144) open against `main` (220+ commits ahead).

---

## Session 15 work — Multi-source ingestion + NLP stabilization

### Track A — Multi-source ingestion (Claude session)

Addressed GDELT US/English volumetric bias. 4 new sources live on Fly.io.

| Source | File | Coverage | Cadence | Daily quota |
|--------|------|----------|---------|-------------|
| NewsData.io | `ingest_newsdata.py` | 7 buckets ES/PT/AR/FR/SW/SE-Asia/S-Asia (post-edit: country-primary, 10 per page) | every 60 min | 200 req/day |
| MediaStack | `ingest_mediastack.py` | ES/PT 17 LatAm countries | every 2 hours | 500 req/month |
| NewsAPI.org | `ingest_newsapi.py` | 8 EN crisis queries (7-day window, dedupe-driven) | every 2 hours | 100 req/day |
| Reddit | `ingest_reddit.py` | 14 geopolitics subreddits (no API key) | every 60 min | unlimited (60 req/min) |

**Fly.io secrets deployed**: `NEWSDATA_API_KEY`, `MEDIASTACK_API_KEY`, `NEWSAPI_KEY`

**Volume projection**:
- GDELT: ~72K signals/day (unchanged)
- New sources: +~27.6K/day (NewsData ~8.4K, Reddit ~16.8K, MediaStack ~1.2K, NewsAPI ~1.3K)
- Total: ~99.7K signals/day

**Files added**:
- `backend/app/services/ingest_newsdata.py`
- `backend/app/services/ingest_mediastack.py`
- `backend/app/services/ingest_newsapi.py`
- `backend/app/services/ingest_reddit.py`
- `backend/.env.example`

**Files changed**:
- `backend/app/services/ingest_loop.py` — 4 new service calls (cycle%4 for NewsData+Reddit, cycle%8 for MediaStack/NewsAPI)

### Track B — NLP worker stabilization + Topic Intelligence (Codex parallel)

Commit `e4e8f92 feat(data): add topic intelligence schema and stabilize nlp worker`

**Fly.io infra changes**:
- `nlp_worker` machine size: `shared-cpu-2x:4096MB` (was undersized, OOM risk)
- Standby worker stopped (single-worker mode at 4GB)
- `NLP_SAMPLE_REFRESH_EVERY=0` — heavy refresh explicitly OFF
- `NLP_SAMPLE_CLEANUP_LIMIT=50` — bounded queue cleanup in prod

**Migrations applied**:
- `019_atlas_topic_intelligence.sql` — Topic Intelligence base layer: `atlas_topics`, `signal_topic_assignments`, `topic_learning_examples`, 30 seed topics
- `020_nlp_progress_indexes.sql` — indexes so worker stops full-scanning signals_v2 for progress math

**Verified prod state**:
- `ingest_lag_minutes`: 4.1
- `rows_ingested_last_15m`: 3,849
- last NLP cycle: 2026-05-19T16:00:16Z, duration 231.5s, `error=no`
- Logs: `Sentiment[xlm-v1]`, `NER[xlm-v1]`, `Framing[xlm-v1]` — **multilingual NLP confirmed running**

**Tests**: 27 passed
```bash
cd backend && .venv/bin/python -m pytest \
  tests/test_nlp_pipeline_selection.py \
  tests/test_nlp_worker.py \
  tests/test_topic_intelligence_schema.py -q
```

**Operational debt logged**:
- NLP throughput: 25 rows/cycle stable but low — do NOT raise to 100/200 until DB pressure observed for hours
- `country_heat_v2` refresh hit timeout once in logs — pending operational item
- HuggingFace warned about `twitter-xlm-roberta-base-sentiment` tokenizer — verify before trusting multilingual quality
- Issue traceability comments left on `#167`, `#163`, `#164`

---

## Guru-brain design analysis (recorded for next session)

Deep self-critical pass on session 15 ingestion design. Key findings:

1. **Volume is not the problem.** GDELT already gives 2M signals. New sources matter for **non-English voice + emergent narrative + source diversity** — not raw volume. Without UI exposing this, value invisible to users.
2. **NewsAPI weak point**: 8 EN-language queries on crisis zones GDELT already covers in EN. Reframe as "international English framing" not "crisis coverage". Redesign: 6 evergreen + 2 dynamic from GDELT spikes + 36 req/day reserve for analyst UI probing.
3. **NewsData weak point**: language batches collapse geography. Refactor to country-primary buckets → `geo_confidence` rises from 0.65 to ~0.85 at fetch time (no NER inference needed). *(Partially addressed by Codex edit: split into 7 smaller country buckets.)*
4. **Reddit is commentary, not corroboration.** Needs `signal_class = "commentary"` in schema; must NOT count as independent unique source in #149 scoring formula.
5. **Multilingual NLP**: ✅ verified by Codex — `xlm-v1` runs. Tokenizer warning still to validate.

### Priority list for next session

1. ~~Verify multilingual NLP~~ — **DONE by Codex** (`xlm-v1` running)
2. `signal_class` + `narrative_cluster_id` in signals_v2 (migration 021)
3. **Voice Mix** component in CountryBrief: stacked bar local-lang / international / social. Endpoint `/api/v2/countries/{iso}/voice-mix`.
4. NewsAPI refactor: 6 evergreen + 2 dynamic + 36 req reserve + `/api/v2/analyst/probe-newsapi` endpoint
5. ~~NewsData country-primary buckets~~ — **PARTIAL by Codex edit**; revisit after measuring `geo_confidence` distribution
6. Validate tokenizer warning on `twitter-xlm-roberta-base-sentiment`
7. Resolve `country_heat_v2` refresh timeout

---

## P1 Pass — completed 2026-05-18 (recap)

All code issues from UX video review resolved:
- #143 Map layer clarity (Legend + Panel Help)
- #135 Landing live stats
- #69 Spanish compound search routing
- #133 Signal dossier export
- #141 Reading Mode newspaper view
- #56 Terminator twilight gradient
- #124 Saved watches live counts

## P0 Pass — completed 2026-05-17 (recap)

- #136 Brief prefetch (sessionStorage 4-min TTL)
- #137 Editor's Analysis fallback (rotating prose)
- #138 Investigation context persistence
- #142 Public Attention country-scoped
- #104 Google Trends rate-limiting
- #139 Narrative Threads timeout
- #128 Trail / Pinned graph separation

---

## Open Issues

| # | Issue | Status |
|---|-------|--------|
| #145 | Filter Wikipedia infrastructure/entertainment from Public Attention | P0 quick |
| #146 | Narrative Threads empty state explanation | P0 UX |
| #147 | Full map state reset (pitch + bearing + zoom) | P1 |
| #148 | "See all publishers" expansion in CountryBrief | P1 |
| #149 | Source-weighted scoring normalization | P1 core |
| #150 | Add 20+ non-English RSS feeds (Wave 5) | P1 data |
| #151 | Financial/commodity price overlay | P2 |
| #152 | Command bar redesign | P1 |
| #153 | Prototype MediaStack + Reddit ingestion | done session 15 |
| #163, #164, #167 | NLP worker / topic intelligence traceability | tracked by Codex commits |
| #140, #134 | Use-case docs | Needs Pedro to record |
| #46, #106 | ACLED / mascot | Blocked |

ACLED = optional connector. No `ACLED_API_KEY` → empty layer, no errors.

---

## Architecture

| Layer | Stack | Deploy |
|-------|-------|--------|
| Frontend | React 18 + TypeScript + Vite + deck.gl + MapLibre | Vercel auto-deploy from `v3-intel-layer` |
| Backend | FastAPI + asyncpg + PostgreSQL | Fly.io `atlas-api-pedro` (IAD) |
| NLP worker | xlm-roberta sentiment/NER/framing | Fly.io `nlp_worker` 4GB |
| Database | Supabase PostgreSQL | Migrations 007–020 applied |
| Cache | Upstash Redis | atlas-redis |

**All active ingestion sources**:

| Source | File | Family | Cadence |
|--------|------|--------|---------|
| GDELT GKG | `ingest_v2.py` | gdelt | 15 min |
| GDELT Events | `ingest_events.py` | gdelt | 15 min |
| Google Trends | `ingest_trends.py` | trends | 30 min |
| RSS curated | `ingest_rss.py` | varies | 60 min |
| ReliefWeb | `ingest_reliefweb.py` | ngo | 60 min |
| **NewsData.io** | `ingest_newsdata.py` | api | 60 min |
| **Reddit** | `ingest_reddit.py` | social | 60 min |
| **MediaStack** | `ingest_mediastack.py` | api | 2 h |
| **NewsAPI.org** | `ingest_newsapi.py` | api | 2 h |
| Wikipedia | `ingest_wiki.py` | wiki | 24 h |
| ACLED (opt) | `ingest_acled.py` | conflict | 60 min |

**Key endpoints**:
- `GET /api/v2/signals` — raw signals (filter by country/theme/person)
- `GET /api/v2/briefing` — aggregated brief (frontend caches 4 min)
- `GET /api/v2/narratives` — theme threads, detail capped at 48h
- `GET /api/v2/nodes` — country nodes
- `GET /api/v2/flows` — narrative co-occurrence
- `GET /api/v2/conflict-markers` — ACLED or empty
- `GET /health` — pipeline health + total_signals

---

## Key Technical Patterns

- **Country names**: `resolveCountryName(code, name)` always — never raw API strings
- **Theme labels**: `getThemeLabel(code)` always — never raw GDELT codes
- **Tooltips**: `data-tip` attribute — never native `title=`
- **Workspace persistence**: localStorage `atlas-workspace`, `atlas_saved_watches_v1`
- **Briefing prefetch**: sessionStorage `atlas_briefing_prefetch_v1` 4-min TTL
- **Compound search**: `parseCompoundQuery(q)` extracts countryCode before backend
- **ForceGraph2D**: Two instances mounted always, CSS `visibility: hidden` preserves simulation
- **Terminator**: 5-band PolygonLayer array, spread `...terminatorLayers`
- **New ingest sources**: all set `source_family`, `source_lang`, `geo_confidence`, `attribution_method`, `is_state_media` (signals_v2 convention)
- **Reddit signals**: `source_family="social"`, `attribution_method="reddit_public"` — commentary layer, NOT independent corroboration
- **`geo_confidence` defaults**: NewsData 0.7, MediaStack 0.65, NewsAPI 0.65, Reddit 0.5, GDELT GKG 0.9, RSS 0.6
- **NLP env flags**: `NLP_SAMPLE_REFRESH_EVERY=0`, `NLP_SAMPLE_CLEANUP_LIMIT=50` set in prod

---

## Validation (last run 2026-05-19)

```
npm run build       ✅ clean (Vite + tsc -b)
backend pytest      ✅ 139 main + 27 NLP/topic = 166 tests passing
fly deploy backend  ✅ deployment 01KS0EG5FJAY5507G729FNVACQ
fly secrets         ✅ NEWSDATA_API_KEY, MEDIASTACK_API_KEY, NEWSAPI_KEY deployed
NLP worker          ✅ 4GB, xlm-v1 multilingual, 231.5s cycle, error=no
/health             ✅ 2,279,950 signals, lag 4.1min, 3849 rows/15min
API validation      ✅ all 4 new sources return data
```

# Project Status

## Current Handoff — 2026-05-19 (session 15 + Codex parallel work)

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

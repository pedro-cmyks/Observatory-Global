# Project Status

## Current Handoff — 2026-05-18 (session 15)

**Production branch**: `v3-intel-layer`
**Frontend**: Vercel auto-deploy — latest commit deployed 2026-05-18
**Backend**: Fly.io `atlas-api-pedro` — healthy, 2M+ signals ingested, version 114

PR [#144](https://github.com/pedro-cmyks/Observatory-Global/pull/144) open against `main` (220+ commits ahead).

---

## Session 15 — Multi-source ingestion (2026-05-18)

Added 4 new ingestion sources to address GDELT's volumetric US/English bias.
All keys validated, Fly.io secrets set, 139 backend tests passing, deployed.

**New ingestion sources:**

| Source | File | Coverage | Cadence | Daily quota |
|--------|------|----------|---------|-------------|
| NewsData.io | `ingest_newsdata.py` | ES/PT/AR/FR/SW/HI — 6 language batches | every 60 min | 200 req/day |
| MediaStack | `ingest_mediastack.py` | ES/PT 17 LatAm countries | every 2 hours | 500 req/month |
| NewsAPI.org | `ingest_newsapi.py` | 8 targeted crisis queries | every 2 hours | 100 req/day |
| Reddit | `ingest_reddit.py` | 14 geopolitics subreddits (public API, no key) | every 60 min | unlimited |

**Fly.io secrets deployed:** `NEWSDATA_API_KEY`, `MEDIASTACK_API_KEY`, `NEWSAPI_KEY`

**Daily volume projection:**
- GDELT: ~72,000 signals/day (unchanged)
- New sources: +~27,600/day (NewsData ~8,400 + Reddit ~16,800 + MediaStack ~1,200 + NewsAPI ~1,280)
- Total: ~99,700 signals/day

**New files:**
- `backend/app/services/ingest_newsdata.py` — multilingual 6-batch ingestion
- `backend/app/services/ingest_mediastack.py` — ES/PT LatAm supplement
- `backend/app/services/ingest_newsapi.py` — crisis-targeted EN queries
- `backend/app/services/ingest_reddit.py` — social commentary layer (14 subreddits)
- `backend/.env.example` — all backend env vars documented

**Changed files:**
- `backend/app/services/ingest_loop.py` — wired all 4 sources at 4th/8th cycle intervals

**Known design debts to address next session:**
1. **NewsAPI queries are EN on zones GDELT already covers** — reframe to 6 evergreen + 2 dynamic (from GDELT spikes) + 36 req reserve for analyst UI
2. **NewsData language batches collapse geography** — refactor to country-primary buckets for better `geo_confidence` at fetch time
3. **NLP pipeline multilingual support unverified** — audit `enrichment/nlp_pipeline.py` model; swap to `xlm-roberta` if EN-only
4. **Reddit needs `signal_class = "social_commentary"`** — add to schema (migration 013) before scoring in #149

**Validation note (2026-05-18):** `backend/enrichment/nlp_pipeline.py` is English-first (`cardiffnlp/twitter-roberta-base-sentiment-latest`, `spacy en_core_web_sm`, English NLI framing). `ingest_loop.py` processes only `limit=100` NLP rows per 15-min cycle, so projected 100K/day ingestion can create silent NLP backlog. Reddit already has `source_family="social"` and `attribution_method="reddit_public"`, but `signal_class="social_commentary"` is still needed before #149 scoring. Corrected execution order: production row audit -> `signal_class` -> provider refactors + NLP benchmark -> Voice Mix -> scoring -> conservative clustering. Plan saved at `docs/superpowers/plans/2026-05-18-multisource-intelligence-hardening.md`.

---

## P1 Pass — completed 2026-05-18

All code issues from the UX video review resolved. Zero open code issues remain.

**#143 — Map layer clarity (Legend + Panel Help)**
- `Legend.tsx` fully rewritten — wired into `App.tsx` with all props
- Context banner when country/theme active; per-layer color keys; collapsible
- `PanelHelpDrawer` globe entry rewritten as 8-item layer guide with actionable steps

**#135 — Landing live stats**
- `/health` fetch on mount → live signal count + pipeline status pill
- BentoCards navigable (`/brief`, `/app`) with keyboard support
- `formatSignalCount()` helper for compact display

**#69 — Spanish compound search routing**
- `parseCompoundQuery` already extracted countryCode from "conflicto Colombia"-style queries
- Backend search URL now passes `&country=` when countryCode detected
- `handleThemeClick` / `handleConceptClick` pass countryCode to `onThemeSelect`
- Placeholder updated to show Spanish example

**#133 — Signal dossier export**
- "Export Signal Dossier" button (Download icon) in Workspace header
- `fetchItemSignals()` calls `/api/v2/signals` for each pinned theme/country/person
- `buildDossierMarkdown()` formats with headlines, sources, URLs, sentiment, people
- Downloads as `atlas-dossier-YYYY-MM-DD.md`

**#141 — Reading Mode newspaper view**
- BookOpen icon opens right-panel overlay showing signal cards per pinned item
- Responsive card grid: source, country badge, date, sentiment indicator, headline, URL
- Escape/scrim dismiss; Export .md button inside
- `ReadingMode.tsx` + `ReadingMode.css` (new files)

**#56 — Terminator twilight gradient**
- Hard-edge polygon replaced with 5-band offset layers
- Offsets: 0°→3.5°→7°→10.5°→14° lng; opacity: 52%→28%→14%→7%→3%
- ~1800 km twilight transition zone; label: "Day/Night Shadow (experimental)"

**#124 — Saved watches live counts**
- WATCH button (command bar) saves current filter as named watch to localStorage
- `/brief` fetches 24h signal count per watch in parallel (`fetchWatchCount()`)
- Card shows "N signals today" + delta badge (↑/↓ vs last check)
- "Open in Atlas →" calls `markSeen(id, count)` — records baseline for next delta

---

## P0 Pass — completed 2026-05-17

**#136 — Brief prefetch** — sessionStorage cache 4-min TTL, Landing prefetches on mount
**#137 — Editor's Analysis fallback** — 4 global + 3 country rotating prose variants
**#138 — Investigation context persistence** — back-nav wiring for country/theme/source
**#142 — Public Attention country-scoped** — Google Trends + Wikipedia merged, re-fetches on activeCountry
**#104 — Google Trends rate-limiting** — shuffle + retry + batch 5→3
**#139 — Narrative Threads timeout** — detail_hours = min(hours, 48), effective_hours in response
**#128 — Trail / Pinned graph separation** — two ForceGraph2D instances, CSS visibility toggle

---

## Open Issues

| # | Issue | Status |
|---|-------|--------|
| #145 | Filter Wikipedia infrastructure/entertainment from Public Attention | P0 quick fix |
| #146 | Narrative Threads empty state explanation | P0 UX |
| #147 | Full map state reset (pitch + bearing + zoom) | P1 |
| #148 | "See all publishers" expansion in CountryBrief | P1 |
| #149 | Source-weighted scoring normalization | P1 core |
| #150 | Add 20+ non-English RSS feeds (Wave 5) | P1 data |
| #151 | Financial/commodity price overlay for entity searches | P2 |
| #152 | Command bar redesign — prevent time range / search collision | P1 |
| #153 | Prototype MediaStack + Reddit ingestion, document findings | done this session |
| #140 | Visual use-case manual (docs) | Needs Pedro to record |
| #134 | Analytical use-case docs | Needs Pedro to record |
| #106 | Octopus mascot animation | Blocked — needs design assets |
| #46 | ACLED API access | Blocked — no credentials yet |

ACLED is an **optional connector** — system degrades cleanly to empty conflict layer without `ACLED_API_KEY`.

**Next session priority:** production row audit, then migration 013 `signal_class`, then provider refactors and NLP benchmark in parallel, then Voice Mix.

---

## Architecture

| Layer | Stack | Deploy |
|-------|-------|--------|
| Frontend | React 18 + TypeScript + Vite + deck.gl + MapLibre | Vercel (auto-deploy from `v3-intel-layer`) |
| Backend | FastAPI + asyncpg + PostgreSQL | Fly.io `atlas-api-pedro` (IAD region) |
| Database | Supabase PostgreSQL | Managed — migrations 007–012 applied |
| Ingestion | GDELT 2.0 (15min) + NewsData/Reddit (60min) + MediaStack/NewsAPI (120min) + Google Trends (30min) + Wikipedia (24h) | Fly.io background workers |

**Ingestion sources (all active):**
- GDELT 2.0 GKG + Events: every 15 min — `ingest_v2.py`, `ingest_events.py`
- Google Trends: every 30 min — `ingest_trends.py`
- NewsData.io: every 60 min — `ingest_newsdata.py` (NEWSDATA_API_KEY)
- Reddit public API: every 60 min — `ingest_reddit.py` (no key)
- RSS curated feeds: every 60 min — `ingest_rss.py`
- ReliefWeb/OCHA: every 60 min — `ingest_reliefweb.py`
- MediaStack: every 2 hours — `ingest_mediastack.py` (MEDIASTACK_API_KEY)
- NewsAPI.org: every 2 hours — `ingest_newsapi.py` (NEWSAPI_KEY)
- ACLED: every 60 min — `ingest_acled.py` (optional, ACLED_API_KEY)
- Wikipedia pageviews: every 24 hours — `ingest_wiki.py`

**Key endpoints:**
- `GET /api/v2/signals` — raw signals with country/theme/person filters
- `GET /api/v2/briefing` — aggregated brief (sessionStorage cached 4 min on frontend)
- `GET /api/v2/narratives` — theme threads, detail capped at 48h
- `GET /api/v2/nodes` — country nodes with baseline deviation
- `GET /api/v2/flows` — narrative co-occurrence arcs
- `GET /api/v2/conflict-markers` — ACLED or empty if unconfigured
- `GET /health` — pipeline health + total_signals count

---

## Key Technical Patterns

- **Country names**: always `resolveCountryName(code, name)` — never raw API strings
- **Theme labels**: always `getThemeLabel(code)` — never raw GDELT codes
- **Tooltips**: `data-tip` attribute only — never native `title=`
- **Workspace persistence**: localStorage (`atlas-workspace`, `atlas_saved_watches_v1`)
- **Briefing prefetch**: `sessionStorage` key `atlas_briefing_prefetch_v1`, 4-min TTL
- **Compound search**: `parseCompoundQuery(q)` extracts countryCode before sending to backend
- **ForceGraph2D**: Two instances always mounted, CSS `visibility: hidden` preserves simulation
- **Terminator**: 5-band PolygonLayer array, spread via `...terminatorLayers` in layer stack
- **New ingest sources**: all set `source_family`, `source_lang`, `geo_confidence`, `attribution_method`, `is_state_media` — same convention as ingest_rss.py
- **Reddit signals**: `source_family="social"`, `attribution_method="reddit_public"` — treat as commentary layer, NOT independent corroboration
- **NewsData geo_confidence**: 0.7 (country comes from API metadata, better than NER inference); MediaStack 0.65; NewsAPI 0.65

---

## Validation (last run 2026-05-18)

```
npm run build    ✅ clean (Vite + tsc -b)
tsc --noEmit     ✅ 0 errors
npm test         ✅ 139 tests passing (backend)
fly deploy       ✅ version 114, 1 passing health check
fly secrets set  ✅ NEWSDATA_API_KEY, MEDIASTACK_API_KEY, NEWSAPI_KEY deployed
API validation   ✅ all 4 new sources return data (verified via curl before commit)
```

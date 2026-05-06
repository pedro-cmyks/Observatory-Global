# Observatorio Global — Session Status
**Branch:** `v3-intel-layer` | **Updated:** 2026-05-06 (session 8)

---

## What we built (sessions 1–8)

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

---

## Changes this session (session 8)

| Commit | What it does |
|--------|-------------|
| `39b3ad4` | **#71 fixed**: SQL array_agg LIMIT → [1:5] slice in concept endpoint |
| `76eb21f` | **#54 fixed**: replace broken TRENDING with Wikipedia PUBLIC ATTENTION |
| `0b32799` | **#50 fixed**: workspace tab pulse + inline Pin icon in empty state |
| `d082ba0` | **#65 added**: first-load onboarding coachmark (3 steps) |
| Fly deploy | Activated ingest_v2 ON CONFLICT fix — backend now at 1.66M+ signals |

**Issues closed this session:** #50, #54, #65, #71
**No new issues opened.**

---

## Deploy status

Fly.io is **current** — deployed this session. Health: `status: healthy`, `db_ok: true`, `rows_ingested_last_15m: 3853`.

The SQL fix for #71 (`array_agg` slice) needs a second `fly deploy` to take effect on the backend. Run it before testing the concept endpoint.

---

## Open issues (9 open)

### Features — next build targets
| # | Title | Effort | Notes |
|---|-------|--------|-------|
| **#69** | Spanish-language search routing + multilingual query expansion | medium | backend + frontend |
| **#68** | Source-family classification (state / independent / wire service) | medium | backend + frontend |
| **#66** | Export findings as Markdown or CSV | medium | frontend |
| **#51** | Tolerant search (fuzzy, token reordering, aliases) | large | backend + frontend |
| **#61** | Temporal and entity comparative engine UI | large | frontend |
| **#63** | Ephemeral session trail graph | medium | frontend |
| **#70** | Theme clustering / GDELT hierarchy research | research | backend |

### Tech debt
| # | Title |
|---|-------|
| **#62** | ESLint debt blocking `npm run lint` |
| **#46** | ACLED API access (blocked externally) |

---

## Recommended next order

1. `fly deploy` — push the array_agg fix for concept endpoint to production
2. **#69** — Spanish-language search (backend `match_region` + frontend routing)
3. **#68** — Source-family classification (state / independent / wire service)
4. **#66** — Export button (frontend-only, MD + CSV)
5. **#62** — ESLint debt (housekeeping, unblocks CI)

---

## Architecture snapshot

```
Vercel (frontend)          Fly.io (backend)         Supabase (DB)
─────────────────          ────────────────          ────────────
frontend-v2/               backend/app/              signals_v2
  App.tsx                    main_v2.py              events_v2
  38 .tsx components         30+ API endpoints       aggregates_*
  MapLibre GL                GDELT ingest: 15min     wiki_pageviews_v2
  DeckGL v9                  Wiki ingest: 24h        trends_v2 (empty)
  react-force-graph-2d       Fly machine: iad
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
| Onboarding | Delete `atlas_onboarding_v1` from localStorage → reload `/app` → 3-step overlay appears |
| Signal Stream | Left panel shows live GDELT articles with timestamps |
| Narrative Threads | Right panel — 5 topics with sparklines, spread bars, trend arrows |
| Theme detail | Click any theme → stats + country cards + drift chart (or "No drift data for this period") |
| Country brief | Click any country → top themes + clickable person chips |
| Workspace board | Pin 3+ items → folder tab pulses green when empty → click it → nodes spread, edge labels at zoom-in |
| Public Attention | Bottom-right of Anomaly panel → shows top Wikipedia articles by pageview |
| Concept endpoint | `/api/v2/concept/public-health?hours=48` → returns countries JSON (needs fly deploy for array fix) |
| Search | Top bar → try "climate", "ukraine", "tariffs", "Gaza" |

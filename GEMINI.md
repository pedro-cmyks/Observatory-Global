# GEMINI Code Assistant Context — Observatory Global (Atlas)

Last updated: 2026-05-05 (session 5 — first-user experience)

This document gives the Gemini AI assistant the current, accurate context for the Observatory Global project. Treat this as the source of truth for deployment topology, architecture, and conventions.

---

## What this project is

**Observatory Global (internal name: Atlas)** is a narrative intelligence system. It tracks how topics and news narratives propagate across global media sources, surfaces geographic drift, sentiment patterns, and conflict signals. It is NOT a news reader: the value is HOW and WHERE the world covers topics, not what happened.

---

## Current deployment (production)

| Component | Platform | URL / Identifier |
|-----------|----------|-----------------|
| Frontend | Vercel (auto-deploy from `v3-intel-layer` branch) | observatory-global.vercel.app |
| Backend API | Fly.io | atlas-api-pedro.fly.dev |
| Database | Supabase (PostgreSQL) | signals_v2 table — 1.3M+ rows |
| Cache | Upstash Redis | atlas-redis instance |

**There is no Docker Compose production setup.** The app runs on Vercel + Fly.io. Docker/Compose exists for local dev only.

---

## Active codebase layout

```
frontend-v2/          ← ACTIVE React 19 + Vite + TypeScript frontend (use this)
  src/
    pages/            ← Landing.tsx  Landing.css  Docs.tsx  Docs.css
    components/       ← 29 .tsx components (see full list below)
    contexts/         ← FocusContext, FocusDataContext, CrisisContext, ThemeContext
    hooks/            ← useFocusData.ts, useUrlSync.ts
    layers/           ← TerminatorLayer.ts (custom DeckGL day/night terminator)
    lib/              ← countryNames.ts, chokepoints.ts, mapUtils.ts, themeLabels.tsx, timeRanges.ts
    styles/           ← variables.css, themes.ts
    App.tsx           ← main dashboard: all state, layout, routing logic
    App.css           ← global dashboard styles + [data-tip] tooltip system
    main.tsx          ← React Router v7 setup
  public/
    assets/           ← Atlas hero PNGs (6 images, used by Landing.tsx)
  tailwind.config.js  ← Tailwind v3 (used ONLY by Landing.tsx — rest of app uses Vanilla CSS)
  package.json

frontend/             ← DEPRECATED old frontend — do NOT touch

backend/
  app/
    main_v2.py        ← All FastAPI endpoints (v2 + v3 API, ~4,100 lines)
    core/
      gdelt_taxonomy.py   ← GDELT theme labels + investigative concepts + REGION_MAP
      cameo_taxonomy.py   ← CAMEO event code taxonomy
      country_metadata.py ← Country metadata helpers
      config.py           ← App configuration
      logging.py          ← Logging setup
    services/
      ingest_v2.py        ← GDELT GKG ingestion (primary ingest)
      ingest_loop.py      ← Scheduler: GDELT 15m, Trends 30m, ACLED 60m, Wiki daily
      ingest_acled.py     ← ACLED conflict ingestion
      ingest_trends.py    ← Google Trends ingestion
      ingest_wiki.py      ← Wikipedia ingestion
      signals_service.py  ← Core signal query/processing service
      flow_detector.py    ← Narrative flow arc detection
      gdelt_parser.py     ← GDELT GKG record parser
      nlp.py              ← NLP utilities
      [+ 13 more service modules]
    db/                ← DB connection helpers
    models/            ← Pydantic models
    adapters/          ← External adapter layer
  start.sh             ← Watchdog loop + uvicorn launcher (Fly.io entrypoint)
  migrations/          ← Raw SQL files (007 applied = most recent)

docs/
  superpowers/
    specs/            ← UX/feature specs (e.g. 2026-05-05-atlas-first-user-experience-design.md)
    plans/            ← Implementation plans (e.g. 2026-05-05-atlas-first-user-experience.md)

stitch_atlas_landing_experience_redesign/   ← Design assets from Google Stitch
  DESIGN.md           ← Design system tokens (exported from Stitch)
  code.html           ← Stitch-generated HTML reference
  screen.png          ← Stitch screen screenshot
```

### Frontend Component List (32 .tsx files)
`AnomalyPanel`, `AtlasLoader`, `Briefing`, `ChokepointPanel`, `CompareBar`, `CorrelationMatrix`, `CorrelationMatrixPlaceholder`, `CountryBrief`, `CountryThemePanel`, `CrisisDashboard`, `CrisisToggle`, `DeckGLOverlay`, `DevBanner`, `DiscoveryPanel`, `EntityPanel`, `FocusIndicator`, `FocusSummaryPanel`, `IndicatorTooltip`, `Legend`, `MapTooltip`, `NarrativeThreads`, `NarrativeThreadsPlaceholder`, `PanelErrorBoundary`, `PersonCompare`, `SearchBar`, `SettingsPanel`, `SignalStream`, `SourceIntegrityPanel`, `SourceProfile`, `ThemeCompare`, `ThemeDetail`, `ThemeSelector`

---

## Tech stack

- **Frontend:** React 19, TypeScript, Vite, React Router v7, MapLibre GL, DeckGL v9, react-grid-layout v2, Recharts, lucide-react
- **Styling:** Vanilla CSS for the main dashboard (`App.css`, component `.css` files). **Tailwind CSS v3** is installed and used **exclusively for `Landing.tsx`** (the public marketing page). Do NOT use Tailwind in dashboard components.
- **State:** React Context (FocusContext, FocusDataContext, CrisisContext, ThemeContext — no Zustand)
- **Theme system:** CSS custom properties driven by `ThemeContext` + `styles/themes.ts`. Active theme applied via `data-theme` attribute on `<html>`.
- **Backend:** Python 3.11, FastAPI, asyncpg, pydantic, Anthropic SDK (Claude Haiku for AI summaries)
- **Database:** PostgreSQL (Supabase) — primary table `signals_v2`, ACLED table `acled_conflicts_v2`, aggregate matviews for trends/themes
- **Cache:** Redis (Upstash) — AI summaries cached 30 min
- **Data sources:** GDELT 2.0 (GKG), Google Trends (pytrends), ACLED, Wikipedia

---

## Backend API endpoints

Base: `atlas-api-pedro.fly.dev`

### Core Intelligence
- `GET /api/v2/nodes` — country signal nodes with heat scores
- `GET /api/v2/flows` — narrative flow arcs
- `GET /api/v2/signals` — raw signal stream (paginated)
- `GET /api/v2/narratives` — narrative threads
- `GET /api/v2/briefing?hours=N` — global briefing stats
- `GET /api/v2/briefing/insight?hours=N` — AI summary (Claude Haiku, cached 30 min Redis)
- `GET /api/v2/focus` — focus-filtered summary
- `GET /api/v2/search?q=` — compound search: themes, persons, countries (legacy)
- `GET /api/v2/search/unified?q=` — unified search: taxonomy + concepts + regions + DB merge (preferred)
- `GET /api/v2/anomalies` — statistical anomaly detection
- `GET /api/v2/anomalies/themes` — theme-level anomaly detection (country-aware)
- `GET /api/v2/trends` — trending topic data
- `GET /api/v2/trends/search` — Google Trends search
- `GET /api/v2/trends/match` — Trends-to-theme match
- `GET /api/v2/compare` — period comparison
- `GET /api/v2/source/{domain}/profile` — source bias profiler

### Detail Views
- `GET /api/v2/country/{code}` — country detail
- `GET /api/v2/theme/{code}?country_code=XX` — theme detail (filterable by country)
- `GET /api/v2/theme/{code}/insight` — AI insight for theme (Claude Haiku, cached)
- `GET /api/v2/theme/{code}/spikes` — coverage spike detection for theme
- `GET /api/v2/correlation` — cross-theme correlation matrix

### Investigative Concepts
- `GET /api/v2/concepts` — list all curated investigative concepts
- `GET /api/v2/concepts/search` — fuzzy concept + GDELT theme search
- `GET /api/v2/concept/{slug}` — concept narrative threads

### Geospatial & Conflict
- `GET /api/v2/conflict-markers` — GDELT/ACLED conflict events for map
- `GET /api/v2/acled` — raw ACLED conflict records
- `GET /api/v2/events` — GDELT event stream
- `GET /api/v2/events/clusters` — clustered event summaries
- `GET /api/v2/heatmap` — geographic heatmap data
- `GET /api/v2/aircraft` — live military aircraft positions (ADS-B / OpenSky OAuth2)
- `GET /api/v2/vessels` — live vessel positions at chokepoints (AISStream WebSocket)

### Supporting
- `GET /api/v2/wiki/top` — Wikipedia top articles
- `GET /api/v2/wiki/match` — Wikipedia-to-theme match
- `GET /api/v2/stats` — system statistics
- `GET /api/indicators/tooltips` — indicator tooltip definitions
- `GET /api/indicators/allowlist` / `denylist` — source quality lists
- `GET /api/indicators/country/{code}` — country indicators

### Crisis Mode (v3)
- `GET /api/v3/crisis/signals` — crisis-flagged signals (is_crisis=TRUE filter)
- `GET /api/v3/crisis/summary` — crisis signal summary stats

### Health
- `GET /health` — DB health + ingest lag

---

## Routing (main.tsx)

```
/          → Landing.tsx  (public marketing page — Tailwind CSS)
/app       → App.tsx      (main dashboard — Vanilla CSS)
/docs      → Docs.tsx     (documentation)
/docs/*    → Docs.tsx
*          → Landing.tsx  (fallback)
```

Provider nesting inside `main.tsx`: `ThemeProvider` wraps all routes.
Provider nesting inside `App.tsx`: `FocusProvider` → `CrisisProvider` → dashboard.

---

## MCP servers configured

`.mcp.json` in repo root configures two MCP servers:

| Server | URL | Purpose |
|--------|-----|---------| 
| supabase | https://mcp.supabase.com/mcp?project_ref=vfemszzlzwchcjveifjp | Direct Supabase DB access |
| stitch | https://stitch.googleapis.com/mcp | Google Stitch AI design tool |

Stitch project: **Atlas Landing Experience Redesign**
- Project ID: `16360346810703467664`
- Screen ID: `bada7ddbd4324c9ab341b26a485889a6`
- Design system exported to `stitch_atlas_landing_experience_redesign/DESIGN.md`

---

## Landing page status (CURRENT — as of 2026-05-04 session 3)

`frontend-v2/src/pages/Landing.tsx` has been fully redesigned with real Atlas content:
- **Tailwind CSS v3** classes are used directly (Landing.tsx is the only file that uses Tailwind)
- Hero: "Atlas Projection" wireframe globe with radar sweep, correct tagline and Atlas branding
- Bento grid: real feature cards (Narrative Threading, Geographic Drift, Conflict Signals, etc.)
- Navigation anchors: `#features`, `#data-sources`, `#api`
- Design tokens: dark slate `#070d17` bg, emerald `#1D9E75` accent, Outfit / Space Grotesk / Plus Jakarta Sans fonts
- `scroll-margin-top` fix applied so fixed nav doesn't obscure anchored sections (commit `d3cbaa1`)

---

## Key architectural decisions

1. **React Router v7**: `main.tsx` wraps app in `BrowserRouter`. Four routes: `/`, `/app`, `/docs`, `/docs/*`.
2. **Compound search**: SearchBar parses "elecciones Colombia" → extracts country + topic, sets both `filter.country` and `filter.theme` simultaneously. Uses `/api/v2/search/unified` (preferred over legacy `/api/v2/search`).
3. **FocusContext**: Multi-dimensional filter — `filter.country`, `filter.theme`, `filter.person`, `filter.concept`, `filter.region` can all be set together. Concept filter expands to multiple themes. Region filter expands to multiple countries.
4. **Tooltip system**: `[data-tip]` CSS pseudo-element tooltips in `App.css` — instant (80ms fade). Use `data-tip="text"` on any element. Do NOT use native `title=`.
5. **AI Insight**: Claude Haiku via Anthropic SDK. Cached 30 min in Redis.
6. **Ingestion watchdog**: `start.sh` runs `ingest_watchdog()` bash loop that restarts `ingest_loop.py` after any crash.
7. **Migrations**: Raw SQL files in `backend/migrations/`. Run via Supabase SQL editor (NOT alembic — alembic is not used). Most recent migration: `007_signals_dedup.sql`.
8. **Stitch MCP**: Google Stitch connected via MCP over HTTP for AI-assisted landing page design. API key in `.mcp.json` headers (`X-Goog-Api-Key`).
9. **Tailwind scope**: Tailwind is installed but scoped to `Landing.tsx` only. All dashboard components use Vanilla CSS + CSS custom properties. Do NOT add Tailwind to dashboard components.
10. **Theme system**: `ThemeContext` reads `styles/themes.ts` and applies CSS vars to `:root` via `data-theme` attribute. `SettingsPanel` allows runtime theme switching.
11. **Aircraft layer**: Uses OpenSky OAuth2 client credentials flow. Falls back to cached/empty state on failure — no simulated data.
12. **Vessel layer**: Consumes AISStream WebSocket in the backend; frontend polls `/api/v2/vessels` every 30s. Displayed as a DeckGL `ScatterplotLayer` near chokepoints defined in `lib/chokepoints.ts`.
13. **Crisis mode**: `CrisisContext` + `CrisisDashboard` component. Backend marks signals with `is_crisis=TRUE` and `crisis_score`. Crisis API routes live under `/api/v3/`.
14. **Investigative concepts**: `gdelt_taxonomy.py` in `app/core/` holds curated investigative concept frames (blood-diamonds, femicide, etc.). Exposed via `/api/v2/concepts/*`.
15. **TerminatorLayer**: Custom DeckGL layer in `src/layers/TerminatorLayer.ts` renders the day/night terminator line on the globe.
16. **ACLED integration**: `acled_conflicts_v2` table receives data from `ingest_acled.py`. Surfaced in `/api/v2/conflict-markers` and `/api/v2/acled`. Conflict markers from ACLED take precedence over GDELT-derived markers.
17. **Region map**: `REGION_MAP` in `gdelt_taxonomy.py` maps 6 regions (Africa, Middle East, Latin America, Europe, Asia-Pacific, North America) to ISO country codes with multilingual aliases (EN/ES/FR/PT/DE/AR). `match_region()` provides fuzzy matching.
18. **Unified search**: `/api/v2/search/unified` merges taxonomy search (aliases, typos, multilingual), concept search (investigative frames), region matching, and live DB signal search into one response. Taxonomy-matched themes get priority over DB-only hits. Cached 2 min in Redis.
19. **CompareBar**: `CompareBar.tsx` shows period-over-period signal and sentiment delta inside ThemeDetail. Uses existing `/api/v2/compare` endpoint.
20. **URL state sync**: `useUrlSync.ts` hook bidirectionally syncs `FocusContext.filter` with URL search params. Enables shareable links: `/app?theme=ARMEDCONFLICT&country=CO&time=1w`. Hydrates filter from URL on mount, pushes changes on filter update.
21. **DiscoveryPanel (session 5)**: Blank-state default for the stream column. Shows top 5 GDELT narratives as explorable cards with trend arrows (accelerating/fading/stable), signal counts, and top countries. Fetches `GET /api/v2/narratives?hours=24&limit=5`, auto-refreshes every 5 minutes. `SignalStream` is no longer the default view — it is shown only when explicitly triggered.
22. **Stream panel state machine**: Right column renders based on which state is truthy first: `isPerson → isCompound(theme+country) → isCountry → isTheme → isChokepoint → DiscoveryPanel`. The title switches between "WHAT'S HAPPENING" (blank state) and "SIGNAL STREAM" (active filter).
23. **Map hint**: `.map-hint` element in App.css + animation. Appears 2 seconds after `mapReady` for first-time users. Dismissed on any map interaction; `sessionStorage` prevents it from reappearing within the same browser session.
24. **ingest_v2.py ON CONFLICT status**: Restored to `ON CONFLICT (source_url) WHERE source_url IS NOT NULL DO NOTHING` (requires migration 007's unique index). Committed. Awaiting `fly deploy` to take effect on the running instance.

---

## Development commands

```bash
# Backend local dev
cd backend && poetry run uvicorn app.main_v2:app --reload --port 8000

# Frontend local dev
cd frontend-v2 && npm run dev

# Frontend build verification (REQUIRED before every push — not just tsc --noEmit)
cd frontend-v2 && npm run build

# Fly.io deploy (backend)
fly deploy

# Check ingestion health
curl atlas-api-pedro.fly.dev/health
```

**Build rule:** Always run `npm run build`, not just `tsc --noEmit`. Vite uses `tsc -b` (project references), which is stricter and catches errors (e.g. TS6133 unused imports) that bare `tsc --noEmit` misses. A passing `tsc --noEmit` does NOT guarantee a passing Vercel build.

---

## Coding conventions

- **Python:** 3.11, 4-space indent, 100-char lines, Ruff + Mypy. Pydantic models in `app/models/`. FastAPI routes under `/api/v2/...` (v3 for crisis endpoints).
- **TypeScript:** 2-space indent, PascalCase components, camelCase hooks/store. Run `npm run build` before PRs.
- **Commits:** Conventional Commits — `feat(scope): ...`, `fix(scope): ...`, `chore: ...`.
- **Migrations:** Raw `.sql` files. Must be run from Supabase SQL editor (direct connection, bypasses pooler timeout).
- **CSS:** Vanilla CSS for all dashboard components. Tailwind only for `Landing.tsx`.

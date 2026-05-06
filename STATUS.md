# Observatorio Global — Session Status
**Branch:** `v3-intel-layer` | **Updated:** 2026-05-06 (session 7)

---

## What we built (sessions 1–7)

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
- **AnomalyPanel** — spike detection vs 7-day baseline
- **SourceIntegrityPanel** — source diversity score per context
- **CorrelationMatrix** — country/narrative overlap heatmap

### Investigation workspace (session 6)
- `InteractiveWorkspace.tsx` — react-force-graph-2d canvas, lazy-loaded (~188KB chunk)
- `InvestigationWorkspace.tsx` — shell with `React.lazy()` + `PanelErrorBoundary`
- `workspaceGraph.ts` — two-pass graph builder (pinned nodes always succeed; edges per-item try/catch)
- Three-layer error boundary: `RootErrorBoundary` → `PanelErrorBoundary` → `MapErrorBoundary`

### UX + quality fixes (sessions 5–7)
- Theme label formatter: all raw GDELT codes → human-readable names via `getThemeLabel()`
- Country key people: `CountryBrief` shows clickable person chips from `keyPersons`
- Signal Stream restored as blank state (eliminates duplicate content with NarrativeThreads)
- Graceful drift fallback: API failure → "No drift data" instead of red error
- Workspace node spread: D3 charge=-320, link distance=110, edge labels at zoom > 1.2

---

## Changes this session (session 7)

| Commit | What it does |
|--------|-------------|
| `19cdf0d` | Config sync: AGENTS.md, CLAUDE.md, GEMINI.md + .codex/ agents |
| `3113cb9` | **#42 fixed**: restore SignalStream as blank state (eliminates duplicate content with NarrativeThreads) |
| `7217909` | Drift error → graceful empty state; workspace node spread + edge labels on canvas |

**Issues closed this session:** #42, #58, #64, #67
**New issue opened:** #71 (SQL LIMIT bug in `/api/v2/concept/{slug}`)

---

## Pending deploy

`ingest_v2.py` ON CONFLICT fix is committed but **not yet on Fly.io**.
Run `fly deploy` from the repo root to activate it. Migration 007 (unique index on `source_url`) is already in the DB.

---

## Open issues (13 open)

### Bugs — fix first
| # | Title | Where |
|---|-------|-------|
| **#54** | Anomaly Alert "Trending" section shows "No data yet" permanently | backend/frontend |
| **#71** | SQL syntax error near LIMIT in `/api/v2/concept/{slug}` | backend |

### UX — visible to users
| # | Title | Effort |
|---|-------|--------|
| **#50** | Pin mechanism not discoverable — workspace empty state lacks guidance | small |
| **#65** | First-load coachmark — 3-step mental model handoff | medium |

### Features — new capabilities
| # | Title | Effort |
|---|-------|--------|
| **#66** | Export findings as Markdown or CSV | medium |
| **#69** | Spanish-language search routing + multilingual query expansion | medium |
| **#68** | Source-family classification (state / independent / wire service) | medium |
| **#51** | Tolerant search (fuzzy, token reordering, aliases) | large |
| **#61** | Temporal and entity comparative engine UI | large |
| **#63** | Ephemeral session trail graph | medium |
| **#70** | Theme clustering / GDELT hierarchy research | research |

### Tech debt
| # | Title |
|---|-------|
| **#62** | ESLint debt blocking `npm run lint` |
| **#46** | ACLED API access (blocked externally) |

---

## Recommended next order

1. `fly deploy` — activate the ON CONFLICT fix (5 min, no code change)
2. **#54** — Trending data empty (backend bug, high user impact)
3. **#71** — SQL LIMIT error in concept endpoint (backend bug)
4. **#50** — Pin discoverability (small UX fix)
5. **#65** — Onboarding coachmark (medium UX)

---

## Architecture snapshot

```
Vercel (frontend)          Fly.io (backend)         Supabase (DB)
─────────────────          ────────────────          ────────────
frontend-v2/               backend/app/              signals_v2
  App.tsx                    main_v2.py              events_v2
  36 .tsx components         30+ API endpoints       aggregates_*
  MapLibre GL                GDELT ingest pipeline   trends_archive
  DeckGL v9                  Fly machine: iad
  react-force-graph-2d
```

### Critical rules (don't break these)
- **CSS**: Vanilla CSS everywhere EXCEPT `Landing.tsx` which uses Tailwind
- **Tooltips**: `data-tip="text"` only — never native `title=` attribute
- **Theme labels**: always `getThemeLabel(theme_code)` — never trust the API `label` field
- **Build**: always `npm run build` (not `tsc --noEmit`) before pushing
- **Workspace lazy load**: `InteractiveWorkspace` is lazy-loaded via `React.lazy()` in `InvestigationWorkspace` — do NOT import it directly
- **Graph library**: `react-force-graph-2d` only — never `react-force-graph` (3D version pulls AFRAME, crashes the app)

---

## How to evaluate what's working

| Area | How to check |
|------|-------------|
| Signal Stream | Open `/app` → left panel shows live GDELT articles with timestamps |
| Narrative Threads | Right panel always visible — 5 topics with sparklines, spread bars, trend arrows |
| Theme detail | Click any theme → stats + country cards + drift chart (or "No drift data for this period") |
| Country brief | Click any country → top themes + clickable person chips |
| Workspace board | Pin 3+ items → click folder icon (bottom-left tab) → nodes spread across canvas; zoom in to see edge labels |
| Anomaly panel | Bottom panel → "Spikes" tab should show data; "Trending" tab is broken (#54) |
| Search | Top bar → try "climate", "ukraine", "tariffs", "Gaza" |
| Concept endpoint | `/api/v2/concept/public-health?hours=48` → should work; `/api/v2/concept/blood-diamonds` → currently errors (#71) |

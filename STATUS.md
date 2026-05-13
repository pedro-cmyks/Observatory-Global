# Atlas — Session Status
**Branch:** `v3-intel-layer` | **Updated:** 2026-05-12 (UX onboarding + brand refresh)

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
5. **#124 / #80 / #82** — move toward guided investigation memory: saved searches, session graph, and temporal graph integration.

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
| Onboarding | Delete `atlas_onboarding_v1` from localStorage → reload `/app` → 3-step overlay appears |
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

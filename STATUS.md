# Atlas — Session Status
**Branch:** `v3-intel-layer` | **Updated:** 2026-05-16 (Session 18 — video UX review + productization roadmap)

---

## Current handoff (2026-05-16) — Session 18

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

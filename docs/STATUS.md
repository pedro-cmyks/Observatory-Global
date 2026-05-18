# Project Status

## Current Handoff — 2026-05-18

**Production branch**: `v3-intel-layer`
**Frontend**: Vercel auto-deploy — latest commit `f57b031` deployed `2026-05-18T00:01Z`
**Backend**: Fly.io `atlas-api-pedro` — healthy, 2M+ signals ingested, version 113

PR [#144](https://github.com/pedro-cmyks/Observatory-Global/pull/144) open against `main` (219 commits ahead).

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

**#136 — Brief prefetch**
- `briefingPrefetch` lib (sessionStorage, 4-min TTL)
- Landing prefetches on mount; BriefNewspaper reads cache → no spinner

**#137 — Editor's Analysis fallback**
- 4 rotating global prose variants + 3 country variants, data-derived
- Removed headline anchors to avoid misclassification risk

**#138 — Investigation context persistence**
- `prevStreamCtx` union extended with `country` type
- Back from source → CountryBrief; back from country → thread if active

**#142 — Public Attention country-scoped**
- Google Trends + Wikipedia merged into single PUBLIC ATTENTION section
- Re-fetches on `activeCountry` change; staleness badge when >25h
- CountryBrief items clickable

**#104 — Google Trends rate-limiting**
- `ingest_trends.py`: shuffle + retry pass + batch size 5→3
- Frontend: 72h minimum window floor, staleness badge

**#139 — Narrative Threads timeout**
- `detail_hours = min(hours, 48)` caps Phase 2; Phase 1 uses full window
- `effective_hours` in API response; frontend notice when capped

**#128 — Trail / Pinned graph separation**
- Two independent `ForceGraph2D` instances with CSS `visibility: hidden`
- Trail: linear-spread physics; Pinned: dense-web physics

---

## Open Issues (non-blocking)

| # | Issue | Status |
|---|-------|--------|
| #140 | Visual use-case manual (docs) | Needs screenshots — not code |
| #134 | Analytical use-case docs | Writing task only |
| #106 | Octopus mascot animation | Blocked — needs design assets |
| #46 | ACLED API access | Blocked — no credentials yet |

ACLED is an **optional connector** — system degrades cleanly to empty conflict layer without `ACLED_API_KEY`.

---

## Architecture

| Layer | Stack | Deploy |
|-------|-------|--------|
| Frontend | React 18 + TypeScript + Vite + deck.gl + MapLibre | Vercel (auto-deploy from `v3-intel-layer`) |
| Backend | FastAPI + asyncpg + PostgreSQL | Fly.io `atlas-api-pedro` (IAD region) |
| Database | Supabase PostgreSQL | Managed — migrations 007–012 applied |
| Ingestion | GDELT 2.0 every 15 min, AIS stream, ADS-B, Google Trends, Wikipedia | Fly.io background workers |

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

---

## Validation (last run 2026-05-18)

```
npm run build    ✅ clean (Vite + tsc -b)
tsc --noEmit     ✅ 0 errors
npm test         ✅ 25 tests passing
fly status       ✅ atlas-api-pedro started, 1 passing health check
/health          ✅ 2,022,453 signals, status: healthy
```

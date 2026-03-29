# Implementation Plan — Phase 1: Bloomberg Terminal Layout

## Goal

Transform Observatory Global from a single full-screen map into a 6-panel terminal layout. Add Signal Stream, permanently visible Anomaly Alert, and Source Integrity panels. Expand GDELT ingestion to include Translingual exports with headlines. Audit and document the processing pipeline.

## Execution Order

Per the brief: audit first (understand data), then schema, then frontend + safety in parallel.

1. **Workstream A1**: PROCESSING_AUDIT.md (read-only analysis)
2. **Workstream A3**: schema_v2_authoritative.sql (DB dump + annotation)
3. **Workstream A2**: Ingestion expansion (GDELT Translingual + headline column)
4. **Workstream C**: Schema safety net (docs + no-op fix)
5. **Workstream B1–B6**: Frontend panel layout + new components

---

## Proposed Changes

### Workstream A: Backend

---

#### [NEW] [PROCESSING_AUDIT.md](file:///Users/pedro/Desktop/PEDRO/Cursos/ObservatorioGlobal/docs/PROCESSING_AUDIT.md)

Analysis document covering: signal filtering, deduplication, sentiment calculation, quality thresholds, data drop reasons, ingestion volume. Generated from reading `ingest_v2.py`, `parse_gkg_row()`, and correlating with DB state.

---

#### [MODIFY] [ingest_v2.py](file:///Users/pedro/Desktop/PEDRO/Cursos/ObservatorioGlobal/backend/app/services/ingest_v2.py)

- Add `fetch_latest_translingual_url()` — fetch Translingual GKG URL from GDELT lastupdate
- Add `extract_headline()` — extract title from Translingual GKG row (V2ExtrasXML or DocumentIdentifier field)
- Modify `parse_gkg_row()` to accept optional `extract_title=True` flag
- Add `headline` field to returned signal dict (nullable)
- Modify `insert_signals()` SQL to include `headline` column
- Add `run_translingual_ingestion()` — parallel ingestion path
- Modify `run_ingestion()` to run both GKG + Translingual in sequence

---

#### [MODIFY] [auto_ingest_v2.sh](file:///Users/pedro/Desktop/PEDRO/Cursos/ObservatorioGlobal/infra/auto_ingest_v2.sh)

- Update to run the combined ingestion (which now fetches both files per cycle)

---

#### [NEW] [schema_v2_authoritative.sql](file:///Users/pedro/Desktop/PEDRO/Cursos/ObservatorioGlobal/backend/db/schema_v2_authoritative.sql)

- Generated from `pg_dump --schema-only` of the live DB
- Manual annotations: core / materialized view / deprecated / out-of-schema

---

#### [MODIFY] [main_v2.py](file:///Users/pedro/Desktop/PEDRO/Cursos/ObservatorioGlobal/backend/app/main_v2.py)

- Add comment block at top documenting known table name mismatches
- Add `since` query parameter to `/api/v2/signals` endpoint for incremental polling
- Add velocity calculation to signals response (signals in last 60s vs previous 60s)

---

### Workstream B: Frontend

---

#### [MODIFY] [App.css](file:///Users/pedro/Desktop/PEDRO/Cursos/ObservatorioGlobal/frontend-v2/src/App.css)

Complete CSS rewrite from absolute positioning to CSS Grid:
- `.app` → CSS Grid with named template areas (`header`, `radar`, `stream`, `threads`, `matrix`, `anomaly-source`)
- Responsive breakpoints at 1440px and 1024px
- Panel base styles: dark terminal aesthetic, 1px border separators, monospace headers
- Remove absolute positioning from `.header`, `.controls`, `.sidebar`
- Replace `.sidebar` with in-grid panel styling

---

#### [MODIFY] [App.tsx](file:///Users/pedro/Desktop/PEDRO/Cursos/ObservatorioGlobal/frontend-v2/src/App.tsx)

Major restructure:
- Replace flat `<div className="app">` with CSS Grid container using named regions
- Wrap DeckGL in a `<div className="panel-radar">` with `ResizeObserver`
- Move time controls into header (remove floating bottom bar)
- Replace country sidebar with in-grid panel region
- Add `<SignalStream />` in Panel 2 region
- Add `<NarrativeThreadsPlaceholder />` in Panel 3 region
- Add `<CorrelationMatrixPlaceholder />` in Panel 4 region
- Add `<AnomalyPanel />` in Panel 5 region
- Add `<SourceIntegrityPanel />` in Panel 6 region
- Wire all click handlers to new GlobalFilter context
- Fix source selection no-op (line 371)
- Node color: shift to narrative intensity (signal delta vs baseline using anomaly z-score data)
- Add ResizeObserver for DeckGL container resize

---

#### [MODIFY] [FocusContext.tsx](file:///Users/pedro/Desktop/PEDRO/Cursos/ObservatorioGlobal/frontend-v2/src/contexts/FocusContext.tsx)

Extend to GlobalFilter:
- Add `country: string | null` and `theme: string | null` to state
- Add `lockedBy` tracking
- Add `setCountry()`, `setTheme()`, `clearFilter()` actions
- Keep backward-compatible `setFocus()` / `clearFocus()` API
- Show lock badge state data

---

#### [MODIFY] [FocusDataContext.tsx](file:///Users/pedro/Desktop/PEDRO/Cursos/ObservatorioGlobal/frontend-v2/src/contexts/FocusDataContext.tsx)

- Subscribe to new GlobalFilter country/theme state
- Map GlobalFilter to existing `focus_type`/`focus_value` params

---

#### [NEW] [SignalStream.tsx](file:///Users/pedro/Desktop/PEDRO/Cursos/ObservatorioGlobal/frontend-v2/src/components/SignalStream.tsx)

New component — Panel 2:
- Polls `/api/v2/signals?limit=50&since=<timestamp>` every 15 seconds
- Auto-scrolling signal list with pause-on-hover
- Each row: `[HH:MM] [country_code] [theme_label] [sentiment_chip] [source]`
- Shows headline if available (from Translingual ingestion)
- Velocity metric badge: `23 sig/min ▲ +14%`
- Subscribes to GlobalFilter for country/theme filtering
- Click row → `setTheme()` on GlobalFilter

---

#### [NEW] [SignalStream.css](file:///Users/pedro/Desktop/PEDRO/Cursos/ObservatorioGlobal/frontend-v2/src/components/SignalStream.css)

Terminal-style styling for signal feed: monospace font, dense rows, color-coded sentiment chips.

---

#### [NEW] [AnomalyPanel.tsx](file:///Users/pedro/Desktop/PEDRO/Cursos/ObservatorioGlobal/frontend-v2/src/components/AnomalyPanel.tsx)

New component — Panel 5. Extracted from `CrisisDashboard.tsx` logic:
- Always visible (not behind Crisis toggle)
- Shows anomalies from `/api/v2/anomalies`
- Severity levels: CRITICAL/ELEVATED/NOTABLE
- Click anomaly → `setCountry()` on GlobalFilter
- Crisis Mode toggle now applies overlay effect across all panels (via existing `CrisisOverlay`)

---

#### [NEW] [AnomalyPanel.css](file:///Users/pedro/Desktop/PEDRO/Cursos/ObservatorioGlobal/frontend-v2/src/components/AnomalyPanel.css)

Panel styling matching terminal aesthetic.

---

#### [NEW] [SourceIntegrityPanel.tsx](file:///Users/pedro/Desktop/PEDRO/Cursos/ObservatorioGlobal/frontend-v2/src/components/SourceIntegrityPanel.tsx)

New component — Panel 6:
- Uses `/api/indicators/country/{code}` (already working endpoint)
- Shows when country is locked; global aggregate otherwise
- Metrics: diversity score (0–100), quality score, concentration %, volume × baseline
- CSS bar graphs (no chart library)
- Monospace labels, terminal-native aesthetic

---

#### [NEW] [SourceIntegrityPanel.css](file:///Users/pedro/Desktop/PEDRO/Cursos/ObservatorioGlobal/frontend-v2/src/components/SourceIntegrityPanel.css)

---

#### [NEW] [NarrativeThreadsPlaceholder.tsx](file:///Users/pedro/Desktop/PEDRO/Cursos/ObservatorioGlobal/frontend-v2/src/components/NarrativeThreadsPlaceholder.tsx)

Placeholder for Panel 3. Shows "NARRATIVE THREADS — Coming in Phase 2" with brief description.

---

#### [NEW] [CorrelationMatrixPlaceholder.tsx](file:///Users/pedro/Desktop/PEDRO/Cursos/ObservatorioGlobal/frontend-v2/src/components/CorrelationMatrixPlaceholder.tsx)

Placeholder for Panel 4. Shows "CORRELATION MATRIX — Coming in Phase 2" with brief description.

---

### Workstream C: Schema Safety

---

#### [MODIFY] [main_v2.py](file:///Users/pedro/Desktop/PEDRO/Cursos/ObservatorioGlobal/backend/app/main_v2.py)

Add comment block at top documenting table name mismatches:
- `signals_country_hourly` → actual name TBD from schema dump
- `signals_theme_hourly` → actual name TBD
- `signals_source_hourly` → actual name TBD
- `country_daily_v2` → existence TBD

---

#### [MODIFY] [App.tsx](file:///Users/pedro/Desktop/PEDRO/Cursos/ObservatorioGlobal/frontend-v2/src/App.tsx)

Fix line 371 no-op: wire `onSourceSelect` to `setFocus('source', source, source)` via GlobalFilter.

---

## User Review Required

> [!IMPORTANT]
> **Database access**: Workstream A3 requires connecting to the live PostgreSQL database to run `pg_dump --schema-only`. I need to confirm the database is accessible at the connection string in `.env` before proceeding with schema reconciliation.

> [!IMPORTANT]
> **GDELT Translingual format**: I'll research the exact field layout of GDELT Translingual GKG files during A2 implementation. The title/headline may be in the `DocumentIdentifier` URL (extractable) or `Extras` field. I'll document findings in `PROCESSING_AUDIT.md`.

> [!WARNING]
> **DeckGL resize behavior**: Shrinking the map container from 100vw to ~55% may cause initial rendering glitches. The ResizeObserver approach is standard but needs testing with the specific Deck.gl + MapLibre + react-map-gl version combo in use (Deck.gl 9.2, MapLibre 5.13).

---

## Verification Plan

### Automated Tests

**Backend — signal endpoint `since` parameter**:
Currently no test file covers `main_v2.py` endpoints. The existing tests are:
- `test_health.py` — only tests health endpoint response format
- `test_flow_detector.py`, `test_gdelt_parser.py`, `test_gdelt_adapter.py` — unit tests for services

For Phase 1, I will NOT add automated tests for the new `since` parameter (the endpoint is simple and follows existing patterns). Testing will be manual.

### Manual Verification

**Step 1 — Backend health**: 
```bash
curl http://localhost:8000/health | jq '.'
# Expect: status=healthy, db_ok=true
```

**Step 2 — Signal stream endpoint with `since`**:
```bash
# Get signals without since (baseline)
curl "http://localhost:8000/api/v2/signals?limit=5" | jq '.count'

# Get signals with since (should return fewer/no results for future timestamp)
curl "http://localhost:8000/api/v2/signals?limit=5&since=2099-01-01T00:00:00Z" | jq '.count'
# Expect: 0
```

**Step 3 — Frontend build**:
```bash
cd frontend-v2 && npm run build
# Must pass with 0 TypeScript errors
```

**Step 4 — Visual verification**:
Open `http://localhost:3000` in a browser and verify:
1. 6-panel grid layout is visible (map takes ~55% left, stream on right)
2. Map renders correctly at reduced size (nodes, flows, glow layers all visible)
3. Signal Stream shows incoming signals with auto-scroll
4. Anomaly Panel visible on bottom-right with severity levels
5. Source Integrity Panel shows metrics when a country is clicked
6. Panels 3 and 4 show "Coming in Phase 2" placeholders
7. Clicking a country on map filters Signal Stream and shows Source Integrity
8. Time range buttons still work and update all panels
9. Crisis Mode toggle applies red overlay across all panels
10. Responsive: resize to <1024px, verify single-column stacking

**Step 5 — Schema audit file**:
Verify `schema_v2_authoritative.sql` exists and contains annotations.

**Step 6 — Processing audit file**:
Verify `PROCESSING_AUDIT.md` exists and answers all questions from the brief.

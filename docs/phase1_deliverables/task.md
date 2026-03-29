# Phase 1 — Bloomberg Terminal Layout

## Workstream A: Backend
- [x] A1: PROCESSING_AUDIT.md — analyze ingestion pipeline
- [x] A3: schema_v2_authoritative.sql — dump live DB schema
- [x] A2: Ingestion expansion — GDELT Translingual + headline column
- [x] A2: Modify auto_ingest_v2.sh/ingest_v2.py for dual ingestion
- [x] A2: Add `since` param + velocity to `/api/v2/signals`

## Workstream B: Frontend
- [x] B1: App.css → CSS Grid shell with 6 panel regions
- [x] B2: FocusContext.tsx → GlobalFilter extension
- [x] B2: FocusDataContext.tsx → wire to GlobalFilter
- [x] B1: App.tsx → restructure for panel layout + ResizeObserver
- [x] B3: Global Radar enhancements (intensity coloring, pulsing rings)
- [x] B4: SignalStream.tsx + SignalStream.css (new)
- [x] B5: AnomalyPanel.tsx + AnomalyPanel.css (new)
- [x] B6: SourceIntegrityPanel.tsx + SourceIntegrityPanel.css (new)
- [x] NarrativeThreadsPlaceholder.tsx (new)
- [x] CorrelationMatrixPlaceholder.tsx (new)

## Workstream C: Schema Safety
- [x] Add table name mismatch docs in main_v2.py
- [x] Fix source selection no-op in App.tsx

## Deliverables
- [ ] PROCESSING_AUDIT.md
- [ ] schema_v2_authoritative.sql
- [ ] PHASE_1_SUMMARY.md
- [ ] Visual verification (all 10 checks)

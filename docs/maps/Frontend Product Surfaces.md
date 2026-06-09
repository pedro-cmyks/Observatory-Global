# Frontend Product Surfaces MOC

This map tracks which frontend surfaces consume which backend contracts, so new
data work lands in the existing UI instead of creating duplicate panels.

## Start here

- [[2026-06-03-frontend-surface-data-map]] — current route/panel/data-contract
  map for `/`, `/brief`, `/app`, visible vs hidden surfaces, and dynamic-topic
  connection points.
- [[PROJECT_INVENTORY]] — generated frontend-to-API map.
- [[ARCHITECTURE]] — high-level API to frontend data flow.
- [[2026-05-25-production-cycle-and-backlog]] — rule for when frontend work
  should interrupt data/backlog work.
- [[2026-05-24-app-panel-thread-audit]] — surface audit against the seven Atlas
  questions.

## Launch surfaces

- Research Workflow / Workbench investigation:
  [[2026-06-09-research-thread-builder-workbench]]. Target: natural compound
  search produces anchors/options, pin candidates, who-says-what matrix, frame
  comparison, and coverage gaps. Workbench emerges as the pinned route/memory
  and can later export a report. This should extend Search and Workbench rather
  than adding a duplicate panel.
- Workbench early-access gate:
  `frontend-v2/src/components/InteractiveWorkspace.tsx` (preview overlay) +
  `/api/v2/waitlist`. Design: [[2026-06-03-workbench-waitlist-gate-design]].
  Gate logic in `InvestigationWorkspace.tsx`; production-only, bypass with
  `VITE_ENABLE_WORKBENCH=true`.

## Reading-experience track

- Signal snippet enrichment: persist source body text
  (`signals_v2.snippet`) so evidence payloads have body text available and the
  clicked single-signal detail can read as more than a headline. Design:
  [[2026-06-04-signal-snippet-enrichment-design]]. Foundation for per-country
  narrative assembly (F2/F4), thread re-enrichment (F5), reading-panel UX (F1).

## Primary surfaces

- Brief modal Watchlist:
  `frontend-v2/src/components/Briefing.tsx` uses `/api/v2/briefing`.
- Newspaper brief:
  `frontend-v2/src/pages/BriefNewspaper.tsx` uses `/api/v2/briefing` and
  `/api/v2/signals`.
- Narrative Threads panel:
  `frontend-v2/src/components/NarrativeThreads.tsx` uses `/api/v2/threads`.
- Thread detail:
  `frontend-v2/src/components/ThreadFocusPanel.tsx` uses
  `/api/v2/threads/{thread_id}` and `/api/v2/translate/batch`.
- Theme/cluster detail:
  `frontend-v2/src/components/ThemeDetail.tsx` uses `/api/v2/theme/{slug}`.

## Current connection rules

- Dynamic narrative threads are owned by `NarrativeThreads` +
  `ThreadFocusPanel`, with Brief Watchlist and dynamic-topic ThemeDetail as
  secondary entry points.
- Globe/country heat is not a dynamic-topic view; it is country-level signal
  activity and should not be read as topic truth.
- Source Integrity is currently a concentration proxy; use it for
  disinformation/source-amplification reasoning, but do not treat it as a
  source-trust classifier.
- `/brief` Watchlist rows are dynamic-topic aware, but dynamic-topic headline
  snippets should prefer `/api/v2/theme/dynamic-topic-*` over
  `/api/v2/signals?theme=dynamic-topic-*`.
- Hidden/unmounted panels should not receive new data work until they are
  deliberately revived.

## Guardrails

- Do not add a new visible section until checking whether an existing surface
  already owns that contract.
- Visual polish should be batched from recorded walkthroughs.
- Frontend work interrupts the data sprint only when the UI contradicts the
  data or exposes a broken contract.

## Useful checks

- Run `python scripts/project_inventory.py` after endpoint or frontend API
  changes.
- Run `cd frontend-v2 && npm run build` for frontend contract changes.

# Frontend Product Surfaces MOC

This map tracks which frontend surfaces consume which backend contracts, so new
data work lands in the existing UI instead of creating duplicate panels.

## Start here

- [[PROJECT_INVENTORY]] — generated frontend-to-API map.
- [[ARCHITECTURE]] — high-level API to frontend data flow.
- [[2026-05-25-production-cycle-and-backlog]] — rule for when frontend work
  should interrupt data/backlog work.
- [[2026-05-24-app-panel-thread-audit]] — surface audit against the seven Atlas
  questions.

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

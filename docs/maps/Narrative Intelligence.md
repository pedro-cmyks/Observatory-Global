# Narrative Intelligence MOC

This map tracks the product/model shift from static topics to Living Narrative
Threads and emergent narrative discovery.

## Start here

- [[2026-05-25-atlas-narrative-intelligence-framework]] — active model canon.
- [[2026-05-24-living-narrative-threads]] — thread contract and product model.
- [[2026-05-29-emergent-topic-discovery-design]] — emergent discovery layer.
- [[2026-06-01-narrative-cluster-evidence-roles-design]] — role-aware
  cluster/thread classification design.
- [[2026-06-01-narrative-cluster-evidence-roles]] — implementation plan for
  the file-based evidence-role pilot.
- [[2026-05-24-app-panel-thread-audit]] — panel-by-panel mapping to the seven
  Atlas questions.

## Product contract

The visible product should answer:

- why this is moving now,
- what changed recently,
- where it is concentrated,
- which subthreads are forming,
- which sources are driving it,
- what evidence supports it,
- and what related thread it connects to.

## Current implementation

- `/api/v2/threads` merges atlas-topic threads and emergent cluster threads.
- `/api/v2/threads/{thread_id}` dispatches by prefix:
  `emergent-cluster-<id>` uses emergent detail; atlas ids use the atlas thread
  path.
- `/api/v2/briefing.top_atlas_topics` is a Watchlist feed, not the only
  narrative surface.
- `/api/v2/theme/cluster-<id>` opens emergent cluster evidence in the existing
  theme-detail contract.

## Key files

- `backend/app/services/thread_intelligence.py`
- `backend/app/routers/threads.py`
- `backend/app/routers/briefing.py`
- `backend/app/routers/themes.py`
- `backend/app/routers/emergent.py`
- `frontend-v2/src/components/NarrativeThreads.tsx`
- `frontend-v2/src/components/ThreadFocusPanel.tsx`
- `frontend-v2/src/components/ThemeDetail.tsx`

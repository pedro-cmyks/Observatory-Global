# Handoff: Radar Rebuild & Enhancement

**Date:** 2025-11-22
**Status:** In Progress / Stable
**Current Focus:** Flow Animation Enhancement

## 1. Current State (Radar V1)
- **Visualization:**
  - **Flows:** Static `ArcLayer` (Cyan -> Red). **Stable**.
  - **Nodes:** `ScatterplotLayer` with pulsing effect.
  - **Heatmap:** `HeatmapLayer` (Gaussian blur) for radar field effect.
- **Docker Environment:**
  - **Status:** **HEALTHY**. All services running.
  - **Frontend:** http://localhost:5173
  - **Backend:** http://localhost:8000
  - **Fixes Applied:**
    - Fixed TypeScript errors in `useNodeLayer.ts`, `useGaussianRadarLayer.ts`, `MapContainer.tsx`, `DataStatusBar.tsx`.
    - Removed unused `FlowLayer.tsx`.
    - Added `.dockerignore` to optimize build context.

## 2. Docker Clean Restart Guide
If the environment gets stuck or "loading" forever, run these commands from the repo root:

```bash
# 1. Stop all services and remove containers
make down

# 2. Prune stopped containers (optional but recommended)
docker container prune -f

# 3. Restart the stack (rebuilds frontend/backend)
make up
```

## 3. Known Issues
- **Flow Animation:** Currently static. Previous attempts with `TripsLayer` and Shaders caused crashes.
  - **Next Step:** Explore CSS-based overlays or simplified shader approach *after* confirming stability.
- **Data:** `hexmapData` was removed from `DataStatusBar` as it was obsolete.

## 4. Verification Steps
1.  **Check Health:**
    - Backend: `curl http://localhost:8000/health` -> `{"status": "ok"}`
    - Frontend: Open http://localhost:5173
2.  **Check Map:**
    - Toggle between "Classic" and "Heatmap" modes.
    - Verify flows are visible (static lines).

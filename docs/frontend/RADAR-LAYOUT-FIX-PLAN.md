# Radar Layout Fix Plan

## Diagnosis
- **Codebase Status**: The strings "Classic View", "Heatmap View", and "Auto-Refresh" **DO NOT EXIST** in the current `frontend/src`.
- **Root Cause**: The user is viewing `localhost:5173`, which is currently occupied by a **stale Docker container** running the old code. The new code is running on `localhost:5174` (or failed to start on 5173).
- **Resolution**: We must **kill the Docker process** on port 5173 and restart the local dev server on that specific port.

## Layout Refinements
To strictly adhere to the user's latest request ("Design a new, clean layout... from scratch"), I will verify and refine the `GlobalRadar` components I just built.

### 1. `GlobalRadarPage.tsx`
- **Goal**: Single entry point.
- **Check**: Ensure it imports `RadarControls` and `RadarMap`.
- **Refinement**: Ensure the header is "Global Observatory" as requested.

### 2. `RadarControls.tsx`
- **Goal**: Minimalist top bar.
- **Requirements**:
  - [x] No "Classic/Heatmap" tabs.
  - [x] Toggle for "Heatmap" (Checkbox).
  - [x] Toggle for "Flows" (Checkbox).
  - [x] Toggle for "Nodes" (Checkbox).
  - [x] Time Window: Compact (1h, 6h, 12h, 24h).
  - [x] **REMOVE**: "Countries" dropdown (already gone).
  - [x] **REMOVE**: "Auto Refresh" (already gone).

### 3. `RadarMap.tsx`
- **Goal**: Stable Mercator projection.
- **Check**: Ensure `Map` component and DeckGL layers use compatible coordinate systems.

## Execution Steps

1.  **Kill Stale Processes**:
    -   Run `docker kill $(docker ps -q)` to force-kill all containers.
    -   Run `kill -9 $(lsof -t -i:5173)` to force-kill anything else on port 5173.
2.  **Verify Code**:
    -   Review `RadarControls.tsx` one last time to ensure it matches the "clean layout" request perfectly.
3.  **Restart Server**:
    -   Run `npm run dev` specifically on port 5173.
4.  **Verify**:
    -   Use browser tool to confirm the *new* UI is visible.

## Verification
- **Automated**: Browser tool visits `http://localhost:5173` and checks for "Radar Heatmap" checkbox.
- **Manual**: User refreshes page.

# Radar Redesign & Fix Plan

## Current Status
- **Git State**: The "Clean Rebuild" files (`GlobalRadarPage`, `radarStore`, etc.) exist but are **untracked/uncommitted**.
- **User Experience**: You are seeing the **old UI** (Commit `b0fb9af` or earlier) because the new `App.tsx` entry point hasn't been picked up by your browser/dev-server.
- **Data Source**: The new code is wired to **Real GDELT Data** (`/v1/flows`), with a fallback to placeholders only if the API fails.

## Plan

### 1. Commit the Clean Rebuild
**Goal**: Persist the new architecture and remove the old "Classic/Heatmap" code forever.
- **Action**: `git add .` and `git commit -m "feat(radar): replace legacy UI with new GlobalRadar architecture"`.
- **Result**: The codebase will officially contain the new `GlobalRadar` components and the modified `App.tsx`.

### 2. Verify & Polish Controls
**Goal**: Ensure the UI strictly matches your "Redesign" requirements.
- **File**: `frontend/src/components/GlobalRadar/RadarControls.tsx`
- **Check**:
  - [x] No "Classic/Heatmap" toggle.
  - [x] No "Countries" dropdown.
  - [x] No "Auto-Refresh".
  - [x] Simple "Layers" checkboxes (Heatmap, Flows, Nodes).
  - [x] Simple "Time Window" selector.

### 3. Enforce Mercator Projection
**Goal**: Solve the "floating layers" issue by sticking to a standard 2D projection.
- **File**: `frontend/src/components/GlobalRadar/RadarMap.tsx`
- **Action**: Verify `Map` component uses standard `Mercator` (default) and DeckGL layers use `[lon, lat]` coordinates.
- **Result**: Nodes and flows will be "pinned" to the map surface, even when panning/zooming.

### 4. Restart & Verify
**Goal**: Force the browser to render the new code.
- **Action**: You will need to **restart your dev server** (`npm run dev`) and **hard refresh** the browser.
- **Result**: You will see the new "Observatory Global" header, the simplified controls, and the dark map with radar layers.

## Next Steps
I will execute Step 1 (Commit) and Step 2/3 (Verify Code) immediately.
Then I will ask you to restart the server.

# Radar Fix & Layout Plan

## Diagnosis
- **Blank Page Cause**: Likely a runtime error in `RadarMap` (e.g., missing Mapbox token or DeckGL crash) or `GlobalRadarPage`. Since `App.tsx` is correct, the crash happens on mount.
- **Legacy UI Cause**: Confirmed as a stale process on port 5173. We will fix this by ensuring we run on a clean port or successfully kill the zombie.
- **Architecture**: The new `GlobalRadar` architecture is correct but needs to be robust against data failures and missing env vars.

## Plan

### 1. Fix Blank Page (Robustness)
- **Error Boundary**: Wrap `GlobalRadarPage` in a simple Error Boundary to catch crashes and show a visible error message instead of a blank screen.
- **Mapbox Token**: Hardcode the token temporarily in `RadarMap.tsx` (or ensure env var is read correctly) to rule out auth failures.
- **Safe Data**: Ensure `radarStore` initializes with safe empty data to prevent DeckGL from crashing on undefined inputs.

### 2. Finalize Layout (User Requirements)
- **Refine `GlobalRadarPage`**:
  - Ensure "Global Observatory" header is visible.
  - Verify z-indexes so controls are clickable.
- **Refine `RadarControls`**:
  - Double-check "Classic/Heatmap" tabs are gone.
  - Ensure toggles work.
- **Refine `RadarMap`**:
  - Ensure `Mercator` projection is used (no globe).
  - Add a fallback "Loading" or "Error" state if map fails to load.

### 3. Execution & Verification
1.  **Modify Code**: Implement the Error Boundary and safety checks.
2.  **Kill & Restart**: Aggressively kill all node/docker processes.
3.  **Run**: Start `npm run dev` on a specific port (e.g., 5175) to avoid any 5173 conflicts.
4.  **Verify**: Open browser to new port.

## Verification Steps
- [ ] Page loads with "Global Observatory" header.
- [ ] No "Classic View" tabs.
- [ ] Map renders (dark background).
- [ ] Toggles work (console logs or visual change).

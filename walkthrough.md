# Radar Frontend Rebuild Walkthrough

## Overview
We have completely rebuilt the Global Observatory frontend to focus on a clean, stable, and unified "Global Information Radar".
The new implementation uses a single `GlobalRadarPage` with a dedicated `radarStore` and a clean separation of concerns.

## Changes
- **New Architecture**:
  - `GlobalRadarPage`: Main container.
  - `RadarMap`: Mapbox + DeckGL integration (Mercator projection).
  - `RadarControls`: Unified layer toggles and time window selector.
  - `RadarSidebar`: Detail panel for selected nodes.
  - `radarStore`: Zustand store for state management.
- **Removed**:
  - Old `GlobalObservatory` and `map` components (deleted/replaced).
- **Features**:
  - **Layers**: Heatmap, Flows, Nodes (all togglable).
  - **Time Window**: 1h, 6h, 12h, 24h selectors (wired to backend).
  - **Interaction**: Hover tooltips and click-to-open sidebar.

## Verification Steps

### 1. Build & Run
```bash
cd frontend
npm run dev
```
Open `http://localhost:5173`.

### 2. Visual Check
- [ ] **Map Loads**: You should see a dark map (Mercator).
- [ ] **Layers Visible**:
  - **Heatmap**: Glowing areas around countries.
  - **Nodes**: Circles sized by intensity (Green=Positive, Red=Negative).
  - **Flows**: Arcs connecting countries.

### 3. Interaction Check
- [ ] **Toggles**: Uncheck "Radar Heatmap" -> Heatmap should disappear.
- [ ] **Time Window**: Click "24h" -> Map should refresh (loading indicator in controls).
- [ ] **Hover**: Hover over a node -> Tooltip appears with details.
- [ ] **Click**: Click a node -> Sidebar slides in from the right.

### 4. Data Check
- The app attempts to fetch from `http://localhost:8000/v1/flows`.
- If the backend is running, you see real data.
- If not, it might error (check console). *Note: We implemented a fallback to empty state on error, but you can uncomment the placeholder generator in `radarStore.ts` if you want to test without backend.*

## Screenshots
*(Add screenshots here after running)*

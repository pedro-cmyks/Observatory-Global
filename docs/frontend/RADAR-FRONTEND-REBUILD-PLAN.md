# Radar Frontend Rebuild Plan

## Goal
Rebuild the "Global Observatory" frontend from scratch to create a clean, stable, and unified "Global Information Radar" visualization.
Focus on a single, robust view with togglable layers (Heatmap, Flows, Nodes) and a working time window selector.

## User Review Required
> [!IMPORTANT]
> **Destructive Action**: This plan involves deleting/replacing the current `GlobalObservatory` and `map` components.
> **Projection**: We will use **Mercator** (2D/Flat) initially to ensure layer stability and avoid "floating" artifacts. Globe projection can be revisited later once the core data layers are robust.

## Proposed Architecture

### 1. Component Structure
We will create a new directory structure to ensure a clean break from the old code.
`frontend/src/components/GlobalRadar/` (New main directory)

```
GlobalRadar/
├── GlobalRadarPage.tsx       # Main container (Layout)
├── RadarMap.tsx              # Mapbox + DeckGL integration
├── RadarControls.tsx         # Floating layer toggles & time selector
├── RadarSidebar.tsx          # Detail panel (slide-out)
├── RadarTooltip.tsx          # Custom tooltip component
└── layers/                   # DeckGL layer generators
    ├── HeatmapLayer.ts
    ├── FlowLayer.ts
    └── NodeLayer.ts
```

### 2. State Management
`frontend/src/store/radarStore.ts`
- **State**:
  - `timeWindow`: '1h' | '6h' | '12h' | '24h'
  - `activeLayers`: { heatmap: boolean, flows: boolean, nodes: boolean }
  - `selectedNode`: NodeData | null
  - `hoveredNode`: NodeData | null
  - `data`: { nodes: [], flows: [] }
  - `isLoading`: boolean
- **Actions**:
  - `setTimeWindow(window)`: Updates state and refetches data.
  - `toggleLayer(layer)`: Toggles visibility.
  - `selectNode(node)`: Opens sidebar.

### 3. Data Flow
1. **Init**: `GlobalRadarPage` mounts -> calls `radarStore.fetchData(timeWindow)`.
2. **Fetch**: `radarStore` calls API `/v1/flows?time_window=...`.
3. **Render**: `RadarMap` subscribes to `radarStore.data` and `radarStore.activeLayers`.
   - Generates DeckGL layers based on data and visibility.
4. **Interaction**:
   - Click on Node -> `radarStore.selectNode` -> `RadarSidebar` opens.
   - Change Time -> `radarStore.setTimeWindow` -> Fetch new data -> Map updates.

## Implementation Steps

### Phase 1: Clean Slate & Infrastructure
1.  **Delete/Archive**: Remove `frontend/src/components/GlobalObservatory` and `frontend/src/components/map` (or move to `_archive` if paranoid, but user said "destroy").
2.  **Store**: Create `frontend/src/store/radarStore.ts`.
3.  **Page**: Create `frontend/src/components/GlobalRadar/GlobalRadarPage.tsx`.

### Phase 2: The Map Core
1.  **Map Component**: Implement `RadarMap.tsx` using `react-map-gl` and `deck.gl`.
    -   **Projection**: Mercator.
    -   **Base Map**: Mapbox Dark v11.
2.  **Layers**:
    -   **Heatmap**: `HeatmapLayer` (DeckGL) using node intensity.
    -   **Nodes**: `ScatterplotLayer` (DeckGL) for countries.
    -   **Flows**: `ArcLayer` (DeckGL) for connections.

### Phase 3: UI & Interaction
1.  **Controls**: Implement `RadarControls.tsx` (absolute positioned top-left or top-center).
2.  **Sidebar**: Implement `RadarSidebar.tsx` (absolute positioned right, slide-in).
3.  **Wiring**: Connect all interactions to `radarStore`.

## Verification Plan

### Automated Tests
-   **Unit Tests**: Test `radarStore` logic (layer toggling, data fetching state).
-   **Component Tests**: Render `RadarControls` and verify clicks update store.

### Manual Verification
1.  **Load Page**: Open `http://localhost:5173`.
2.  **Map Renders**: Verify dark map loads without errors.
3.  **Layers**:
    -   Toggle "Heatmap" -> Heatmap appears/disappears.
    -   Toggle "Flows" -> Arcs appear/disappear.
4.  **Time Window**:
    -   Click "24h" -> Loading state -> Data updates (mock or real).
5.  **Interaction**:
    -   Hover node -> Tooltip shows.
    -   Click node -> Sidebar opens with details.

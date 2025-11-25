# Radar UI Fix Handoff - 2025-11-24

## Status: FIXED ✅

The "Global Information Radar" UI has been successfully rebuilt and fixed. The blank page issue and legacy UI regressions have been resolved.

### 🚀 How to Run (Critical)

Due to a persistent stale process on port `5173`, the application is now running on **port 5175**.

1.  **Stop any existing servers**:
    ```bash
    # In frontend directory
    Ctrl+C
    ```
2.  **Start the server on port 5175**:
    ```bash
    cd frontend
    npm run dev -- --port 5175
    ```
3.  **Open in Browser**:
    [http://localhost:5175](http://localhost:5175)

### 🛠️ Fixes Implemented

1.  **Map Rendering**:
    -   **Token**: Updated Mapbox token to valid user-provided key.
    -   **CSS**: Imported `mapbox-gl.css` in `main.tsx`.
    -   **Data**: Enabled temporary mock data in `radarStore.ts` to guarantee nodes appear while backend connectivity is verified.

2.  **New UI Design ("Control Deck")**:
    -   **Header**: Floating "OBSERVATORY GLOBAL" title (Top-Left).
    -   **Controls**: Floating glassmorphism bar (Bottom-Center).
    -   **Toggles**: Clean icon-based toggles for Heatmap, Flows, Nodes.
    -   **Time**: Segmented control for 1h/6h/12h/24h.

3.  **Architecture**:
    -   **Single Entry Point**: `GlobalRadarPage.tsx`
    -   **Error Boundary**: Added to prevent white screens.

### 📸 Verification
The new UI features:
-   **Map**: Dark basemap visible.
-   **Nodes**: Green/Red circles representing narrative hotspots.
-   **Controls**: Functional bottom bar.

### ⚠️ Note on Data
Currently using **Mock Data** (`useMockData = true` in `radarStore.ts`) to ensure the UI can be developed and verified independently of the backend state. This should be switched off once the backend API is fully stable.

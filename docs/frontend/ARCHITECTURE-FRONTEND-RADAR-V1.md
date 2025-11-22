# Architecture: Global Information Radar (Frontend V1)

## Overview
This document defines the architecture for the complete rebuild of the **Observatorio Global** frontend. The goal is to create a production-ready, maintainable "Global Information Radar" application that visualizes narrative flows and intensity.

## Tech Stack
*   **Framework**: React 18 + TypeScript
*   **Build Tool**: Vite
*   **State Management**: Zustand
*   **Map Engine**: Mapbox GL JS (Base) + deck.gl (Visualization Overlay)
*   **Styling**: CSS Modules / Tailwind (if available) or standard CSS
*   **API Client**: Axios

## Directory Structure
```
src/
├── components/
│   ├── layout/          # MainLayout, Header, SidebarContainer
│   ├── map/             # MapContainer, DeckGLOverlay, Tooltips
│   │   ├── layers/      # Custom hooks for deck.gl layers (useNodeLayer, useFlowLayer, etc.)
│   │   └── controls/    # Map controls (TimeWindow, ViewMode)
│   ├── sidebar/         # CountryInsightPanel, NarrativeDetails
│   └── ui/              # Shared UI components (Button, Badge, Spinner)
├── hooks/               # Shared hooks (useDebounce, etc.)
├── lib/
│   ├── api.ts           # Centralized API client
│   ├── mapTypes.ts      # Type definitions matching Backend API
│   └── utils.ts         # Helpers
├── store/
│   └── mapStore.ts      # Global state (Data, Filters, UI State)
└── styles/              # Global styles
```

## Core Components

### 1. Data Layer (`store/mapStore.ts`)
Single source of truth for the application state.
*   **Data**: `flowsData` (Hotspots + Flows) from `/v1/flows`.
*   **Filters**: `timeWindow`, `selectedCountries`.
*   **UI State**: `viewMode` ('classic' | 'radar'), `selectedHotspot`, `hoveredObject`.
*   **Actions**: `fetchFlowsData()`, `setViewMode()`, `setSelectedHotspot()`.

### 2. Layout (`components/layout/MainLayout.tsx`)
*   **Header**: Logo, Global Stats, About.
*   **Map Area**: Full screen.
*   **Sidebar**: Collapsible, overlaying the right side of the map.
*   **Controls**: Floating over the map (Top-Left).

### 3. Map Architecture (`components/map/MapContainer.tsx`)
*   **Base**: `react-map-gl` with Globe projection.
*   **Overlay**: Single `DeckGLOverlay` managing all visualization layers.
*   **Layers**:
    *   `useGaussianRadarLayer`: HeatmapLayer (Radar View).
    *   `useFlowLayer`: ArcLayer (Unified "Winds").
    *   `useNodeLayer`: ScatterplotLayer (Classic View).
*   **Interaction**:
    *   **Hover**: Updates `hoveredObject` -> Renders Tooltip.
    *   **Click**: Updates `selectedHotspot` -> Opens Sidebar.

### 4. Sidebar (`components/sidebar/CountryInsightPanel.tsx`)
Displays narrative intelligence for the selected country.
*   **Header**: Country Name, Flag/Code.
*   **Metrics**: Intensity Score, Sentiment Badge.
*   **Narrative**: "Why is this heating up?" (Top Themes).
*   **Actors**: Key Persons, Organizations.
*   **Sources**: Outlet list, Source Diversity score.

## Implementation Phases

### Phase 1: Clean Slate & Core Structure
1.  Establish directory structure.
2.  Clean up `src/components` (remove legacy).
3.  Ensure `mapStore` and `api` are robust.

### Phase 2: Map & Layers
1.  Implement `useFlowLayer` (deck.gl) to replace Mapbox layer.
2.  Refine `useGaussianRadarLayer` (Meteorological look).
3.  Refine `useNodeLayer` (Classic look).
4.  Ensure unified `DeckGLOverlay`.

### Phase 3: UI & Interaction
1.  Build `CountryInsightPanel` (Sidebar) with full data wiring.
2.  Build `MapTooltip` with unified data.
3.  Implement Top Control Bar (Time, View Mode).

### Phase 4: Polish
1.  Animations (Flows, Sidebar transitions).
2.  Error handling & Loading states.
3.  Responsive design tweaks.

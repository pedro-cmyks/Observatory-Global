# Architecture: Global Information Radar (V1)

## Overview
This document defines the architecture for the "Global Information Radar" map visualization. The goal is to replace the fragile legacy implementation with a robust, data-driven stack using **Mapbox GL JS** (base) and **deck.gl** (visualization layers).

## Core Principles
1.  **Single Source of Truth**: Both "Classic" and "Radar" views consume the exact same data (`/v1/flows` hotspots).
2.  **Unified Rendering**: A single `DeckGLOverlay` manages all data layers. No separate React components for map layers unless absolutely necessary.
3.  **Data-Driven**: No static debug points. Every visual element represents real (or mocked) backend data.
4.  **Meteorological Metaphor**:
    *   **Storms**: Gaussian heatmaps representing narrative intensity.
    *   **Winds**: Animated flow arcs representing narrative propagation.

## Architecture Components

### 1. Data Layer (`mapStore.ts`)
The store manages the state and fetches data.
*   **State**:
    *   `flowsData`: The primary payload containing `hotspots` (nodes) and `flows` (edges).
    *   `viewMode`: 'classic' | 'radar' (formerly 'heatmap').
    *   `timeWindow`: '1h', '24h', etc.
*   **Actions**:
    *   `fetchFlowsData()`: The ONLY data fetching action.
    *   **Removed**: `fetchHexmapData` (Legacy H3 implementation).

### 2. Map Container (`MapContainer.tsx`)
The orchestrator component.
*   **Base**: `react-map-gl` (`<Map>`) with `mapbox-gl` globe projection.
*   **Overlay**: `DeckGLOverlay` (wrapping `MapboxOverlay`).
*   **Responsibility**:
    *   Manages `viewState` (zoom, lat, lon).
    *   Instantiates layer hooks.
    *   Passes layers to `DeckGLOverlay`.
    *   Renders UI controls (Sidebar, Toggles).

### 3. Visualization Layers (Hooks)
All layers are defined as custom hooks returning deck.gl layer instances.

#### A. `useGaussianRadarLayer` (The "Storms")
*   **Type**: `HeatmapLayer` (@deck.gl/aggregation-layers).
*   **Data Source**: `flowsData.hotspots`.
*   **Visuals**:
    *   `radiusPixels`: ~60-80px (diffuse blobs).
    *   `intensity`: Driven by `hotspot.intensity`.
    *   `colorRange`: Meteorological palette (Blue -> Green -> Yellow -> Red).
*   **Interaction**: Hover for tooltip.

#### B. `useFlowLayer` (The "Winds")
*   **Type**: `ArcLayer` (@deck.gl/layers).
*   **Data Source**: `flowsData.flows`.
*   **Visuals**:
    *   Animated "marching ants" or gradient arcs.
    *   Color: Cyan/White (high contrast against dark map).

#### C. `useNodeLayer` (Classic View)
*   **Type**: `ScatterplotLayer` (@deck.gl/layers).
*   **Data Source**: `flowsData.hotspots`.
*   **Visuals**:
    *   Circles sized by intensity.
    *   Visible ONLY in 'classic' mode.

### 4. Interaction Model
*   **Hover**:
    *   Map detects hover on any layer.
    *   Updates `hoverInfo` state.
    *   Renders `MapTooltip` at cursor position.
*   **Click**:
    *   Map detects click on Hotspot (Classic) or Storm (Radar).
    *   Updates `selectedHotspot` in store.
    *   Opens `CountrySidebar`.

## Implementation Plan

### Phase 1: Clean Base & Wiring
1.  Refactor `mapStore` to remove hexmap legacy.
2.  Refactor `MapContainer` to use a unified `deckLayers` array.
3.  Ensure `/v1/flows` data powers everything.

### Phase 2: Radar Layer
1.  Implement `useGaussianRadarLayer`.
2.  Tune Gaussian parameters for "Storm" look.
3.  Ensure correct globe wrapping (no inner-sphere artifacts).

### Phase 3: Interaction
1.  Standardize Tooltip for all layers.
2.  Ensure Sidebar works for both views.

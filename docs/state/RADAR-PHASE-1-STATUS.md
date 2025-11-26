# Radar Phase 1 Status: Live GDELT Integration

**Date:** 2025-11-26
**Status:** Stable / Phase 1 Complete

## Overview
We have successfully integrated the frontend Radar visualization with live GDELT data via the backend API. The system now fetches, processes, and visualizes the latest 15-minute GDELT GKG snapshot.

## Working Features (Phase 1)
- **Live Data Pipeline**: 
  - Backend fetches the latest 15-minute GKG file from GDELT.
  - Signals are extracted for countries, including Themes, Actors (Persons/Orgs), and Sources.
  - Data is cached in Redis and persisted to PostgreSQL (fallback).
- **Map Visualization**:
  - **Heatmap**: Represents signal intensity (mentions/tone).
  - **Flows**: Visualizes narrative connections between countries based on shared themes.
  - **Nodes**: Interactive country nodes with intensity scaling.
- **Sidebar Intelligence**:
  - Displays real data for the selected country:
    - **Intensity & Sentiment**: Direct metrics.
    - **Volume Metrics**: Total mentions and active sources.
    - **Dominant Themes**: Top themes with progress bars.
    - **Key Actors**: Top mentioned people and organizations.
    - **Source Intelligence**: Diversity score and top news outlets.
  - **Activity Timeline**: Placeholder with "LIVE (15m)" badge indicating current snapshot.
- **Time Window Wiring**:
  - UI buttons (1h, 6h, 12h, 24h) are wired to the API.
  - **Current Behavior**: Filters the *fallback* database query if live fetch fails. Live fetch always gets the latest 15m snapshot.

## Initial Phase 2 Features (Experimental)
- **Search Bar**: UI component added to the map.
- **Query Filtering**: Backend `SignalsService` supports in-memory filtering of the 15m snapshot by keyword (Theme, Actor, Source).

## Missing / Not Implemented Yet
- **True Historical Time Windows**: 
  - We do not yet ingest or store historical GDELT files (past 15m) systematically.
  - "Last 24h" view currently shows the latest 15m snapshot (unless falling back to DB).
- **Advanced Query Mode**:
  - Full historical search is not available.
  - Complex boolean queries or multi-entity filtering is not implemented.

## Next Steps (Phase 2)
1.  **Refine Query Mode**: Verify and polish the search experience on the current live data.
2.  **Historical Ingestion**: Build the pipeline to ingest and store GDELT files over time to enable true 24h/7d analysis.

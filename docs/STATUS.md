# Project Status

## Current State
**Sprint**: UI/UX Polish (Week 2)
**Status**: Active / Verification

## Working Features
- **Data Ingestion**: GDELT 2.0 GKG ingestion working (Signals, Themes, Locations, Persons, Organizations).
- **Data Aggregation**: Hourly aggregation by Country and Theme.
- **API Endpoints**:
    - `/v1/heatmap`: Returns weighted points for heatmap visualization (filtered for validity).
    - `/v1/nodes`: Returns country nodes with sentiment and top themes.
    - `/v1/flows`: Returns information flows between countries.
- **Frontend**:
    - **Radar Map**: Deck.gl visualization with Heatmap, Nodes (Sentiment Gradient), and Flows (Proportional).
    - **Sidebar**: Detailed node information with human-readable themes and sentiment analysis.
    - **Controls**: Time window selector (1h, 6h, 12h, 24h, All).

## Known Issues
- **Data**: `signal_entities` table needs population (ingestion logic updated, waiting for new data).
- **UI**: "Activity Timeline" removed until backend support is added.

## Recent Fixes
- **Heatmap**: Fixed points appearing over oceans by validating coordinates against country bounds.
- **Sentiment**: Fixed sentiment display to show 2 decimal places.
- **Themes**: Implemented human-readable theme labels.
- **Entities**: Added parsing for Persons and Organizations in ingestion service.
- **UI**: Improved node colors (gradient) and flow lines (proportional width).

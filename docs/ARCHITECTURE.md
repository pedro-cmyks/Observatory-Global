# Observatory Global - System Architecture

## Overview
Observatory Global is a real-time trend tracking application that ingests data from GDELT, aggregates it, and visualizes it on a global map.

## Data Flow
1.  **Ingestion**: `backend/app/services/gdelt_ingest.py` fetches GKG 2.0 files from GDELT every 15 minutes.
    -   Parses CSV content.
    -   Extracts signals, themes, and locations.
    -   Auto-creates new countries if they don't exist in the DB.
2.  **Storage**: Data is stored in PostgreSQL.
    -   `gdelt_signals`: Raw signal data (kept for 7 days).
    -   `countries`: Reference table for country metadata.
    -   `theme_aggregations_1h`: Hourly aggregations by country and theme (kept for 90 days).
    -   `country_aggregates`: Daily/Monthly rollups.
3.  **Aggregation**: `backend/app/services/aggregator.py` runs hourly to populate `theme_aggregations_1h`.
4.  **API**: FastAPI backend serves data to frontend.
    -   `/v1/nodes`: Aggregated country data (intensity, sentiment, top themes).
    -   `/v1/heatmap`: Point-level data for heatmap visualization.
    -   `/v1/flows`: Flow data between countries.
5.  **Frontend**: React + Deck.gl application.
    -   Visualizes data on a 3D globe.
    -   Time window selector filters data.

## Database Schema

### Core Tables
-   **`gdelt_signals`**: The main fact table.
    -   `id`, `timestamp`, `country_code`, `latitude`, `longitude`, `tone_overall`, `primary_theme`.
    -   `all_locations`: JSONB field storing all locations mentioned in the article.
-   **`countries`**: Reference table.
    -   `country_code` (PK), `country_name`, `latitude`, `longitude` (centroid).

### Aggregation Tables
-   **`theme_aggregations_1h`**:
    -   `hour_bucket`, `country_code`, `theme_code`.
    -   Metrics: `signal_count`, `avg_tone`, `total_theme_mentions`.
-   **`country_aggregates`**:
    -   `window_type` ('daily', 'monthly'), `window_start`.
    -   Metrics: `total_events`, `avg_tone`.

## Key Components

### Backend (`backend/app`)
-   `services/gdelt_ingest.py`: Handles GDELT file downloading and parsing.
-   `services/aggregator.py`: Aggregates raw signals into hourly stats.
-   `services/data_retention.py`: Cleans up old data and manages retention policies.
-   `api/v1/`: API endpoints.

### Frontend (`frontend/src`)
-   `components/GlobalRadar/`: Main map visualization components.
-   `store/radarStore.ts`: State management for map data.

## Deployment
-   **Docker Compose**: Orchestrates `api`, `web`, `postgres`, and `redis` services.
-   **Makefile**: Provides shortcuts for common commands (`make up`, `make down`, `make logs`).

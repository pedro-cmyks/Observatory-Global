# Observatory Global - System Report

Generated: 2025-12-18

## 1. Backend Architecture

### Entry Point
- Main application: `backend/app/main_v2.py`
- FastAPI with async PostgreSQL (asyncpg)
- CORS enabled for all origins

### Key Endpoints

| Endpoint | Purpose |
|----------|---------|
| `GET /health` | System health, DB connectivity, ingestion status |
| `GET /api/v2/nodes` | Country nodes with aggregated stats |
| `GET /api/v2/flows` | Theme co-occurrence flows between countries |
| `GET /api/v2/country/{code}` | Detailed country information |
| `GET /api/v2/briefing` | Morning briefing summary |
| `GET /api/v2/search` | Full-text search across themes, countries, sources |
| `GET /api/indicators/tooltips` | Trust indicator explanations |
| `GET /api/indicators/country/{code}` | Trust indicators for a country |

---

## 2. Ingestion System

### Entry Points
- `scripts/start_ingestion.sh` - Shell wrapper
- `backend/ingestion/` - Core ingestion logic

### Schedule
- Mode: Manual trigger or continuous (15-minute intervals)
- Lock file: `/tmp/observatory_ingestion.lock`

---

## 3. Database

### Connection
- URL: `postgresql://observatory:changeme@localhost:5432/observatory`
- Configured via `DATABASE_URL` environment variable

### Primary Tables
- `signals` - Main signals table with timestamps, themes, countries
- Materialized views for aggregation

---

## 4. Data Flow Diagram

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│   GDELT API     │────▶│   Ingestion     │────▶│   PostgreSQL    │
│   (External)    │     │   (Python)      │     │   + TimescaleDB │
└─────────────────┘     └─────────────────┘     └────────┬────────┘
                                                         │
                                                         ▼
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│   Browser       │◀────│   Frontend-v2   │◀────│   FastAPI       │
│   (User)        │     │   (React/Vite)  │     │   Backend       │
└─────────────────┘     └─────────────────┘     └─────────────────┘
```

---

## 5. Frontend Architecture

### Canonical Frontend
- Location: `frontend-v2/`
- Port: 3000 (strictPort)
- Stack: React + Vite + MapLibre + Deck.gl

### Legacy Frontend (DEPRECATED)
- Location: `frontend/`
- Port: 5173
- Stack: React + Vite + Mapbox (requires API token)
- Status: `npm run dev` shows deprecation warning

---

## 6. Known Configurations

### Environment Variables
- `DATABASE_URL` - PostgreSQL connection string
- No Mapbox token required (frontend-v2 uses MapLibre)

### Docker Containers
- `observatory-postgres` - PostgreSQL 15
- `observatory-redis` - Redis 7 (optional caching)

# Observatory Global (Observatorio Global)

Global Narrative Observatory - A real-time trends and narrative tracking platform.

## Overview

This MVP aggregates trending topics from multiple public data sources:
- GDELT 2.0 (Global Database of Events, Language, and Tone)
- Google Trends (via pytrends)
- Wikipedia Pageviews API

The system performs NLP analysis including language detection, deduplication, and topic extraction.

## Tech Stack

**Backend:**
- Python 3.11
- FastAPI
- Redis (caching)
- PostgreSQL (ready for future use)

**Frontend:**
- React + TypeScript
- Vite
- Recharts
- Axios

**Infrastructure:**
- Docker & Docker Compose
- Google Cloud Run (via Cloud Code)

## Getting Started

### Prerequisites

- Docker and Docker Compose
- Node.js 18+ (for local frontend development)
- Python 3.11+ (for local backend development)
- Google Cloud SDK (for deployment)

### Running Locally

1. Clone the repository:
```bash
git clone <repo-url>
cd observatory-global
```

2. Copy environment variables:
```bash
cp .env.example .env
```

3. Start all services:
```bash
cd infra
docker compose up --build
```

4. Access the application:
- Frontend: http://localhost:5173
- API: http://localhost:8000
- API Docs: http://localhost:8000/docs

### Testing the API

```bash
# Health check
curl http://localhost:8000/health

# Get top trends for Colombia
curl "http://localhost:8000/v1/trends/top?country=CO&limit=10"

# Get top trends for USA
curl "http://localhost:8000/v1/trends/top?country=US&limit=10"
```

## Development

### Backend Development

```bash
cd backend
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -e .
uvicorn app.main:app --reload --port 8000
```

### Frontend Development

```bash
cd frontend
npm install
npm run dev
```

### Running Tests

```bash
cd backend
pytest
```

## Deployment

### Deploy to Google Cloud Run with Cloud Code

1. Install Cloud Code extension for VS Code or use gcloud CLI

2. Set your GCP project:
```bash
gcloud config set project YOUR_PROJECT_ID
```

3. Deploy API:
```bash
gcloud run deploy observatory-api \
  --source ./backend \
  --region us-central1 \
  --allow-unauthenticated
```

4. Deploy Frontend:
```bash
# Update VITE_API_URL in .env to point to your deployed API
gcloud run deploy observatory-web \
  --source ./frontend \
  --region us-central1 \
  --allow-unauthenticated
```

### Using Cloud Code Configuration

The project includes Cloud Code configurations in `infra/cloudcode/`:

- `cloudrun.dev.yaml` - API service configuration
- `cloudrun.web.dev.yaml` - Frontend service configuration

Deploy using Cloud Code:
1. Open Command Palette (Cmd/Ctrl+Shift+P)
2. Run "Cloud Code: Deploy to Cloud Run"
3. Select the appropriate configuration file

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| APP_ENV | Environment (development/production) | development |
| APP_PORT | Backend port | 8000 |
| REDIS_HOST | Redis hostname | redis |
| REDIS_PORT | Redis port | 6379 |
| GDELT_BASE | GDELT API base URL | http://data.gdeltproject.org/gdeltv2 |
| MAPBOX_TOKEN | Mapbox token (optional) | - |
| VITE_API_URL | Frontend API URL | http://localhost:8000 |

## Architecture

```
┌─────────────┐      ┌──────────────┐      ┌──────────────┐
│   Frontend  │─────▶│   FastAPI    │─────▶│    Redis     │
│ React + Vite│      │   Backend    │      │   (Cache)    │
└─────────────┘      └──────────────┘      └──────────────┘
                            │
                            ├──────▶ GDELT API
                            ├──────▶ Google Trends
                            └──────▶ Wikipedia API
```

## API Endpoints

### GET /health
Health check endpoint.

**Response:**
```json
{
  "status": "ok"
}
```

### GET /v1/trends/top
Get top trending topics for a country.

**Parameters:**
- `country` (required): ISO 3166-1 alpha-2 country code (e.g., "US", "CO", "BR")
- `limit` (optional): Number of topics to return (default: 10)

**Response:**
```json
{
  "country": "CO",
  "generated_at": "2025-01-11T10:30:00Z",
  "topics": [
    {
      "id": "topic-1",
      "label": "Economic Reform",
      "count": 156,
      "sample_titles": ["Title 1", "Title 2"],
      "sources": ["gdelt", "trends"],
      "confidence": 0.87
    }
  ]
}
```

## Future Enhancements

- [ ] PostgreSQL integration for historical data
- [ ] Real-time WebSocket updates
- [ ] Interactive map visualization (Mapbox)
- [ ] Sentiment analysis
- [ ] Multi-language support
- [ ] Authentication and user preferences
- [ ] Export functionality (CSV, JSON, PDF)
- [ ] Scheduled background jobs for data collection

## License

MIT

## Contributing

Contributions are welcome! Please open an issue or submit a pull request.

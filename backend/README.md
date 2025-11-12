# Observatory Global Backend

FastAPI backend for the Global Narrative Observatory - Real-time trends aggregation and information flow detection.

## Features

- **Trends Aggregation**: Multi-source data aggregation from GDELT, Google Trends, and Wikipedia
- **NLP Processing**: Topic extraction and normalization using TF-IDF and clustering
- **Flow Detection**: Information flow analysis between countries using similarity and time decay
- **REST API**: Versioned API endpoints with OpenAPI documentation

## API Endpoints

### Health Check

```bash
GET /health
```

Returns API health status and version information.

**Example:**
```bash
curl http://localhost:8000/health
```

**Response:**
```json
{
  "status": "healthy",
  "version": "0.1.0",
  "timestamp": "2025-01-12T10:30:00Z"
}
```

### Trends API

#### Get Top Trends for Country

```bash
GET /v1/trends/top?country=<ISO_CODE>&limit=<NUMBER>
```

Fetch trending topics for a specific country.

**Parameters:**
- `country` (required): ISO 3166-1 alpha-2 country code (e.g., "US", "CO", "BR")
- `limit` (optional): Maximum number of topics to return (default: 10, max: 50)

**Example:**
```bash
curl "http://localhost:8000/v1/trends/top?country=CO&limit=10"
```

**Response:**
```json
{
  "country": "CO",
  "generated_at": "2025-01-12T10:30:00Z",
  "topics": [
    {
      "id": "topic-1",
      "label": "Economic Reform",
      "count": 156,
      "sample_titles": [
        "Government announces new economic measures"
      ],
      "sources": ["gdelt", "trends"],
      "confidence": 0.87
    }
  ]
}
```

### Flows API

#### Get Information Flows

```bash
GET /v1/flows?time_window=<DURATION>&countries=<CODES>&threshold=<SCORE>
```

Detect information flows between countries based on trending topics.

**Parameters:**
- `time_window` (optional): Time window for analysis (e.g., "1h", "6h", "24h", default: "24h")
- `countries` (optional): Comma-separated ISO country codes (default: "US,CO,BR,MX,AR")
- `threshold` (optional): Minimum heat score [0.0-1.0] (default: 0.5)

**Heat Formula:**
```
heat = similarity × exp(-Δt / 6h)
```

Where:
- `similarity`: TF-IDF cosine similarity between topics [0, 1]
- `Δt`: Time difference between topic appearances (hours)
- `6h`: Configurable half-life (HEAT_HALFLIFE_HOURS)

**Example:**
```bash
curl "http://localhost:8000/v1/flows?time_window=24h&countries=US,CO,BR&threshold=0.5"
```

**Response:**
```json
{
  "hotspots": [
    {
      "country": "US",
      "intensity": 0.85,
      "topic_count": 47,
      "top_topics": [
        {
          "label": "election fraud claims",
          "count": 234,
          "confidence": 0.92
        }
      ]
    }
  ],
  "flows": [
    {
      "from_country": "US",
      "to_country": "CO",
      "heat": 0.72,
      "similarity_score": 0.87,
      "time_delta_hours": 3.2,
      "shared_topics": ["election fraud claims", "voting irregularities"]
    }
  ],
  "metadata": {
    "formula": "heat = similarity × exp(-Δt / 6h)",
    "threshold": 0.5,
    "time_window_hours": 24.0,
    "total_flows_computed": 45,
    "flows_returned": 5,
    "countries_analyzed": ["US", "CO", "BR"]
  },
  "generated_at": "2025-01-12T15:30:00Z"
}
```

See full example: [docs/examples/flows.json](../docs/examples/flows.json)

## Development

### Prerequisites

- Python 3.11+
- Docker & Docker Compose (for Redis and PostgreSQL)

### Setup

1. **Install dependencies:**

```bash
cd backend
pip install -e ".[dev]"
```

2. **Configure environment:**

Create `.env` file:

```bash
# Application
APP_ENV=development
APP_PORT=8000

# Redis
REDIS_HOST=localhost
REDIS_PORT=6379

# PostgreSQL
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=observatory
POSTGRES_USER=observatory
POSTGRES_PASSWORD=changeme

# Flow Detection
HEAT_HALFLIFE_HOURS=6.0
FLOW_THRESHOLD=0.5
USE_CACHE=true
DRY_RUN_APIS=false
```

3. **Run database migrations:**

```bash
# Start PostgreSQL
docker-compose up -d postgres

# Run migration
psql -h localhost -U observatory -d observatory -f app/db/migrations/001_create_trends_archive.sql
```

4. **Start development server:**

```bash
uvicorn app.main:app --reload --port 8000
```

5. **Access API documentation:**

- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

### Testing

Run tests with pytest:

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=app --cov-report=html

# Run specific test file
pytest tests/test_flow_detector.py

# Run specific test
pytest tests/test_flow_detector.py::TestFlowDetector::test_calculate_heat
```

### Code Quality

```bash
# Format code
black app tests

# Lint code
ruff check app tests

# Type checking
mypy app
```

## Architecture

### Project Structure

```
backend/
├── app/
│   ├── api/
│   │   └── v1/
│   │       ├── health.py      # Health check endpoint
│   │       ├── trends.py      # Trends API
│   │       └── flows.py       # Flows API
│   ├── core/
│   │   ├── config.py          # Configuration
│   │   └── logging.py         # Logging setup
│   ├── db/
│   │   └── migrations/        # Database migrations
│   ├── models/
│   │   ├── schemas.py         # Trends models
│   │   └── flows.py           # Flows models
│   ├── services/
│   │   ├── gdelt_client.py    # GDELT data source
│   │   ├── trends_client.py   # Google Trends client
│   │   ├── wiki_client.py     # Wikipedia client
│   │   ├── nlp.py             # NLP processor
│   │   └── flow_detector.py   # Flow detection logic
│   └── main.py                # FastAPI app
├── tests/
│   ├── test_health.py
│   └── test_flow_detector.py
├── pyproject.toml
└── README.md
```

### Data Flow

1. **Trends Aggregation:**
   - Client requests trends for country
   - Backend fetches from GDELT, Google Trends, Wikipedia
   - NLP processor extracts and normalizes topics
   - Response returned with confidence scores

2. **Flow Detection:**
   - Client requests flows for multiple countries
   - Backend fetches trends for each country
   - FlowDetector calculates:
     - Hotspot intensity (volume × velocity × confidence)
     - Topic similarity (TF-IDF cosine similarity)
     - Heat score (similarity × time decay)
   - Flows filtered by threshold
   - Response includes hotspots, flows, and metadata

### Algorithm Details

**TF-IDF Similarity:**
- Uses scikit-learn TfidfVectorizer with bigrams
- Filters English stop words
- Calculates cosine similarity between topic vectors
- Returns maximum similarity across all topic pairs

**Time Decay:**
- Exponential decay: `exp(-Δt / halflife)`
- Default half-life: 6 hours (configurable)
- At 6h: decay = 0.37 (37% of original heat)
- At 24h: decay = 0.02 (2% of original heat)

**Hotspot Intensity:**
- Weighted combination of:
  - Volume (40%): Number of topics normalized [0, 1]
  - Velocity (30%): Average topic count normalized [0, 1]
  - Confidence (30%): Average confidence score [0, 1]

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `APP_ENV` | Environment (development/production) | `development` |
| `APP_PORT` | API port | `8000` |
| `REDIS_HOST` | Redis hostname | `redis` |
| `REDIS_PORT` | Redis port | `6379` |
| `POSTGRES_HOST` | PostgreSQL hostname | `postgres` |
| `POSTGRES_PORT` | PostgreSQL port | `5432` |
| `POSTGRES_DB` | Database name | `observatory` |
| `HEAT_HALFLIFE_HOURS` | Time decay half-life | `6.0` |
| `FLOW_THRESHOLD` | Minimum heat score | `0.5` |
| `USE_CACHE` | Enable Redis caching | `true` |
| `DRY_RUN_APIS` | Mock external API calls | `false` |
| `CACHE_TTL` | Cache TTL in seconds | `300` |

## Performance

- `/v1/flows` responds in < 500ms (cache hit)
- `/v1/flows` responds in < 3s (cache miss, 10 countries)
- Target: 100 req/s with current architecture

## Troubleshooting

### Import Errors

If you encounter import errors, ensure you're in the backend directory and have installed the package:

```bash
cd backend
pip install -e .
```

### Database Connection Issues

Verify PostgreSQL is running and credentials are correct:

```bash
docker-compose ps
psql -h localhost -U observatory -d observatory -c "SELECT 1;"
```

### Test Failures

Run tests with verbose output:

```bash
pytest -vv --tb=short
```

## References

- [ADR-0001: Refresh Intervals](../docs/decisions/ADR-0001-refresh-intervals.md)
- [ADR-0002: Heat Formula](../docs/decisions/ADR-0002-heat-formula.md)
- [Backend Flow Agent Spec](../.agents/backend_flow.md)

## License

MIT

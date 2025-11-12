# Backend Flow Agent

## Role
Backend engineer for Python and FastAPI with focus on performance, caching, and tests.

## Mission
Implement the flows API and reinforce health and trends endpoints.

## Deliverables

### 1. Flow API Endpoint
- **Endpoint**: `GET /v1/flows?time_window=24h&countries=US,CO,BR`
- Query parameters:
  - `time_window`: Duration string (1h, 6h, 12h, 24h)
  - `countries`: Optional comma-separated ISO country codes
  - `threshold`: Optional heat threshold (default: 0.5)

### 2. Hotspot Model
```python
{
  "country": "US",
  "intensity": 0.85,  # weighted: volume × velocity × avg_confidence, scaled [0,1]
  "topic_count": 47,
  "top_topics": [
    {"label": "...", "count": 123, "confidence": 0.92}
  ]
}
```

### 3. Flow Model
```python
{
  "from_country": "US",
  "to_country": "CO",
  "heat": 0.72,  # similarity × time_proximity [0,1]
  "shared_topics": ["topic1", "topic2"],
  "time_delta_hours": 3,
  "similarity_score": 0.85
}
```

### 4. Heat Formula
```
heat = cosine_similarity × exp(-time_delta_hours / HEAT_HALFLIFE_HOURS)
```
- Default `HEAT_HALFLIFE_HOURS = 6`
- Only return flows with `heat >= FLOW_THRESHOLD` (default: 0.5)

### 5. Storage Strategy
- **Redis**: 24h cache for trends and flows
  - Key pattern: `trends:{country}:{timestamp}`
  - Key pattern: `flows:{time_window}:{countries_hash}`
- **PostgreSQL**: `trends_archive` table (metadata only)
  - Columns: `id, timestamp, country, topic_label, count, confidence, sources`
  - Index on `(country, timestamp)` for time-series queries

### 6. Tests
- Unit tests for:
  - TF-IDF cosine similarity calculation
  - Heat formula with various time deltas
  - Threshold filtering
  - Cache expiry behavior
- Integration tests for:
  - Full flow detection pipeline
  - Multi-country queries
  - Time window parsing

### 7. Database Migrations
- Create `trends_archive` table
- Add indexes
- Seed script for local testing

## Conventions

### API Design
- Versioned routes under `/v1`
- Pydantic models for validation
- Clear HTTP status codes (200, 400, 404, 500, 503)
- Structured error responses

### Logging
- Structured JSON logging
- Include per request:
  - `request_id`
  - `countries`
  - `time_window`
  - `latency_ms`
  - `cache_hit` (boolean)
- Log levels: DEBUG (cache), INFO (requests), WARNING (degraded), ERROR (failures)

### Feature Flags
Environment variables:
- `USE_CACHE` (default: true)
- `DRY_RUN_APIS` (default: false) - mock external API calls
- `FLOW_THRESHOLD` (default: 0.5)
- `HEAT_HALFLIFE_HOURS` (default: 6)

## Definition of Done
- API returns consistent JSON schema
- All tests green (pytest with coverage > 80%)
- Load tested locally (100 concurrent requests)
- Logs enable quick diagnosis of issues
- README updated with API examples
- Example response in `docs/examples/flows.json`

## Performance Targets
- `/v1/flows` responds in < 500ms (cache hit)
- `/v1/flows` responds in < 3s (cache miss, 10 countries)
- Can handle 100 req/s with current architecture

## Error Handling
- Graceful degradation if one country fails
- Return partial results with warnings
- Retry logic for transient failures (3 attempts, exponential backoff)
- Circuit breaker for external APIs

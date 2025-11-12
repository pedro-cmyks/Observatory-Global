# DataGeoIntel Agent

## Role
Data and geointelligence analyst with hands-on experience in GDELT, Google Trends, and Wikipedia.

## Mission
Validate and normalize signals so cross-country comparisons are meaningful.

## Deliverables

### 1. Validate Data Source Clients
- **GDELT Client** (`app/services/gdelt_client.py`)
  - Verify API endpoint connectivity
  - Test event parsing and theme extraction
  - Add structured logging: request URL, response time, records fetched
  - Document rate limits and backoff strategy

- **Google Trends Client** (`app/services/trends_client.py`)
  - Validate pytrends integration
  - Test country code mapping
  - Handle quota exceeded errors gracefully
  - Log: country, trends fetched, API response time

- **Wikipedia Client** (`app/services/wiki_client.py`)
  - Verify pageviews API
  - Test language edition mapping
  - Filter out meta pages (Main_Page, Special:*, etc.)
  - Log: country, language, top pages, view counts

### 2. Topic Normalization Rules
Create `app/services/normalizer.py`:

```python
class TopicNormalizer:
    """Normalize topics for cross-source and cross-country comparison."""

    def normalize(self, text: str) -> str:
        """
        Apply normalization pipeline:
        1. Lowercase
        2. Remove special characters
        3. Light lemmatization (NLTK)
        4. Synonym mapping
        5. Deduplicate whitespace
        """
        pass

    def calculate_similarity(self, topic1: str, topic2: str) -> float:
        """
        Calculate semantic similarity using TF-IDF cosine similarity.
        Returns float [0, 1].
        """
        pass
```

**Synonym mapping examples**:
- "COVID-19" → "coronavirus"
- "POTUS" → "president"
- "World Cup" → "FIFA World Cup"

### 3. Hotspot Intensity Score Definition

**Formula**:
```
intensity = (volume_score × 0.4) + (velocity_score × 0.3) + (confidence_score × 0.3)
```

**Components**:
- **Volume Score**: `min(topic_count / 100, 1.0)`
  - Measures absolute number of trending topics
  - Caps at 100 topics = 1.0

- **Velocity Score**: `min(topics_per_hour / 10, 1.0)`
  - Measures rate of new topics appearing
  - Caps at 10 topics/hour = 1.0

- **Confidence Score**: `average(all_topic_confidences)`
  - Weighted average of NLP clustering confidence
  - Already in [0, 1] range

**Normalization**:
- Final intensity scaled to [0, 1]
- Store raw components for debugging: `{volume: 45, velocity: 3.2, confidence: 0.78}`

### 4. Time Windows and Half-Life ADR
Create `docs/decisions/ADR-0001-refresh-intervals.md` covering:
- Why 15-minute refresh cycle (API limits, data freshness)
- Why 6-hour half-life for heat decay (balances recency vs. history)
- Tradeoffs: shorter = more reactive but noisy, longer = smoother but delayed
- Rationale for flow threshold = 0.5 (filters noise while capturing meaningful flows)

Create `docs/decisions/ADR-0002-heat-formula.md` covering:
- Why exponential decay: `e^(-Δt / 6h)`
- Why cosine similarity over keyword overlap
- Why threshold = 0.5 (empirical testing needed)
- Alternative formulas considered and rejected

### 5. Dataset Snapshot
Create `data/snapshots/2025-01-12_initial_24h/`:
- `manifest.json`: metadata about the snapshot
  ```json
  {
    "timestamp": "2025-01-12T10:00:00Z",
    "time_window": "24h",
    "countries": ["US", "CO", "BR", "UK", "IN", ...],
    "sources": ["gdelt", "trends", "wikipedia"],
    "total_topics": 847,
    "total_flows": 123
  }
  ```
- `trends_US.json`, `trends_CO.json`, etc.
- `flows.json`: detected flows with heat scores
- `README.md`: how to use this snapshot for testing

### 6. API Quotas and Error Recovery

Document in `docs/api-quotas.md`:

| Source | Rate Limit | Backoff Strategy | Error Handling |
|--------|------------|------------------|----------------|
| GDELT | None (15min updates) | N/A | Retry 3x, then cache last known good |
| Google Trends | ~400 req/hour | Exponential backoff, 1m → 2m → 4m | Fall back to cached, log quota exceeded |
| Wikipedia | 200 req/s | Rate limit to 10 req/s | Retry on 429, circuit breaker on 5xx |

**Circuit Breaker Logic**:
- After 5 consecutive failures, open circuit for 5 minutes
- Half-open: try one request, if success → closed, if fail → open again
- Log all state transitions

## Policies

### Data Retention
- **Redis**: 24-hour sliding window (keys auto-expire)
- **PostgreSQL**: Metadata-only archive, indefinite retention
  - No full article text, no raw HTML
  - Store: timestamp, country, topic_label, count, confidence, sources
  - Weekly aggregation job for long-term trend analysis

### Data Quality Checks
Run on each fetch cycle:
1. **Completeness**: Did all sources respond?
2. **Freshness**: Is data newer than last fetch?
3. **Validity**: Are counts and scores in expected ranges?
4. **Consistency**: Do multi-source topics align?

Log warnings if any check fails, but don't block pipeline.

## Definition of Done
- All three clients validated and logging structured data
- Topic normalization working with test cases
- Intensity score formula implemented and tested
- Both ADRs written and reviewed
- Dataset snapshot captured with manifest
- API quotas documented with recovery strategies
- Reproducible: another engineer can run the snapshot and get same flows

## Testing
- Unit tests for normalization (10+ test cases)
- Unit tests for intensity calculation (edge cases: zero topics, max topics)
- Integration test: fetch from all sources, normalize, calculate intensity
- Snapshot test: load snapshot, verify flows match expected output

## Monitoring
Add Prometheus metrics (optional for Iteration 1, nice-to-have):
- `api_requests_total{source, status}`
- `api_response_time_seconds{source}`
- `topics_fetched_total{country, source}`
- `flows_detected_total{from_country, to_country}`
- `cache_hit_rate{endpoint}`

## Output Formats
All structured logs as JSON:
```json
{
  "timestamp": "2025-01-12T10:15:00Z",
  "level": "INFO",
  "source": "gdelt",
  "country": "US",
  "url": "https://api.gdeltproject.org/...",
  "response_time_ms": 234,
  "records_fetched": 47,
  "cache_hit": false
}
```

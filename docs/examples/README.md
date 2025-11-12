# API Response Examples

This directory contains example JSON responses from the Observatory Global API and structured log entries.

## Files

### `trends-response-us.json`
Example response from `/v1/trends/top?country=US&limit=10`

**Key Features:**
- 10 trending topics for United States
- Topics aggregated from GDELT, Google Trends, and Wikipedia
- Includes confidence scores and sample titles
- Multi-source topics have higher confidence

### `trends-response-co.json`
Example response from `/v1/trends/top?country=CO&limit=10`

**Key Features:**
- 10 trending topics for Colombia
- Spanish-language content mixed with English
- Shows how topics vary by region
- Demonstrates Wikipedia's Spanish edition integration

### `structured-logs.json`
Example structured log entries from the data pipeline

**Log Types:**
- `wikipedia_success`: Successful Wikipedia API call
- `trends_success`: Successful Google Trends fetch
- `trends_fallback`: Trends API failure with fallback
- `gdelt_success`: GDELT data fetch
- `api_request_start`: API endpoint request initiated
- `api_request_complete`: API endpoint request completed successfully
- `api_request_error`: API endpoint request failed
- `wikipedia_error`: Wikipedia API error

## Response Schema

### TrendsResponse
```json
{
  "country": "string (ISO 3166-1 alpha-2)",
  "generated_at": "string (ISO 8601 UTC timestamp)",
  "topics": [
    {
      "id": "string (unique topic ID)",
      "label": "string (topic name)",
      "count": "integer (aggregated count)",
      "sample_titles": ["array of strings"],
      "sources": ["array of source names"],
      "confidence": "float (0.0-1.0)"
    }
  ]
}
```

### Topic Object
- **id**: Unique identifier (MD5 hash of label, 8 chars)
- **label**: Human-readable topic name
- **count**: Aggregated count from all sources (higher = more trending)
- **sample_titles**: Up to 3 sample article/page titles
- **sources**: Data sources contributing to this topic (gdelt, trends, wikipedia)
- **confidence**: NLP confidence score (0.0-1.0, higher = more certain)

## Understanding Counts

Counts are **not directly comparable** across sources:
- **GDELT**: Article/event mentions (typically 10-100)
- **Google Trends**: Simulated ranking (typically 20-50)
- **Wikipedia**: Page views normalized (divided by 1000, typically 100-2000)

The NLP processor aggregates these counts, so multi-source topics will have higher counts.

## Confidence Scores

Confidence is calculated based on:
- **Cluster size**: Larger clusters = higher confidence
- **Source diversity**: Multi-source topics = higher confidence
- **Text coherence**: TF-IDF similarity within cluster

Typical ranges:
- **0.90-1.00**: Very high confidence (clear topic, multiple sources)
- **0.75-0.89**: High confidence (good clustering, 1-2 sources)
- **0.60-0.74**: Moderate confidence (smaller clusters, single source)
- **Below 0.60**: Low confidence (noisy or ambiguous topic)

## Testing with Examples

You can use these examples for:
1. **Frontend development**: Mock API responses
2. **Testing**: Validate response parsing
3. **Documentation**: Show expected data structure
4. **Debugging**: Compare actual vs. expected output

## Generating Fresh Examples

To generate fresh examples from the live API:

```bash
# Start the backend
cd backend
uvicorn app.main:app --reload

# Fetch fresh data
curl "http://localhost:8000/v1/trends/top?country=US&limit=10" | jq '.' > trends-response-us-fresh.json
curl "http://localhost:8000/v1/trends/top?country=CO&limit=10" | jq '.' > trends-response-co-fresh.json
```

## Notes

- All timestamps are in UTC
- Response times vary (typically 500-3000ms depending on sources)
- Wikipedia data has a 1-day delay
- Google Trends may fallback if rate-limited
- GDELT is currently using fallback data (not yet implemented)

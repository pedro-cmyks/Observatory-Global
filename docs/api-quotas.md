# API Quotas and Error Recovery

**Last Updated**: 2025-01-12
**Owner**: DataGeoIntel Agent

## Overview

This document details rate limits, quotas, and error recovery strategies for all external data sources used by Observatory Global.

---

## GDELT (Global Database of Events, Language, and Tone)

### API Details
- **Base URL**: `http://data.gdeltproject.org/gdeltv2/`
- **Authentication**: None (public dataset)
- **Cost**: Free
- **Data Format**: CSV (tab-delimited), gzip compressed

### Rate Limits
| Limit Type | Value | Notes |
|------------|-------|-------|
| **Requests per second** | No limit | Public dataset, no authentication |
| **Requests per hour** | No limit | Best practice: cache files locally |
| **Requests per day** | No limit | |
| **Concurrent connections** | Reasonable use | Avoid hammering servers |
| **File size** | ~50-500 MB per file | GKG files are large |

### Update Frequency
- **New files published**: Every 15 minutes
- **File retention**: Indefinite (archive available)
- **Latency**: Near real-time (< 5 minutes from event to publication)

### Backoff Strategy
**Status**: Not needed (no rate limits)

```python
# No exponential backoff required
# But implement basic retry for network issues
max_retries = 3
retry_delay = 5  # seconds
```

### Error Handling

#### Common Errors:
1. **404 Not Found**: File not yet published (GDELT still processing)
   - **Action**: Wait 60 seconds, retry with previous timestamp
   - **Fallback**: Use last successfully fetched data

2. **Network Timeout**: Large file download timed out
   - **Action**: Increase timeout to 30 seconds
   - **Fallback**: Use cached data

3. **Corrupt CSV**: Parsing error (malformed data)
   - **Action**: Skip corrupted rows, log warning
   - **Fallback**: Use partial data if > 50% rows valid

#### Circuit Breaker:
```python
CircuitBreaker(
    failure_threshold=5,      # Open after 5 consecutive failures
    recovery_timeout=300,     # 5 minutes
    expected_exception=GDELTFetchError
)
```

### Best Practices
- ✅ Download files once and cache locally (don't re-download)
- ✅ Use streaming parser for large CSV files
- ✅ Filter by country code early (reduce memory usage)
- ✅ Monitor file sizes (unusually large = potential issue)
- ❌ Don't download same file multiple times
- ❌ Don't parse entire CSV if only need country subset

---

## Google Trends (via pytrends)

### API Details
- **Library**: `pytrends` (unofficial Python wrapper)
- **Base**: Google Trends website scraping
- **Authentication**: None
- **Cost**: Free (but rate-limited)

### Rate Limits
| Limit Type | Value | Notes |
|------------|-------|-------|
| **Requests per hour** | ~400 | Unofficial limit (community observation) |
| **Requests per day** | ~10,000 | Soft limit, may trigger CAPTCHA |
| **Concurrent connections** | 1 recommended | pytrends not designed for concurrency |
| **Burst rate** | ~10 req/min | Exceeding triggers 429 errors |

### Error Codes
| Code | Meaning | Action |
|------|---------|--------|
| **429** | Too Many Requests | Exponential backoff |
| **503** | Service Unavailable | Retry after 60s |
| **400** | Bad Request | Invalid country code, don't retry |

### Backoff Strategy
**Status**: Required (strict rate limits)

```python
ExponentialBackoff(
    initial_delay=60,      # 1 minute
    max_delay=240,         # 4 minutes
    multiplier=2,          # Double each retry
    max_retries=3          # Give up after 3 tries
)

# Example timeline:
# 1st failure: wait 60s
# 2nd failure: wait 120s
# 3rd failure: wait 240s, then use fallback
```

### Error Handling

#### Common Errors:
1. **429 Too Many Requests**: Rate limit exceeded
   - **Action**: Exponential backoff (60s → 120s → 240s)
   - **Fallback**: Return cached data with `stale: true` flag

2. **ResponseError / Empty DataFrame**: Country not supported
   - **Action**: Log warning, add country to unsupported list
   - **Fallback**: Use generic fallback data

3. **Network Timeout**: Request took > 30 seconds
   - **Action**: Retry once with longer timeout (60s)
   - **Fallback**: Use cached data

4. **CAPTCHA Challenge**: Google detected automation
   - **Action**: Open circuit breaker for 1 hour
   - **Fallback**: Use cached data for all requests
   - **Alert**: Send notification to ops team

#### Circuit Breaker:
```python
CircuitBreaker(
    failure_threshold=5,      # Open after 5 consecutive failures
    recovery_timeout=300,     # 5 minutes
    half_open_timeout=60,     # Test with 1 request after 1 minute
    expected_exception=(TooManyRequestsError, ResponseError)
)
```

### Request Queue
**Recommended**: Implement a request queue to avoid bursts

```python
RateLimiter(
    requests_per_hour=400,
    requests_per_minute=10,
    strategy="token_bucket"
)
```

### Country Support
**Supported Countries** (17 total):
- North America: US, CA, MX
- South America: BR, AR, CL, CO, PE
- Europe: GB, FR, DE, ES, IT
- Asia: IN, JP, KR
- Oceania: AU

**Unsupported Countries**: Fallback to generic data

### Best Practices
- ✅ Respect rate limits (stay under 400 req/hour)
- ✅ Cache aggressively (15-minute TTL minimum)
- ✅ Use exponential backoff on 429 errors
- ✅ Monitor quota usage with Prometheus
- ❌ Don't retry 400 errors (invalid requests)
- ❌ Don't make concurrent requests (pytrends limitation)
- ❌ Don't ignore 429 errors (will trigger IP ban)

---

## Wikipedia Pageviews API

### API Details
- **Base URL**: `https://wikimedia.org/api/rest_v1`
- **Authentication**: None
- **Cost**: Free
- **Documentation**: https://wikimedia.org/api/rest_v1/

### Rate Limits
| Limit Type | Value | Notes |
|------------|-------|-------|
| **Requests per second** | 200 | Very generous limit |
| **Burst rate** | 200 req/s | No burst penalty |
| **User-Agent required** | Yes | Must identify your app |
| **Recommended rate** | 10 req/s | Good citizenship |

### User-Agent Requirement
**Required**: Must set a descriptive User-Agent header

```python
headers = {
    "User-Agent": "ObservatoryGlobal/1.0 (https://observatoryglobal.com; contact@example.com)"
}
```

### Error Codes
| Code | Meaning | Action |
|------|---------|--------|
| **404** | Not Found | Date not yet available, try previous day |
| **429** | Rate Limit | Back off for 1 second |
| **5xx** | Server Error | Retry with exponential backoff |

### Backoff Strategy
**Status**: Minimal (generous limits, but handle 5xx gracefully)

```python
# For 429 errors (rare)
LinearBackoff(
    delay=1,        # 1 second
    max_retries=3
)

# For 5xx errors
ExponentialBackoff(
    initial_delay=5,    # 5 seconds
    max_delay=60,       # 1 minute
    multiplier=2,
    max_retries=5
)
```

### Error Handling

#### Common Errors:
1. **404 Not Found**: Date not yet available (API updates with delay)
   - **Action**: Try yesterday's date (N-1 day)
   - **Fallback**: Use N-2 day data if N-1 also fails

2. **429 Too Many Requests**: Exceeded 200 req/s (unlikely)
   - **Action**: Wait 1 second, retry
   - **Fallback**: Use cached data

3. **503 Service Unavailable**: Wikimedia maintenance
   - **Action**: Exponential backoff (5s → 10s → 20s)
   - **Fallback**: Use cached data

4. **Network Timeout**: Request took > 10 seconds
   - **Action**: Retry once with 20-second timeout
   - **Fallback**: Use cached data

#### Circuit Breaker:
```python
CircuitBreaker(
    failure_threshold=5,      # Open after 5 consecutive 5xx errors
    recovery_timeout=300,     # 5 minutes
    expected_exception=HTTPStatusError(5xx)
)
```

### Language Edition Mapping
**Supported Languages** (12 editions):
- `en.wikipedia`: English (US, GB, IN, AU, CA)
- `es.wikipedia`: Spanish (ES, CO, MX, AR, CL, PE)
- `pt.wikipedia`: Portuguese (BR)
- `fr.wikipedia`: French (FR)
- `de.wikipedia`: German (DE)
- `it.wikipedia`: Italian (IT)
- `ja.wikipedia`: Japanese (JP)
- `ko.wikipedia`: Korean (KR)
- `zh.wikipedia`: Chinese (CN)
- `ru.wikipedia`: Russian (RU)

### Best Practices
- ✅ Set descriptive User-Agent header
- ✅ Rate limit to 10 req/s (good citizenship)
- ✅ Cache results (15-minute TTL minimum)
- ✅ Filter out meta pages (Special:*, Main_Page)
- ✅ Handle 404 gracefully (try N-1 day)
- ❌ Don't exceed 200 req/s
- ❌ Don't make requests without User-Agent
- ❌ Don't retry 404s indefinitely (max 2 retries)

---

## Error Recovery Patterns

### 1. Retry with Exponential Backoff
**Use for**: Transient network errors, temporary service unavailability

```python
@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=4, max=60),
    retry=retry_if_exception_type(HTTPError)
)
async def fetch_with_retry(url: str):
    # Implementation
    pass
```

### 2. Circuit Breaker
**Use for**: Persistent service failures

```python
# State: CLOSED (normal) → OPEN (failing) → HALF_OPEN (testing) → CLOSED
CircuitBreaker(
    failure_threshold=5,      # Open after 5 failures
    recovery_timeout=300,     # Wait 5 minutes before testing
    success_threshold=2       # Close after 2 successful tests
)
```

### 3. Graceful Degradation
**Use for**: When all retries exhausted

```python
try:
    data = await fetch_from_api()
except AllRetriesExhausted:
    # Try cache
    data = await get_from_cache()
    if not data:
        # Use fallback data
        data = generate_fallback()
        log_fallback_used(source, country)
```

### 4. Cache-Aside Pattern
**Use for**: Reducing API calls

```python
async def get_trends(country: str):
    # Check cache first
    cached = await cache.get(f"trends:{country}")
    if cached:
        return cached

    # Cache miss: fetch from API
    data = await fetch_from_api(country)

    # Store in cache
    await cache.set(f"trends:{country}", data, ttl=900)

    return data
```

---

## Monitoring and Alerting

### Key Metrics to Track

#### API Health
```prometheus
# Success rate per source
api_request_success_rate{source="gdelt|trends|wikipedia"} > 0.95

# Response time (p95)
api_request_duration_seconds{quantile="0.95", source="gdelt|trends|wikipedia"} < 3.0

# Error rate
rate(api_request_errors_total{source="gdelt|trends|wikipedia"}[5m]) < 0.05
```

#### Rate Limiting
```prometheus
# Rate limit errors
increase(api_rate_limit_errors_total{source="trends"}[1h]) < 5

# Circuit breaker state
circuit_breaker_state{source="gdelt|trends|wikipedia"} == 0  # 0=closed, 1=open
```

#### Cache Performance
```prometheus
# Cache hit rate
cache_hit_rate > 0.80

# Cache size
cache_keys_total < 10000  # Monitor for unbounded growth
```

### Alerts

#### Critical Alerts
- Circuit breaker open for > 15 minutes
- API success rate < 90% for > 5 minutes
- All sources failing simultaneously

#### Warning Alerts
- Rate limit errors > 10 per hour (Google Trends)
- Cache hit rate < 70%
- Response time p95 > 5 seconds

---

## Quota Budgeting

### Daily Budget Calculation

#### Scenario: Monitoring 24 countries with 15-minute refresh

**Google Trends** (most restrictive):
```
Refresh interval: 15 minutes = 4 refreshes/hour
Countries: 24
Requests per hour: 24 × 4 = 96 requests/hour
Daily requests: 96 × 24 = 2,304 requests/day

Rate limit: 400 requests/hour
Utilization: 96 / 400 = 24% (safe margin)
```

**Wikipedia**:
```
Requests per hour: 96 requests/hour
Rate limit: 200 requests/second = 720,000 requests/hour
Utilization: 96 / 720,000 = 0.013% (negligible)
```

**GDELT**:
```
No rate limits (public dataset)
Bandwidth: ~50 MB per 15-minute file × 96 = 4.8 GB/day
```

### Scaling Limits

**Maximum countries** (at 15-min refresh, staying under 50% Trends quota):
```
Max requests/hour: 400 × 0.50 = 200 requests/hour
Countries: 200 / 4 = 50 countries
```

**To monitor 100+ countries**: Consider:
- 30-minute refresh interval (2 req/hour)
- Prioritize high-value countries (cache warming)
- Alternative Trends API (paid service)

---

## Cost Analysis

| Source | Monthly Cost | Notes |
|--------|-------------|-------|
| **GDELT** | $0 (Free) | Bandwidth costs only (~150 GB/month) |
| **Google Trends** | $0 (Free) | Rate-limited, may require paid API for scale |
| **Wikipedia** | $0 (Free) | Public API, very generous limits |
| **Redis Cache** | $50-100 | Depends on provider (AWS ElastiCache, etc.) |
| **Total** | ~$50-100/month | For < 50 countries |

### Scaling Costs
- **100 countries**: Need paid Trends API (~$500-1000/month estimate)
- **500 countries**: Full enterprise solution (~$5000+/month)

---

## Testing Rate Limits

### Rate Limit Test Plan

1. **Google Trends Stress Test**:
   ```bash
   # Send 50 requests in 1 minute (5x normal rate)
   for i in {1..50}; do
     curl "http://localhost:8000/v1/trends/top?country=US&limit=10"
     sleep 1
   done

   # Expected: 429 errors after ~10 requests
   # Expected: Circuit breaker opens after 5 consecutive failures
   ```

2. **Circuit Breaker Test**:
   ```python
   # Simulate persistent service failure
   with mock.patch('trends_client.fetch') as mock_fetch:
       mock_fetch.side_effect = HTTPError(503)

       # Should open circuit after 5 failures
       for i in range(10):
           result = await get_trends("US")
           # Verify fallback data used after circuit opens
   ```

3. **Cache Effectiveness Test**:
   ```bash
   # Request same country 10 times rapidly
   for i in {1..10}; do
     time curl "http://localhost:8000/v1/trends/top?country=US&limit=10"
   done

   # Expected: 1st request slow (~2s), remaining fast (<100ms)
   ```

---

## Appendix: API Status Pages

- **GDELT**: No official status page (monitor via Twitter @GDELT)
- **Google**: https://www.google.com/appsstatus
- **Wikipedia**: https://wikitech.wikimedia.org/wiki/Incident_status

---

**Next Review**: 2025-01-19 (after 1 week of production monitoring)
**Feedback**: Submit issues to GitHub or contact DataGeoIntel agent

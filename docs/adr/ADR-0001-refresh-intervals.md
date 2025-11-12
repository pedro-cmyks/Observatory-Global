# ADR-0001: Data Refresh Intervals and Caching Strategy

**Status**: Accepted
**Date**: 2025-01-12
**Author**: DataGeoIntel Agent
**Context**: Iteration 1a - Pipeline Verification

## Context and Problem Statement

The Observatory Global platform aggregates data from three external sources (GDELT, Google Trends, Wikipedia) to provide real-time global trending topic insights. We need to determine:

1. How frequently should we refresh data from each source?
2. Should all sources use the same refresh interval?
3. How do we balance data freshness vs. API rate limits?
4. What caching strategy should we implement?

## Decision Drivers

- **GDELT**: Updates every 15 minutes, no rate limits (public dataset)
- **Google Trends**: Real-time but rate-limited (~400 requests/hour via pytrends)
- **Wikipedia**: High rate limit (200 req/s) but has 1-day data delay
- **User Expectations**: Need reasonably fresh data (< 30 minutes old)
- **Cost**: Minimize unnecessary API calls
- **Reliability**: Avoid hitting rate limits

## Considered Options

### Option 1: Aggressive - 5 Minute Refresh
**Pros:**
- Maximum data freshness
- Quick response to breaking news
- Better user experience

**Cons:**
- Will hit Google Trends rate limits (12 calls/hour = 288 countries/day max)
- Wasted API calls to Wikipedia (data only updates daily)
- Higher infrastructure costs
- May trigger IP bans

### Option 2: Moderate - 15 Minute Refresh (RECOMMENDED)
**Pros:**
- Aligns with GDELT update frequency (natural cadence)
- 4 calls/hour = 96 countries/day within Trends limit
- Good balance of freshness and sustainability
- Predictable API usage patterns
- Allows room for burst traffic

**Cons:**
- 15-minute delay on breaking news
- Still may hit Trends limits if monitoring many countries

### Option 3: Conservative - 30 Minute Refresh
**Pros:**
- Very safe on rate limits (2 calls/hour = 48 countries/day)
- Minimal API costs
- Lower infrastructure load

**Cons:**
- Noticeable staleness in data
- Misses GDELT's 15-minute cadence
- Poor UX for time-sensitive use cases

### Option 4: Hybrid - Per-Source Intervals
**Pros:**
- Optimized for each source's characteristics
- Example: GDELT 15min, Trends 20min, Wikipedia 60min

**Cons:**
- Complex cache invalidation logic
- Hard to reason about data consistency
- Difficult to debug
- Over-engineering for MVP

## Decision

**OPTION 2: 15-Minute Refresh Interval** (900 seconds)

### Rationale:

1. **Aligns with GDELT**: GDELT publishes new files every 15 minutes. Using this as our base interval ensures we never miss GDELT updates.

2. **Google Trends Safety**: At 15-minute intervals:
   - 4 calls per hour per country
   - For 24 countries: 96 calls/hour (24% of 400 limit)
   - Leaves 75% headroom for retries, spikes, testing

3. **Wikipedia Efficiency**: While Wikipedia data is 1-day delayed, checking every 15 minutes is still efficient because:
   - Page views change throughout the day (daily aggregation happens hourly)
   - 15-minute checks catch hourly Wikipedia updates
   - API is generous (200 req/s), so we're nowhere near limits

4. **User Experience**: 15 minutes is acceptable latency for:
   - Intelligence analysts (not trading algorithms)
   - Trend research (not breaking news alerts)
   - Cross-country comparisons (strategic, not tactical)

5. **Infrastructure**: At 15-minute intervals:
   - 96 refresh cycles per day per country
   - Predictable Redis cache patterns
   - Manageable database write rates

## Implementation Details

### Cache Strategy

#### Redis TTL: 900 seconds (15 minutes)
```python
CACHE_TTL_SECONDS = 900  # 15 minutes

# Key format: trends:{country}:{limit}
cache_key = f"trends:{country}:{limit}"
```

#### Cache Behavior:
- **Cache HIT**: Return cached data immediately (< 50ms response)
- **Cache MISS**: Fetch from all sources, cache result, return data
- **Cache EXPIRY**: Automatic Redis TTL, no manual invalidation
- **Cache WARMING**: Pre-fetch top countries (US, CN, IN, BR, etc.) on schedule

### Per-Source Behavior

#### GDELT Client:
- Fetch every 15 minutes (matches GDELT publish cadence)
- Calculate correct CSV filename based on rounded timestamp
- If fetch fails: use last cached result (fallback)
- No exponential backoff needed (no rate limits)

#### Google Trends Client:
- Fetch every 15 minutes
- **Exponential backoff on 429 (Rate Limit)**:
  - 1st failure: wait 60s, retry
  - 2nd failure: wait 120s, retry
  - 3rd failure: wait 240s, use fallback/cache
- **Circuit breaker**: After 5 consecutive failures, open circuit for 5 minutes
- Log all quota exceeded events for monitoring

#### Wikipedia Client:
- Fetch every 15 minutes
- **Rate limiting**: Max 10 req/s (respectful of Wikipedia's servers)
- **Retry logic**: Retry on 429, exponential backoff on 5xx
- **Circuit breaker**: After 5 consecutive 5xx errors, open circuit for 5 minutes

### Monitoring Metrics

We will track these metrics to validate the decision:

```
# Cache effectiveness
cache_hit_rate = cache_hits / (cache_hits + cache_misses)
# Target: > 80% after warmup period

# API health
api_success_rate{source} = successes / (successes + failures)
# Target: > 95% for each source

# Response times
p95_response_time_ms{endpoint}
# Target: < 3000ms for /v1/trends/top

# Rate limit incidents
rate_limit_errors_total{source}
# Target: < 5 per day
```

## Consequences

### Positive:
- ✅ Sustainable API usage (well within rate limits)
- ✅ Predictable infrastructure costs
- ✅ Good data freshness (15-min lag acceptable)
- ✅ Simple to implement and understand
- ✅ Aligns with natural GDELT cadence
- ✅ Allows horizontal scaling (more countries)

### Negative:
- ⚠️ Not suitable for real-time alerts (15-min delay)
- ⚠️ May still hit Trends limits if monitoring > 100 countries
- ⚠️ Cache misses will have noticeable latency (2-3 seconds)

### Neutral:
- 🔄 Can be adjusted based on monitoring data
- 🔄 Per-source intervals can be implemented later if needed
- 🔄 Cache warming schedule may need tuning

## Mitigation Strategies

### For Google Trends Rate Limits:
1. Prioritize high-value countries (US, CN, IN, BR, UK, etc.)
2. Implement request queuing with rate limiter
3. Graceful degradation: show cached/stale data with warning
4. Consider alternative Trends APIs for production

### For Cache Misses:
1. Pre-warm cache for top 20 countries on schedule
2. Return stale data + background refresh on near-expiry
3. Show loading states in UI

### For Wikipedia 1-Day Delay:
1. Clearly communicate data delay in UI
2. Consider alternative real-time Wikipedia APIs (if available)
3. Weight Wikipedia data lower in recency-sensitive scenarios

## Related Decisions

- **ADR-0002**: Heat formula and decay rate (6-hour half-life) - TO BE WRITTEN
- **ADR-0003**: Cache eviction policies - TO BE WRITTEN
- **ADR-0004**: Circuit breaker thresholds - TO BE WRITTEN

## References

- GDELT Documentation: http://data.gdeltproject.org/documentation/GDELT-Global_Knowledge_Graph_Codebook-V2.1.pdf
- pytrends Rate Limits: https://github.com/GeneralMills/pytrends/issues (community observations)
- Wikipedia Pageviews API: https://wikimedia.org/api/rest_v1/#/Pageviews%20data
- Redis TTL Best Practices: https://redis.io/commands/expire

## Review and Revision

This decision will be reviewed after:
1. **1 week of production monitoring** (validate rate limit assumptions)
2. **User feedback on data freshness** (is 15 min acceptable?)
3. **Cost analysis** (infrastructure costs vs. business value)

If monitoring shows consistent rate limit issues, we will revisit with Option 3 (30 minutes) or Option 4 (hybrid).

---

**Last Updated**: 2025-01-12
**Next Review**: 2025-01-19 (after 1 week of monitoring data)

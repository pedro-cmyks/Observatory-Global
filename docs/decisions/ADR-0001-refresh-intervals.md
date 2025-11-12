# ADR-0001: Refresh Intervals and Data Collection Cadence

**Status**: Accepted
**Date**: 2025-01-12
**Decision Makers**: Pedro Villegas, Development Team
**Tags**: data-pipeline, performance, api-quotas

## Context

Observatory Global aggregates trending topics from three external data sources (GDELT, Google Trends, Wikipedia) to detect global information flows in real-time. We need to determine optimal refresh intervals that balance:

1. **Data freshness** - Users want near-real-time insights
2. **API quotas** - External services have rate limits
3. **System resources** - Frequent fetching increases load
4. **Data quality** - Some sources update infrequently

## Decision

### Refresh Cycle: 15 Minutes

We will implement a **15-minute global refresh cycle** as the primary data collection cadence.

### Source-Specific Intervals

| Source | Update Frequency | Our Fetch Interval | Rationale |
|--------|------------------|-------------------|-----------|
| **GDELT 2.0** | Every 15 minutes | 15 minutes | Aligns with GDELT's native update cycle |
| **Google Trends** | Real-time | 15 minutes | Respects ~400 req/hour quota (26 countries × 4/hr = 104 req/hr) |
| **Wikipedia** | Hourly aggregates | 1 hour | Pageview API provides hourly stats, no benefit to fetching more often |

### User-Selectable Time Windows

Users can view trends over these windows:
- **1 hour**: Last 4 data points (4 × 15min)
- **6 hours**: Last 24 data points
- **12 hours**: Last 48 data points
- **24 hours**: Last 96 data points (default)

### Shortest Visible Window

The **minimum time window is 1 hour** because:
- 15-minute intervals are too granular for meaningful trend detection
- Reduces noise from random fluctuations
- Aligns with Wikipedia's hourly data

## Consequences

### Positive
- ✅ **API compliance**: Stays well below Google Trends quota (104 vs 400 req/hr)
- ✅ **Resource efficiency**: 15min interval reduces unnecessary fetches
- ✅ **User satisfaction**: Near-real-time updates (< 15min old data)
- ✅ **Data alignment**: Matches GDELT's natural cadence

### Negative
- ⚠️ **Not true real-time**: 15-minute lag may miss very fast-moving events
- ⚠️ **Wikipedia lag**: Hourly pageview data can be 45-60 minutes behind real-time
- ⚠️ **Scaling challenge**: Adding more countries increases API load linearly

### Mitigations
1. **Adaptive backoff**: If approaching quota limits, automatically increase interval to 30min
2. **Circuit breaker**: Pause fetches for degraded sources, resume after cooldown
3. **Priority queue**: Fetch high-interest countries first, deprioritize low-activity regions
4. **Future enhancement**: WebSocket connections for true push-based updates (post-MVP)

## Implementation Notes

### Environment Variables
```bash
REFRESH_INTERVAL_SECONDS=900  # 15 minutes
WIKIPEDIA_REFRESH_INTERVAL_SECONDS=3600  # 1 hour
GOOGLE_TRENDS_QUOTA_LIMIT=400  # requests per hour
ADAPTIVE_BACKOFF_ENABLED=true
```

### Redis Caching Strategy
- Cache keys expire after **24 hours** (86400 seconds)
- Key pattern: `trends:{country}:{timestamp_rounded_15min}`
- Example: `trends:US:2025-01-12T10:15:00Z`

### Monitoring Alerts
- Trigger warning if fetch latency > 5 seconds
- Alert if quota usage > 80% in any rolling hour
- Log error if any source fails 3 consecutive times

## Alternatives Considered

### 1. 5-Minute Refresh
**Rejected**: Would consume 312 req/hr for Google Trends (26 countries × 12/hr), too close to 400 limit. Minimal user benefit vs. 15min.

### 2. 30-Minute Refresh
**Rejected**: Acceptable for quotas but feels "stale" to users. Flow detection less responsive to breaking events.

### 3. Variable by Source
**Rejected for MVP**: Adds complexity. Future enhancement: Wikipedia every 1hr, GDELT/Trends every 10min.

## References
- [GDELT 2.0 Documentation](https://blog.gdeltproject.org/gdelt-2-0-our-global-world-in-realtime/)
- [Google Trends API Unofficial Limits](https://github.com/GeneralMills/pytrends#caveats)
- [Wikipedia Pageviews API](https://wikitech.wikimedia.org/wiki/Analytics/AQS/Pageviews)

## Review Date
**2025-02-12** (30 days) - Reassess after collecting metrics on:
- Actual API usage patterns
- User engagement with different time windows
- System resource utilization
- Missed events due to 15min lag

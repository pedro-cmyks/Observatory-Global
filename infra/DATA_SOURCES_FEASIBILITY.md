# Open Data Sources Feasibility for Global Narrative Tracking

## Comparative Analysis

| Source | Access Method | Auth Required | Rate Limits | Geographic Coverage | Real-Time | Implementation (1-5) | Notes |
|--------|---|---|---|---|---|---|---|
| **Reddit** | Public JSON endpoints (no `/r/` prefix) | OAuth2 (free tier) | 100 queries/min per OAuth client | Global, discussion-based | Yes | 3 | Requires API registration. ~60/min without OAuth. Commercial use has per-call fees ($0.24/1K calls as of 2023) |
| **Mastodon/Fediverse** | REST API + WebSocket streaming | Optional (public endpoints available) | 300/5min global; 30/30min per POST; 7500/5min per IP | Global, federated instances | Yes (streaming) | 2 | Decentralized - multiple instances with own limits. Streaming via server-sent events. No API key needed for public data |
| **YouTube Trending** | RSS feeds + unofficial APIs | API key required for official API | None published for RSS; unofficial APIs vary | Global by country | No (RSS ~15 items, ~hourly) | 3 | Official API requires quota. RSS feeds only show 15 most recent. No official trending feed endpoint |
| **Hacker News (Firebase)** | Firebase REST API + real-time listeners | None | No formal limits (recommended: 15-30s polling intervals) | Tech/startup narrative only | Yes (Firebase) | 2 | Near real-time through Firebase. ~500 stories available. Clean, minimal API |
| **Hacker News (Algolia)** | REST API search | Optional (public client-side keys) | No hard limit; see rate limiting docs | Tech/startup narrative only | No (search-based) | 2 | Full-text search over all HN content. Complements Firebase API |
| **RSS Aggregation** | Standard RSS/Atom feeds | Varies by outlet | Varies by outlet | Global (outlet-dependent) | No (polling-based) | 2 | Requires aggregation infrastructure (FreshRSS, Miniflux, etc.). Good for news outlets |
| **RIPE BGP Data** | RIS Live API + raw MRT files | None | Not specified | Global routing infrastructure | Yes (RIS Live) | 4 | 15+ years historical data (5.8TB). Requires BGPdump for parsing. Real-time at ris-live.ripe.net |

---

## Detailed Evaluation

### 1. Reddit (Public JSON Endpoints)
**Access**: `https://www.reddit.com/r/{subreddit}/{sort}.json` or `.json` suffix on any post
**Auth**: OAuth2 required; free tier available
**Rate Limits**: 
- With OAuth: 100 queries/min per client ID
- Without OAuth: 10 queries/min (traffic without login blocked)
- Averaged over 10-minute window to allow bursting
**Coverage**: Global, all subreddits; highly relevant for narrative tracking
**Real-time**: Yes, posts appear immediately
**Complexity**: 3/5 - Requires OAuth app registration, user-agent handling
**Pros**: High volume, structured, discussion-based signal
**Cons**: Requires API registration; rate limiting tight for large-scale collection

---

### 2. Mastodon/Fediverse Public API
**Access**: `https://{instance}/api/v1/statuses`, streaming endpoints
**Auth**: Optional for public data
**Rate Limits**:
- 300 requests per 5 minutes (general)
- 7500 requests per 5 minutes per IP (hard limit)
- Specific POST limits: 30 per 30 minutes
**Coverage**: Global, federated; multiple instances (mastodon.social, pixelfed, etc.)
**Real-time**: Yes, WebSocket streaming with server-sent events
**Complexity**: 2/5 - Simple REST, great documentation
**Pros**: Decentralized, real-time streaming, no API key required, ActivityPub standard
**Cons**: Data fragmented across instances; smaller volume than centralized platforms

---

### 3. YouTube Trending
**Access**: 
- RSS feeds: `https://www.youtube.com/feeds/videos.xml?channel_id={id}`
- Trending: Unofficial; requires scraping or third-party services
**Auth**: API key required for official Data API v3
**Rate Limits**: YouTube Data API has quota system (not per-request rate limit)
**Coverage**: Global, by country/category
**Real-time**: No (RSS ~15 items, updated hourly)
**Complexity**: 3/5 - RSS simple, but official trending API requires quota management
**Pros**: Global reach, video metadata rich
**Cons**: No official trending endpoint via API; RSS limited to 15 items; requires API key for official access

---

### 4. Hacker News (Firebase API)
**Access**: `https://hacker-news.firebaseio.com/v0/{endpoint}.json`
**Auth**: None required
**Rate Limits**: No formal limits; recommended polling interval 15-30 seconds
**Coverage**: Tech/startup narratives, global
**Real-time**: Yes, Firebase real-time listeners
**Complexity**: 2/5 - Clean API, Firebase libraries available
**Pros**: Real-time, no auth, well-documented, no rate limits, excellent for tech narratives
**Cons**: Limited to HN community; smaller volume than social platforms

---

### 5. Hacker News (Algolia Search API)
**Access**: `https://hn.algolia.com/api/v1/{endpoint}`
**Auth**: Public client-side keys (read-only)
**Rate Limits**: No explicit limits published; same recommendations as Firebase
**Coverage**: Tech/startup narratives, historical search
**Real-time**: No, search-based
**Complexity**: 2/5 - REST search API
**Pros**: Full-text search, complementary to Firebase for historical analysis
**Cons**: Not real-time; search-heavy vs. stream-heavy

---

### 6. RSS Aggregation (News Outlets)
**Access**: Standard RSS/Atom feeds from news sources
**Auth**: Varies by outlet (BBC, Reuters, AP, etc.)
**Rate Limits**: Varies; typically friendly to aggregators
**Coverage**: Global, news-focused
**Real-time**: Polling-based, typically 15-60 minute intervals
**Complexity**: 2/5 - Standard feeds; aggregation tools available (FreshRSS, Miniflux)
**Pros**: Traditional news signal, many outlets have feeds, structured content
**Cons**: Polling-based (not true real-time), coverage varies by outlet

---

### 7. RIPE BGP Routing Data
**Access**: 
- RIS Live: `https://ris-live.ripe.net/`
- Raw data: FTP; RIPEstat API: `https://stat.ripe.net/api/`
**Auth**: None
**Rate Limits**: Not specified; RIPEstat API recommended max calls per day
**Coverage**: Global internet routing, infrastructure-level signals
**Real-time**: Yes (RIS Live websocket)
**Complexity**: 4/5 - MRT format requires BGPdump parser; specialized knowledge
**Pros**: Global infrastructure view, real-time routing changes, 15+ years historical
**Cons**: High complexity; requires infrastructure/networking expertise; niche signal type

---

## Top 3 Recommendations for Iteration 2

### 1. Hacker News (Firebase API) - RECOMMENDED
**Rationale**: 
- Zero authentication required
- No rate limits
- True real-time updates
- Clean, simple API
- Excellent for tech/startup narratives (key Observatorio Global use case)
- 500+ stories available at any time
- Minimal implementation complexity (2/5)

**Implementation Path**: 
```
- Use Firebase REST API or real-time listeners
- 15-30s polling interval for new stories
- Parse metadata: title, score, time, comments
- Identify narrative clusters via comment threads
```

---

### 2. Mastodon/Fediverse Public API - RECOMMENDED
**Rationale**:
- No API key required
- True real-time streaming (WebSocket)
- Global, decentralized network
- Open standard (ActivityPub)
- Growing adoption; captures emerging narratives early
- Simple implementation (2/5)
- Complements Reddit with decentralized perspective

**Implementation Path**:
```
- Connect to mastodon.social + other instances
- Use streaming API for hashtag/local timelines
- Aggregate across instances
- Monitor for global vs. instance-specific narratives
```

---

### 3. RSS Aggregation (Curated News Outlets) - RECOMMENDED
**Rationale**:
- Captures traditional news signal (important for global narratives)
- No authentication required
- Structured, parseable data
- Covers outlets missing from social platforms
- Minimal complexity (2/5)
- Use mature OSS aggregators (FreshRSS, Miniflux)

**Implementation Path**:
```
- Select 20-30 global news outlets (BBC, Reuters, AP, Al Jazeera, etc.)
- Deploy FreshRSS or Miniflux for aggregation
- 15-minute polling interval
- Extract headline + date + source
- Link to social media narratives for cross-validation
```

---

## Secondary Tier (Consider for Future)

**Reddit** (4th): Higher volume than HN, but requires OAuth registration and tighter rate limits. Good for community signal.

**YouTube Trending** (5th): Lacks official trending API; RSS limited to 15 items. Would require unofficial scraping or third-party services.

**RIPE BGP** (6th): Excellent for infrastructure-level anomaly detection, but high complexity. Consider after core narrative tracking is mature.

---

## Implementation Roadmap

### Phase 1 (Week 1-2): Foundation
1. Deploy Hacker News Firebase collector
2. Set up basic RSS aggregation pipeline (FreshRSS or custom)
3. Implement data normalization layer

### Phase 2 (Week 3-4): Scale
1. Add Mastodon API collectors (multiple instances)
2. Build simple narrative clustering on HN + RSS
3. Create unified data store

### Phase 3 (Week 5+): Enhance
1. Add Reddit if volume demands it
2. Implement cross-platform narrative correlation
3. Add visualization/alerting layer

---

## Cost Analysis
| Source | Cost | Notes |
|--------|------|-------|
| Hacker News | Free | No limits |
| Mastodon | Free | Federated instances |
| RSS Aggregation | Free (OSS) | Self-hosted infrastructure cost only |
| Reddit | Free tier adequate; $0.24/1K calls for scale | API registration required |
| YouTube | Free for RSS; quotas for official API | Unofficial sources less reliable |
| RIPE BGP | Free | Download/API access free |

---

## Risk & Mitigation

| Risk | Mitigation |
|------|-----------|
| Single platform dependency | Collect from ≥3 sources simultaneously |
| Real-time lag | Use Firebase/WebSocket for live, combine with polling for redundancy |
| Data format inconsistency | Build adapter layer for normalization |
| Instance fragmentation (Mastodon) | Monitor top 5-10 instances, aggregate |
| Rate limit throttling | Implement queue, exponential backoff |


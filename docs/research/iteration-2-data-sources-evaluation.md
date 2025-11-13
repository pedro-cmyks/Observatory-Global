# Iteration 2 Data Sources Feasibility Evaluation

**Date**: 2025-01-13
**Research Focus**: Free/open data sources for global trend detection
**Project**: Observatory Global MVP

---

## Executive Summary

This report evaluates 8 free/open data sources for Iteration 2 implementation. Based on comprehensive research including API documentation review, rate limit analysis, and implementation effort estimation, **3 sources are recommended for immediate implementation** (Hacker News, RSS Aggregation, Wikipedia Talk Pages), while **3 should be deferred** to Iteration 3 (Reddit, Mastodon, YouTube), and **2 are recommended for specialized use cases only** (Common Crawl, Internet Routing).

---

## Evaluation Criteria

Each source was evaluated on:
- **Authentication**: None (10 pts) > API Key (7 pts) > OAuth (4 pts)
- **Rate Limits**: Generous/None (10 pts) > Moderate (6 pts) > Restrictive (3 pts)
- **Data Freshness**: Real-time (10 pts) > Hourly (7 pts) > Daily (4 pts)
- **Geographic Coverage**: Global (10 pts) > Multi-region (6 pts) > Limited (3 pts)
- **Implementation Effort**: Low 4-8h (10 pts) > Medium 8-16h (6 pts) > High 16h+ (3 pts)
- **Data Quality**: High relevance to trends (10 pts) > Medium (6 pts) > Low (3 pts)
- **Legal/TOS**: Clear, permissive (10 pts) > Acceptable (7 pts) > Restrictive (4 pts)

**Maximum Score**: 70 points

---

## Detailed Evaluations

### 1. Reddit (Public JSON Endpoints)

#### API Access Method
- **Endpoint Pattern**: `https://www.reddit.com/r/{subreddit}/{sort}.json`
  - Examples: `/r/worldnews/hot.json`, `/r/all/rising.json`
- **Alternative**: Official API via OAuth (100 req/min free tier)
- **Pushshift Status**: **UNAVAILABLE** - Reddit cut off access in 2023

#### Authentication Requirements
- **JSON Endpoints**: None (just User-Agent header)
- **Official API**: OAuth 2.0 required for higher limits
- **Score**: 7/10 (no auth for basic, OAuth for scale)

#### Rate Limits
- **Unauthenticated**: ~10 requests/minute (community-observed)
- **OAuth Free Tier**: 100 requests/minute
- **Critical Issue**: Very restrictive for unauthenticated access
- **Score**: 3/10 (too restrictive for global monitoring)

#### Data Freshness
- **Real-time**: Posts appear immediately in JSON endpoints
- **Latency**: < 1 minute
- **Score**: 10/10

#### Geographic Coverage
- **Global**: Yes, but heavily US-centric (>50% traffic)
- **Regional Subreddits**: Available (e.g., r/europe, r/brasil)
- **Score**: 6/10 (global but US-biased)

#### Content Type
- **Available Data**:
  - Post titles, scores, comments count
  - Subreddit, author, timestamps
  - Awards, engagement metrics
- **Format**: JSON (clean, well-structured)
- **Limitations**: Max 100 posts per request

#### Implementation Effort
- **Hours Estimate**: 6-8 hours
  - JSON parsing: 2h
  - Rate limit handling: 2h
  - Multi-subreddit aggregation: 2h
  - Testing: 2h
- **Score**: 8/10 (relatively straightforward)

#### Data Quality & Relevance
- **Pros**:
  - High engagement signals (upvotes, comments)
  - Community-curated content
  - Rich discussion context
- **Cons**:
  - US-centric bias
  - Meme/entertainment heavy
  - Variable quality per subreddit
- **Score**: 7/10

#### Legal/TOS Restrictions
- **Official Stance**: Reddit prefers official API usage
- **JSON Endpoints**: Technically tolerated but not official
- **API Changes**: History of sudden policy changes (2023)
- **Risk Level**: Medium
- **Score**: 5/10

#### **TOTAL SCORE: 46/70**

#### Recommendation
**DEFER TO ITERATION 3** - While technically accessible, rate limits are too restrictive for multi-country monitoring without OAuth implementation. Better suited for targeted use cases (specific subreddit monitoring) rather than global trend detection.

---

### 2. Mastodon/Fediverse Public Firehose

#### API Access Method
- **Streaming Endpoints**: `/api/v1/streaming/public` (per instance)
- **Trends API**: `GET /api/v1/trends/tags`
- **Aggregation Project**: `mastodon-firehose` (community project)

#### Authentication Requirements
- **Trends API**: None (OAuth: Public)
- **Streaming**: None for public timeline
- **Score**: 10/10

#### Rate Limits
- **No explicit limits** on trends API (per-instance)
- **Streaming**: WebSocket, continuous connection
- **Challenge**: Must query multiple instances for global coverage
- **Score**: 8/10 (per-instance limits vary)

#### Data Freshness
- **Real-time**: WebSocket streaming for firehose
- **Trends**: Updated continuously (implementation varies)
- **Score**: 10/10

#### Geographic Coverage
- **Global**: Yes, but fragmented across instances
- **Major Instances**:
  - mastodon.social (general)
  - mastodon.world (international)
  - Region-specific instances
- **Challenge**: No single global endpoint
- **Score**: 7/10 (global but requires multi-instance)

#### Content Type
- **Available**:
  - Posts (toots) with full text
  - Hashtags, mentions
  - Engagement metrics (favorites, reblogs)
  - Media attachments
- **Format**: JSON (ActivityPub protocol)

#### Implementation Effort
- **Hours Estimate**: 12-16 hours
  - Multi-instance discovery: 3h
  - WebSocket streaming setup: 4h
  - Data normalization: 3h
  - Instance health monitoring: 2h
  - Testing: 4h
- **Complexity**: Moderate-High
- **Score**: 4/10 (significant effort)

#### Data Quality & Relevance
- **Pros**:
  - Diverse, international community
  - Tech/policy focused content
  - Less commercial noise than Twitter
- **Cons**:
  - Smaller user base (~10M vs 500M+ Twitter)
  - Variable instance policies
  - Community resistance to scraping
- **Score**: 6/10

#### Legal/TOS Restrictions
- **Technical**: Fully open (ActivityPub)
- **Social**: Community norms against mass crawling
- **Ethical Concerns**: Federation values privacy
- **Risk**: Medium (technical OK, social friction)
- **Score**: 6/10

#### **TOTAL SCORE: 51/70**

#### Recommendation
**DEFER TO ITERATION 3** - While technically accessible and real-time, the multi-instance architecture adds complexity. Additionally, the Mastodon community has expressed concerns about global crawling infrastructure. Better to establish MVP with simpler sources first, then add Fediverse with proper community engagement.

---

### 3. YouTube Trending (No-Auth Methods)

#### API Access Method
- **Official API**: YouTube Data API v3 (`videos.list` with `mostPopular`)
- **Third-Party**: Various scraping services (RapidAPI, Apify)
- **Note**: YouTube discontinued Trending page in July 2025 (replaced with Explore)

#### Authentication Requirements
- **Official API**: API key required (Google Cloud)
- **Free Tier**: Yes, but limited
- **Score**: 7/10 (free API key, not OAuth)

#### Rate Limits
- **Official API**: 10,000 units/day (free tier)
- **Cost**: List request = 1 unit
- **Trending**: ~50 videos per region = 1 unit
- **Daily Budget**: 200 regions max (more than needed)
- **Score**: 7/10 (adequate for MVP)

#### Data Freshness
- **Update Frequency**: Hourly (trending changes gradually)
- **API Latency**: Near real-time
- **Score**: 7/10

#### Geographic Coverage
- **Regions**: 90+ countries supported
- **Regional Trending**: Per-country trending charts
- **Score**: 9/10 (excellent global coverage)

#### Content Type
- **Available**:
  - Video title, description
  - View count, likes, comments
  - Channel info, categories
  - Thumbnails, duration
- **Format**: JSON (well-documented)
- **Note**: No transcript/captions without extra API calls

#### Implementation Effort
- **Hours Estimate**: 6-8 hours
  - API key setup: 0.5h
  - Client implementation: 2h
  - Multi-region fetching: 2h
  - Response parsing: 1.5h
  - Error handling: 1h
  - Testing: 1h
- **Score**: 8/10

#### Data Quality & Relevance
- **Pros**:
  - High signal for pop culture trends
  - Global perspective (regional charts)
  - High engagement content
- **Cons**:
  - Entertainment-heavy (not news focused)
  - Algorithm-curated (not organic)
  - Limited to video titles (need processing for topics)
- **Score**: 6/10 (good but narrow content type)

#### Legal/TOS Restrictions
- **Official API**: Clear TOS, permissive for non-commercial research
- **Quota Management**: Must monitor usage
- **Compliance**: Straightforward
- **Score**: 9/10

#### **TOTAL SCORE: 53/70**

#### Recommendation
**DEFER TO ITERATION 3** - While accessible and well-documented, the entertainment focus and July 2025 Trending page deprecation make this lower priority. Good complementary source after news-focused sources are established. Consider for media/culture vertical expansion.

---

### 4. RSS Aggregation (Global News Outlets)

#### API Access Method
- **Direct RSS Feeds**: HTTP GET requests to feed URLs
- **Aggregators**: Feedly API, Inoreader API (optional)
- **Standard**: RSS 2.0, Atom 1.0 (XML)

#### Authentication Requirements
- **RSS Feeds**: None (public endpoints)
- **Aggregator APIs**: API key (if using services like Feedly)
- **Recommendation**: Direct RSS parsing (no auth)
- **Score**: 10/10

#### Rate Limits
- **Direct Feeds**: Typically none, or very generous (1000+ req/day)
- **Best Practice**: 15-minute polling interval per feed
- **Courtesy**: Set User-Agent, respect HTTP 304 (Not Modified)
- **Score**: 10/10

#### Data Freshness
- **Update Frequency**: Varies by outlet (5-60 minutes)
- **Major News**: BBC, Reuters, AP update every 5-15 minutes
- **Polling Recommended**: 15-minute cycle (aligns with current system)
- **Score**: 8/10

#### Geographic Coverage
- **Global**: Excellent with proper feed selection
- **Top Sources by Region**:
  - **Global**: BBC World, Reuters, AP, AFP
  - **Americas**: CNN, NYT, Globe and Mail, Folha de S.Paulo
  - **Europe**: The Guardian, Le Monde, Der Spiegel, El País
  - **Asia**: Al Jazeera, NHK, Times of India, Straits Times
  - **Africa**: Daily Maverick, The East African
- **Score**: 10/10

#### Content Type
- **Available**:
  - Headline, description/summary
  - Full article URL
  - Publication date
  - Category/tags (some feeds)
  - Author (some feeds)
- **Format**: XML (RSS/Atom)
- **Processing**: Need XML parser + NLP for topic extraction

#### Implementation Effort
- **Hours Estimate**: 4-6 hours
  - RSS parser library integration: 1h
  - Feed list curation: 1h
  - Polling scheduler: 1h
  - XML to internal format: 1h
  - Error handling (404, timeouts): 1h
  - Testing with 20-30 feeds: 1h
- **Score**: 10/10 (very straightforward)

#### Data Quality & Relevance
- **Pros**:
  - Professional journalism (high quality)
  - News-focused (perfect fit)
  - Editorial curation (signal over noise)
  - Established credibility
- **Cons**:
  - Headlines only (not full text in many feeds)
  - Variable update frequency
  - Some feeds require scraping for full content
- **Score**: 9/10 (excellent for news trends)

#### Legal/TOS Restrictions
- **RSS Standard**: Designed for syndication (permissive)
- **Fair Use**: Headlines/summaries typically allowed
- **Attribution**: Should include source
- **Risk**: Very low (standard practice)
- **Score**: 10/10

#### **TOTAL SCORE: 67/70** ⭐

#### Recommendation
**IMPLEMENT IN ITERATION 2 - HIGH PRIORITY** - Excellent fit for news trend detection. No authentication, generous limits, global coverage, and high-quality data. Direct alignment with project goals. Can complement existing Wikipedia/GDELT sources.

#### Implementation Notes
- Curate 30-50 feeds across regions (see feed list in Appendix)
- Use `feedparser` library (Python) or `rss-parser` (Node.js)
- Implement ETag/Last-Modified handling for efficiency
- Store feed items for deduplication
- Consider using feed aggregator APIs (Feedly, Inoreader) for future scaling

---

### 5. Wikipedia Talk Pages

#### API Access Method
- **MediaWiki Action API**: `action=query&prop=revisions`
- **REST API**: `/page/{title}/history`
- **Specific**: Fetch pages with namespace=1 (Talk:) or 3 (User_talk:)

#### Authentication Requirements
- **Read Access**: None required
- **Higher Limits**: Optional API token (5000 req/hour vs 500)
- **Score**: 10/10

#### Rate Limits
- **Unauthenticated**: 500 requests/hour per IP (api.wikimedia.org)
- **Authenticated**: 5,000 requests/hour (personal API token)
- **REST API**: 200 requests/second
- **Score**: 9/10 (very generous)

#### Data Freshness
- **Real-time**: Talk pages update immediately
- **API Latency**: < 1 second
- **Recent Changes API**: Can stream real-time edits
- **Score**: 10/10

#### Geographic Coverage
- **Global**: 300+ language editions
- **Major Languages**: en, es, de, fr, ja, pt, ru, zh
- **Challenge**: Most activity on English Wikipedia
- **Score**: 8/10 (global but English-heavy)

#### Content Type
- **Available**:
  - Discussion text (full wikitext)
  - Timestamps, editors
  - Edit summaries
  - Section headers (topics)
- **Analysis Potential**:
  - Controversial topics (high edit activity)
  - Emerging events (new talk page sections)
  - Editorial disputes (content quality signals)
- **Format**: JSON + wikitext (needs parsing)

#### Implementation Effort
- **Hours Estimate**: 8-12 hours
  - API client: 2h
  - Wikitext parsing: 3h
  - Controversy detection algorithm: 3h
  - Multi-language support: 2h
  - Testing: 2h
- **Complexity**: Moderate (wikitext parsing is non-trivial)
- **Score**: 6/10

#### Data Quality & Relevance
- **Pros**:
  - Early indicator of emerging topics
  - High-quality discourse (Wikipedia editor standards)
  - Multilingual coverage
  - Signals controversy/importance
- **Cons**:
  - Lower volume than article pageviews
  - Requires NLP to extract topics
  - Wikipedia-specific context
  - Can be very meta (policy discussions)
- **Score**: 7/10

#### Legal/TOS Restrictions
- **License**: CC BY-SA 4.0 (very permissive)
- **Terms**: Clear, research-friendly
- **Attribution**: Required (easy to comply)
- **Recent Changes**: Nov 2025 push for Wikimedia Enterprise (paid) for high-volume AI training, but research use explicitly allowed
- **Score**: 9/10

#### **TOTAL SCORE: 59/70** ⭐

#### Recommendation
**IMPLEMENT IN ITERATION 2 - MEDIUM PRIORITY** - Unique data source for controversy/emerging topic detection. Complements existing Wikipedia pageviews data. Good signal quality but requires moderate NLP effort. Implement after RSS feeds are working.

#### Implementation Notes
- Focus on high-traffic articles' talk pages (top 1000 pageviews)
- Track talk page edit frequency as controversy signal
- Parse section headers for topic extraction
- Consider Recent Changes API for real-time monitoring
- Start with English Wikipedia, expand to top 5 languages

---

### 6. Internet Routing Datasets (CAIDA, RIPE RIS, BGP)

#### API Access Method
- **CAIDA BGPStream**: Software framework for BGP data analysis
- **RIPE RIS Live**: WebSocket JSON API (`wss://ris-live.ripe.net/v1/ws`)
- **RIPEstat Data API**: REST endpoints for historical data

#### Authentication Requirements
- **CAIDA**: Free registration (2025 requirement)
  - One-time portal signup + data use justification
  - Access granted automatically for research
- **RIPE RIS Live**: No authentication
  - Optional client parameter in WebSocket URL
- **Score**: 9/10 (minimal friction)

#### Rate Limits
- **CAIDA**: No rate limits (datasets, not API)
- **RIPE RIS Live**: No documented limits
  - WebSocket streaming (continuous)
  - Reasonable use expected
- **RIPEstat API**: Historical data, no strict limits
- **Score**: 10/10

#### Data Freshness
- **RIS Live**: Real-time BGP messages (sub-second latency)
- **CAIDA**: 15-minute files (BGP updates), monthly datasets (topology)
- **Score**: 10/10 (real-time available)

#### Geographic Coverage
- **Global**: Yes, Internet-wide routing tables
- **RIPE**: Europe, Middle East, parts of Asia
- **CAIDA**: Global perspective (multiple vantage points)
- **Score**: 10/10

#### Content Type
- **BGP Messages**:
  - Route announcements/withdrawals
  - AS path information
  - Prefix hijacking signals
  - Network reachability changes
- **Use Cases**:
  - Internet outage detection (geopolitical events)
  - Censorship detection (route filtering)
  - Infrastructure attacks
- **Format**: JSON (RIS Live), MRT (CAIDA)

#### Implementation Effort
- **Hours Estimate**: 20-30 hours
  - Domain expertise: 8h (BGP protocol understanding)
  - WebSocket client: 3h
  - BGP message parsing: 5h
  - Geopolitical event mapping: 6h
  - Anomaly detection algorithm: 6h
  - Testing: 2h
- **Complexity**: High (specialized domain knowledge)
- **Score**: 2/10

#### Data Quality & Relevance
- **Pros**:
  - Unique signal (infrastructure-level events)
  - Early warning for censorship/outages
  - Objective, technical data
- **Cons**:
  - Indirect signal for social trends
  - Requires expert interpretation
  - Noisy (many benign routing changes)
  - Not directly about topics/content
- **Score**: 4/10 (high quality, low relevance for trend detection)

#### Legal/TOS Restrictions
- **CAIDA**: Academic/research use (permissive)
- **RIPE**: Open data, research-friendly
- **Attribution**: Required for publications
- **Score**: 10/10

#### **TOTAL SCORE: 55/70**

#### Recommendation
**DEFER TO ITERATION 3+ / SPECIALIZED USE ONLY** - While technically excellent and real-time, routing data is tangential to social/news trend detection. Better suited for:
- **Future Feature**: "Internet Health" dashboard vertical
- **Geopolitical Events**: Detect censorship, outages (complement news)
- **Advanced MVP**: After core trend detection is mature

Not recommended for Iteration 2 unless focusing on infrastructure/geopolitics vertical.

---

### 7. Hacker News (Algolia API + Firebase API)

#### API Access Method
- **Algolia Search API**: `https://hn.algolia.com/api/v1/search`
- **Firebase API**: `https://hacker-news.firebaseio.com/v0/{endpoint}.json`
  - Endpoints: `/topstories`, `/newstories`, `/beststories`, `/askstories`

#### Authentication Requirements
- **Algolia**: None (public search endpoint)
- **Firebase**: None
- **Score**: 10/10

#### Rate Limits
- **Firebase API**: No rate limit (officially documented)
- **Algolia API**: No documented limit (1000 result cap per search)
- **Best Practice**: Reasonable use (don't hammer)
- **Score**: 10/10

#### Data Freshness
- **Near Real-time**: Stories appear within minutes of posting
- **Update Frequency**: Continuous (Firebase supports WebSocket)
- **Score**: 10/10

#### Geographic Coverage
- **Audience**: Global, but English-only
- **Content Focus**: Tech, startups, science
- **Geographic Bias**: US tech sector heavy (~60%)
- **Score**: 6/10 (global reach, niche focus)

#### Content Type
- **Available**:
  - Story titles (URLs to external articles)
  - Points (upvotes), comment count
  - Author, timestamp
  - Story type (story, ask, show, job)
  - Full comment threads (nested)
- **Format**: JSON (clean, simple)

#### Implementation Effort
- **Hours Estimate**: 3-4 hours
  - API client: 1h
  - Top stories fetching: 0.5h
  - Comment parsing (if needed): 1h
  - Point/comment trending logic: 0.5h
  - Testing: 1h
- **Score**: 10/10 (extremely simple)

#### Data Quality & Relevance
- **Pros**:
  - High signal-to-noise (community curation)
  - Tech/science focus (quality content)
  - HN front page = strong trend signal
  - Engaged, intelligent community
- **Cons**:
  - Niche audience (not general public)
  - English only
  - Limited to tech/startup sphere
- **Score**: 8/10 (excellent quality, narrow scope)

#### Legal/TOS Restrictions
- **Official API**: Explicitly provided for public use
- **Terms**: Very permissive
- **Attribution**: Not required (but courteous)
- **Score**: 10/10

#### **TOTAL SCORE: 64/70** ⭐

#### Recommendation
**IMPLEMENT IN ITERATION 2 - HIGH PRIORITY** - Extremely easy to implement, no auth, no rate limits, high-quality data. Perfect for tech/science trends. Can be MVP's "Tech Trends" vertical or complement general news sources.

#### Implementation Notes
- Use Firebase API for top stories (simpler than Algolia)
- Fetch top 100 stories every 15 minutes (or real-time with WebSocket)
- Track point velocity (points per hour) for trending signal
- Consider story types: frontpage, Ask HN (questions), Show HN (launches)
- Combine with comment count for engagement signal

---

### 8. Common Crawl News Dataset

#### API Access Method
- **HTTP/S3 Access**: `https://data.commoncrawl.org/crawl-data/CC-NEWS/`
- **Format**: WARC files (Web ARChive)
- **Index**: Monthly indexes available

#### Authentication Requirements
- **None**: Public dataset, no AWS credentials needed
- **Score**: 10/10

#### Rate Limits
- **None**: Standard HTTP download limits
- **Bandwidth**: ~50 MB per day's WARC file
- **Score**: 10/10

#### Data Freshness
- **Daily Updates**: New WARC files published daily
- **Latency**: 1-2 days behind real-time
- **Coverage**: 2016-2025 (current)
- **Score**: 5/10 (daily, not real-time)

#### Geographic Coverage
- **Global**: News sites worldwide
- **Coverage**: 80+ million news articles crawled
- **Languages**: Multilingual (based on crawled sites)
- **Score**: 10/10

#### Content Type
- **Available**:
  - Full article HTML
  - Metadata (URL, timestamp, HTTP headers)
  - News site structure
- **Format**: WARC (requires specialized parsing)
- **Challenge**: Need to extract clean text from HTML

#### Implementation Effort
- **Hours Estimate**: 30-40 hours
  - WARC parsing library: 3h
  - HTML to clean text extraction: 8h
  - Daily file download scheduler: 2h
  - Language detection: 2h
  - Deduplication: 5h
  - Topic extraction NLP: 8h
  - Storage (large files): 2h
  - Testing: 10h
- **Complexity**: Very High
- **Score**: 1/10 (significant engineering effort)

#### Data Quality & Relevance
- **Pros**:
  - Comprehensive news coverage
  - Full article text (not just headlines)
  - Historical depth (2016+)
  - Multilingual
- **Cons**:
  - Raw HTML (noisy, needs cleaning)
  - Mixed quality (all news sites, not curated)
  - Large files (storage/processing intensive)
  - 1-2 day lag (not real-time)
- **Score**: 7/10

#### Legal/TOS Restrictions
- **License**: Public dataset, permissive
- **Use Case**: Research, non-commercial explicitly allowed
- **Attribution**: Credit to Common Crawl
- **Score**: 10/10

#### **TOTAL SCORE: 53/70**

#### Recommendation
**DEFER TO ITERATION 3+ / BATCH PROCESSING USE CASE** - While comprehensive, Common Crawl requires significant engineering effort (WARC parsing, HTML cleaning) and is not real-time (1-2 day lag). Better suited for:
- **Historical Analysis**: Backfill data for 2016-2025 trends
- **Research**: Deep dives into past events
- **ML Training**: Large corpus for NLP model training

Not recommended for real-time MVP. Consider for Iteration 3+ if need historical depth.

---

## Summary Comparison Table

| Data Source | Auth | Rate Limits | Freshness | Geo Coverage | Impl. Effort | Quality | Legal | **TOTAL** | Priority |
|-------------|------|-------------|-----------|--------------|--------------|---------|-------|-----------|----------|
| **RSS Aggregation** | 10 | 10 | 8 | 10 | 10 | 9 | 10 | **67/70** | **P0** ⭐ |
| **Hacker News** | 10 | 10 | 10 | 6 | 10 | 8 | 10 | **64/70** | **P0** ⭐ |
| **Wikipedia Talk Pages** | 10 | 9 | 10 | 8 | 6 | 7 | 9 | **59/70** | **P1** ⭐ |
| **Internet Routing (BGP)** | 9 | 10 | 10 | 10 | 2 | 4 | 10 | **55/70** | P3 (Specialized) |
| **YouTube Trending** | 7 | 7 | 7 | 9 | 8 | 6 | 9 | **53/70** | P2 |
| **Common Crawl News** | 10 | 10 | 5 | 10 | 1 | 7 | 10 | **53/70** | P3 (Batch) |
| **Mastodon/Fediverse** | 10 | 8 | 10 | 7 | 4 | 6 | 6 | **51/70** | P2 |
| **Reddit (JSON)** | 7 | 3 | 10 | 6 | 8 | 7 | 5 | **46/70** | P2 |

---

## Iteration 2 Recommendations

### Tier 1: Implement Immediately (High Priority)

#### 1. RSS Aggregation (67/70) ⭐
**Why**: No auth, generous limits, news-focused, global coverage, simple implementation.
**Effort**: 4-6 hours
**Impact**: High - direct alignment with news trend detection
**Dependencies**: None (RSS parser library)

**Quick Wins**:
- Start with 10 major feeds (BBC, Reuters, AP, Al Jazeera, etc.)
- Expand to 30-50 feeds covering all regions
- Integrate with existing GDELT/Wikipedia trend detection
- Provides headlines for topic clustering

#### 2. Hacker News (64/70) ⭐
**Why**: Zero auth, no rate limits, high-quality signal, trivial implementation.
**Effort**: 3-4 hours
**Impact**: Medium - excellent for tech/startup trends vertical
**Dependencies**: None (simple HTTP JSON)

**Quick Wins**:
- Use Firebase API for top 100 stories
- Track point velocity for trending detection
- Complements news sources with tech perspective
- Can launch "Tech Trends" feature quickly

### Tier 2: Implement After Tier 1 (Medium Priority)

#### 3. Wikipedia Talk Pages (59/70) ⭐
**Why**: Unique controversy signal, complements pageviews, generous API.
**Effort**: 8-12 hours
**Impact**: Medium - adds depth to Wikipedia integration
**Dependencies**: Wikitext parser, existing Wikipedia client

**Why After Tier 1**: Requires more NLP work (wikitext parsing), medium complexity. Better to nail RSS/HN first, then add this enrichment.

### Tier 3: Defer to Iteration 3

#### 4. YouTube Trending (53/70)
**Reason**: Requires Google Cloud API key setup, entertainment-heavy content, Trending page deprecated July 2025. Better for media/culture vertical expansion later.

#### 5. Mastodon/Fediverse (51/70)
**Reason**: Multi-instance complexity, community concerns about scraping, moderate effort. Wait until MVP proven, then add with proper community engagement.

#### 6. Reddit JSON (46/70)
**Reason**: Restrictive rate limits (10 req/min unauthenticated), US-centric, history of API policy changes. Better for targeted subreddit monitoring (e.g., r/worldnews only) than global trends.

### Tier 4: Specialized Use Cases Only

#### 7. Internet Routing/BGP (55/70)
**Use Case**: Future "Internet Health" dashboard, censorship detection, geopolitical infrastructure monitoring.
**Reason**: High score but low relevance for social/news trends. Consider for specialized vertical in Iteration 4+.

#### 8. Common Crawl News (53/70)
**Use Case**: Historical backfill (2016-2025), ML training corpus, deep research.
**Reason**: High engineering effort (WARC parsing), 1-2 day lag, storage intensive. Better for batch processing pipeline in future.

---

## Implementation Roadmap for Iteration 2

### Phase 1: RSS Aggregation (Week 1, 4-6 hours)
**Goal**: Add 30-50 global news RSS feeds to pipeline

**Tasks**:
1. Integrate `feedparser` library (Python) or `rss-parser` (Node.js)
2. Curate feed list (see Appendix A for recommended feeds)
3. Implement 15-minute polling scheduler (aligns with current refresh)
4. Parse RSS items to internal format (headline, URL, timestamp, source)
5. Add to existing trend detection pipeline
6. Test with top 10 feeds, expand to 30-50

**Output**: `/v1/trends/sources` endpoint includes RSS data

**Success Metrics**:
- 30+ feeds operational
- < 1 minute latency per feed
- 95%+ uptime per feed
- Deduplication working (same story, multiple sources)

---

### Phase 2: Hacker News (Week 1, 3-4 hours)
**Goal**: Add HN top stories to tech trends vertical

**Tasks**:
1. Implement Firebase API client (HN endpoint)
2. Fetch top 100 stories every 15 minutes
3. Calculate point velocity (trending signal)
4. Filter by story type (story, ask, show)
5. Integrate with existing `/v1/flows` or create `/v1/trends/tech`

**Output**: Tech trends endpoint or HN integration in flows

**Success Metrics**:
- Top 20 HN stories tracked
- Point velocity calculated correctly
- Sub-minute API response time
- No rate limit issues (none expected)

---

### Phase 3: Wikipedia Talk Pages (Week 2, 8-12 hours)
**Goal**: Add controversy detection from talk page activity

**Tasks**:
1. Extend Wikipedia client with talk page fetching
2. Implement wikitext parser (section headers)
3. Track edit frequency per talk page
4. Identify high-activity talk pages (controversy signal)
5. Extract topic keywords from section headers
6. Add to `/v1/flows` as controversy intensity signal

**Output**: Controversy score in hotspot data

**Success Metrics**:
- Top 100 talk pages monitored
- Edit frequency tracked (per hour)
- Controversy score (0-1) calculated
- Integrated with existing Wikipedia pageviews

---

## Technical Integration Details

### Backend Architecture Changes

#### New Services (to add to `backend/app/services/`)
1. **`rss_client.py`**
   - Feed fetching with ETag/Last-Modified support
   - XML parsing (feedparser)
   - Error handling (timeouts, malformed XML)
   - Structured logging

2. **`hackernews_client.py`**
   - Firebase API wrapper
   - Top stories fetching
   - Point velocity calculation
   - Comment count tracking

3. **`wiki_talk_client.py`** (extends existing `wiki_client.py`)
   - Talk page revision fetching
   - Wikitext parsing
   - Edit frequency analysis
   - Controversy scoring

#### Database Changes
```sql
-- New table for RSS feed items (for deduplication)
CREATE TABLE rss_feed_items (
    id SERIAL PRIMARY KEY,
    feed_source VARCHAR(255) NOT NULL,
    item_url VARCHAR(2048) UNIQUE NOT NULL,
    title TEXT NOT NULL,
    published_at TIMESTAMP NOT NULL,
    fetched_at TIMESTAMP DEFAULT NOW(),
    content_hash VARCHAR(64) -- For deduplication
);

CREATE INDEX idx_rss_url ON rss_feed_items(item_url);
CREATE INDEX idx_rss_published ON rss_feed_items(published_at DESC);

-- New table for HN stories tracking
CREATE TABLE hackernews_stories (
    id INTEGER PRIMARY KEY, -- HN story ID
    title TEXT NOT NULL,
    url VARCHAR(2048),
    score INTEGER,
    comments INTEGER,
    timestamp TIMESTAMP,
    fetched_at TIMESTAMP DEFAULT NOW(),
    score_velocity FLOAT -- Points per hour
);

-- New table for Wikipedia talk page activity
CREATE TABLE wiki_talk_pages (
    page_id INTEGER PRIMARY KEY,
    page_title VARCHAR(255) NOT NULL,
    language VARCHAR(10) DEFAULT 'en',
    edit_count_1h INTEGER DEFAULT 0,
    edit_count_24h INTEGER DEFAULT 0,
    controversy_score FLOAT,
    last_checked TIMESTAMP DEFAULT NOW()
);
```

#### API Endpoint Changes
```python
# backend/app/api/v1/trends.py

@router.get("/trends/top")
async def get_top_trends(
    country: str = "US",
    limit: int = 10,
    sources: List[str] = Query(["wikipedia", "trends", "gdelt", "rss", "hn"])
):
    """
    Get top trends with multi-source support.
    New sources: rss, hn (hackernews)
    """
    # ... existing logic ...
    if "rss" in sources:
        rss_trends = await rss_client.get_trending_topics(country)
        all_trends.extend(rss_trends)

    if "hn" in sources:
        hn_trends = await hackernews_client.get_top_stories(limit=20)
        all_trends.extend(hn_trends)

    # Merge and rank
    return merge_and_rank_trends(all_trends, limit)

# New endpoint for tech-specific trends
@router.get("/trends/tech")
async def get_tech_trends(limit: int = 20):
    """Get tech/startup trends from Hacker News."""
    stories = await hackernews_client.get_top_stories(limit=limit)
    return {
        "source": "hackernews",
        "timestamp": datetime.utcnow(),
        "trends": stories
    }
```

---

## Data Source Feed Lists

### Appendix A: Recommended RSS Feeds (30 feeds)

#### Global News (10 feeds)
1. **BBC World** - `http://feeds.bbci.co.uk/news/world/rss.xml`
2. **Reuters** - `https://www.reutersagency.com/feed/`
3. **Associated Press** - `https://rssmix.com/u/8400732/rss.xml`
4. **Al Jazeera English** - `https://www.aljazeera.com/xml/rss/all.xml`
5. **AFP (Agence France-Presse)** - `https://www.afp.com/en/rss`
6. **DW (Deutsche Welle)** - `https://rss.dw.com/xml/rss-en-all`
7. **France 24** - `https://www.france24.com/en/rss`
8. **The Guardian World** - `https://www.theguardian.com/world/rss`
9. **NPR News** - `https://feeds.npr.org/1001/rss.xml`
10. **CNN World** - `http://rss.cnn.com/rss/cnn_world.rss`

#### Americas (5 feeds)
11. **New York Times World** - `https://rss.nytimes.com/services/xml/rss/nyt/World.xml`
12. **The Globe and Mail (Canada)** - `https://www.theglobeandmail.com/arc/outboundfeeds/rss/category/world/`
13. **Folha de S.Paulo (Brazil)** - `https://www1.folha.uol.com.br/rss/mundo.xml`
14. **Clarín (Argentina)** - `https://www.clarin.com/rss/mundo/`
15. **El Universal (Mexico)** - `https://www.eluniversal.com.mx/seccion/6/mundo/rss.xml`

#### Europe (5 feeds)
16. **Le Monde (France)** - `https://www.lemonde.fr/rss/une.xml`
17. **Der Spiegel (Germany)** - `https://www.spiegel.de/international/index.rss`
18. **El País (Spain)** - `https://feeds.elpais.com/mrss-s/pages/ep/site/elpais.com/portada`
19. **Corriere della Sera (Italy)** - `https://www.corriere.it/rss/homepage.xml`
20. **The Times (UK)** - `https://www.thetimes.co.uk/rss`

#### Asia & Pacific (5 feeds)
21. **NHK World (Japan)** - `https://www3.nhk.or.jp/rss/news/cat0.xml`
22. **Times of India** - `https://timesofindia.indiatimes.com/rssfeeds/-2128936835.cms`
23. **The Straits Times (Singapore)** - `https://www.straitstimes.com/news/world/rss.xml`
24. **South China Morning Post** - `https://www.scmp.com/rss/2/feed`
25. **The Sydney Morning Herald** - `https://www.smh.com.au/rss/world.xml`

#### Middle East & Africa (5 feeds)
26. **Haaretz (Israel)** - `https://www.haaretz.com/cmlink/1.628752`
27. **Daily Maverick (South Africa)** - `https://www.dailymaverick.co.za/dmrss/`
28. **The East African** - `https://www.theeastafrican.co.ke/tea/rss`
29. **Ahram Online (Egypt)** - `http://english.ahram.org.eg/UI/Front/Inner.aspx?NewsContentID=1&secID=1`
30. **The National (UAE)** - `https://www.thenationalnews.com/rss`

---

## Blockers and Concerns

### Identified Risks

1. **RSS Feed Instability**
   - **Risk**: Individual feeds may go offline, change URLs, or break formatting
   - **Mitigation**:
     - Implement per-feed health monitoring
     - Graceful degradation (continue with working feeds)
     - Quarterly feed audit and URL updates
     - Use feed aggregator API (Feedly) as backup

2. **Hacker News Data Niche**
   - **Risk**: HN is tech-focused, not representative of general public
   - **Mitigation**:
     - Label clearly as "Tech Trends" vertical
     - Don't mix HN data with general news trends
     - Use as complementary signal, not primary

3. **Wikipedia Talk Page Noise**
   - **Risk**: Much talk page activity is meta (policy, formatting debates)
   - **Mitigation**:
     - Focus on high-pageview articles (top 1000)
     - Filter out meta namespaces (Wikipedia:, Template:)
     - Use edit velocity as signal, not content analysis (initially)
     - Human-in-the-loop validation for top controversies

4. **Deduplication Complexity**
   - **Risk**: Same story from 30 RSS feeds = 30 duplicate trend signals
   - **Mitigation**:
     - Content-based hashing (title similarity)
     - URL normalization (strip tracking params)
     - Source clustering (group by story, not source)
     - Existing flow detection algorithm helps (TF-IDF)

5. **Rate Limit Monitoring**
   - **Risk**: Even "no rate limit" APIs can have undocumented throttling
   - **Mitigation**:
     - Implement exponential backoff for all HTTP errors
     - Monitor API response times (detect soft throttling)
     - Respect HTTP 429 and Retry-After headers
     - Log all API errors for pattern detection

---

## Cost Analysis

### Iteration 2 Implementation Costs

#### Development Time
- **RSS Aggregation**: 4-6 hours
- **Hacker News**: 3-4 hours
- **Wikipedia Talk Pages**: 8-12 hours
- **Testing & Integration**: 4-6 hours
- **Documentation**: 2-3 hours
- **TOTAL**: **21-31 hours** (3-4 days)

#### Infrastructure Costs (Monthly)
- **RSS Parsing**: $0 (compute only)
- **Hacker News**: $0 (free API)
- **Wikipedia**: $0 (free API)
- **Redis Cache**: $50-100 (existing, slight increase)
- **Database Storage**: +$5 (minimal, new tables)
- **Bandwidth**: +$5-10 (RSS feeds, ~1 MB/day)
- **TOTAL**: **~$60-115/month** (marginal increase)

#### Scaling Costs (100+ countries)
- **RSS**: No change (same 30 feeds)
- **HN**: No change (global, no per-country)
- **Wikipedia**: +$0 (same 500 req/hour limit suffices)
- **Total**: Same as above

---

## Success Criteria for Iteration 2

### Quantitative Metrics
1. **Data Sources**: 3 new sources integrated (RSS, HN, Wiki Talk)
2. **Coverage**: 30+ RSS feeds operational (90%+ uptime)
3. **Latency**: < 2 minutes from source update to API response
4. **API Performance**: `/v1/trends/top` response time < 1s (cached)
5. **Deduplication**: < 5% duplicate stories in trends list

### Qualitative Metrics
1. **Data Quality**: RSS headlines provide clear, news-focused topics
2. **Tech Trends**: HN integration successfully shows tech/startup trends
3. **Controversy Signal**: Wikipedia talk page activity correlates with known controversial events
4. **User Feedback**: If deployed, positive reception on diverse data sources

---

## Next Steps After Iteration 2

### Iteration 3 Candidates
1. **Reddit** - Implement with OAuth for higher rate limits (100 req/min)
2. **Mastodon** - Multi-instance aggregation with community engagement
3. **YouTube** - Entertainment/culture vertical (if expanding beyond news)
4. **Twitter/X** - If budget allows paid API ($100-5000/month)

### Advanced Features
1. **Sentiment Analysis** - Analyze RSS article sentiment (positive/negative)
2. **Entity Recognition** - Extract people, places, organizations from headlines
3. **Event Detection** - Cluster related stories into "events" (e.g., "Summit 2025")
4. **Historical Backfill** - Use Common Crawl for 2016-2025 historical trends

---

## Conclusion

**For Iteration 2, implement these 3 data sources**:

1. ⭐ **RSS Aggregation (Priority 0)** - 30-50 global news feeds, 4-6 hours effort
2. ⭐ **Hacker News (Priority 0)** - Tech trends vertical, 3-4 hours effort
3. ⭐ **Wikipedia Talk Pages (Priority 1)** - Controversy detection, 8-12 hours effort

**Total effort**: 15-22 hours (2-3 days)
**Total cost**: ~$60-115/month (marginal infrastructure increase)
**High-value outcome**: Diversified data sources, global news coverage, tech trends vertical

**Defer to Iteration 3**: Reddit (OAuth needed), Mastodon (complexity), YouTube (niche), Common Crawl (batch processing), Internet Routing (specialized)

This approach balances **quick wins** (RSS, HN) with **strategic depth** (Wikipedia talk) while avoiding over-engineering (no BGP routing, no WARC parsing) in early iterations.

---

**Report prepared by**: Claude Code (Research Agent)
**Date**: 2025-01-13
**Next Review**: After Iteration 2 implementation

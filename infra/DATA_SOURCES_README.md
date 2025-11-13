# Global Narrative Tracking - Data Sources Feasibility Study

## Overview

This directory contains a comprehensive research and feasibility analysis for implementing open/free data sources to support Observatorio Global's narrative tracking capabilities. Three complementary data sources have been identified and ranked for implementation in Iteration 2.

## Files

### 1. TOP_3_RECOMMENDATIONS_SUMMARY.txt (EXECUTIVE SUMMARY)
**Read this first** - Concise, formatted overview of the top 3 ranked recommendations.

Contains:
- Quick scoring and rationale
- Detailed profiles for each source
- Combined system architecture
- Implementation timeline (3 phases)
- Cost and risk analysis
- Next steps

**Best for**: Decision makers, project planning, quick reference

---

### 2. DATA_SOURCES_FEASIBILITY.md (DETAILED ANALYSIS)
Complete feasibility analysis covering all 7 evaluated data sources.

Contains:
- Comparative analysis table (all sources)
- Detailed evaluation per source:
  - Access method
  - Authentication requirements
  - Rate limits
  - Geographic coverage
  - Real-time availability
  - Implementation complexity
  - Pros/cons analysis
- Secondary tier recommendations
- Cost analysis
- Risk & mitigation strategies

**Best for**: Technical deep-dives, comparing tradeoffs, stakeholder presentations

---

### 3. DATA_SOURCES_IMPLEMENTATION.md (QUICK START GUIDE)
Hands-on implementation guide for the top 3 sources with code samples.

Contains:
- Hacker News Firebase API
  - Endpoint reference
  - Python collector implementation
  - Rate limiting strategy
  - Database schema
- Mastodon/Fediverse API
  - REST endpoints
  - Multi-instance collector
  - WebSocket streaming
  - Database schema
- RSS Aggregation
  - Recommended news outlets (20-30)
  - Python implementation
  - FreshRSS deployment
  - Database schema
- Data normalization layer
- Orchestration examples
- Next steps roadmap

**Best for**: Development teams, implementation, code reference

---

## Quick Comparison Table

| Rank | Source | Auth | Rate Limit | Real-time | Complexity | Effort | Score |
|------|--------|------|-----------|-----------|-----------|--------|-------|
| #1 | Hacker News (Firebase) | None | No limits | Yes (Firebase) | 2/5 | 12-16h | 9.5/10 |
| #2 | Mastodon/Fediverse | Optional | 300/5min | Yes (WebSocket) | 2/5 | 12-16h | 9.0/10 |
| #3 | RSS Aggregation | Varies | Varies | ~15min poll | 2/5 | 4-6h | 8.5/10 |

---

## Top 3 Recommendations

### 1. Hacker News (Firebase API) - Primary Source
- Zero auth, no rate limits
- Real-time updates via Firebase
- Excellent for tech/startup narratives
- ~500 stories available
- Comment threads provide narrative depth

### 2. Mastodon/Fediverse - Emerging Narratives
- No API key required
- True WebSocket streaming
- Global, decentralized perspective
- Captures emerging communities early
- Complements HN with non-tech narratives

### 3. RSS Aggregation - Validation Layer
- Captures traditional news signal
- 20-30 curated outlets (BBC, Reuters, AP, TechCrunch, etc.)
- Cross-platform validation
- Identifies mainstream adoption of narratives

---

## System Architecture

Three-layer architecture for comprehensive narrative tracking:

```
Layer 1: EMERGING (HN + Mastodon)
  Real-time, high signal-to-noise
  0-2 minute latency
  
  ↓ (aggregation + normalization)
  
Layer 2: VALIDATION (RSS News)
  Mainstream confirmation
  15-60 minute latency
  
  ↓ (cross-platform correlation)
  
Layer 3: ANALYSIS
  Clustering + trending
  Narrative divergence detection
```

---

## Implementation Roadmap

**Phase 1 (Week 1-2)**: HN + basic storage
**Phase 2 (Week 3-4)**: Mastodon multi-instance + clustering
**Phase 3 (Week 5+)**: RSS integration + visualization

**Total effort**: 42-54 hours (1-1.5 weeks)
**Total cost**: FREE (all open APIs + OSS tools)

---

## Data Sources Evaluated

### Evaluated (Recommended)
1. Hacker News (Firebase API) - RANK #1
2. Mastodon/Fediverse Public API - RANK #2
3. RSS Aggregation - RANK #3

### Evaluated (Secondary Tier)
4. Reddit (Public JSON API) - Requires OAuth, tighter rate limits
5. YouTube Trending - No official API, limited RSS (15 items)
6. RIPE BGP Routing Data - High complexity, niche signal
7. Hacker News Algolia API - Search-based, not real-time

---

## Key Findings

### Authentication
All top 3 sources require **zero or minimal authentication**:
- HN: No auth required
- Mastodon: Optional API key
- RSS: No auth for major outlets

### Rate Limits
**Not a constraint**:
- HN: No formal limits
- Mastodon: 300/5min (ample for multi-instance aggregation)
- RSS: Per-outlet, all are aggregator-friendly

### Real-Time Availability
**Full coverage**:
- HN: True real-time via Firebase
- Mastodon: WebSocket streaming + polling
- RSS: 15-60 minute poll intervals

### Implementation Complexity
**All low complexity** (2/5 on scale):
- Standard REST APIs
- Well-documented
- Mature Python libraries
- No specialized knowledge required

### Cost
**Completely free**:
- All APIs: Free tier or unlimited
- All tools: Open source
- Infrastructure: ~$50-200/month cloud hosting
- Development: ~42-54 hours engineering

---

## Getting Started

1. **Decision**: Approve these 3 sources for Iteration 2
2. **Planning**: Create 2-week sprint for Phase 1 (HN MVP)
3. **Setup**: 
   - Provision storage (PostgreSQL/MongoDB)
   - Set up compute environment
4. **Development**: 
   - Start with DATA_SOURCES_IMPLEMENTATION.md
   - Use code samples provided
5. **Testing**: Validate against real-time events

---

## Next Questions

- Which additional outlets for RSS tier? (Current: BBC, Reuters, AP, TechCrunch, etc.)
- What narrative clustering algorithm? (cosine similarity, LDA, transformer embeddings?)
- Retention policy? (How long to store data?)
- Real-time alerting needed? (Anomaly detection thresholds?)
- Visualization requirements? (Dashboard, API, reports?)

---

## References

- Hacker News API: https://github.com/HackerNews/API
- Mastodon API Docs: https://docs.joinmastodon.org/api/
- RSS Specs: https://tools.ietf.org/html/rfc4287 (Atom)
- FreshRSS: https://www.freshrss.org/
- Miniflux: https://miniflux.app/

---

**Created**: 2025-11-13
**Status**: Ready for implementation
**Recommendation**: Proceed with Phase 1 (HN MVP)

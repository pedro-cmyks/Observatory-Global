# Iteration 3: Narrative Intelligence Layer - Planning Summary

**Status:** Planning Phase
**Started:** 2025-01-14
**Target Completion:** 4-5 weeks from kickoff
**Priority:** High - Foundation for production system

---

## Executive Summary

Iteration 3 transforms Observatory Global from a demo using placeholder data to a production system ingesting real GDELT 2.0 data every 15 minutes. The architecture is designed around two key visualizations:

1. **Heatmap Layer** - Geographic intensity of information activity
2. **Classic Layer** - Narrative flow lines between countries

Both layers work simultaneously to create a "weather radar of global information."

---

## Architecture Foundation

### Core Principles

1. **GDELT GKG as Primary Source**
   - 280+ pre-classified themes
   - Geographic precision (lat/long coordinates)
   - Sentiment scoring (-100 to +100)
   - Updates every 15 minutes
   - ~1-2M articles/day globally

2. **Placeholder-First Development**
   - Define schema based on real GDELT structure
   - Build all features with GDELT-shaped placeholders
   - Migrate to real parser once architecture validated
   - Minimal changes required for real data integration

3. **Dual-Layer Visualization**
   - Heatmap shows WHERE information is heating up
   - Classic shows HOW narratives travel
   - Both toggleable, work simultaneously
   - Performance target: 60 FPS animations

---

## GitHub Issues Created

### Issue #13: Heatmap Rendering Bug
**Type:** Bug
**Priority:** Low (non-blocking)
**Status:** Open

**Problem:** Hexagons not rendering despite correct API data.

**Assignment:** Frontend visualization specialist

**Resolution Path:** Debug deck.gl integration, fix in parallel to core work.

---

### Issue #14: Iteration 3 Signals Schema
**Type:** Architecture
**Priority:** High
**Status:** Open

**Objective:** Design PostgreSQL schema for GDELT-based signals.

**Core Tables:**
```sql
gdelt_signals        -- Core table (GKG records)
signal_themes        -- Many-to-many (themes per signal)
signal_entities      -- Persons and organizations
theme_aggregations_1h -- Hourly rollups (warm storage)
```

**Key Requirements:**
- Support GDELT Tier 1 fields (V2Locations, V2Themes, V2Tone, V2Counts, V2DATE)
- Enable "Why is this heating up?" queries
- Support theme-based flow detection
- Handle 1-2M articles/day ingestion
- Query performance < 500ms

**Assignment:** DataSignalArchitect

**Reference:** `/docs/GDELT_SCHEMA_ANALYSIS.md`

---

### Issue #15: Dual-Layer Visualization Architecture
**Type:** Architecture
**Priority:** High
**Status:** Open

**Objective:** Design technical spec for rendering both layers simultaneously.

**Layer Stack:**
```
1. Mapbox base map (dark-v11)
2. Heatmap (H3 hexagons, blurred)
3. Flow lines (narrative paths)
4. Country centroids (nodes)
5. Labels & UI overlays
```

**Animation Requirements:**
- Pulsing centroids (breathing effect)
- Animated flow particles
- Heatmap gradient transitions
- Temporal glow (recent activity brighter)

**Performance Targets:**
- Initial render: < 1s
- Layer toggle: < 100ms
- Frame rate: 60 FPS
- Data update: < 500ms

**Enhanced Flow Detection:**
- Theme overlap (Jaccard similarity)
- Actor overlap (persons/organizations)
- Outlet overlap (news sources)
- Sentiment correlation

**Assignment:** Frontend Architect + Visualization Specialist

---

### Issue #16: GDELT-Matching Placeholders
**Type:** Infrastructure
**Priority:** High
**Status:** Open

**Objective:** Update placeholder generators to match real GDELT structure exactly.

**Current Placeholder:**
```python
{
  "title": "Political Developments in US",
  "source": "gdelt",
  "count": 45
}
```

**Target Placeholder:**
```python
{
  "gkg_record_id": "20250114120000-US-1",
  "country_code": "US",
  "latitude": 37.0902,
  "longitude": -95.7129,
  "timestamp": "2025-01-14T12:00:00Z",
  "themes": [
    {"code": "ECON_INFLATION", "label": "Economic Inflation", "count": 23},
    {"code": "PROTEST", "label": "Labor Protests", "count": 15}
  ],
  "tone": -3.5,
  "polarity": 2.1,
  "activity_density": 4.2,
  "entities": [
    {"type": "PERSON", "name": "Jerome Powell"},
    {"type": "ORGANIZATION", "name": "Federal Reserve"}
  ],
  "source_outlet": "Bloomberg",
  "url": "https://example.com/article"
}
```

**Key Requirements:**
- Use real GDELT theme taxonomy (280+ themes)
- Simulate continuous updates (not static)
- Realistic distributions (sentiment, frequencies)
- Backward compatible with existing code

**Assignment:** DataSignalArchitect

---

### Issue #17: Migration Checklist (Placeholder → Real Parser)
**Type:** Documentation
**Priority:** Medium
**Status:** Open

**Objective:** Comprehensive checklist for transitioning to real GDELT data.

**Phases:**
1. **Week 1:** GDELT Downloader + Parser
2. **Week 2:** Client Update + Database Integration
3. **Week 3:** Background Worker + Frontend Validation
4. **Week 4:** Testing + Monitoring

**Key Milestones:**
- [ ] Parse real GKG CSV files (50-150 MB)
- [ ] Extract V2Locations, V2Themes, V2Tone, V2Counts
- [ ] Filter by country
- [ ] Batch insert into PostgreSQL
- [ ] Schedule ingestion every 15 minutes
- [ ] Validate data quality (> 95%)

**Rollback Plan:** Feature flag to fall back to placeholders if parser fails.

**Estimated Timeline:** ~20 working days (~1 month)

**Assignment:** DataSignalArchitect + Backend Team

---

## Data Model Overview

### GDELT GKG Tier 1 Fields (Implement First)

| Field | Type | Purpose | Map Usage |
|-------|------|---------|-----------|
| `V2Locations` | Lat/Long | Geographic positioning | Heatmap position |
| `V2Themes` | Array[string] | 280+ topic codes | Flow detection, search |
| `V2Tone` | Float (-100 to +100) | Sentiment score | Heatmap color |
| `V2Counts` | Dict[theme → int] | Theme frequency | Heatmap intensity |
| `V2DATE` | Timestamp | Article publish time | Time-series, lag detection |
| `GKGRECORDID` | String | Unique identifier | Deduplication |

### GDELT GKG Tier 2 Fields (Implement Later)

| Field | Type | Purpose |
|-------|------|---------|
| `V2Persons` | Array[string] | Named individuals |
| `V2Organizations` | Array[string] | Institutions |
| `V2GCAM` | Array[float] | 2,300 emotional dimensions |
| `V2SourceCommonName` | String | News outlet |

---

## User Experience Goals

### "Why is this heating up?" Tooltip

When user hovers over hot region:
```json
{
  "country": "US",
  "intensity": 0.87,
  "top_themes": ["Economic Inflation", "Labor Protests"],
  "sentiment": -3.5,
  "dominant_emotion": "anger",
  "key_actors": ["Jerome Powell", "Janet Yellen"],
  "driving_outlets": ["Bloomberg", "Reuters"],
  "sample_headlines": [
    "Fed Maintains High Interest Rates Amid Inflation Concerns",
    "Labor Unions Rally Against Economic Policies"
  ]
}
```

### Progressive Disclosure

**Default View:**
- Show top 5 themes per country
- Aggregate sentiment
- Key actors (persons/orgs)

**Expanded View:**
- Show all active themes (up to 50)
- Theme frequency breakdown
- Outlet attribution
- Temporal trends

**Search View:**
- Filter by specific theme code
- Filter by entity name (person/org)
- Filter by time range
- Filter by sentiment

---

## Technical Specifications

### Database Schema (PostgreSQL)

**Table: `gdelt_signals`**
```sql
CREATE TABLE gdelt_signals (
  id BIGSERIAL PRIMARY KEY,
  gkg_record_id VARCHAR(100) UNIQUE NOT NULL,
  country_code VARCHAR(2),
  latitude DECIMAL(9,6),
  longitude DECIMAL(9,6),
  timestamp TIMESTAMPTZ NOT NULL,
  bucket_15min TIMESTAMPTZ NOT NULL,
  tone DECIMAL(5,2),
  polarity DECIMAL(5,2),
  activity_density DECIMAL(5,2),
  source_outlet VARCHAR(200),
  url TEXT,
  created_at TIMESTAMPTZ DEFAULT NOW(),

  INDEX idx_country_time (country_code, bucket_15min),
  INDEX idx_bucket (bucket_15min)
);
```

**Table: `signal_themes`**
```sql
CREATE TABLE signal_themes (
  id BIGSERIAL PRIMARY KEY,
  signal_id BIGINT REFERENCES gdelt_signals(id),
  theme_code VARCHAR(100),
  theme_label VARCHAR(200),
  count INTEGER DEFAULT 1,

  INDEX idx_theme_time (theme_code, bucket_15min),
  INDEX idx_signal (signal_id)
);
```

### API Endpoints

**Enhanced `/v1/flows`**
```python
@router.get("/v1/flows")
async def get_flows(
    time_window: str = "6h",
    countries: Optional[str] = None,
    theme_filter: Optional[str] = None,  # NEW
    min_intensity: float = 0.3  # NEW
):
    # Fetch GDELT signals
    # Apply theme filter if specified
    # Calculate flows using multi-signal detection
    # Return flows + metadata
```

**Enhanced `/v1/hexmap`**
```python
@router.get("/v1/hexmap")
async def get_hexmap(
    time_window: str = "6h",
    zoom: int = 2,
    k_ring: int = 2,
    sentiment_range: Optional[str] = None  # NEW: "negative", "neutral", "positive"
):
    # Fetch GDELT signals
    # Filter by sentiment if specified
    # Generate H3 hexagons
    # Apply k-ring smoothing
    # Return hexes + metadata
```

**New `/v1/narratives/topic`**
```python
@router.get("/v1/narratives/topic")
async def get_topic_narrative(
    theme: str,  # e.g., "ECON_INFLATION"
    time_window: str = "24h",
    countries: Optional[str] = None
):
    # Fetch signals matching theme
    # Group by country
    # Calculate sentiment trajectory
    # Identify key actors
    # Return narrative summary
```

---

## Performance Considerations

### Ingestion Pipeline

**Expected Load:**
- 1-2M articles/day globally
- ~1,400 articles/minute
- ~23 articles/second

**Strategy:**
- Background worker (Celery/RQ)
- Batch inserts (1000 rows at a time)
- PostgreSQL COPY for bulk loading
- Streaming CSV parser (don't load full file to memory)

### Query Optimization

**Hot Path Queries:**
```sql
-- Heatmap data (most frequent)
SELECT country_code, SUM(intensity), AVG(tone)
FROM theme_aggregations_1h
WHERE hour_bucket > NOW() - INTERVAL '6 hours'
GROUP BY country_code;
```

**Indexes Required:**
- `(country_code, bucket_15min)` - Composite index for time-series queries
- `(theme_code, bucket_15min)` - For theme filtering
- `(bucket_15min)` - For time range queries

**Caching Strategy:**
- Redis: 5-minute TTL for aggregated data
- PostgreSQL: 15-minute buckets (match GDELT publish)
- CDN: Static assets only

### Data Retention

**Hot Storage** (PostgreSQL, < 7 days):
- Full signal records in `gdelt_signals`
- Theme associations in `signal_themes`
- Entity associations in `signal_entities`

**Warm Storage** (PostgreSQL, 7-30 days):
- Hourly aggregations in `theme_aggregations_1h`
- Daily rollups in `theme_aggregations_1d`

**Cold Storage** (S3, > 30 days):
- Archived raw signals (Parquet format)
- Available for historical analysis
- Not loaded by default

---

## Implementation Roadmap

### Phase 1: Schema & Placeholders (Week 1)
**Deliverables:**
- PostgreSQL schema deployed (Issue #14)
- Placeholders match GDELT structure (Issue #16)
- Migration scripts ready
- Tests passing with placeholders

**Success Criteria:**
- [ ] All GDELT Tier 1 fields in database
- [ ] Placeholders generate realistic data
- [ ] Continuous updates working
- [ ] No breaking changes to existing features

---

### Phase 2: Visualization Architecture (Week 2)
**Deliverables:**
- Dual-layer rendering spec (Issue #15)
- Enhanced flow detection algorithm
- Animation implementation plan
- Performance optimization strategy

**Success Criteria:**
- [ ] Both layers render simultaneously
- [ ] Each layer toggleable
- [ ] Animations run at 60 FPS
- [ ] Performance targets met

---

### Phase 3: Real GDELT Integration (Weeks 3-4)
**Deliverables:**
- GDELT downloader + parser (Issue #17, Phase 1-2)
- Background worker (Phase 3)
- Database integration (Phase 4)
- Monitoring & validation (Phase 5)

**Success Criteria:**
- [ ] Real data flowing every 15 minutes
- [ ] Data quality > 95%
- [ ] No performance degradation
- [ ] Rollback plan tested

---

### Phase 4: Production Hardening (Week 5)
**Deliverables:**
- Error handling & retry logic
- Monitoring dashboards
- Alerting rules
- Performance tuning
- Documentation

**Success Criteria:**
- [ ] System handles failures gracefully
- [ ] Alerts trigger on anomalies
- [ ] Query performance < 500ms
- [ ] Documentation complete

---

## Risk Mitigation

### Risk: GDELT Data Quality Issues
**Likelihood:** Medium
**Impact:** High
**Mitigation:**
- Implement confidence scoring
- Deduplicate by URL
- Filter low-quality sources
- Manual review of top themes

### Risk: Performance Degradation
**Likelihood:** Medium
**Impact:** High
**Mitigation:**
- Load testing before production
- Database query profiling
- Implement caching aggressively
- Monitor query execution plans

### Risk: Schema Changes Required
**Likelihood:** Low
**Impact:** Medium
**Mitigation:**
- Use Alembic migrations
- Test with GDELT-shaped placeholders first
- Backward compatibility checks
- Rollback scripts ready

### Risk: Heatmap Rendering Issues
**Likelihood:** High (already occurring)
**Impact:** Low (non-blocking)
**Mitigation:**
- Delegated to frontend specialist (Issue #13)
- Parallel work stream
- Classic View still functional

---

## Success Metrics

### Data Quality
- [ ] **95%+** of signals have valid coordinates
- [ ] **90%+** of signals have at least 2 themes
- [ ] **85%+** of signals have valid sentiment scores
- [ ] **0** duplicate `gkg_record_id` values

### Performance
- [ ] API response time: **< 500ms** (p95)
- [ ] Ingestion lag: **< 2 minutes** (from GDELT publish)
- [ ] Database size growth: **< 10 GB/week**
- [ ] Frontend frame rate: **60 FPS** (with animations)

### User Experience
- [ ] User can see real-world trending topics
- [ ] Themes match actual news events
- [ ] "Why heating up?" explanations make sense
- [ ] Geographic heatmap shows real hotspots
- [ ] Search returns relevant results

---

## References

- **GDELT Schema Analysis:** `/docs/GDELT_SCHEMA_ANALYSIS.md` (400+ lines)
- **ADR-0002:** Heat calculation formula (`docs/adrs/002-flow-detection-algorithm.md`)
- **Agent Specs:**
  - DataSignalArchitect: `/.agents/data_signal_architect.md`
  - DataGeoIntel: `/.agents/data_geo_intel.md`
  - NarrativeGeopoliticsAnalyst: `/.agents/narrative_geopolitics_analyst.md`

---

## Next Steps

1. **Review & Approve Issues #14-17** (user confirmation)
2. **Assign DataSignalArchitect** to schema design (Issue #14)
3. **Assign Frontend Architect** to visualization spec (Issue #15)
4. **Begin placeholder updates** (Issue #16)
5. **Set up monitoring for heatmap fix** (Issue #13)

---

**Document Version:** 1.0
**Last Updated:** 2025-01-14
**Author:** Claude Code + DataSignalArchitect
**Status:** Awaiting User Approval

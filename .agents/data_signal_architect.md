# DataSignalArchitect Agent

## Role
Senior expert in large-scale signal processing, anomaly detection, topic/entity extraction, and cross-source normalization with deep expertise in time-series data architecture and lightweight schema design.

## Mission
Ensure that the signals model is mathematically sound, efficient, and capable of supporting narrative-level analysis while remaining lightweight enough for mobile deployment.

## Core Responsibilities

### 1. Signals Schema Design
Design and maintain the minimal "signals" schema that balances expressiveness with efficiency.

**Required Fields**:
- `timestamp_bucket` - Aggregation window (15min or 1h intervals)
- `country` - ISO 3166-1 alpha-2 code
- `hex_id` - Optional H3 cell identifier for geographic precision
- `topic_id` - UUID for topic tracking across time
- `topic_label` - Human-readable topic string
- `entity_type` - Classification: theme, person, organization, keyword, event
- `volume` - Count of mentions/occurrences
- `sentiment` - Numeric score [-1.0, 1.0] from GDELT tone or other sources
- `stance` - Enum: supportive, critical, neutral, unknown
- `source_family` - Enum: gdelt, hn, mastodon, reddit, twitter_agg, etc.

**Optional Metadata Fields**:
- `confidence` - Signal quality score [0.0, 1.0]
- `example_urls` - Array of max 3 representative URLs per topic/country
- `related_entities` - Array of linked entity IDs
- `narrative_cluster_id` - For tracking narrative mutation

### 2. Time-Bucketing Strategy
Define the optimal time-bucketing approach for different use cases.

**Recommendations**:
- **15-minute buckets**: For real-time narrative tracking and fast-moving stories
  - Use case: Breaking news, viral topics, crisis monitoring
  - Storage: Redis for last 6 hours, PostgreSQL for last 24 hours
  - Aggregation: Pre-compute hourly rollups for historical queries

- **1-hour buckets**: For trend analysis and comparative narratives
  - Use case: Topic/Entity View, Source Comparison, narrative drift
  - Storage: PostgreSQL with efficient indexing
  - Retention: Keep 30 days at 1-hour granularity, then weekly aggregates

**Bucketing Rules**:
```python
# Round down to bucket start
bucket_15min = floor(timestamp / 900) * 900
bucket_1hour = floor(timestamp / 3600) * 3600

# Bucket label format
"2025-01-14T09:15:00Z"  # 15-min bucket
"2025-01-14T09:00:00Z"  # 1-hour bucket
```

### 3. PostgreSQL Schema Proposal

**Table: `narrative_signals`**
```sql
CREATE TABLE narrative_signals (
    id BIGSERIAL PRIMARY KEY,

    -- Time dimension
    timestamp_bucket TIMESTAMPTZ NOT NULL,
    bucket_granularity VARCHAR(10) NOT NULL,  -- '15min' or '1hour'

    -- Geographic dimension
    country VARCHAR(2) NOT NULL,
    hex_id VARCHAR(20),  -- H3 cell ID, optional

    -- Topic/Entity dimension
    topic_id UUID NOT NULL,
    topic_label VARCHAR(255) NOT NULL,
    entity_type VARCHAR(50) NOT NULL,

    -- Metrics
    volume INTEGER NOT NULL DEFAULT 0,
    sentiment NUMERIC(3,2),  -- -1.00 to 1.00
    stance VARCHAR(20),  -- supportive, critical, neutral, unknown
    confidence NUMERIC(3,2),  -- 0.00 to 1.00

    -- Source tracking
    source_family VARCHAR(50) NOT NULL,
    source_count INTEGER DEFAULT 1,  -- Number of sources contributing

    -- Metadata
    example_urls TEXT[],  -- Max 3 URLs
    related_entities UUID[],
    narrative_cluster_id UUID,

    -- Audit
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),

    -- Constraints
    CONSTRAINT valid_sentiment CHECK (sentiment >= -1.0 AND sentiment <= 1.0),
    CONSTRAINT valid_confidence CHECK (confidence >= 0.0 AND confidence <= 1.0),
    CONSTRAINT valid_volume CHECK (volume >= 0),
    CONSTRAINT valid_bucket_granularity CHECK (bucket_granularity IN ('15min', '1hour'))
);

-- High-performance indexes
CREATE INDEX idx_signals_time_country ON narrative_signals (timestamp_bucket DESC, country);
CREATE INDEX idx_signals_topic ON narrative_signals (topic_id, timestamp_bucket DESC);
CREATE INDEX idx_signals_entity_type ON narrative_signals (entity_type, timestamp_bucket DESC);
CREATE INDEX idx_signals_source ON narrative_signals (source_family, timestamp_bucket DESC);
CREATE INDEX idx_signals_hex ON narrative_signals (hex_id, timestamp_bucket DESC) WHERE hex_id IS NOT NULL;
CREATE INDEX idx_signals_narrative_cluster ON narrative_signals (narrative_cluster_id) WHERE narrative_cluster_id IS NOT NULL;

-- Composite index for common queries
CREATE INDEX idx_signals_topic_country_time ON narrative_signals (topic_label, country, timestamp_bucket DESC);
```

**Table: `narrative_topics`** (dimension table for topic metadata)
```sql
CREATE TABLE narrative_topics (
    topic_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    canonical_label VARCHAR(255) UNIQUE NOT NULL,
    aliases TEXT[],  -- Variations, synonyms
    entity_type VARCHAR(50) NOT NULL,
    first_seen TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    last_seen TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    total_volume BIGINT DEFAULT 0,
    active BOOLEAN DEFAULT TRUE
);

CREATE INDEX idx_topics_label ON narrative_topics (canonical_label);
CREATE INDEX idx_topics_entity_type ON narrative_topics (entity_type);
```

**Table: `source_health`** (track data source status)
```sql
CREATE TABLE source_health (
    id SERIAL PRIMARY KEY,
    source_family VARCHAR(50) NOT NULL,
    timestamp_bucket TIMESTAMPTZ NOT NULL,
    status VARCHAR(20) NOT NULL,  -- healthy, degraded, down, inactive
    signals_produced INTEGER DEFAULT 0,
    error_count INTEGER DEFAULT 0,
    error_message TEXT,
    latency_ms INTEGER,
    created_at TIMESTAMPTZ DEFAULT NOW(),

    UNIQUE(source_family, timestamp_bucket)
);

CREATE INDEX idx_source_health_time ON source_health (timestamp_bucket DESC);
CREATE INDEX idx_source_health_source ON source_health (source_family, timestamp_bucket DESC);
```

### 4. Redis Caching Strategy

**Purpose**: Ultra-fast access to recent signals (last 6 hours) for Global Overview and real-time queries.

**Key Patterns**:

```python
# Recent signals by country (sorted set by timestamp)
KEY: "signals:country:{country}:recent"
VALUE: ZSET of signal IDs, scored by timestamp_bucket
EXPIRE: 6 hours

# Topic signals (hash)
KEY: "signals:topic:{topic_id}:latest"
VALUE: HASH of {country: signal_json, ...}
EXPIRE: 24 hours

# Global overview cache
KEY: "cache:overview:{time_window}:{granularity}"
VALUE: JSON of pre-aggregated global data
EXPIRE: 5 minutes

# Source health cache
KEY: "source:health:{source_family}"
VALUE: JSON of latest health status
EXPIRE: 15 minutes
```

**Memory Optimization**:
- Store only signal IDs in sorted sets, fetch full data from PostgreSQL if needed
- Use Redis hashes for structured data (more memory-efficient than JSON strings)
- Implement LRU eviction policy
- Target max 500MB Redis memory usage

### 5. Data Validation and Realness

**Signal Validation Pipeline**:

```python
class SignalValidator:
    """Ensure signals are real, not synthetic."""

    def validate_signal(self, signal: Dict) -> Tuple[bool, str]:
        """
        Returns: (is_valid, reason)

        Validation checks:
        1. Source verification: Does source_family exist and is it healthy?
        2. Volume sanity: Is volume within expected range for source?
        3. Sentiment bounds: Is sentiment in [-1.0, 1.0]?
        4. Timestamp freshness: Is data recent enough?
        5. Topic coherence: Does topic_label match entity_type?
        6. URL validation: Are example URLs reachable (sample check)?
        """

    def mark_synthetic(self, signal: Dict) -> None:
        """Log and reject synthetic/placeholder signals."""

    def calculate_signal_quality(self, signal: Dict) -> float:
        """
        Returns confidence score [0.0, 1.0] based on:
        - Source reliability
        - Data completeness
        - Consistency with historical patterns
        - Cross-source corroboration
        """
```

**Source Health Tracking**:
- Every fetch cycle logs: source_family, status, signals_produced, error_count, latency
- Status categories:
  - `healthy`: Producing real signals, low error rate (<5%)
  - `degraded`: Producing signals but high latency or errors (5-20%)
  - `down`: Unable to fetch data (error rate >20%)
  - `inactive`: Intentionally disabled (e.g., Google Trends until fixed)

### 6. Statistical Corrections

**Bias Removal Strategies**:

1. **Volume Normalization**:
   - Different sources have different baseline volumes (GDELT >> Reddit >> Mastodon)
   - Normalize by source: `normalized_volume = volume / source_baseline`
   - Calculate source_baseline from rolling 7-day average

2. **Geographic Bias Correction**:
   - English-language sources over-represent US/UK
   - Weight by population or internet penetration
   - Flag signals from under-represented regions

3. **Temporal Smoothing**:
   - Apply exponential moving average to reduce noise
   - Smooth parameter: α = 0.3 for 15-min buckets, α = 0.5 for 1-hour buckets

4. **Outlier Detection**:
   - Use Z-score to identify anomalous spikes
   - Flag signals with Z > 3.0 for review
   - Distinguish real events from data errors

### 7. Future Source Integration

**Design Principles for Extensibility**:

1. **Source Adapters**: Each source implements a common interface
   ```python
   class SourceAdapter(Protocol):
       async def fetch_signals(
           self,
           time_window: str,
           countries: List[str]
       ) -> List[Signal]:
           """Fetch and normalize signals to standard format."""
   ```

2. **Source Registry**:
   ```python
   SOURCE_REGISTRY = {
       'gdelt': GDELTAdapter(),
       'hn': HackerNewsAdapter(),
       'mastodon': MastodonAdapter(),
       'reddit': RedditAdapter(),  # Future
       'twitter_agg': TwitterAggregatorAdapter(),  # Future, paid
   }
   ```

3. **Normalization Layer**:
   - All sources map to the same signal schema
   - Source-specific fields go into optional metadata
   - Entity type mapping rules per source

4. **Quality Tiers**:
   - Tier 1: GDELT (free, high volume, global coverage)
   - Tier 2: Reddit, Mastodon, HN (free, medium volume, specific communities)
   - Tier 3: Paid aggregators (high quality, low noise, requires subscription)

### 8. Lightweight Mobile-Ready Design

**Constraints**:
- No full article storage (only URLs and short snippets)
- Signals-only approach: store metrics, not raw content
- Fast queries: All common queries under 100ms
- Small payloads: API responses under 50KB for mobile

**Optimizations**:
- Pre-aggregate common queries (Global Overview, top countries)
- Use compression for API responses (gzip)
- Implement pagination for large result sets (max 100 items per page)
- Mobile API endpoints with reduced payload (fewer fields)

## Deliverables

1. **PostgreSQL Schema DDL** - Complete schema with indexes and constraints
2. **Redis Key Design Document** - Key patterns, expiration policies, memory estimates
3. **Signal Validation Module** - Python implementation with unit tests
4. **Source Integration Guide** - How to add new sources to the system
5. **ADR: Signals Architecture** - Design decisions, tradeoffs, alternatives considered
6. **Performance Benchmarks** - Query times, memory usage, throughput metrics

## Definition of Done

- PostgreSQL schema deployed and tested
- Redis caching implemented for recent signals
- Signal validation pipeline validates 100% of incoming signals
- Source health tracking logs every fetch cycle
- All queries for Global Overview run under 100ms
- Documentation complete and reviewed
- Unit tests for validation logic (>90% coverage)
- Load testing shows system handles 1000 signals/minute

## Testing

- **Unit Tests**: Signal validation, time bucketing, normalization
- **Integration Tests**: PostgreSQL write/read, Redis caching, source adapters
- **Performance Tests**: Query latency, cache hit rates, memory usage
- **Data Quality Tests**: Validate signals against known ground truth

## Monitoring

Key metrics to track:
- `signals_ingested_total{source_family, country}`
- `signal_validation_failures{reason}`
- `query_latency_seconds{endpoint, percentile}`
- `cache_hit_rate{cache_type}`
- `source_health_status{source_family}`
- `storage_size_bytes{table_name}`

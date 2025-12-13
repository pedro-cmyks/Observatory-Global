# Data Contract v3 - Observatory Global

This document defines the core data structures, calculations, and usage patterns for Observatory Global v3.

## Core Concepts

### 1. Signal

The atomic unit of information in the system. Each signal represents a single piece of content captured from a data source.

| Field | Type | Description |
|-------|------|-------------|
| id | BIGSERIAL | Unique identifier |
| source_url | TEXT | Original article URL |
| source_name | TEXT | Domain/name of the source |
| title | TEXT | Article title (v3 addition) |
| snippet | TEXT | Short excerpt - first 200 chars or meta description (v3 addition) |
| timestamp | TIMESTAMPTZ | Publication/capture time |
| created_at | TIMESTAMPTZ | When we ingested it |
| country_code | CHAR(2) | Primary country (ISO 3166-1 alpha-2) |
| latitude | NUMERIC(9,6) | Geo coordinate |
| longitude | NUMERIC(9,6) | Geo coordinate |
| themes | TEXT[] | Detected themes/topics (GDELT taxonomy) |
| persons | TEXT[] | Person names mentioned |
| sentiment | NUMERIC(4,2) | GDELT tone score (-10 to +10) |
| is_crisis | BOOLEAN | Crisis classification flag |
| crisis_score | FLOAT | Crisis severity score (0-1) |
| crisis_themes | TEXT[] | Subset of themes that are crisis-related |
| severity | TEXT | 'low', 'medium', 'high', 'critical' |
| event_type | TEXT | Crisis event category |

**Source of truth:** `signals_v2` table  
**Used by UI:** Story lists, source citations, drill-down views

---

### 2. Theme

A categorical topic detected in signals. Themes follow the GDELT Global Knowledge Graph taxonomy.

| Field | Type | Description |
|-------|------|-------------|
| theme_code | STRING | Canonical GDELT theme identifier (e.g., "ECON_BANKRUPTCY") |
| label | STRING | Human-readable name (derived from taxonomy) |
| signal_count | INT | Number of signals in time window |
| avg_sentiment | FLOAT | Average sentiment of signals with this theme |
| country_breakdown | ARRAY | Countries where theme appears with counts |

**Source of truth:** Aggregated from `signals_v2.themes` array  
**Calculation:** 
```sql
SELECT 
    unnest(themes) as theme,
    COUNT(*) as signal_count,
    AVG(sentiment) as avg_sentiment
FROM signals_v2
WHERE timestamp > NOW() - INTERVAL '24 hours'
GROUP BY theme
ORDER BY signal_count DESC
```
**Used by UI:** Theme filters, theme rankings, drill-down, search results

---

### 3. Narrative-Story (Cluster)

A cluster of related signals covering the same event or story. Signals are grouped based on similarity.

| Field | Type | Description |
|-------|------|-------------|
| story_id | UUID | Cluster identifier |
| representative_title | STRING | Title of most central signal |
| representative_url | STRING | URL of most central signal |
| signal_ids | UUID[] | Member signal IDs |
| signal_count | INT | Number of signals in cluster |
| countries | STRING[] | All countries involved |
| themes | STRING[] | All themes present |
| sources | STRING[] | All sources reporting |
| peak_time | TIMESTAMP | When activity peaked |
| avg_sentiment | FLOAT | Average sentiment across signals |

**Source of truth:** Computed via clustering algorithm (future implementation)  
**Calculation criteria:**
- URL similarity (same base URL = same story)
- Title similarity (cosine similarity > 0.7)
- Time proximity (within 24h window)
- Shared entities (persons, locations)

**Used by UI:** Top stories list, executive brief, story detail view

---

### 4. Narrative-Topic (Broad Grouping)

A higher-level thematic grouping spanning multiple stories and themes.

| Field | Type | Description |
|-------|------|-------------|
| topic_id | STRING | Topic identifier |
| label | STRING | Descriptive name |
| child_themes | STRING[] | GDELT themes in this topic |
| story_count | INT | Stories in time window |
| signal_count | INT | Signals in time window |

**Source of truth:** Configuration mapping + aggregation  
**Calculation:** Predefined theme-to-topic mapping (see `gdelt_taxonomy.py`) + COUNT  
**Used by UI:** High-level navigation, topic filters

**Example topic mappings:**
- "Economy" → ECON_*, UNEMPLOYMENT, INFLATION, etc.
- "Conflict" → CONFLICT*, MILITARY*, TERROR*, etc.
- "Health" → HEALTH*, PANDEMIC*, DISEASE*, etc.

---

### 5. Flow (Attention Overlap)

Non-causal correlation of attention between countries on shared themes.

| Field | Type | Description |
|-------|------|-------------|
| source_country | CHAR(2) | Country A (ISO code) |
| target_country | CHAR(2) | Country B (ISO code) |
| source_coords | [lon, lat] | Country A coordinates |
| target_coords | [lon, lat] | Country B coordinates |
| shared_themes | STRING[] | Themes both countries are covering |
| shared_count | INT | Number of shared themes |
| similarity | FLOAT | Jaccard similarity (0-1) |
| strength | FLOAT | Combined similarity × volume metric |

**Source of truth:** Computed from signals  
**Calculation:**
```python
# For each country pair:
themes_a = set(top_30_themes_for_country_a)
themes_b = set(top_30_themes_for_country_b)

intersection = themes_a & themes_b
union = themes_a | themes_b

jaccard_similarity = len(intersection) / len(union)

# Only create flow if similarity >= 0.2 and shared >= 3 themes
strength = similarity * min(volume_a, volume_b) / 10
```

**Used by UI:** Flow lines on map, "information corridor" visualization

> ⚠️ **Important:** This is **correlation**, NOT causation. Does not imply one country influences another.

---

### 6. Crisis/Spike (Baseline Deviation)

Anomaly detection for unusual activity levels.

| Field | Type | Description |
|-------|------|-------------|
| entity_type | STRING | 'country' or 'theme' |
| entity_id | STRING | Country code or theme ID |
| current_volume | INT | Signals in current window |
| baseline_volume | FLOAT | Rolling 7-day average |
| baseline_stddev | FLOAT | Standard deviation over 7 days |
| z_score | FLOAT | Standard deviations from baseline |
| multiplier | FLOAT | current / baseline ratio |
| level | STRING | 'exceptional', 'high', 'elevated', 'normal', 'low' |

**Source of truth:** Computed from signals with rolling window  
**Calculation:**
```python
baseline_avg = AVG(signal_count) over past 7 days, same hour of day
baseline_stddev = STDDEV(signal_count) over past 7 days

z_score = (current_count - baseline_avg) / baseline_stddev
multiplier = current_count / baseline_avg

# Levels:
# z_score > 3  → 'exceptional'
# z_score > 2  → 'high'  
# z_score > 1  → 'elevated'
# z_score > -1 → 'normal'
# z_score < -1 → 'low'
```

**Used by UI:** Spike indicators, "X times normal" labels, alerts

---

## Trust Indicators

These indicators help users understand the reliability and context of the data.

### Source Diversity Score (0-100)

Measures how diverse the sourcing is for a given aggregation.

**Components:**
- **Unique count score (0-50):** Logarithmic scale based on number of unique domains
- **Entropy score (0-50):** Shannon entropy of source distribution (more even = higher)

**Formula:**
```python
unique_score = min(50, (log(unique_count + 1) / log(21)) * 50)

entropy = -sum((count/total) * log2(count/total) for each source)
max_entropy = log2(unique_count)
entropy_score = (entropy / max_entropy) * 50

total_score = unique_score + entropy_score
```

**Interpretation:**
- 80-100: Excellent diversity, many sources with even coverage
- 50-79: Good diversity
- 20-49: Limited diversity, dominated by few sources
- 0-19: Poor diversity, single source or highly skewed

---

### Source Quality Score (0-100)

Transparent scoring based on source verification status.

**Components:**
- Base score: 30 points
- Each verified source (allowlist): +10 points (max +70)
- Each flagged source (denylist): -20 points

**Allowlist (examples):**
reuters.com, apnews.com, bbc.com, nytimes.com, washingtonpost.com, theguardian.com, economist.com, ft.com, wsj.com, bloomberg.com, aljazeera.com, dw.com, france24.com, nhk.or.jp

> ⚠️ **Important:** This is a simple heuristic, not a truth judgment. Verified sources are major news agencies and established outlets, but all sources can contain errors.

---

### Normalized Volume

Shows current activity relative to historical baseline.

**Fields:**
- `multiplier`: Current signals ÷ 7-day average for same time period
- `z_score`: Standard deviations from baseline
- `level`: Human-readable interpretation

**Levels:**
| Level | Z-Score | Interpretation |
|-------|---------|----------------|
| exceptional | > 3 | Very unusual activity |
| high | 2-3 | Elevated activity |
| elevated | 1-2 | Above normal |
| normal | -1 to 1 | Within expected range |
| low | < -1 | Below normal |

---

## API Response Shapes

### GET /api/v2/nodes
```json
{
  "nodes": [
    {
      "id": "US",
      "name": "United States",
      "lat": 37.0902,
      "lon": -95.7129,
      "intensity": 0.85,
      "sentiment": -0.12,
      "signalCount": 1523,
      "sourceCount": 89
    }
  ],
  "count": 45,
  "hours": 24
}
```

### GET /health
```json
{
  "status": "healthy",
  "db_ok": true,
  "timestamp": "2024-01-15T10:30:00Z",
  "last_ingest_ts": "2024-01-15T10:15:00Z",
  "ingest_lag_minutes": 15.0,
  "rows_ingested_last_15m": 342,
  "total_signals": 1523456,
  "error_count_last_15m": 0
}
```

### GET /api/indicators/country/{code}
```json
{
  "country_code": "US",
  "hours": 24,
  "diversity": {
    "score": 78,
    "unique_count": 45,
    "tooltip": "Diversity score based on 45 unique sources..."
  },
  "quality": {
    "score": 85,
    "allowlisted_count": 12,
    "tooltip": "Quality score: 12 verified sources..."
  },
  "volume": {
    "multiplier": 1.3,
    "z_score": 0.8,
    "level": "normal",
    "tooltip": "1.3x normal volume..."
  }
}
```

---

## Data Freshness Requirements

| Data Type | Target Freshness | Degraded Threshold |
|-----------|------------------|-------------------|
| Signals | < 15 minutes | > 30 minutes |
| Aggregates (materialized view) | < 1 hour | > 2 hours |
| Flows | Real-time calculation | N/A |
| Baselines | Rolling 7-day | N/A |

---

## Change Log

- **v3.0** (2024-01): Added trust indicators, title/snippet fields, connector interface
- **v2.0** (2023): Simplified schema, removed TimescaleDB dependency
- **v1.0** (2023): Initial implementation with complex schema

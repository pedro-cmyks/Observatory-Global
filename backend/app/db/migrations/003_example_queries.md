# GDELT Signals Schema - Example Queries

## Overview

This document provides example queries demonstrating optimal index usage for the `gdelt_signals` schema. All queries are designed to meet the **< 100ms latency target** for production use.

---

## 1. Heatmap Queries (Most Frequent)

### 1.1 Get signals for country in time window

**Use case**: Load heatmap data for specific country
**Index used**: `idx_gdelt_signals_country_bucket15`

```sql
-- Get last 6 hours of signals for US
EXPLAIN ANALYZE
SELECT
    id,
    gkg_record_id,
    latitude,
    longitude,
    tone_overall,
    intensity,
    primary_theme,
    primary_theme_label
FROM gdelt_signals
WHERE country_code = 'US'
  AND bucket_15min >= NOW() - INTERVAL '6 hours'
ORDER BY bucket_15min DESC
LIMIT 1000;

-- Expected: Index Scan using idx_gdelt_signals_country_bucket15
-- Estimated time: 10-50ms
```

### 1.2 Get aggregated heatmap points by location

**Use case**: Generate hexagon data for deck.gl HexagonLayer
**Index used**: `idx_gdelt_signals_heatmap`

```sql
-- Aggregate signals by location for heatmap rendering
SELECT
    country_code,
    ROUND(latitude::numeric, 1) as lat_bucket,
    ROUND(longitude::numeric, 1) as lon_bucket,
    COUNT(*) as signal_count,
    AVG(tone_overall) as avg_tone,
    AVG(intensity) as avg_intensity,
    array_agg(DISTINCT primary_theme ORDER BY primary_theme) FILTER (WHERE primary_theme IS NOT NULL) as themes
FROM gdelt_signals
WHERE country_code IN ('US', 'GB', 'DE')
  AND bucket_15min >= NOW() - INTERVAL '6 hours'
  AND latitude IS NOT NULL
GROUP BY country_code, lat_bucket, lon_bucket
HAVING COUNT(*) >= 3
ORDER BY avg_intensity DESC
LIMIT 500;

-- Expected: Index Scan using idx_gdelt_signals_heatmap
-- Estimated time: 50-100ms
```

---

## 2. Flow Detection Queries

### 2.1 Get shared themes between countries

**Use case**: Calculate Jaccard similarity for flow detection
**Index used**: `idx_signal_themes_code_signal`, `idx_gdelt_signals_country_bucket15`

```sql
-- Find shared themes between US and GB in last 6 hours
WITH us_themes AS (
    SELECT DISTINCT st.theme_code
    FROM gdelt_signals gs
    JOIN signal_themes st ON gs.id = st.signal_id
    WHERE gs.country_code = 'US'
      AND gs.bucket_15min >= NOW() - INTERVAL '6 hours'
),
gb_themes AS (
    SELECT DISTINCT st.theme_code
    FROM gdelt_signals gs
    JOIN signal_themes st ON gs.id = st.signal_id
    WHERE gs.country_code = 'GB'
      AND gs.bucket_15min >= NOW() - INTERVAL '6 hours'
)
SELECT
    COUNT(*) FILTER (WHERE ut.theme_code IS NOT NULL AND gt.theme_code IS NOT NULL) as shared_count,
    COUNT(DISTINCT COALESCE(ut.theme_code, gt.theme_code)) as union_count,
    COUNT(*) FILTER (WHERE ut.theme_code IS NOT NULL AND gt.theme_code IS NOT NULL)::float
        / NULLIF(COUNT(DISTINCT COALESCE(ut.theme_code, gt.theme_code)), 0) as jaccard_similarity
FROM us_themes ut
FULL OUTER JOIN gb_themes gt ON ut.theme_code = gt.theme_code;

-- Expected time: 30-80ms
```

### 2.2 Get first appearance of theme by country

**Use case**: Determine flow directionality (time delta)
**Index used**: `idx_gdelt_signals_country_theme`

```sql
-- Find when ECON_INFLATION first appeared in each country (last 24h)
SELECT
    gs.country_code,
    MIN(gs.timestamp) as first_appeared,
    COUNT(*) as total_signals,
    AVG(gs.tone_overall) as avg_tone
FROM gdelt_signals gs
WHERE gs.primary_theme = 'ECON_INFLATION'
  AND gs.bucket_15min >= NOW() - INTERVAL '24 hours'
GROUP BY gs.country_code
ORDER BY first_appeared ASC;

-- Expected: Index Scan using idx_gdelt_signals_country_theme
-- Estimated time: 20-50ms
```

---

## 3. Trend Analysis Queries

### 3.1 Hourly aggregation for theme

**Use case**: Display trend chart for specific theme
**Index used**: `idx_theme_agg_1h_theme_hour`

```sql
-- Get hourly trend for ECON_INFLATION across all countries
SELECT
    hour_bucket,
    SUM(signal_count) as total_signals,
    AVG(avg_tone) as avg_tone,
    SUM(total_theme_mentions) as total_mentions
FROM theme_aggregations_1h
WHERE theme_code = 'ECON_INFLATION'
  AND hour_bucket >= NOW() - INTERVAL '7 days'
GROUP BY hour_bucket
ORDER BY hour_bucket ASC;

-- Expected: Index Scan using idx_theme_agg_1h_theme_hour
-- Estimated time: 10-30ms
```

### 3.2 Compare themes across countries

**Use case**: Narrative comparison dashboard
**Index used**: `idx_theme_agg_1h_country_theme`

```sql
-- Compare inflation narrative across US, GB, DE
SELECT
    country_code,
    SUM(signal_count) as total_signals,
    AVG(avg_tone) as avg_sentiment,
    MAX(max_intensity) as peak_intensity,
    SUM(total_theme_mentions) as total_mentions
FROM theme_aggregations_1h
WHERE theme_code = 'ECON_INFLATION'
  AND country_code IN ('US', 'GB', 'DE')
  AND hour_bucket >= NOW() - INTERVAL '24 hours'
GROUP BY country_code
ORDER BY total_signals DESC;

-- Expected: Index Scan using idx_theme_agg_1h_country_theme
-- Estimated time: 5-15ms
```

---

## 4. Entity Search Queries

### 4.1 Find signals mentioning specific person

**Use case**: Entity search feature
**Index used**: `idx_signal_entities_type_name`

```sql
-- Find all signals mentioning "Jerome Powell" in last 24h
SELECT
    gs.id,
    gs.gkg_record_id,
    gs.country_code,
    gs.timestamp,
    gs.primary_theme,
    gs.tone_overall,
    gs.source_outlet,
    gs.source_url
FROM gdelt_signals gs
JOIN signal_entities se ON gs.id = se.signal_id
WHERE se.entity_type = 'person'
  AND se.entity_name_normalized LIKE '%jerome powell%'
  AND gs.bucket_15min >= NOW() - INTERVAL '24 hours'
ORDER BY gs.timestamp DESC
LIMIT 100;

-- Expected: Index Scan using idx_signal_entities_type_name
-- Estimated time: 20-60ms
```

### 4.2 Find shared entities between flows

**Use case**: Enhance flow detection with actor overlap
**Index used**: `idx_signal_entities_signal`

```sql
-- Find shared persons between US and GB signals
WITH us_persons AS (
    SELECT DISTINCT se.entity_name_normalized as person
    FROM gdelt_signals gs
    JOIN signal_entities se ON gs.id = se.signal_id
    WHERE gs.country_code = 'US'
      AND gs.bucket_15min >= NOW() - INTERVAL '6 hours'
      AND se.entity_type = 'person'
),
gb_persons AS (
    SELECT DISTINCT se.entity_name_normalized as person
    FROM gdelt_signals gs
    JOIN signal_entities se ON gs.id = se.signal_id
    WHERE gs.country_code = 'GB'
      AND gs.bucket_15min >= NOW() - INTERVAL '6 hours'
      AND se.entity_type = 'person'
)
SELECT u.person
FROM us_persons u
INNER JOIN gb_persons g ON u.person = g.person
LIMIT 50;

-- Expected time: 40-80ms
```

---

## 5. "Why is this heating up?" Query

### 5.1 Complete hotspot analysis

**Use case**: Tooltip/sidebar detail for clicked hotspot
**Index used**: Multiple indexes

```sql
-- Complete analysis for US hotspot
WITH signal_data AS (
    SELECT
        gs.*,
        array_agg(DISTINCT st.theme_code) as all_themes,
        array_agg(DISTINCT st.theme_label) FILTER (WHERE st.theme_label IS NOT NULL) as theme_labels
    FROM gdelt_signals gs
    LEFT JOIN signal_themes st ON gs.id = st.signal_id
    WHERE gs.country_code = 'US'
      AND gs.bucket_15min >= NOW() - INTERVAL '6 hours'
    GROUP BY gs.id
),
theme_summary AS (
    SELECT
        st.theme_code,
        st.theme_label,
        SUM(st.theme_count) as total_count,
        AVG(gs.tone_overall) as avg_tone
    FROM gdelt_signals gs
    JOIN signal_themes st ON gs.id = st.signal_id
    WHERE gs.country_code = 'US'
      AND gs.bucket_15min >= NOW() - INTERVAL '6 hours'
    GROUP BY st.theme_code, st.theme_label
    ORDER BY total_count DESC
    LIMIT 5
),
entity_summary AS (
    SELECT
        se.entity_type,
        se.entity_name,
        COUNT(*) as mention_count
    FROM gdelt_signals gs
    JOIN signal_entities se ON gs.id = se.signal_id
    WHERE gs.country_code = 'US'
      AND gs.bucket_15min >= NOW() - INTERVAL '6 hours'
    GROUP BY se.entity_type, se.entity_name
    ORDER BY mention_count DESC
    LIMIT 10
),
outlet_summary AS (
    SELECT
        source_outlet,
        COUNT(*) as article_count
    FROM gdelt_signals
    WHERE country_code = 'US'
      AND bucket_15min >= NOW() - INTERVAL '6 hours'
      AND source_outlet IS NOT NULL
    GROUP BY source_outlet
    ORDER BY article_count DESC
    LIMIT 5
)
SELECT
    'US' as country,
    (SELECT COUNT(*) FROM signal_data) as total_signals,
    (SELECT AVG(tone_overall) FROM signal_data) as avg_sentiment,
    (SELECT AVG(intensity) FROM signal_data) as avg_intensity,
    (SELECT json_agg(row_to_json(t)) FROM theme_summary t) as top_themes,
    (SELECT json_agg(row_to_json(e)) FROM entity_summary e) as top_entities,
    (SELECT json_agg(row_to_json(o)) FROM outlet_summary o) as top_outlets;

-- Expected time: 50-100ms
```

---

## 6. Deduplication Queries

### 6.1 Check for duplicate URL

**Use case**: Pre-insert deduplication check
**Index used**: `idx_gdelt_signals_url_hash`

```sql
-- Check if URL already exists before insert
SELECT id, gkg_record_id, timestamp
FROM gdelt_signals
WHERE url_hash = md5('https://example.com/article')
LIMIT 1;

-- Expected: Index Scan using idx_gdelt_signals_url_hash
-- Estimated time: < 5ms
```

### 6.2 Find duplicate clusters

**Use case**: Aggregate duplicate articles for analysis
**Index used**: `idx_gdelt_signals_url_hash`

```sql
-- Find articles with most duplicates
SELECT
    url_hash,
    MAX(source_url) as sample_url,
    SUM(duplicate_count) as total_duplicates,
    array_agg(DISTINCT source_outlet) as outlets
FROM gdelt_signals
WHERE bucket_15min >= NOW() - INTERVAL '24 hours'
GROUP BY url_hash
HAVING SUM(duplicate_count) > 1
ORDER BY total_duplicates DESC
LIMIT 20;

-- Expected time: 30-60ms
```

---

## 7. Performance Monitoring Queries

### 7.1 Check index usage

```sql
-- Monitor index hit rates
SELECT
    schemaname,
    tablename,
    indexrelname,
    idx_scan,
    idx_tup_read,
    idx_tup_fetch
FROM pg_stat_user_indexes
WHERE tablename IN ('gdelt_signals', 'signal_themes', 'signal_entities', 'theme_aggregations_1h')
ORDER BY idx_scan DESC;
```

### 7.2 Table size monitoring

```sql
-- Check table and index sizes
SELECT
    relname as table_name,
    pg_size_pretty(pg_total_relation_size(relid)) as total_size,
    pg_size_pretty(pg_relation_size(relid)) as data_size,
    pg_size_pretty(pg_indexes_size(relid)) as index_size,
    n_live_tup as row_count
FROM pg_stat_user_tables
WHERE relname IN ('gdelt_signals', 'signal_themes', 'signal_entities', 'theme_aggregations_1h')
ORDER BY pg_total_relation_size(relid) DESC;
```

### 7.3 Query execution analysis

```sql
-- Analyze slow queries (requires pg_stat_statements extension)
SELECT
    query,
    calls,
    mean_time,
    max_time,
    rows
FROM pg_stat_statements
WHERE query LIKE '%gdelt_signals%'
ORDER BY mean_time DESC
LIMIT 10;
```

---

## 8. Batch Insert Pattern

### 8.1 Efficient bulk insert

**Use case**: Ingesting 10K-30K signals per 15-minute GDELT file

```sql
-- Use COPY for fastest bulk insert (from application)
-- This is ~10x faster than individual INSERTs

COPY gdelt_signals (
    gkg_record_id,
    source_collection_id,
    timestamp,
    country_code,
    country_name,
    location_name,
    latitude,
    longitude,
    location_type,
    tone_overall,
    tone_positive_pct,
    tone_negative_pct,
    polarity,
    activity_density,
    self_reference,
    primary_theme,
    primary_theme_label,
    primary_theme_count,
    total_theme_count,
    source_outlet,
    source_url,
    url_hash,
    confidence
)
FROM STDIN WITH (FORMAT csv, DELIMITER E'\t', NULL '');
-- ... data rows ...
\.

-- Or use multi-row INSERT for smaller batches
INSERT INTO gdelt_signals (
    gkg_record_id, timestamp, country_code, ...
) VALUES
    ('20250115120000-T01', '2025-01-15 12:00:00', 'US', ...),
    ('20250115120000-T02', '2025-01-15 12:00:00', 'GB', ...),
    -- ... up to 1000 rows per batch
ON CONFLICT (gkg_record_id) DO NOTHING;
```

---

## 9. Data Retention Queries

### 9.1 Archive old signals

```sql
-- Move signals older than 7 days to archive (future implementation)
-- For now, delete to manage storage

DELETE FROM gdelt_signals
WHERE bucket_15min < NOW() - INTERVAL '30 days';

-- Note: Foreign key ON DELETE CASCADE will remove related
-- signal_themes and signal_entities rows automatically
```

### 9.2 Refresh materialized aggregations

```sql
-- Rebuild hourly aggregations for specific time range
INSERT INTO theme_aggregations_1h (
    hour_bucket,
    country_code,
    theme_code,
    signal_count,
    total_theme_mentions,
    avg_tone,
    min_tone,
    max_tone,
    avg_polarity,
    avg_intensity,
    max_intensity,
    unique_outlets
)
SELECT
    gs.bucket_1h,
    gs.country_code,
    st.theme_code,
    COUNT(DISTINCT gs.id),
    SUM(st.theme_count),
    AVG(gs.tone_overall),
    MIN(gs.tone_overall),
    MAX(gs.tone_overall),
    AVG(gs.polarity),
    AVG(gs.intensity),
    MAX(gs.intensity),
    COUNT(DISTINCT gs.source_outlet)
FROM gdelt_signals gs
JOIN signal_themes st ON gs.id = st.signal_id
WHERE gs.bucket_1h >= NOW() - INTERVAL '24 hours'
GROUP BY gs.bucket_1h, gs.country_code, st.theme_code
ON CONFLICT (hour_bucket, country_code, theme_code)
DO UPDATE SET
    signal_count = EXCLUDED.signal_count,
    total_theme_mentions = EXCLUDED.total_theme_mentions,
    avg_tone = EXCLUDED.avg_tone,
    min_tone = EXCLUDED.min_tone,
    max_tone = EXCLUDED.max_tone,
    avg_polarity = EXCLUDED.avg_polarity,
    avg_intensity = EXCLUDED.avg_intensity,
    max_intensity = EXCLUDED.max_intensity,
    unique_outlets = EXCLUDED.unique_outlets,
    updated_at = NOW();
```

---

## Summary

| Query Type | Target Latency | Primary Index |
|-----------|---------------|---------------|
| Country heatmap | < 50ms | idx_gdelt_signals_country_bucket15 |
| Time-range scan | < 30ms | idx_gdelt_signals_bucket15 |
| Theme filtering | < 50ms | idx_gdelt_signals_primary_theme |
| Entity search | < 60ms | idx_signal_entities_type_name |
| Hourly trends | < 30ms | idx_theme_agg_1h_theme_hour |
| Dedup check | < 5ms | idx_gdelt_signals_url_hash |
| Full hotspot analysis | < 100ms | Multiple indexes |

All queries are designed to utilize index scans rather than sequential scans, ensuring consistent performance as data volume grows.

# Database Schema Quick Reference

**Related**: [Full Schema Design](/docs/database-schema-design.md) | [Migration SQL](/backend/app/db/migrations/002_comprehensive_flow_schema.sql)

---

## Quick Overview

```
6 Core Tables:
├── countries (reference, ~250 rows)
├── topics (master, ~10K-100K rows)
├── topic_snapshots (time-series, partitioned, 15MB/day)
├── hotspots (aggregated, 288KB/day)
├── flows (relationships, 648KB/day)
└── stance_history (narrative tracking, 672KB/day)

2 Materialized Views:
├── mv_recent_hotspots (refresh every 15min)
└── mv_active_flows (refresh every 15min)
```

---

## Table Cheat Sheet

### 1. Countries (Reference)
```sql
country_code (PK)  | country_name | region | latitude | longitude | is_active
-------------------|--------------|--------|----------|-----------|----------
US                 | United States| Americas | 37.09  | -95.71    | true
CO                 | Colombia     | Americas |  4.57  | -74.30    | true
```
**Use Case**: Map visualization, country metadata, filtering by region

### 2. Topics (Master)
```sql
topic_id (UUID, PK) | normalized_label     | aliases[]                        | category  | first_seen_at
--------------------|----------------------|----------------------------------|-----------|------------------
uuid-1234...        | election fraud       | ['voter fraud', 'electoral...']  | politics  | 2025-01-13 10:00
```
**Use Case**: Topic deduplication, search, categorization

### 3. Topic_Snapshots (Time-Series Core)
```sql
snapshot_id | topic_id | country | snapshot_time       | count | velocity | confidence | sample_titles[]
------------|----------|---------|---------------------|-------|----------|------------|-----------------
uuid-abc... | uuid-123 | US      | 2025-01-13 10:00:00 | 456   | 0.78     | 0.89       | ['Title 1', ...]
```
**Use Case**: Raw time-series data, trend analysis, API responses
**Note**: Partitioned by `snapshot_time` (weekly partitions)

### 4. Hotspots (Aggregated)
```sql
hotspot_id | country | snapshot_time       | intensity | topic_count | top_topics (JSONB)
-----------|---------|---------------------|-----------|-------------|-----------------------
uuid-def.. | US      | 2025-01-13 10:00:00 | 0.85      | 47          | [{"label": "...", ...}]
```
**Use Case**: Map circles (country intensity), dashboard KPIs
**Refresh**: Computed every 15 minutes

### 5. Flows (Information Flows)
```sql
flow_id | from_country | to_country | from_time | to_time | heat | similarity | time_delta_hrs | shared_topics (JSONB)
--------|--------------|------------|-----------|---------|------|------------|-----------------|-----------------------
uuid... | US           | CO         | 10:00     | 13:00   | 0.72 | 0.87       | 3.0             | [{"label": "...", ...}]
```
**Use Case**: Map arcs (flow lines), flow intensity visualization
**Formula**: `heat = similarity × exp(-Δt / 6h)`

### 6. Stance_History (Narrative Drift)
```sql
stance_id | topic_id | country | snapshot_time | stance_label | previous_stance | stance_changed | drift_magnitude
----------|----------|---------|---------------|--------------|-----------------|----------------|----------------
uuid...   | uuid-123 | US      | 2025-01-13    | anti         | neutral         | true           | 0.5
```
**Use Case**: Narrative evolution, stance tracking, drift detection
**Trigger**: Auto-calculates drift on insert

---

## Common Queries (Copy-Paste Ready)

### Get Recent Trends for Country
```sql
SELECT
    t.normalized_label,
    ts.count,
    ts.confidence,
    ts.sample_titles
FROM topic_snapshots ts
JOIN topics t ON ts.topic_id = t.topic_id
WHERE ts.country_code = 'US'
  AND ts.snapshot_time >= NOW() - INTERVAL '1 hour'
ORDER BY ts.count DESC
LIMIT 20;
```

### Get Active Flows (Last 24h)
```sql
SELECT * FROM mv_active_flows
WHERE heat >= 0.6
ORDER BY heat DESC
LIMIT 50;
```

### Track Topic Across Countries
```sql
SELECT
    ts.country_code,
    ts.snapshot_time,
    ts.count,
    ts.stance_label
FROM topic_snapshots ts
JOIN topics t ON ts.topic_id = t.topic_id
WHERE t.normalized_label = 'climate change'
  AND ts.snapshot_time >= NOW() - INTERVAL '7 days'
ORDER BY ts.snapshot_time DESC;
```

### Detect Narrative Drift
```sql
SELECT
    t.normalized_label,
    sh.country_code,
    sh.previous_stance,
    sh.stance_label AS current_stance,
    sh.drift_magnitude,
    sh.snapshot_time
FROM stance_history sh
JOIN topics t ON sh.topic_id = t.topic_id
WHERE sh.stance_changed = true
  AND sh.drift_magnitude >= 0.5
  AND sh.snapshot_time >= NOW() - INTERVAL '30 days'
ORDER BY sh.drift_magnitude DESC;
```

### Database Health Check
```sql
-- Table sizes
SELECT * FROM v_table_sizes;

-- Row counts
SELECT * FROM v_row_counts;

-- Cache hit ratio (should be >95%)
SELECT
    ROUND(SUM(heap_blks_hit) * 100.0 / NULLIF(SUM(heap_blks_hit + heap_blks_read), 0), 2) AS cache_hit_ratio
FROM pg_statio_user_tables;
```

---

## Index Quick Reference

### Most Important Indexes
```sql
-- Topic_Snapshots (time-series queries)
idx_topic_snapshots_country_time_count  -- For: WHERE country = X AND time > Y ORDER BY count
idx_topic_snapshots_topic_country_time  -- For: WHERE topic_id = X AND country = Y

-- Flows (visualization)
idx_flows_heat                          -- For: ORDER BY heat DESC
idx_flows_from_country_time             -- For: WHERE from_country = X

-- Stance (narrative drift)
idx_stance_changed                      -- For: WHERE stance_changed = true
idx_stance_drift                        -- For: WHERE drift_magnitude > 0.3
```

### Checking Unused Indexes
```sql
SELECT
    schemaname || '.' || tablename AS table,
    indexname,
    idx_scan,
    pg_size_pretty(pg_relation_size(indexrelid)) AS size
FROM pg_stat_user_indexes
WHERE idx_scan = 0
  AND schemaname = 'public'
ORDER BY pg_relation_size(indexrelid) DESC;
```

---

## Partition Management

### Current Partitions
```sql
-- View all partitions
SELECT
    parent.relname AS parent_table,
    child.relname AS partition_name,
    pg_get_expr(child.relpartbound, child.oid) AS partition_range
FROM pg_inherits
JOIN pg_class parent ON pg_inherits.inhparent = parent.oid
JOIN pg_class child ON pg_inherits.inhrelid = child.oid
WHERE parent.relname = 'topic_snapshots';
```

### Create Next Week's Partition
```sql
-- Example: Create partition for 2025-W08
CREATE TABLE topic_snapshots_2025_w08
    PARTITION OF topic_snapshots
    FOR VALUES FROM ('2025-02-17') TO ('2025-02-24');
```

### Drop Old Partition (After Archiving)
```sql
-- WARNING: This deletes data permanently!
DROP TABLE topic_snapshots_2025_w03;
```

---

## Materialized View Refresh

### Manual Refresh
```sql
REFRESH MATERIALIZED VIEW CONCURRENTLY mv_recent_hotspots;
REFRESH MATERIALIZED VIEW CONCURRENTLY mv_active_flows;
```

### Automated Refresh (via pg_cron)
```sql
-- Install pg_cron extension
CREATE EXTENSION pg_cron;

-- Schedule refresh every 15 minutes
SELECT cron.schedule(
    'refresh-materialized-views',
    '*/15 * * * *',
    $$
    REFRESH MATERIALIZED VIEW CONCURRENTLY mv_recent_hotspots;
    REFRESH MATERIALIZED VIEW CONCURRENTLY mv_active_flows;
    $$
);

-- View scheduled jobs
SELECT * FROM cron.job;
```

---

## Retention Policy Summary

| Data | Hot (0-30d) | Warm (30-90d) | Cold (90d-1y) | Delete After |
|------|-------------|---------------|---------------|--------------|
| **topic_snapshots** | 15-min granularity | Hourly aggregation | Daily aggregation | 1 year |
| **hotspots** | All records | All records | Weekly averages | 1 year |
| **flows** | heat >= 0.5 | heat >= 0.7 | Top 100/month | 1 year |
| **stance_history** | All records | Changes only | drift > 0.5 | 1 year |

### Manual Cleanup (Run Monthly)
```sql
-- Delete topic_snapshots older than 1 year
DELETE FROM topic_snapshots
WHERE snapshot_time < NOW() - INTERVAL '1 year';

-- Delete old hotspots
DELETE FROM hotspots
WHERE snapshot_time < NOW() - INTERVAL '1 year';

-- Delete old flows
DELETE FROM flows
WHERE detected_at < NOW() - INTERVAL '1 year';

-- Vacuum to reclaim space
VACUUM ANALYZE;
```

---

## Storage Estimates

### 10 Countries
- **Per Day**: 14 MB
- **Per Month**: 430 MB
- **Per Year**: 5.3 GB (hot) + 1.5 GB (warm) = **6.8 GB**

### 50 Countries (Scale Factor: 5x)
- **Per Day**: 70 MB
- **Per Month**: 2.2 GB
- **Per Year**: **27 GB**

### Cost (AWS RDS PostgreSQL)
- **Iteration 2** (10 countries): db.t3.medium (20GB) = **~$60/month**
- **Iteration 3** (50 countries): db.t3.large (50GB) = **~$110/month**

---

## Troubleshooting

### Query is slow (>1s)
```sql
-- Check query plan
EXPLAIN ANALYZE
SELECT * FROM topic_snapshots WHERE country_code = 'US';

-- Look for "Seq Scan" (bad) vs "Index Scan" (good)
-- If Seq Scan found, check if index exists:
\d+ topic_snapshots
```

### Table bloat (too much dead space)
```sql
-- Check bloat percentage
SELECT
    schemaname || '.' || tablename AS table,
    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) AS size,
    n_dead_tup,
    n_live_tup,
    ROUND(n_dead_tup * 100.0 / NULLIF(n_live_tup, 0), 2) AS bloat_percent
FROM pg_stat_user_tables
WHERE schemaname = 'public'
ORDER BY n_dead_tup DESC;

-- If bloat > 20%, run VACUUM
VACUUM FULL topic_snapshots;
```

### Out of disk space
```sql
-- Check largest tables
SELECT * FROM v_table_sizes;

-- Archive old partitions to S3, then drop:
-- 1. Export: pg_dump -t topic_snapshots_2025_w03 > archive.sql
-- 2. Upload to S3
-- 3. Drop: DROP TABLE topic_snapshots_2025_w03;
```

---

## Migration Checklist

### Initial Setup
- [ ] Enable PostgreSQL in docker-compose.yml
- [ ] Run migration 002_comprehensive_flow_schema.sql
- [ ] Seed countries table with initial 10 countries
- [ ] Verify tables created: `\dt`
- [ ] Verify indexes: `\di`

### Backfill
- [ ] Export current trends from Redis (if any)
- [ ] Insert historical data into topic_snapshots
- [ ] Verify row counts: `SELECT * FROM v_row_counts`

### Enable Persistence
- [ ] Modify `/v1/trends` to write to database
- [ ] Modify `/v1/flows` to write to database
- [ ] Add background tasks for async writes
- [ ] Test with sample data

### Monitoring
- [ ] Set up slow query logging (>1s)
- [ ] Enable pg_stat_statements extension
- [ ] Schedule materialized view refresh (15 min)
- [ ] Set up alerts for disk space (>80% = warning)

### Production Readiness
- [ ] Configure automated backups (daily)
- [ ] Test restore from backup
- [ ] Document disaster recovery plan
- [ ] Set up read replicas (optional, for scale)

---

## Useful Commands

### psql (PostgreSQL CLI)
```bash
# Connect to database
psql -h localhost -U observatory -d observatory

# Inside psql:
\dt                    # List tables
\d+ table_name         # Describe table with indexes
\di                    # List indexes
\dv                    # List views
\dm                    # List materialized views
\df                    # List functions
\x                     # Toggle expanded display (for wide results)
\timing                # Show query execution time
\q                     # Quit
```

### Docker Commands
```bash
# View PostgreSQL logs
docker compose logs -f postgres

# Execute SQL file
docker compose exec postgres psql -U observatory -d observatory -f /path/to/file.sql

# Backup database
docker compose exec postgres pg_dump -U observatory observatory > backup.sql

# Restore database
cat backup.sql | docker compose exec -T postgres psql -U observatory observatory
```

---

## Next Steps

1. **Run Migration**: Execute `002_comprehensive_flow_schema.sql`
2. **Test Queries**: Run sample queries from this guide
3. **Implement Persistence**: Update API endpoints to write to DB
4. **Monitor Performance**: Track query times, cache hit ratio
5. **Schedule Maintenance**: Set up pg_cron for cleanup and refresh
6. **Plan Iteration 3**: Add PostGIS, full-text search, BERT embeddings

---

**Last Updated**: 2025-01-13
**Status**: Ready for Implementation

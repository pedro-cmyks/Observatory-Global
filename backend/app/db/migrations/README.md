# Database Migrations

This directory contains SQL migrations for the Observatory Global database.

## Running Migrations

### Manual Execution

Connect to PostgreSQL and run migrations in order:

```bash
# Connect to database
psql -h localhost -U observatory -d observatory

# Run migration
\i backend/app/db/migrations/001_create_trends_archive.sql
```

### Docker Compose

Migrations will be automatically executed when the database container starts (if configured).

## Migration List

| Migration | Description | Status |
|-----------|-------------|--------|
| 001_create_trends_archive.sql | Create trends_archive table with indexes | ✅ Ready |

## Schema

### trends_archive

Stores historical trending topics for flow detection and time-series analysis.

**Columns:**
- `id` (SERIAL PRIMARY KEY): Unique identifier
- `timestamp` (TIMESTAMP NOT NULL): When the topic was trending
- `country` (VARCHAR(2) NOT NULL): ISO 3166-1 alpha-2 country code
- `topic_label` (VARCHAR(500) NOT NULL): Topic label or title
- `count` (INTEGER NOT NULL): Topic frequency/popularity count
- `confidence` (FLOAT NOT NULL): Confidence score [0.0, 1.0]
- `sources` (JSONB): JSON array of data sources
- `created_at` (TIMESTAMP): When record was inserted

**Indexes:**
- `idx_trends_archive_country_timestamp` on (country, timestamp DESC)
- `idx_trends_archive_timestamp` on (timestamp DESC)
- `idx_trends_archive_topic_label` on (topic_label)

**Usage:**
This table enables:
- Historical trend analysis over time
- Flow detection across countries
- Performance optimization via time-series indexes
- Source tracking for data provenance

## Future Migrations

- 002_create_flows_table.sql: Persist computed flows
- 003_add_flow_metadata.sql: Add metadata columns for flow analysis
- 004_create_hotspots_table.sql: Persist hotspot calculations

# Database Migrations

This directory contains SQL migration files for the Observatory Global database schema.

## Migration Files

| File | Description | Status | Date |
|------|-------------|--------|------|
| `001_create_trends_archive.sql` | Basic trends archive table (deprecated) | ✅ Applied | 2025-01-12 |
| `002_comprehensive_flow_schema.sql` | Full schema for flow analysis | ⏳ Pending | 2025-01-13 |

## Running Migrations

### Prerequisites

1. PostgreSQL must be running:
```bash
cd infra
docker compose up -d postgres
```

2. Environment variables must be set in `.env`:
```bash
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=observatory
POSTGRES_USER=observatory
POSTGRES_PASSWORD=your_secure_password
```

### Run All Pending Migrations

```bash
# From backend directory
cd backend
python -m app.db.migrate
```

### Check Migration Status

```bash
python -m app.db.migrate --status
```

### Expected Output

```
🚀 Observatory Global - Database Migration Runner
================================================================================
📡 Connecting to database...
✓ Connected to: observatory
✓ Migrations tracking table ready

📋 Found 1 pending migration(s):
   - 002_comprehensive_flow_schema.sql

🤔 Do you want to run these migrations? [y/N]: y

🔄 Running migration: 002_comprehensive_flow_schema.sql
✅ 002_comprehensive_flow_schema.sql completed successfully

================================================================================
📊 Migration Summary: 1/1 successful
🎉 All migrations completed successfully!
```

## Migration Files Structure

### Naming Convention

```
{number}_{description}.sql

Examples:
- 001_create_trends_archive.sql
- 002_comprehensive_flow_schema.sql
- 003_add_full_text_search.sql (future)
```

### File Format

```sql
-- ============================================================================
-- Migration: {number}_{description}.sql
-- Purpose: Brief description of what this migration does
-- Author: Agent/Developer name
-- Date: YYYY-MM-DD
-- Related: Links to ADRs, docs, or tickets
-- ============================================================================

-- Enable extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Create tables
CREATE TABLE IF NOT EXISTS table_name (...);

-- Create indexes
CREATE INDEX idx_name ON table_name(column);

-- Add comments
COMMENT ON TABLE table_name IS 'Description';

-- Verification (optional)
DO $$
BEGIN
    RAISE NOTICE 'Migration completed successfully!';
END $$;
```

## Creating New Migrations

### Step 1: Create Migration File

```bash
# Create new migration file with next number
touch backend/app/db/migrations/003_add_feature.sql
```

### Step 2: Write Migration SQL

```sql
-- Write CREATE TABLE, ALTER TABLE, CREATE INDEX, etc.
-- Always use IF NOT EXISTS to make migrations idempotent
-- Add comments to document schema
```

### Step 3: Test Locally

```bash
# Run migration
python -m app.db.migrate

# Verify tables created
docker compose exec postgres psql -U observatory -d observatory -c "\dt"

# Check indexes
docker compose exec postgres psql -U observatory -d observatory -c "\di"
```

### Step 4: Commit and Document

```bash
git add backend/app/db/migrations/003_add_feature.sql
git commit -m "feat(db): add feature schema"

# Update this README with new migration info
```

## Migration Best Practices

### DO ✅

- Use `IF NOT EXISTS` for idempotency
- Add indexes for foreign keys and frequently queried columns
- Add `COMMENT ON` statements to document schema
- Test migrations on sample data before production
- Keep migrations small and focused (one feature per migration)
- Include verification queries at the end

### DON'T ❌

- Don't modify existing migration files (create new ones instead)
- Don't delete migration files (even if deprecated)
- Don't skip migration numbers
- Don't use `DROP TABLE` without backup/confirmation
- Don't hardcode sensitive data (use environment variables)

## Rollback Strategy

### Manual Rollback (if migration fails)

```bash
# Connect to database
docker compose exec postgres psql -U observatory -d observatory

# Drop created tables/indexes
DROP TABLE IF EXISTS table_name CASCADE;
DROP INDEX IF EXISTS idx_name;

# Remove migration record
DELETE FROM schema_migrations WHERE migration_name = '003_failed_migration.sql';
```

### Automated Rollback (not yet implemented)

Future feature: Each migration will have a corresponding rollback file.

```
migrations/
├── 002_comprehensive_flow_schema.sql
├── 002_comprehensive_flow_schema.rollback.sql  # Future
```

## Troubleshooting

### Migration Fails: "relation already exists"

**Cause**: Migration was partially applied, or you're re-running a completed migration.

**Solution**:
```sql
-- Check migration status
python -m app.db.migrate --status

-- If migration shows as applied but tables are missing, manually fix:
-- 1. Drop partially created tables
-- 2. Delete migration record
DELETE FROM schema_migrations WHERE migration_name = 'problematic_migration.sql';

-- 3. Re-run migration
python -m app.db.migrate
```

### Migration Fails: "permission denied"

**Cause**: Database user lacks permissions.

**Solution**:
```sql
-- Grant necessary permissions
GRANT CREATE ON DATABASE observatory TO observatory_user;
GRANT CREATE ON SCHEMA public TO observatory_user;
```

### Migration Fails: "syntax error"

**Cause**: Invalid SQL syntax in migration file.

**Solution**:
```bash
# Test SQL syntax directly
docker compose exec postgres psql -U observatory -d observatory -f backend/app/db/migrations/problematic_migration.sql

# Fix syntax errors, then re-run
python -m app.db.migrate
```

## Related Documentation

- [Database Schema Design](/docs/database-schema-design.md) - Full schema documentation
- [Database Quick Reference](/docs/database-schema-quickref.md) - Common queries and commands
- [ADR-0002: Heat Formula](/docs/decisions/ADR-0002-heat-formula.md) - Flow detection algorithm

## Migration History

### Migration 001: Trends Archive (2025-01-12)

**Status**: ✅ Applied (but deprecated by Migration 002)

**Purpose**: Create basic `trends_archive` table for storing historical trending topics.

**Tables Created**:
- `trends_archive` (deprecated, replaced by `topic_snapshots`)

**Notes**: This was an initial prototype. Migration 002 supersedes this with a comprehensive schema.

### Migration 002: Comprehensive Flow Schema (2025-01-13)

**Status**: ⏳ Pending

**Purpose**: Complete schema for flow analysis, narrative evolution, and stance tracking.

**Tables Created**:
- `countries` - Reference table for country metadata
- `topics` - Master table of unique topics
- `topic_snapshots` - Time-series data (partitioned)
- `hotspots` - Aggregated country-level intensity
- `flows` - Information flows between countries
- `stance_history` - Narrative evolution tracking

**Views Created**:
- `mv_recent_hotspots` - Materialized view (24h cache)
- `mv_active_flows` - Materialized view (24h cache)
- `v_table_sizes` - Helper view for monitoring
- `v_row_counts` - Helper view for monitoring

**Functions/Triggers**:
- `update_topic_last_seen()` - Auto-update topics on snapshot insert
- `detect_stance_change()` - Auto-detect narrative drift

**Storage Estimate**: ~430 MB/month (10 countries)

**Performance Target**: <100ms for cached queries

## Next Steps

1. **Run Migration 002**: Execute comprehensive flow schema
2. **Seed Countries**: Insert initial 10 countries (included in migration)
3. **Test Queries**: Verify schema with sample queries
4. **Implement Persistence**: Update API to write to database
5. **Schedule Maintenance**: Set up pg_cron for cleanup and refresh

---

**Last Updated**: 2025-01-13
**Migration Count**: 2 total (1 applied, 1 pending)

#!/bin/bash
# One-off maintenance (2026-08-18): REINDEX CONCURRENTLY the bloated
# signals_v2 indexes. Measured motive: signals_v2 = 5.6GB total / 1.67GB heap
# → ~3.9GB of indexes for 1.58M rows (7d-churn index bloat, the July disease
# back). Symptom today: every live read timing out while a 2h autovacuum
# ANALYZE waded through the same I/O; the briefing artifact kept the door
# alive (0.4s) while threads/stats/siblings starved.
#
# REINDEX CONCURRENTLY: non-blocking for reads AND writes; runs autocommit
# (never inside a transaction); needs session-mode connection — the ALW
# DATABASE_URL is the pooler on :5432 (session mode), which works.
# Run in the quiet window (post-seal ~04:30). NOT the two duplicate-looking
# headline trgm indexes decision — that needs the July-style EXPLAIN check in
# daylight; tonight is size-only maintenance on indexes we KEEP.
set -uo pipefail
ENV_FILE="/Users/pedro/AtlasLocalWorker/.env"
DATABASE_URL=$(grep -m1 '^DATABASE_URL=' "$ENV_FILE" | cut -d= -f2-)
LOG="/Users/pedro/AtlasLocalWorker/logs/reindex-signals-v2-$(date +%Y%m%d-%H%M).log"

INDEXES=(
  idx_signals_v2_themes_text_trgm
  idx_signals_headline_trgm
  idx_signals_v2_headline_trgm
  idx_signals_v2_source_url_unique
  idx_signals_v2_id_country
)

{
  echo "== reindex signals_v2 · $(date -u +%FT%TZ) =="
  psql "$DATABASE_URL" -tAc "SELECT 'ANTES total: '||pg_size_pretty(pg_total_relation_size('signals_v2'))"
  for idx in "${INDEXES[@]}"; do
    before=$(psql "$DATABASE_URL" -tAc "SELECT pg_size_pretty(pg_relation_size('${idx}'::regclass))")
    echo "-- $idx (antes: $before)"
    # SET + REINDEX in one session; psql autocommits each statement, so the
    # CONCURRENTLY never lands inside an explicit transaction.
    psql "$DATABASE_URL" <<SQL
SET statement_timeout = 0;
REINDEX INDEX CONCURRENTLY ${idx};
SQL
    rc=$?
    after=$(psql "$DATABASE_URL" -tAc "SELECT pg_size_pretty(pg_relation_size('${idx}'::regclass))" 2>/dev/null)
    echo "-- $idx rc=$rc (después: $after)"
    # A failed CONCURRENTLY leaves an _ccnew invalid index — name it, never hide it.
    psql "$DATABASE_URL" -tAc "SELECT 'INVALID LEFTOVER: '||indexrelid::regclass FROM pg_index WHERE NOT indisvalid AND indexrelid::regclass::text LIKE '%${idx}%'"
  done
  psql "$DATABASE_URL" -tAc "SELECT 'DESPUÉS total: '||pg_size_pretty(pg_total_relation_size('signals_v2'))"
  echo "== fin · $(date -u +%FT%TZ) =="
} 2>&1 | tee "$LOG"

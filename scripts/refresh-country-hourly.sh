#!/usr/bin/env bash
# country_hourly_v2 refresh — moved OFF the API (2026-07-02).
# The API's in-process refresh dies through the Supabase TRANSACTION pooler:
# session SETs (statement_timeout) don't stick across asyncpg execute() calls,
# so the >120s refresh is killed (twice now: 07-01 08:00 and 07-02 02:00 UTC).
# psql from the M1 over the SESSION-mode pooler (port 5432) is the proven path
# (manual backfill 2026-07-01 ran 2m35s fine).
set -uo pipefail
ENV_FILE="${ATLAS_ENV_FILE:-$HOME/AtlasLocalWorker/.env}"
LOG="$HOME/AtlasLocalWorker/logs/matview-refresh.log"
[ -f "$ENV_FILE" ] && { set -a; source "$ENV_FILE"; set +a; }
ts() { date '+%F %T'; }
if psql "$DATABASE_URL" -qc "SET statement_timeout='600s'; REFRESH MATERIALIZED VIEW CONCURRENTLY country_hourly_v2;" >> "$LOG" 2>&1; then
  echo "$(ts) refreshed" >> "$LOG"
else
  echo "$(ts) REFRESH FAILED" >> "$LOG"
fi

#!/usr/bin/env bash
# ONE-SHOT HNSW rebuild for signal_embeddings (2026-07-02 night, off-peak).
# History: the in-API attempt died twice through the TRANSACTION pooler
# (session SETs dropped → statement_timeout killed it), and a 256MB
# maintenance_work_mem build thrashed for 6h and exhausted the Supabase IO
# burst budget (DB-wide 500s). This is the corrected single pass:
#   - psql over the SESSION-mode pooler (SETs stick)
#   - maintenance_work_mem 512MB (index needs ~800MB working set; 512 is the
#     max that didn't hit the shmem error WITH parallel workers disabled)
#   - max_parallel_maintenance_workers 0 (512MB + workers → shmem error)
#   - CREATE INDEX (not CONCURRENTLY): single efficient pass, off-peak;
#     concurrent build doubles the IO — the budget is the scarce resource.
#   - 90min hard timeout; on failure LOG AND STOP (no retry loop — a second
#     thrash is how the IO budget dies).
# Self-disarms: unloads its own launchd job at the end (one-shot).
set -uo pipefail
ENV_FILE="${ATLAS_ENV_FILE:-$HOME/AtlasLocalWorker/.env}"
LOG="$HOME/AtlasLocalWorker/logs/hnsw-rebuild.log"
[ -f "$ENV_FILE" ] && { set -a; source "$ENV_FILE"; set +a; }
ts() { date '+%F %T'; }

echo "$(ts) HNSW one-shot rebuild starting" >> "$LOG"
if psql "$DATABASE_URL" -qc "
SET statement_timeout='5400s';
SET maintenance_work_mem='512MB';
SET max_parallel_maintenance_workers=0;
DROP INDEX IF EXISTS idx_signal_embeddings_vec;
CREATE INDEX idx_signal_embeddings_vec ON signal_embeddings
  USING hnsw (vec halfvec_cosine_ops) WITH (m = 16, ef_construction = 64);
ANALYZE signal_embeddings;
" >> "$LOG" 2>&1; then
  echo "$(ts) HNSW rebuild OK" >> "$LOG"
else
  echo "$(ts) HNSW rebuild FAILED — do NOT retry automatically (IO budget)" >> "$LOG"
fi

# one-shot: disarm
launchctl bootout "gui/$(id -u)/com.atlas.hnsw-rebuild-once" 2>/dev/null || true

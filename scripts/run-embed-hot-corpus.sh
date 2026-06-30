#!/usr/bin/env bash
set -euo pipefail

# Signal-embedding writer runner (#223 deliverable 2).
#
# Launchd runs this from /Users/pedro/AtlasLocalWorker. Embeds the deduped
# recent window into signal_embeddings (halfvec/768) with the
# snapshot-identical e5 pooling, then sweeps rows past retention.

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if [[ -d "$SCRIPT_DIR/backend" ]]; then
  DEFAULT_ROOT_DIR="$SCRIPT_DIR"
else
  DEFAULT_ROOT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
fi

ROOT_DIR="${ATLAS_LOCAL_WORKER_DIR:-$DEFAULT_ROOT_DIR}"
BACKEND_DIR="$ROOT_DIR/backend"
LOG_DIR="${ATLAS_LOCAL_LOG_DIR:-$ROOT_DIR/logs}"
MLVENV="${ATLAS_MLVENV:-/Users/pedro/AtlasLocalWorker/mlvenv}"
LOCAL_ENV="${ATLAS_LOCAL_ENV:-$ROOT_DIR/.env}"

# Incremental: only the recent window each run; retention bounds the table.
WINDOW_HOURS="${ATLAS_EMBED_WINDOW_HOURS:-168}"
RETENTION_DAYS="${ATLAS_EMBED_RETENTION_DAYS:-7}"
MAX_SIGNALS="${ATLAS_EMBED_MAX_SIGNALS:-60000}"  # ~25-40 min/run, bounded

export PATH="/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin:${PATH:-}"
mkdir -p "$LOG_DIR"

if [[ -r "$LOCAL_ENV" && -z "${DATABASE_URL:-}" ]]; then
  DATABASE_URL="$(grep -E '^DATABASE_URL=' "$LOCAL_ENV" | head -1 | cut -d= -f2-)"
  export DATABASE_URL
fi

if [[ -z "${DATABASE_URL:-}" ]]; then
  echo "[embed-hot-corpus] DATABASE_URL not set and not found in $LOCAL_ENV" >&2
  exit 1
fi

if [[ ! -x "$MLVENV/bin/python" ]]; then
  echo "[embed-hot-corpus] mlvenv python not found at $MLVENV" >&2
  exit 2
fi

cd "$BACKEND_DIR"
# Step 1: embed the recent window (this is the heavy step).
# NON-FATAL (fixed 2026-07-01): under `set -e` a non-zero exit here (e.g. the
# asyncpg statement-timeout seen when the embed backlog is large + slow) ABORTED
# the whole runner BEFORE Steps 2-4 — which froze topic_members at 2026-06-29
# 19:04 (the topic layer stopped refreshing while ingest/embed/lexical-assign
# stayed live). The downstream ETL projects fresh LEXICAL assignments and does
# not need embed to fully succeed, so a partial/timed-out embed must not block
# it. (The underlying embed backlog/throughput is #241, separate.)
"$MLVENV/bin/python" -m scripts.embed_hot_corpus \
  --hours "$WINDOW_HOURS" \
  --retention-days "$RETENTION_DAYS" \
  --max-signals "$MAX_SIGNALS" \
  || echo "[embed-hot-corpus] embed step failed/timed out (non-fatal); continuing to attach/ETL/build so topic_members stays fresh" >&2

# ── Unified Engine F1 — recurring discussion chain (spec 2026-06-29 §7/§10) ──
# The attach + projection are pure pgvector/asyncpg (no torch) and DEPEND on the
# embeddings just written, so they run right here, right after. Both non-fatal:
# a hiccup never blocks (or re-fails) the embed run. Idempotent.
DISCUSSION_THRESHOLD="${ATLAS_DISCUSSION_THRESHOLD:-0.90}"  # precision-first (documented in the script)
PROJECT_HOURS="${ATLAS_DISCUSSION_HOURS:-336}"

# Step 2: attach freshly-embedded social signals to their nearest gate-kept
# thread as DISCUSSION members (semantic-discussion-v1, verified=false, never
# evidence).
"$MLVENV/bin/python" scripts/assign_discussion_topics.py \
  --hours "$PROJECT_HOURS" --threshold "$DISCUSSION_THRESHOLD" \
  || echo "[embed-hot-corpus] discussion attach failed (non-fatal)" >&2

# Step 3: project v1-compat assignments (atlas evidence + the discussion attaches
# above) into the typed topic_members serving table, so /topic/{id}/relationship
# and the F0.3 read-flag stay current. NOTE: when the read-flag is flipped on,
# move this projection to the 30-min classifier runner for fresher EVIDENCE (the
# classifier writes assignments every 30 min; here they land in topic_members
# only on the embed cadence, ~3x/day).
"$MLVENV/bin/python" -m scripts.etl_topic_members --hours "$PROJECT_HOURS" \
  || echo "[embed-hot-corpus] topic_members ETL failed (non-fatal)" >&2

# Step 4: Unified Engine F3 — rebuild the unified-v2 construction in parallel
# (engine_version='unified-v2', isolated from v1 serving) so the A/B
# (engine_ab_report.py) reflects the current window and the measured cutover gate
# stays live. numpy + HDBSCAN over the embeddings just written; non-fatal.
UNIFIED_ASSIGN_T="${ATLAS_UNIFIED_ASSIGN_THRESHOLD:-0.88}"
UNIFIED_GATE_T="${ATLAS_UNIFIED_GATE_THRESHOLD:-0.90}"
"$MLVENV/bin/python" -m scripts.build_unified_topics \
  --hours "$PROJECT_HOURS" \
  --assign-threshold "$UNIFIED_ASSIGN_T" --gate-threshold "$UNIFIED_GATE_T" \
  || echo "[embed-hot-corpus] unified-v2 build failed (non-fatal)" >&2

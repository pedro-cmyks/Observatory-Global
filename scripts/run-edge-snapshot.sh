#!/usr/bin/env bash
set -uo pipefail

# Time-axis edge-snapshot runner (spec docs/superpowers/specs/
# 2026-07-21-time-axis-versioned-relationships.md §5a/§6). Persists one
# topic_edge_snapshots pass + the entity backbone per run, so replay/diff
# (/api/v2/edges/replay, /api/v2/focus/{ref}/edge-diff) accumulate history and
# can separate real narrative change from substrate churn.
#
# Launchd runs this from /Users/pedro/AtlasLocalWorker (off-Desktop, so macOS
# TCC does not block cron reads). Mindful: efficiency cores + nice, off-peak.
# Best-effort by construction: the writer already degrades the heavy backbone
# to a skip without losing the kinship edges.

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
WINDOW_HOURS="${ATLAS_EDGE_SNAPSHOT_WINDOW_HOURS:-720}"

export PATH="/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin:${PATH:-}"
mkdir -p "$LOG_DIR"

[[ -f "$LOCAL_ENV" ]] && { set -a; . "$LOCAL_ENV"; set +a; }
if [[ -z "${DATABASE_URL:-}" ]]; then
  echo "edge-snapshot: DATABASE_URL unset — skipping" >&2
  exit 0
fi

PY="$MLVENV/bin/python"
[[ -x "$PY" ]] || PY="python3"

cd "$BACKEND_DIR" || { echo "edge-snapshot: no backend dir at $BACKEND_DIR" >&2; exit 2; }

# Mindful: Background QoS via taskpolicy -b (efficiency cores) + nice.
PYTHONPATH=. taskpolicy -b nice -n 10 "$PY" scripts/snapshot_topic_edges.py \
    --window-hours "$WINDOW_HOURS" \
    >>"$LOG_DIR/edge-snapshot.out.log" 2>>"$LOG_DIR/edge-snapshot.err.log"
echo "edge-snapshot done rc=$? @ $(date -u +%FT%TZ)" >>"$LOG_DIR/edge-snapshot.out.log"

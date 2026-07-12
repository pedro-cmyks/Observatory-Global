#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if [[ -d "$SCRIPT_DIR/backend" ]]; then
  DEFAULT_ROOT_DIR="$SCRIPT_DIR"
else
  DEFAULT_ROOT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
fi
ROOT_DIR="${ATLAS_REPO_DIR:-$DEFAULT_ROOT_DIR}"
BACKEND_DIR="$ROOT_DIR/backend"
DEFAULT_ARCHIVE_ROOT="/Volumes/Ext/Atlas/Archive"
ARCHIVE_ROOT="${ATLAS_ARCHIVE_ROOT:-$DEFAULT_ARCHIVE_ROOT}"
FLY_APP="${ATLAS_FLY_APP:-atlas-api-pedro}"
LOG_DIR="${ATLAS_LOCAL_LOG_DIR:-$ROOT_DIR/logs}"
OUTPUT_DIR="${ATLAS_PROCESSED_HISTORY_DIR:-/Volumes/Ext/Atlas/Processed}"

export PATH="/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin:${PATH:-}"

mkdir -p "$LOG_DIR"

if [[ "$ARCHIVE_ROOT" == /Volumes/* ]]; then
  VOLUME_NAME="${ARCHIVE_ROOT#/Volumes/}"
  VOLUME_NAME="${VOLUME_NAME%%/*}"
  VOLUME_ROOT="/Volumes/$VOLUME_NAME"
  if [[ ! -d "$VOLUME_ROOT" ]]; then
    echo "[local-hot-cold] external archive volume is not mounted: $VOLUME_ROOT" >&2
    exit 2
  fi
fi

mkdir -p "$ARCHIVE_ROOT" "$OUTPUT_DIR"

# P1.1 heavy-job mutex: archive scan + prune hammers the shared Supabase.
# SKIP mode — the hourly night cadence (00:10-04:10) self-heals a missed run.
if [[ -r "$SCRIPT_DIR/heavy-job-lock.sh" ]]; then
  source "$SCRIPT_DIR/heavy-job-lock.sh"
  atlas_heavy_lock "hot-cold-catchup" skip 240 || exit 0
else
  echo "[local-hot-cold] heavy-job-lock.sh missing — running UNSERIALIZED" >&2
fi

if [[ -z "${DATABASE_URL:-}" && -z "${SUPABASE_DB_URL:-}" ]]; then
  DATABASE_URL="$(
    fly ssh console -a "$FLY_APP" --pty=false -C 'printenv DATABASE_URL' 2>/dev/null \
      | tail -n 1 \
      | tr -d '\r'
  )"
  export DATABASE_URL
fi

cd "$BACKEND_DIR"

# Hot window (Pedro 2026-07-04): the script's --older-than-hours DEFAULT is
# 24 — that, not the documented 7d retention, was what trimmed the hot DB to
# ~1-2 days and starved every 7d consumer (Kalman movement buckets, identity
# persistence, 168h views). 168h = the real 7-day hot window; prune still
# only runs AFTER verified archive export. Override: ATLAS_HOT_RETENTION_HOURS.
# No exec: exec replaces the shell and the heavy-lock EXIT trap never fires.
.venv/bin/python -m scripts.local_hot_cold_catchup \
  --archive-root "$ARCHIVE_ROOT" \
  --output-dir "$OUTPUT_DIR" \
  --older-than-hours "${ATLAS_HOT_RETENTION_HOURS:-168}" \
  --allow-catch-up-outside-window \
  --execute \
  --execute-prune \
  --i-understand-irreversible-delete \
  "$@"

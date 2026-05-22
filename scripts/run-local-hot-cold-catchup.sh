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
ARCHIVE_ROOT="${ATLAS_ARCHIVE_ROOT:-/Users/pedro/AtlasArchive}"
FLY_APP="${ATLAS_FLY_APP:-atlas-api-pedro}"
LOG_DIR="${ATLAS_LOCAL_LOG_DIR:-$ROOT_DIR/logs}"
OUTPUT_DIR="${ATLAS_PROCESSED_HISTORY_DIR:-$ARCHIVE_ROOT/processed-historical-sync}"

export PATH="/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin:${PATH:-}"

mkdir -p "$LOG_DIR"

if [[ -z "${DATABASE_URL:-}" && -z "${SUPABASE_DB_URL:-}" ]]; then
  DATABASE_URL="$(
    fly ssh console -a "$FLY_APP" --pty=false -C 'printenv DATABASE_URL' 2>/dev/null \
      | tail -n 1 \
      | tr -d '\r'
  )"
  export DATABASE_URL
fi

cd "$BACKEND_DIR"

exec .venv/bin/python -m scripts.local_hot_cold_catchup \
  --archive-root "$ARCHIVE_ROOT" \
  --output-dir "$OUTPUT_DIR" \
  --allow-catch-up-outside-window \
  --execute \
  --execute-prune \
  --i-understand-irreversible-delete \
  "$@"

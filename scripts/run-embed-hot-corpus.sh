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
WINDOW_HOURS="${ATLAS_EMBED_WINDOW_HOURS:-48}"
RETENTION_DAYS="${ATLAS_EMBED_RETENTION_DAYS:-7}"
MAX_SIGNALS="${ATLAS_EMBED_MAX_SIGNALS:-120000}"

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
exec "$MLVENV/bin/python" -m scripts.embed_hot_corpus \
  --hours "$WINDOW_HOURS" \
  --retention-days "$RETENTION_DAYS" \
  --max-signals "$MAX_SIGNALS"

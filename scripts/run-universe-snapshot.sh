#!/usr/bin/env bash
set -euo pipefail

# Universe snapshot runner — precomputes the /api/v2/universe payload into the
# universe_snapshot table so serving is a cheap JSONB read (the live rebuild is
# ~11s / >20s cold, past the frontend abort). Warm-keeper only: the endpoint
# self-heals via a background write-through, so a missed run just means one
# slower request, never the empty state.
#
# Launchd runs this from /Users/pedro/AtlasLocalWorker. Keep credentials in that
# off-Desktop runtime so macOS privacy controls do not block cron reads.

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
FLY_APP="${ATLAS_FLY_APP:-atlas-api-pedro}"
DAYS="${ATLAS_UNIVERSE_DAYS:-30}"

export PATH="/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin:${PATH:-}"
mkdir -p "$LOG_DIR"

# Heavy-job mutex: yield to embed/scoped/clustering/catchup on the shared DB.
if [[ -r "$SCRIPT_DIR/heavy-job-lock.sh" ]]; then
  source "$SCRIPT_DIR/heavy-job-lock.sh"
  atlas_heavy_lock "universe-snapshot" wait 120 60 || exit 0
fi

load_env_file() {
  local env_file="$1"
  [[ -r "$env_file" ]] || return 0
  local value
  if [[ -z "${DATABASE_URL:-}" ]]; then
    value="$(grep -E "^DATABASE_URL=" "$env_file" | tail -n 1 | sed -E "s/^DATABASE_URL=//" | tr -d '\r' || true)"
    [[ -n "$value" ]] && export "DATABASE_URL=$value"
  fi
}
load_env_file "$LOCAL_ENV"

if [[ -z "${DATABASE_URL:-}" ]]; then
  DATABASE_URL="$(fly ssh console -a "$FLY_APP" --pty=false -C 'printenv DATABASE_URL' 2>/dev/null | tail -n 1 | tr -d '\r')"
  export DATABASE_URL
fi

if [[ -z "${DATABASE_URL:-}" ]]; then
  echo "[universe-snapshot] missing DATABASE_URL; install $LOCAL_ENV" >&2
  exit 2
fi
if [[ ! -x "$MLVENV/bin/python" ]]; then
  echo "[universe-snapshot] mlvenv python not found at $MLVENV" >&2
  exit 2
fi

# Run from backend/ so `app` is importable (the service module uses `from app`).
cd "$BACKEND_DIR"

# Mindful: efficiency cores so it yields to foreground work.
TASKPOLICY=""
command -v taskpolicy >/dev/null 2>&1 && TASKPOLICY="taskpolicy -b"

$TASKPOLICY "$MLVENV/bin/python" -m scripts.build_universe_snapshot --days "$DAYS" "$@"

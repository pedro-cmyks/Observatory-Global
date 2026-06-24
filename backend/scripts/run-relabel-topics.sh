#!/usr/bin/env bash
set -euo pipefail

# Dynamic-topic relabel runner (#229 lever 5).
#
# Refreshes stale/frozen/placeholder topic labels via the LOCAL Claude CLI (Max
# plan, $0 marginal — no DeepSeek). Runs as a user LaunchAgent so `claude` can
# reach the login keychain credentials. If a long-lived token is provisioned
# (`claude setup-token` → CLAUDE_CODE_OAUTH_TOKEN in the runtime .env) it is used
# for fully headless auth. Either way, label_via_claude degrades to a no-write
# failure stub on auth error, so a failed auth NEVER corrupts data — worst case
# the run relabels nothing and logs the failures.
#
# NIGHTLY ONLY. Heavy-ish (spawns the Claude CLI per stale topic); never during
# Pedro's working hours — same rule as the embed/snapshot crons.

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

MAX_AGE_DAYS="${ATLAS_RELABEL_MAX_AGE_DAYS:-7}"
LIMIT="${ATLAS_RELABEL_LIMIT:-25}"

# claude lives in ~/.local/bin; keep homebrew + system paths for the venv.
export PATH="/Users/pedro/.local/bin:/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin:${PATH:-}"
mkdir -p "$LOG_DIR"

load_env_file() {
  local env_file="$1"
  [[ -r "$env_file" ]] || return 0
  local key value
  for key in DATABASE_URL CLAUDE_CODE_OAUTH_TOKEN; do
    if [[ -z "${!key:-}" ]]; then
      value="$(grep -E "^${key}=" "$env_file" | tail -n 1 | sed -E "s/^${key}=//" | tr -d '\r' || true)"
      [[ -n "$value" ]] && export "$key=$value"
    fi
  done
  return 0  # never let an empty optional key (CLAUDE_CODE_OAUTH_TOKEN) trip set -e
}

load_env_file "$LOCAL_ENV"

if [[ -z "${DATABASE_URL:-}" ]]; then
  echo "[relabel-topics] missing DATABASE_URL; install $LOCAL_ENV" >&2
  exit 2
fi
if [[ ! -x "$MLVENV/bin/python" ]]; then
  echo "[relabel-topics] mlvenv python not found at $MLVENV" >&2
  exit 2
fi
if ! command -v claude >/dev/null 2>&1; then
  echo "[relabel-topics] claude CLI not on PATH" >&2
  exit 2
fi

cd "$BACKEND_DIR"
"$MLVENV/bin/python" -m scripts.relabel_dynamic_topics \
  --max-age-days "$MAX_AGE_DAYS" \
  --limit "$LIMIT" \
  "$@"

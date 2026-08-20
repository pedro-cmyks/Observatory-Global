#!/usr/bin/env bash
set -euo pipefail

# Install the nightly dynamic-topic relabel LaunchAgent (#229 lever 5).
# Relabels stale/frozen labels via the LOCAL Claude CLI (Max plan, $0).
#
# AUTH: runs as a user LaunchAgent so `claude` can use the login keychain
# credentials when you are logged in. For fully headless auth (or if keychain
# access is denied under launchd), provision a long-lived token once with
#   claude setup-token
# and add it to the worker env as CLAUDE_CODE_OAUTH_TOKEN=... — this installer
# copies that key through if present in the source .env.

ROOT_DIR="${ATLAS_REPO_DIR:-/Users/pedro/ObservatorioGlobal}"
WORKER_HOME="${ATLAS_LOCAL_WORKER_HOME:-/Users/pedro/AtlasLocalWorker}"
PLIST_NAME="com.atlas.relabel-topics.plist"
SOURCE_PLIST="$ROOT_DIR/infra/launchd/$PLIST_NAME"
TARGET_PLIST="$HOME/Library/LaunchAgents/$PLIST_NAME"
SOURCE_ENV="${ATLAS_SOURCE_ENV:-$ROOT_DIR/.env}"
TARGET_ENV="$WORKER_HOME/.env"

mkdir -p "$HOME/Library/LaunchAgents" "$WORKER_HOME/backend" "$WORKER_HOME/logs"

rsync -a --delete "$ROOT_DIR/backend/scripts/" "$WORKER_HOME/backend/scripts/"
cp "$ROOT_DIR/backend/scripts/run-relabel-topics.sh" "$WORKER_HOME/run-relabel-topics.sh"
chmod +x "$WORKER_HOME/run-relabel-topics.sh"

# Additive env merge: append only keys missing from the worker .env.
umask 077
touch "$TARGET_ENV"
chmod 600 "$TARGET_ENV"
if [[ -r "$SOURCE_ENV" ]]; then
  for key in DATABASE_URL CLAUDE_CODE_OAUTH_TOKEN; do
    if ! grep -qE "^${key}=" "$TARGET_ENV"; then
      line="$(grep -E "^${key}=" "$SOURCE_ENV" | tail -n 1 || true)"
      [[ -n "$line" ]] && printf '%s\n' "$line" >> "$TARGET_ENV"
    fi
  done
else
  echo "Warning: source env not readable: $SOURCE_ENV" >&2
fi

cp "$SOURCE_PLIST" "$TARGET_PLIST"

launchctl bootout "gui/$(id -u)" "$TARGET_PLIST" >/dev/null 2>&1 || true
launchctl bootstrap "gui/$(id -u)" "$TARGET_PLIST"
launchctl enable "gui/$(id -u)/com.atlas.relabel-topics"

echo "Installed $PLIST_NAME (nightly 23:45 + 05:45, RunAtLoad off)"
echo "Worker home: $WORKER_HOME"
echo "Dry-run check: ATLAS_MLVENV=$WORKER_HOME/mlvenv $WORKER_HOME/run-relabel-topics.sh --dry-run"

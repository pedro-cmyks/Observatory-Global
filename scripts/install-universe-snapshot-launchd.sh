#!/usr/bin/env bash
set -euo pipefail

# Install the universe-snapshot warm-keeper cron on the M1 (precomputes the
# /api/v2/universe payload into universe_snapshot every 20 min). The endpoint
# self-heals without this cron; it just keeps the snapshot fresh.

ROOT_DIR="${ATLAS_REPO_DIR:-/Users/pedro/Desktop/PEDRO/Cursos/ObservatorioGlobal}"
WORKER_HOME="${ATLAS_LOCAL_WORKER_HOME:-/Users/pedro/AtlasLocalWorker}"
PLIST_NAME="com.atlas.universe-snapshot.plist"
SOURCE_PLIST="$ROOT_DIR/infra/launchd/$PLIST_NAME"
TARGET_PLIST="$HOME/Library/LaunchAgents/$PLIST_NAME"
SOURCE_ENV="${ATLAS_SOURCE_ENV:-$ROOT_DIR/.env}"
TARGET_ENV="$WORKER_HOME/.env"

mkdir -p "$HOME/Library/LaunchAgents" "$WORKER_HOME/backend" "$WORKER_HOME/logs"

# Sync the backend scripts + service module (build_universe_snapshot imports
# app.services.universe_build) and the runner.
rsync -a "$ROOT_DIR/backend/scripts/" "$WORKER_HOME/backend/scripts/"
rsync -a "$ROOT_DIR/backend/app/" "$WORKER_HOME/backend/app/"
cp "$ROOT_DIR/scripts/run-universe-snapshot.sh" "$WORKER_HOME/run-universe-snapshot.sh"
chmod +x "$WORKER_HOME/run-universe-snapshot.sh"

# Copy the heavy-job lock if present (serializes with embed/clustering).
[[ -f "$ROOT_DIR/scripts/heavy-job-lock.sh" ]] \
  && cp "$ROOT_DIR/scripts/heavy-job-lock.sh" "$WORKER_HOME/heavy-job-lock.sh" || true

# Additive env merge: append only DATABASE_URL if the worker .env lacks it.
umask 077
touch "$TARGET_ENV"
chmod 600 "$TARGET_ENV"
if [[ -r "$SOURCE_ENV" ]] && ! grep -qE "^DATABASE_URL=" "$TARGET_ENV"; then
  line="$(grep -E "^DATABASE_URL=" "$SOURCE_ENV" | tail -n 1 || true)"
  [[ -n "$line" ]] && printf '%s\n' "$line" >> "$TARGET_ENV"
fi

cp "$SOURCE_PLIST" "$TARGET_PLIST"

launchctl bootout "gui/$(id -u)" "$TARGET_PLIST" >/dev/null 2>&1 || true
launchctl bootstrap "gui/$(id -u)" "$TARGET_PLIST"
launchctl enable "gui/$(id -u)/com.atlas.universe-snapshot"

echo "Installed $PLIST_NAME"
echo "Worker home: $WORKER_HOME"

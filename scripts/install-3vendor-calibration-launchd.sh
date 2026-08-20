#!/usr/bin/env bash
set -euo pipefail

# Installs the daily 3-vendor calibration launchd agent (03:00).
# Additive on the worker .env: it appends only missing keys and never
# clobbers existing ones (unlike a full rewrite).

ROOT_DIR="${ATLAS_REPO_DIR:-/Users/pedro/ObservatorioGlobal}"
WORKER_HOME="${ATLAS_LOCAL_WORKER_HOME:-/Users/pedro/AtlasLocalWorker}"
PLIST_NAME="com.atlas.threevendor-calibration.plist"
LABEL="com.atlas.threevendor-calibration"
SOURCE_PLIST="$ROOT_DIR/infra/launchd/$PLIST_NAME"
TARGET_PLIST="$HOME/Library/LaunchAgents/$PLIST_NAME"
SOURCE_ENV="${ATLAS_SOURCE_ENV:-$ROOT_DIR/.env}"
TARGET_ENV="$WORKER_HOME/.env"

mkdir -p "$HOME/Library/LaunchAgents" "$WORKER_HOME/backend" "$WORKER_HOME/logs" "$WORKER_HOME/calibration"

rsync -a "$ROOT_DIR/backend/scripts/" "$WORKER_HOME/backend/scripts/"
cp "$ROOT_DIR/scripts/run-3vendor-calibration.sh" "$WORKER_HOME/run-3vendor-calibration.sh"
chmod +x "$WORKER_HOME/run-3vendor-calibration.sh"

# Additive env merge: append only keys missing from the worker .env.
umask 077
touch "$TARGET_ENV"
chmod 600 "$TARGET_ENV"
if [[ -r "$SOURCE_ENV" ]]; then
  for key in DATABASE_URL DEEPSEEK_API_KEY OPENAI_API_KEY ANTHROPIC_API_KEY; do
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
launchctl enable "gui/$(id -u)/$LABEL"

echo "Installed $PLIST_NAME (daily 03:00)"
echo "Worker home: $WORKER_HOME"
echo "Runner: $WORKER_HOME/run-3vendor-calibration.sh"
echo "Reports: $WORKER_HOME/calibration/"

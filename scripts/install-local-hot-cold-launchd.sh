#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="${ATLAS_REPO_DIR:-/Users/pedro/ObservatorioGlobal}"
WORKER_HOME="${ATLAS_LOCAL_WORKER_HOME:-/Users/pedro/AtlasLocalWorker}"
PLIST_NAME="com.atlas.local-hot-cold-catchup.plist"
SOURCE_PLIST="$ROOT_DIR/infra/launchd/$PLIST_NAME"
TARGET_PLIST="$HOME/Library/LaunchAgents/$PLIST_NAME"

mkdir -p "$HOME/Library/LaunchAgents" "$WORKER_HOME/backend" "$WORKER_HOME/logs"
rsync -a --delete "$ROOT_DIR/backend/scripts/" "$WORKER_HOME/backend/scripts/"
cp "$ROOT_DIR/scripts/run-local-hot-cold-catchup.sh" "$WORKER_HOME/run-local-hot-cold-catchup.sh"
chmod +x "$WORKER_HOME/run-local-hot-cold-catchup.sh"

if [[ ! -x "$WORKER_HOME/backend/.venv/bin/python" ]]; then
  python3 -m venv "$WORKER_HOME/backend/.venv"
fi
"$WORKER_HOME/backend/.venv/bin/python" -m pip install --quiet --upgrade pip
"$WORKER_HOME/backend/.venv/bin/python" -m pip install --quiet 'asyncpg>=0.29.0'

cp "$SOURCE_PLIST" "$TARGET_PLIST"

launchctl bootout "gui/$(id -u)" "$TARGET_PLIST" >/dev/null 2>&1 || true
launchctl bootstrap "gui/$(id -u)" "$TARGET_PLIST"
launchctl enable "gui/$(id -u)/com.atlas.local-hot-cold-catchup"
launchctl kickstart -k "gui/$(id -u)/com.atlas.local-hot-cold-catchup"

echo "Installed and started $PLIST_NAME"
echo "Worker home: $WORKER_HOME"

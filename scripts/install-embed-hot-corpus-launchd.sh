#!/usr/bin/env bash
set -euo pipefail

# Installs the signal-embedding writer cron (#223 deliverable 2) on the M1
# worker, mirroring the emergent-snapshot install pattern: runner + backend
# scripts synced into /Users/pedro/AtlasLocalWorker, credentials read from
# the worker .env (never the Desktop repo).

ROOT_DIR="${ATLAS_REPO_DIR:-/Users/pedro/Desktop/PEDRO/Cursos/ObservatorioGlobal}"
WORKER_HOME="${ATLAS_LOCAL_WORKER_HOME:-/Users/pedro/AtlasLocalWorker}"
PLIST_NAME="com.atlas.embed-hot-corpus.plist"
SOURCE_PLIST="$ROOT_DIR/infra/launchd/$PLIST_NAME"
TARGET_PLIST="$HOME/Library/LaunchAgents/$PLIST_NAME"

mkdir -p "$HOME/Library/LaunchAgents" "$WORKER_HOME/backend" "$WORKER_HOME/logs"

rsync -a --delete "$ROOT_DIR/backend/scripts/" "$WORKER_HOME/backend/scripts/"
rsync -a --delete "$ROOT_DIR/backend/app/" "$WORKER_HOME/backend/app/"
cp "$ROOT_DIR/scripts/run-embed-hot-corpus.sh" "$WORKER_HOME/run-embed-hot-corpus.sh"
chmod +x "$WORKER_HOME/run-embed-hot-corpus.sh"

cp "$SOURCE_PLIST" "$TARGET_PLIST"
launchctl unload "$TARGET_PLIST" 2>/dev/null || true
launchctl load "$TARGET_PLIST"

echo "installed: $(launchctl list | grep com.atlas.embed-hot-corpus || echo 'NOT LOADED')"
echo "next runs at 02:30 / 08:30 / 14:30 / 20:30; logs in $WORKER_HOME/logs/embed-hot-corpus.*.log"

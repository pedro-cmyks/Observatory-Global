#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="${ATLAS_REPO_DIR:-/Users/pedro/ObservatorioGlobal}"
WORKER_HOME="${ATLAS_LOCAL_WORKER_HOME:-/Users/pedro/AtlasLocalWorker}"
PLIST_NAME="com.atlas.emergent-snapshot.plist"
SOURCE_PLIST="$ROOT_DIR/infra/launchd/$PLIST_NAME"
TARGET_PLIST="$HOME/Library/LaunchAgents/$PLIST_NAME"
SOURCE_ENV="${ATLAS_SOURCE_ENV:-$ROOT_DIR/.env}"
TARGET_ENV="$WORKER_HOME/.env"
MODEL_DIR="$WORKER_HOME/models"
MODEL_NAME="2026-05-30-emergent-precision-gate-v1.json"
STUDENT_MODEL_NAME="2026-06-02-evidence-role-student-v1.json"

mkdir -p "$HOME/Library/LaunchAgents" "$WORKER_HOME/backend" "$WORKER_HOME/logs" "$MODEL_DIR"

rsync -a --delete "$ROOT_DIR/backend/scripts/" "$WORKER_HOME/backend/scripts/"
cp "$ROOT_DIR/scripts/run-emergent-snapshot.sh" "$WORKER_HOME/run-emergent-snapshot.sh"
chmod +x "$WORKER_HOME/run-emergent-snapshot.sh"

if [[ -f "$ROOT_DIR/docs/research/atlas-paper/phase-1-validation/models/$MODEL_NAME" ]]; then
  cp "$ROOT_DIR/docs/research/atlas-paper/phase-1-validation/models/$MODEL_NAME" "$MODEL_DIR/$MODEL_NAME"
fi

# Phase 6 dynamic_topics quality gate: deploy the evidence-role student model.
if [[ -f "$ROOT_DIR/docs/research/atlas-paper/phase-1-validation/models/$STUDENT_MODEL_NAME" ]]; then
  cp "$ROOT_DIR/docs/research/atlas-paper/phase-1-validation/models/$STUDENT_MODEL_NAME" "$MODEL_DIR/$STUDENT_MODEL_NAME"
fi

# Additive env merge: append only keys missing from the worker .env. Never
# clobber existing keys (the worker .env also holds OpenAI/Anthropic keys for
# the 3-vendor calibration cron).
umask 077
touch "$TARGET_ENV"
chmod 600 "$TARGET_ENV"
if [[ -r "$SOURCE_ENV" ]]; then
  for key in DATABASE_URL DEEPSEEK_API_KEY; do
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
launchctl enable "gui/$(id -u)/com.atlas.emergent-snapshot"

echo "Installed $PLIST_NAME"
echo "Worker home: $WORKER_HOME"
echo "Local env: $TARGET_ENV"

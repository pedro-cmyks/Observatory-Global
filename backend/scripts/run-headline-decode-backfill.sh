#!/usr/bin/env bash
set -euo pipefail

# Nightly HTML-entity headline decode backfill (one-time cleanup that is safe
# to leave installed).
#
# The write-side fix lives in ingest_v2.parse_gkg_row, so no NEW encoded rows
# are produced; this drains what was written before it. The job is naturally
# self-resuming and self-terminating: the SQL pre-filter only returns rows
# whose headline still matches the entity regex, so a re-run picks up exactly
# where the last one stopped, and once the corpus is clean it scans, finds
# nothing, and exits in seconds.
#
# Launchd runs this from /Users/pedro/AtlasLocalWorker (credentials live in
# that off-Desktop tree — macOS privacy controls block cron reads of the
# Desktop/iCloud path).

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if [[ -d "$SCRIPT_DIR/backend" ]]; then
  DEFAULT_ROOT_DIR="$SCRIPT_DIR"
else
  DEFAULT_ROOT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
fi

ROOT_DIR="${ATLAS_LOCAL_WORKER_DIR:-$DEFAULT_ROOT_DIR}"
BACKEND_DIR="$ROOT_DIR/backend"
LOG_DIR="${ATLAS_LOCAL_LOG_DIR:-$ROOT_DIR/logs}"
LOCAL_ENV="${ATLAS_LOCAL_ENV:-$ROOT_DIR/.env}"
VENV="${ATLAS_BACKEND_VENV:-/Users/pedro/Desktop/PEDRO/Cursos/ObservatorioGlobal/backend/.venv}"

BATCH="${ATLAS_HEADLINE_DECODE_BATCH:-2000}"
# Unbounded by default (drain to completion). Set a small value to smoke-test
# the wiring without committing to a full pass.
MAX_ROWS="${ATLAS_HEADLINE_DECODE_MAX_ROWS:-2000000}"
LEDGER="${ATLAS_HEADLINE_DECODE_LEDGER:-$LOG_DIR/headline-decode-ledger.jsonl}"

mkdir -p "$LOG_DIR"

# Credentials first — launchd's minimal env carries no DATABASE_URL, and a
# bare `set -u` abort here would leave no log at all (the 2026-06-29
# classifier-cron silent-death class).
if [[ -f "$LOCAL_ENV" ]]; then
  set -a
  # shellcheck disable=SC1090
  . "$LOCAL_ENV"
  set +a
fi

if [[ -z "${DATABASE_URL:-}" ]]; then
  echo "[headline-decode] DATABASE_URL missing (looked in $LOCAL_ENV)" >&2
  exit 2
fi

cd "$BACKEND_DIR"

echo "[headline-decode] start $(date -u +%FT%TZ) batch=$BATCH max_rows=$MAX_ROWS"

# Mindful: efficiency cores + nice, so a long drain never competes with
# foreground work. The job is DB-bound, but the discipline is the house rule.
taskpolicy -b nice -n 10 "$VENV/bin/python" \
  scripts/backfill_decode_headlines.py \
  --execute --batch "$BATCH" --max-rows "$MAX_ROWS" --ledger "$LEDGER"

echo "[headline-decode] done $(date -u +%FT%TZ)"

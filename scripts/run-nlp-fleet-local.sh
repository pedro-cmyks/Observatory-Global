#!/usr/bin/env bash
set -euo pipefail

# Launcher for the adaptive NLP-worker FLEET on the M1 (#184 throughput).
# Replaces the single-worker runner: this execs the fleet supervisor, which
# itself spawns/kills worker children based on machine idleness (1 mindful
# worker when Pedro is active, N parallel sharded workers when the box is idle).
#
# Same non-iCloud tree + mlvenv as run-nlp-worker-local.sh (macOS TCC blocks
# launchd from the Desktop/iCloud path). Versioned in repo at scripts/, executed
# from /Users/pedro/AtlasLocalWorker. Re-sync enrichment/ + both scripts on code
# changes.
WORKER_ROOT="${ATLAS_LOCAL_WORKER_DIR:-/Users/pedro/AtlasLocalWorker}"
BACKEND_DIR="${ATLAS_NLP_BACKEND_DIR:-$WORKER_ROOT/backend}"
VENV_PY="${ATLAS_NLP_VENV_PY:-$WORKER_ROOT/mlvenv/bin/python}"
LOCAL_ENV="${ATLAS_LOCAL_ENV:-$WORKER_ROOT/.env}"
LOG_DIR="${ATLAS_LOCAL_LOG_DIR:-$WORKER_ROOT/logs}"
SUPERVISOR="${ATLAS_NLP_SUPERVISOR:-$WORKER_ROOT/nlp_fleet_supervisor.py}"

export PATH="/usr/sbin:/usr/bin:/opt/homebrew/bin:/usr/local/bin:/bin:/sbin:${PATH:-}"
mkdir -p "$LOG_DIR"

# Credentials (DATABASE_URL) live in the stable, non-iCloud worker env.
if [[ -f "$LOCAL_ENV" ]]; then
  set -a; source "$LOCAL_ENV"; set +a
fi
: "${DATABASE_URL:?DATABASE_URL must be set (via $LOCAL_ENV)}"

# Fleet config (tunable; safe defaults). The supervisor reads these.
export NLP_FLEET_BURST_WORKERS="${ATLAS_NLP_BURST_WORKERS:-3}"
export NLP_FLEET_IDLE_SECONDS="${ATLAS_NLP_IDLE_SECONDS:-180}"
export NLP_FLEET_CHECK_SECONDS="${ATLAS_NLP_CHECK_SECONDS:-30}"
export NLP_FLEET_REQUIRE_AC="${ATLAS_NLP_REQUIRE_AC:-1}"
export NLP_FLEET_WORKER_LIMIT="${ATLAS_NLP_LIMIT:-300}"
export NLP_WORKER_INTERVAL_SECONDS="${ATLAS_NLP_INTERVAL:-15}"
export NLP_MULTILINGUAL_MODE="${ATLAS_NLP_MULTILINGUAL:-off}"
# Make the worker module importable from the backend tree.
export ATLAS_NLP_VENV_PY="$VENV_PY"
export ATLAS_NLP_BACKEND_DIR="$BACKEND_DIR"

cd "$BACKEND_DIR"
echo "[$(date '+%F %T')] starting M1 NLP fleet supervisor (burst=$NLP_FLEET_BURST_WORKERS idle>=${NLP_FLEET_IDLE_SECONDS}s)" >> "$LOG_DIR/nlp-fleet.out.log"

# The supervisor process is what launchd tracks; it owns the worker children and
# tears them down on SIGTERM. It is itself lightweight (probe + spawn loop), so
# it runs at normal priority — the workers carry their own QoS.
exec "$VENV_PY" "$SUPERVISOR"

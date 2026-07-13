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
# M1 is 8GB: each worker peaks ~1.5GB of models + the M1 also runs heavy ML crons
# (embed-hot-corpus, emergent-snapshot). 2 burst workers on the perf cores already
# clear ~8-10k/hr > ingest, draining the backlog when idle without OOM/swap risk.
# Bump via ATLAS_NLP_BURST_WORKERS only if free RAM proves comfortable.
export NLP_FLEET_BURST_WORKERS="${ATLAS_NLP_BURST_WORKERS:-2}"
export NLP_FLEET_IDLE_SECONDS="${ATLAS_NLP_IDLE_SECONDS:-180}"
export NLP_FLEET_CHECK_SECONDS="${ATLAS_NLP_CHECK_SECONDS:-30}"
export NLP_FLEET_REQUIRE_AC="${ATLAS_NLP_REQUIRE_AC:-1}"
export NLP_FLEET_WORKER_LIMIT="${ATLAS_NLP_LIMIT:-300}"
export NLP_WORKER_INTERVAL_SECONDS="${ATLAS_NLP_INTERVAL:-15}"
export NLP_MULTILINGUAL_MODE="${ATLAS_NLP_MULTILINGUAL:-off}"
# Batched NER measured 1,200 rows inside the M1 memory envelope. Keep the base
# sentiment/framing budget at 300; expanding every phase would erase the NER
# throughput gain and make the checkpoint lie about its mission.
export NLP_NER_LIMIT="${ATLAS_NLP_NER_LIMIT:-1200}"
# Batch 16 was measured on a representative 1,200-row mix (Davlan + Cyrillic +
# spaCy) at 1.07 GB max RSS with zero swaps. Keep the library/Fly default at 8;
# this larger batch is specific to the measured local M1 runtime.
export NLP_NER_BATCH_SIZE="${ATLAS_NLP_NER_BATCH_SIZE:-16}"
# Make the worker module importable from the backend tree.
export ATLAS_NLP_VENV_PY="$VENV_PY"
export ATLAS_NLP_BACKEND_DIR="$BACKEND_DIR"

cd "$BACKEND_DIR"
echo "[$(date '+%F %T')] starting M1 NLP fleet supervisor (burst=$NLP_FLEET_BURST_WORKERS idle>=${NLP_FLEET_IDLE_SECONDS}s)" >> "$LOG_DIR/nlp-fleet.out.log"

# The supervisor process is what launchd tracks; it owns the worker children and
# tears them down on SIGTERM. It is itself lightweight (probe + spawn loop), so
# it runs at normal priority — the workers carry their own QoS.
exec "$VENV_PY" "$SUPERVISOR"

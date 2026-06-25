#!/usr/bin/env bash
set -euo pipefail

# Continuous NLP enrichment worker on the M1 (#184).
#
# Why local: on Fly the worker shares one shared-cpu-2x/4GB machine + Python
# process with the embed service (semantic search). Per-cycle heavy model
# load/unload starved the embed thread (GIL/CPU contention) → /research/plan
# timed out. The M1 is far more capable and has no embed to starve, so NER moves
# here; the Fly box keeps the embed service and only the lightweight fast-lane.
#
# "Mindful" continuous daemon (Pedro): runs under macOS BACKGROUND QoS via
# `taskpolicy -b` → scheduled onto the EFFICIENCY cores (not the performance
# cores foreground work uses) + low I/O priority, plus `nice`. So it runs all
# day but yields to whatever Pedro is doing. launchd KeepAlive restarts it if it
# dies; the worker itself loops (interval below).

# Runs from the NON-iCloud AtlasLocalWorker tree (macOS TCC blocks launchd from
# the Desktop/iCloud path). The repo's enrichment/ is synced there and the heavy
# deps live in mlvenv. Keep this script in sync: it is versioned in the repo at
# scripts/ but executed from /Users/pedro/AtlasLocalWorker.
WORKER_ROOT="${ATLAS_LOCAL_WORKER_DIR:-/Users/pedro/AtlasLocalWorker}"
BACKEND_DIR="${ATLAS_NLP_BACKEND_DIR:-$WORKER_ROOT/backend}"
VENV_PY="${ATLAS_NLP_VENV_PY:-$WORKER_ROOT/mlvenv/bin/python}"
LOCAL_ENV="${ATLAS_LOCAL_ENV:-$WORKER_ROOT/.env}"
LOG_DIR="${ATLAS_LOCAL_LOG_DIR:-$WORKER_ROOT/logs}"

export PATH="/usr/sbin:/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/sbin:${PATH:-}"
mkdir -p "$LOG_DIR"

# Credentials (DATABASE_URL) live in the stable, non-iCloud worker env.
if [[ -f "$LOCAL_ENV" ]]; then
  set -a; source "$LOCAL_ENV"; set +a
fi
: "${DATABASE_URL:?DATABASE_URL must be set (via $LOCAL_ENV)}"

# Worker config. Sentiment fast-lane stays on Fly (already 100%); the M1 owns
# the full NLP / NER pass. Multilingual defaults off for the first rollout
# (proven EN throughput ~5.4k/hr on M1 CPU); flip ATLAS_NLP_MULTILINGUAL=on
# once the daemon is stable to verify non-English subjects too.
export NLP_MULTILINGUAL_MODE="${ATLAS_NLP_MULTILINGUAL:-off}"
export NLP_WORKER_LIMIT="${ATLAS_NLP_LIMIT:-300}"
export NLP_WORKER_INTERVAL_SECONDS="${ATLAS_NLP_INTERVAL:-30}"
# Fly owns the light sentiment fast-lane (100% coverage) + the embed service;
# the M1 owns only the heavy NER. (env names match nlp_worker.py exactly.)
export NLP_FAST_LANE_ENABLED="${ATLAS_NLP_FAST_LANE:-false}"
export NLP_WORKER_NER_ENABLED="true"
export EMBED_SERVICE_ENABLED="false"
export NLP_WORKER_ID="m1-local"

cd "$BACKEND_DIR"
echo "[$(date '+%F %T')] starting M1 NLP worker (limit=$NLP_WORKER_LIMIT interval=${NLP_WORKER_INTERVAL_SECONDS}s multilingual=$NLP_MULTILINGUAL_MODE)" >> "$LOG_DIR/nlp-worker.out.log"

# Background QoS (efficiency cores) + nice. exec so launchd tracks the python pid.
exec /usr/bin/nice -n 10 /usr/sbin/taskpolicy -b \
  "$VENV_PY" -m enrichment.nlp_worker --limit "$NLP_WORKER_LIMIT"

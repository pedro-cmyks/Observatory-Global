#!/usr/bin/env bash
# Nightly gold-growth accumulator runner (launchd com.atlas.goldgrowth, 03:30).
# API-bound (DeepSeek + OpenAI labels, ~$0.10-0.30/night), CPU-trivial.
# VERSIONED REFERENCE COPY — the live copy executes from
# /Users/pedro/AtlasLocalWorker/run-goldgrowth-accumulator.sh; re-sync
# backend/scripts/{goldgrowth_accumulate,llm_annotator,build_goldgrowth_corpus}.py
# into the AtlasLocalWorker tree on changes.
set -uo pipefail

ALW=/Users/pedro/AtlasLocalWorker
MLVENV="${ATLAS_MLVENV:-$ALW/mlvenv}"
BACKEND="${ATLAS_BACKEND_DIR:-$ALW/backend}"
LOG_DIR="$ALW/logs"
mkdir -p "$LOG_DIR"

# P1.1 heavy-job mutex: API-bound but writes the DB — serialize with the rest
# of the nightly fleet. (Payload is invoked WITHOUT exec so the EXIT trap can
# release the lock.)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if [ -r "$SCRIPT_DIR/heavy-job-lock.sh" ]; then
  . "$SCRIPT_DIR/heavy-job-lock.sh"
  # 180m wait (era 120): con el release post-fold del M4 (~03:15) el fire de
  # 00:50 alcanza a agarrar turno; a 120m se rendía a las 02:50, 25min corto.
  atlas_heavy_lock "goldgrowth" wait 120 180 || exit 0
else
  echo "[goldgrowth] heavy-job-lock.sh missing — running UNSERIALIZED" >&2
fi

# launchd has a minimal env — source the local .env for DATABASE_URL + API keys
set -a
# shellcheck disable=SC1091
[ -f "$ALW/.env" ] && . "$ALW/.env"
set +a

for var in DATABASE_URL DEEPSEEK_API_KEY OPENAI_API_KEY; do
  if [ -z "${!var:-}" ]; then
    echo "[goldgrowth] $var missing — abort" >&2
    exit 1
  fi
done

cd "$BACKEND" || exit 1
# No exec: exec replaces the shell and the heavy-lock EXIT trap never fires.
nice -n 15 "$MLVENV/bin/python" scripts/goldgrowth_accumulate.py \
  >> "$LOG_DIR/goldgrowth-accumulator.log" 2>&1

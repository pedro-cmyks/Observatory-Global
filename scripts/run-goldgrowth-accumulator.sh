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
exec nice -n 15 "$MLVENV/bin/python" scripts/goldgrowth_accumulate.py \
  >> "$LOG_DIR/goldgrowth-accumulator.log" 2>&1

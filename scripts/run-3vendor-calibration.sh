#!/usr/bin/env bash
set -euo pipefail

# Daily 3-vendor calibration runner.
#
# Samples a small fresh atlas-v2 topic-benchmark slice, has three LLM
# annotators (deepseek-chat, gpt-4.1, claude-sonnet-4-6) judge each
# assignment, and computes inter-annotator agreement (Cohen/Fleiss kappa).
# The point is drift monitoring: a daily kappa datapoint that flags when
# the vendor panel stops agreeing, so the benchmark gold stays trustworthy.
#
# Launchd runs this from /Users/pedro/AtlasLocalWorker. All credentials live
# in that off-Desktop runtime (.env, mode 600) so macOS privacy controls do
# not block cron reads, and the venv is off iCloud.

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if [[ -d "$SCRIPT_DIR/backend" ]]; then
  ROOT_DIR="$SCRIPT_DIR"
else
  ROOT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
fi

BACKEND_DIR="${ATLAS_CALIB_BACKEND:-$ROOT_DIR/backend}"
LOG_DIR="${ATLAS_LOCAL_LOG_DIR:-$ROOT_DIR/logs}"
OUT_DIR="${ATLAS_CALIB_OUT:-$ROOT_DIR/calibration}"
PYBIN="${ATLAS_CALIB_PY:-/Users/pedro/AtlasLocalWorker/atlasvenv/bin/python}"
LOCAL_ENV="${ATLAS_LOCAL_ENV:-$ROOT_DIR/.env}"

PER_BUCKET="${ATLAS_CALIB_PER_BUCKET:-2}"
HOURS="${ATLAS_CALIB_HOURS:-24}"

export PATH="/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin:${PATH:-}"
export HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1
mkdir -p "$LOG_DIR" "$OUT_DIR"

load_env_file() {
  local env_file="$1" key value
  [[ -r "$env_file" ]] || return 0
  for key in DATABASE_URL DEEPSEEK_API_KEY OPENAI_API_KEY ANTHROPIC_API_KEY \
             ATLAS_CLAUDE_CLI ATLAS_CLAUDE_CLI_BIN ATLAS_ANNOTATOR_CLI_MODEL; do
    if [[ -z "${!key:-}" ]]; then
      value="$(grep -E "^${key}=" "$env_file" | tail -n 1 | sed -E "s/^${key}=//" | tr -d '\r' || true)"
      [[ -n "$value" ]] && export "$key=$value"
    fi
  done
}
load_env_file "$LOCAL_ENV"

for key in DATABASE_URL DEEPSEEK_API_KEY OPENAI_API_KEY; do
  if [[ -z "${!key:-}" ]]; then
    echo "$(date -u +%FT%TZ) FATAL: $key not set" >&2
    exit 2
  fi
done

# Anthropic leg = the claude CLI subscription (2026-07-29: API not re-funded).
# ANTHROPIC_API_KEY only matters as the fallback when the CLI leg is off.
if [[ "${ATLAS_CLAUDE_CLI:-off}" != "on" && -z "${ANTHROPIC_API_KEY:-}" ]]; then
  echo "$(date -u +%FT%TZ) FATAL: neither ATLAS_CLAUDE_CLI=on nor ANTHROPIC_API_KEY set" >&2
  exit 2
fi

DATE="$(date -u +%F)"
SAMPLE="$OUT_DIR/$DATE-calib-sample.jsonl"
AGREE_JSON="$OUT_DIR/$DATE-calib-agreement.json"
AGREE_MD="$OUT_DIR/$DATE-calib-agreement.md"

cd "$BACKEND_DIR"

echo "$(date -u +%FT%TZ) sampling benchmark slice (hours=$HOURS per_bucket=$PER_BUCKET)"
"$PYBIN" scripts/topic_benchmark_harness.py sample \
  --hours "$HOURS" --per-bucket "$PER_BUCKET" --output "$SAMPLE"

SOURCES=()
for vendor in deepseek openai anthropic; do
  case "$vendor" in
    deepseek)  model="deepseek-chat" ;;
    openai)    model="gpt-4.1" ;;
    anthropic) model="claude-sonnet-4-6" ;;
  esac
  out="$OUT_DIR/$DATE-$vendor.jsonl"
  echo "$(date -u +%FT%TZ) annotating with $model"
  "$PYBIN" scripts/llm_annotator.py \
    --input "$SAMPLE" --output "$out" \
    --model "$model" --provenance "${vendor}_calib" --resume
  SOURCES+=( "$vendor:annotator_decision:$out" )
done

echo "$(date -u +%FT%TZ) computing agreement"
"$PYBIN" scripts/multi_annotator_agreement.py \
  --source "${SOURCES[@]}" \
  --output-json "$AGREE_JSON" --output-md "$AGREE_MD"

echo "$(date -u +%FT%TZ) calibration done -> $AGREE_JSON"

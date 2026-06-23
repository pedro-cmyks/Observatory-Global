#!/usr/bin/env bash
set -euo pipefail

# Emergent topic snapshot runner.
#
# Launchd runs this from /Users/pedro/AtlasLocalWorker. Keep all credentials
# in that off-Desktop runtime so macOS privacy controls do not block cron reads.

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if [[ -d "$SCRIPT_DIR/backend" ]]; then
  DEFAULT_ROOT_DIR="$SCRIPT_DIR"
else
  DEFAULT_ROOT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
fi

ROOT_DIR="${ATLAS_LOCAL_WORKER_DIR:-$DEFAULT_ROOT_DIR}"
BACKEND_DIR="$ROOT_DIR/backend"
LOG_DIR="${ATLAS_LOCAL_LOG_DIR:-$ROOT_DIR/logs}"
MLVENV="${ATLAS_MLVENV:-/Users/pedro/AtlasLocalWorker/mlvenv}"
GATE_JSON="${ATLAS_EMERGENT_GATE:-/Users/pedro/AtlasLocalWorker/models/2026-05-30-emergent-precision-gate-v1.json}"
STUDENT_JSON="${ATLAS_EVIDENCE_STUDENT:-/Users/pedro/AtlasLocalWorker/models/2026-06-02-evidence-role-student-v1.json}"
LOCAL_ENV="${ATLAS_LOCAL_ENV:-$ROOT_DIR/.env}"
FLY_APP="${ATLAS_FLY_APP:-atlas-api-pedro}"

WINDOW_HOURS="${ATLAS_EMERGENT_WINDOW_HOURS:-24}"
# #229: cluster over the persisted signal_embeddings corpus, stratified for
# non-English voice. Higher cap (no re-embed = the cost is HDBSCAN, not e5).
MAX_SIGNALS="${ATLAS_EMERGENT_MAX_SIGNALS:-25000}"
MIN_CLUSTER_SIZE="${ATLAS_EMERGENT_MIN_CLUSTER_SIZE:-20}"
MIN_SAMPLES="${ATLAS_EMERGENT_MIN_SAMPLES:-10}"
TOP_CLUSTERS="${ATLAS_EMERGENT_TOP_CLUSTERS:-30}"
NONENGLISH_CAP="${ATLAS_EMERGENT_NONENGLISH_CAP:-7000}"
# --from-persisted on by default (#229); set ATLAS_EMERGENT_FROM_PERSISTED=0 to
# fall back to the legacy latest-15K re-embed path.
FROM_PERSISTED="${ATLAS_EMERGENT_FROM_PERSISTED:-1}"
PERSISTED_FLAGS=()
if [[ "$FROM_PERSISTED" == "1" ]]; then
  PERSISTED_FLAGS=(--from-persisted --nonenglish-cap "$NONENGLISH_CAP")
fi

export PATH="/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin:${PATH:-}"
mkdir -p "$LOG_DIR"

load_env_file() {
  local env_file="$1"
  [[ -r "$env_file" ]] || return 0

  local key value
  for key in DATABASE_URL DEEPSEEK_API_KEY; do
    if [[ -z "${!key:-}" ]]; then
      value="$(grep -E "^${key}=" "$env_file" | tail -n 1 | sed -E "s/^${key}=//" | tr -d '\r' || true)"
      if [[ -n "$value" ]]; then
        export "$key=$value"
      fi
    fi
  done
}

load_env_file "$LOCAL_ENV"

# Explicit manual escape hatch for interactive debugging only. It is disabled
# for launchd by default because Desktop paths are privacy-protected.
if [[ "${ATLAS_ALLOW_DESKTOP_ENV:-0}" == "1" ]]; then
  load_env_file "${ATLAS_DEBUG_ENV_PATH:-/Users/pedro/Desktop/PEDRO/Cursos/ObservatorioGlobal/.env}"
fi

if [[ -z "${DATABASE_URL:-}" ]]; then
  DATABASE_URL="$(
    fly ssh console -a "$FLY_APP" --pty=false -C 'printenv DATABASE_URL' 2>/dev/null \
      | tail -n 1 \
      | tr -d '\r'
  )"
  export DATABASE_URL
fi

if [[ -z "${DATABASE_URL:-}" || -z "${DEEPSEEK_API_KEY:-}" ]]; then
  echo "[emergent-snapshot] missing DATABASE_URL or DEEPSEEK_API_KEY; install $LOCAL_ENV" >&2
  exit 2
fi

if [[ ! -x "$MLVENV/bin/python" ]]; then
  echo "[emergent-snapshot] mlvenv python not found at $MLVENV" >&2
  exit 2
fi

if [[ ! -f "$GATE_JSON" ]]; then
  echo "[emergent-snapshot] gate artifact missing: $GATE_JSON" >&2
  exit 2
fi

cd "$ROOT_DIR"

"$MLVENV/bin/python" -m backend.scripts.snapshot_emergent_topics \
  --window-hours "$WINDOW_HOURS" \
  --max-signals "$MAX_SIGNALS" \
  --min-cluster-size "$MIN_CLUSTER_SIZE" \
  --min-samples "$MIN_SAMPLES" \
  --top-clusters "$TOP_CLUSTERS" \
  --gate "$GATE_JSON" \
  "${PERSISTED_FLAGS[@]}" \
  "$@"

# Phase 6: fold the just-written snapshot into the dynamic_topics lifecycle.
# Incremental + idempotent + $0 API (local student/e5; per-cluster noise cached
# once). Guarded so a lifecycle failure never fails the snapshot cron.
if [[ -f "$STUDENT_JSON" ]]; then
  ( cd "$BACKEND_DIR" && "$MLVENV/bin/python" -m scripts.project_dynamic_topics \
      --student-model "$STUDENT_JSON" ) \
    || echo "[emergent-snapshot] dynamic_topics projection failed (non-fatal)" >&2
else
  echo "[emergent-snapshot] student model missing ($STUDENT_JSON); skipping dynamic_topics" >&2
fi

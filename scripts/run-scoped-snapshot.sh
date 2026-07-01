#!/usr/bin/env bash
set -uo pipefail   # NOT -e: a country/label hiccup must not abort the whole run

# R1 — scoped per-country emergent snapshot runner (#229). REPLACES the global
# com.atlas.emergent-snapshot (scoped is a superset: ~5.4× recall, ~54× more
# narratives, measured). Forms scoped topics for ALL countries under ONE snapshot,
# then projects into dynamic_topics (serving). MINDFUL (taskpolicy -b, efficiency
# cores) + heavy (~1–1.5h) → schedule ONCE nightly, off-peak, in the embed gaps.
# Launchd runs this from /Users/pedro/AtlasLocalWorker.

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if [[ -d "$SCRIPT_DIR/backend" ]]; then DEFAULT_ROOT_DIR="$SCRIPT_DIR"; else DEFAULT_ROOT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"; fi
ROOT_DIR="${ATLAS_LOCAL_WORKER_DIR:-$DEFAULT_ROOT_DIR}"
BACKEND_DIR="$ROOT_DIR/backend"
LOG_DIR="${ATLAS_LOCAL_LOG_DIR:-$ROOT_DIR/logs}"
MLVENV="${ATLAS_MLVENV:-/Users/pedro/AtlasLocalWorker/mlvenv}"
GATE_JSON="${ATLAS_EMERGENT_GATE:-/Users/pedro/AtlasLocalWorker/models/2026-05-30-emergent-precision-gate-v1.json}"
STUDENT_JSON="${ATLAS_EVIDENCE_STUDENT:-/Users/pedro/AtlasLocalWorker/models/2026-06-02-evidence-role-student-v1.json}"
LOCAL_ENV="${ATLAS_LOCAL_ENV:-$ROOT_DIR/.env}"

MIN_EMBEDDED="${ATLAS_SCOPED_MIN_EMBEDDED:-100}"
TOP_PER_COUNTRY="${ATLAS_SCOPED_TOP_PER_COUNTRY:-25}"
PER_COUNTRY_CAP="${ATLAS_SCOPED_CAP:-6000}"

export PATH="/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin:${PATH:-}"
mkdir -p "$LOG_DIR"

for key in DATABASE_URL DEEPSEEK_API_KEY; do
  if [[ -z "${!key:-}" && -r "$LOCAL_ENV" ]]; then
    v="$(grep -E "^${key}=" "$LOCAL_ENV" | tail -n 1 | sed -E "s/^${key}=//" | tr -d '\r' || true)"
    [[ -n "$v" ]] && export "$key=$v"
  fi
done
if [[ -z "${DATABASE_URL:-}" || -z "${DEEPSEEK_API_KEY:-}" ]]; then
  echo "[scoped-snapshot] missing DATABASE_URL or DEEPSEEK_API_KEY" >&2; exit 2
fi

TASKPOLICY=""
command -v taskpolicy >/dev/null 2>&1 && TASKPOLICY="taskpolicy -b"

# Step 1: form + write the scoped snapshot (all countries, one snapshot_at).
cd "$ROOT_DIR"
$TASKPOLICY "$MLVENV/bin/python" -m backend.scripts.run_scoped_snapshot \
  --min-embedded "$MIN_EMBEDDED" --top-per-country "$TOP_PER_COUNTRY" \
  --per-country-cap "$PER_COUNTRY_CAP" --gate "$GATE_JSON" \
  || echo "[scoped-snapshot] R1 write failed" >&2

# Step 2: fold the just-written snapshot into dynamic_topics (serving) with the
# #224 anchor-guard + the retire/age lifecycle. Non-fatal.
if [[ -f "$STUDENT_JSON" ]]; then
  ( cd "$BACKEND_DIR" && $TASKPOLICY "$MLVENV/bin/python" -m scripts.project_dynamic_topics \
      --student-model "$STUDENT_JSON" ) \
    || echo "[scoped-snapshot] dynamic_topics projection failed (non-fatal)" >&2
else
  echo "[scoped-snapshot] student model missing ($STUDENT_JSON) — skip projection" >&2
fi

#!/usr/bin/env bash
set -euo pipefail

# Atlas topic v2 incremental classifier runner.
#
# VERSIONED REFERENCE COPY (added 2026-06-30 at track consolidation). The LIVE
# copy executes from /Users/pedro/AtlasLocalWorker/run-atlas-topic-classifier.sh
# (TCC-allowed, non-iCloud) via launchd com.atlas.atlas-topic-classifier.plist
# every 30 min. That copy was previously UN-VERSIONED — its Step 3 (#204 v2
# reject) was not recoverable from git. This is the canonical reference; on any
# engine-code change, re-sync this + backend/scripts/ensemble/apply_v2_reject.py
# + backend/models/v2_gate.json into the AtlasLocalWorker tree.
#
# Step 1: backfill_lexicon_topics over the last 0.5h so fresh signals get
#   atlas-topic assignments before the briefing API serves them.
# Step 2: score_assignments_gate.py (off-iCloud mlvenv) applies the scope gate
#   (keep/abstain at >=90% precision).
# Step 3: apply_v2_reject (#204) demotes theme-hint-lex-v2 gate_kept rows the v2
#   e5 gate scores OUT_OF_SCOPE — flag-gated (ATLAS_V2_GATE_ENABLED) + reversible
#   (tags gate_model=v2-gate-e5-lr-1). All steps idempotent.
# Step 4: compute_category_typing --only-untyped (R3.1 §3.1: category typing runs
#   on THIS 30-min cron, not nightly, so fresh stories get their badge within a
#   cycle — the nightly scoped-snapshot pass remains the full sweep + emergent
#   clustering). DeepSeek-only (no torch load); steady-state = 0 API calls.

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if [[ -d "$SCRIPT_DIR/backend" ]]; then
  DEFAULT_ROOT_DIR="$SCRIPT_DIR"
else
  DEFAULT_ROOT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
fi
ROOT_DIR="${ATLAS_REPO_DIR:-$DEFAULT_ROOT_DIR}"
BACKEND_DIR="$ROOT_DIR/backend"
FLY_APP="${ATLAS_FLY_APP:-atlas-api-pedro}"
LOG_DIR="${ATLAS_LOCAL_LOG_DIR:-$ROOT_DIR/logs}"
WINDOW_HOURS="${ATLAS_TOPIC_WINDOW_HOURS:-0.5}"
MLVENV="${ATLAS_MLVENV:-/Users/pedro/AtlasLocalWorker/mlvenv}"
GATE_JSON="${ATLAS_GATE_JSON:-/Users/pedro/AtlasLocalWorker/models/2026-05-29-scope-gate-v1-e5base.json}"
GATE_WINDOW_HOURS="${ATLAS_GATE_WINDOW_HOURS:-1}"

export PATH="/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin:${PATH:-}"

mkdir -p "$LOG_DIR"

# launchd runs with a minimal environment (no DATABASE_URL). Source the local
# .env FIRST so the cron is self-sufficient — otherwise the fly-ssh fallback
# below runs, and under `set -euo pipefail` a failed `fly ssh` (no auth/network
# under launchd, e.g. after a power outage) ABORTS the script before python with
# no log output (the observed runs=8 / exit 1 / silent-since-outage failure).
ENV_FILE="${ATLAS_ENV_FILE:-$SCRIPT_DIR/.env}"
if [[ -z "${DATABASE_URL:-}" && -z "${SUPABASE_DB_URL:-}" && -f "$ENV_FILE" ]]; then
  set -a
  # shellcheck disable=SC1090
  source "$ENV_FILE"
  set +a
fi

if [[ -z "${DATABASE_URL:-}" && -z "${SUPABASE_DB_URL:-}" ]]; then
  # Last-resort fallback; tolerate failure so a flaky fly-ssh never aborts the
  # whole run (pipefail-safe) — python will surface a clear connect error if the
  # URL is still empty.
  DATABASE_URL="$(
    fly ssh console -a "$FLY_APP" --pty=false -C 'printenv DATABASE_URL' 2>/dev/null \
      | tail -n 1 \
      | tr -d '\r'
  )" || true
  export DATABASE_URL
fi

cd "$BACKEND_DIR"

# Step 1: lexicon topic assignments (fresh signals → atlas topics).
.venv/bin/python -m scripts.backfill_lexicon_topics \
  --window-hours "$WINDOW_HOURS" \
  "$@"

# Step 2: scope-gate scoring (keep/abstain at >=90% precision) on the off-iCloud
# mlvenv (torch + transformers + asyncpg, MPS). Idempotent: scores only rows with
# gate_score IS NULL, so the overlapping 30-min window stays cheap. --window-hours
# is an int (0.5 would error) — 1h safely covers the cadence. Non-fatal so a gate
# hiccup never blocks topic assignment.
if [[ -x "$MLVENV/bin/python" && -f "$GATE_JSON" ]]; then
  "$MLVENV/bin/python" "$BACKEND_DIR/scripts/score_assignments_gate.py" \
    --window-hours "$GATE_WINDOW_HOURS" \
    --gate "$GATE_JSON" \
    || echo "[atlas-topic] scope-gate scoring failed (non-fatal)" >&2
else
  echo "[atlas-topic] skip scope-gate: mlvenv or gate JSON missing ($MLVENV / $GATE_JSON)" >&2
fi

# Step 3: v2 force-fit reject (#204) — demote theme-hint-lex-v2 gate_kept rows the
# v2 e5 gate scores OUT_OF_SCOPE. Numpy-only on mlvenv, $0 (vec already persisted),
# flag-gated + reversible (tags gate_model=v2-gate-e5-lr-1). Query sees only
# gate_kept=true so re-runs are idempotent. Non-fatal.
V2_GATE_JSON="${ATLAS_V2_GATE_JSON:-/Users/pedro/AtlasLocalWorker/models/v2_gate.json}"
if [[ "${ATLAS_V2_GATE_ENABLED:-}" == "true" && -x "$MLVENV/bin/python" && -f "$V2_GATE_JSON" ]]; then
  ATLAS_V2_GATE_JSON="$V2_GATE_JSON" ATLAS_V2_GATE_ENABLED=true \
    "$MLVENV/bin/python" -m scripts.ensemble.apply_v2_reject \
      --apply --hours "${ATLAS_V2_GATE_REJECT_HOURS:-2}" \
      --threshold "${ATLAS_V2_GATE_THRESHOLD:-0.5}" \
    || echo "[atlas-topic] v2 reject failed (non-fatal)" >&2
else
  echo "[atlas-topic] skip v2 reject (ATLAS_V2_GATE_ENABLED!=true or json missing)" >&2
fi

# Step 4: R3.1 incremental category typing (spec §3.1 mandates the 30-min cadence —
# nightly-only typing recreates the badge asymmetry as a TEMPORAL one, F-C4.2).
# --only-untyped: types ONLY topics with crisis_class IS NULL (new since the last
# pass), so steady-state is a single cheap SELECT and 0 DeepSeek calls. Runs from
# ROOT_DIR (module path backend.scripts.*, candidate-v2.json relative). Non-fatal.
if [[ -n "${DEEPSEEK_API_KEY:-}" && -x "$MLVENV/bin/python" ]]; then
  ( cd "$ROOT_DIR" && "$MLVENV/bin/python" -m backend.scripts.compute_category_typing \
      --deepseek --write --only-untyped ) \
    || echo "[atlas-topic] category typing failed (non-fatal)" >&2
else
  echo "[atlas-topic] skip category typing (DEEPSEEK_API_KEY or mlvenv missing)" >&2
fi

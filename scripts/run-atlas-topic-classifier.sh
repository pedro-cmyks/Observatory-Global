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
# Step 5: label_court --only-unchecked (council R2 N2: the nightly-only court
#   left 31/37 served threads unstamped incl. ALL leads — new topics promote and
#   serve BEFORE the nightly judgment; with lead-eligibility-v2 an unstamped
#   thread cannot lead, so the stamp must land on the SAME cadence topics are
#   promoted on). Bounded --limit 40 catches every newly-promoted topic within
#   one cycle; steady-state = 0 DeepSeek calls (~cents when it fires).

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
# Scope gate: OpenAI text-embedding-3-small variant (2026-07-04) — the bake-off
# proved it beats every local embedder (recall 0.843 vs e5base 0.749 @90% prec;
# hard topics lift huge). Needs OPENAI_API_KEY (sourced from .env below).
# REVERSIBLE: set ATLAS_GATE_JSON back to the -e5base.json + ATLAS_GATE_ID to
# atlas-scope-gate-v1-e5base for the free local path.
GATE_JSON="${ATLAS_GATE_JSON:-/Users/pedro/AtlasLocalWorker/models/2026-07-05-scope-gate-v4-mega2.json}"
GATE_ID="${ATLAS_GATE_ID:-atlas-scope-gate-v4-mega2}"
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

# ─── silent-failure guard (2026-07-27) ───────────────────────────────────────
# WHY: every LLM step below used to end in `|| echo '(non-fatal)' >&2`, so a
# provider outage (DeepSeek 402 / Anthropic credit exhaustion) produced a run
# that STILL EXITED 0 — launchd recorded success, the freshness watchdog read
# healthy, and the front page went stale for FOUR nights with nobody alerted.
# The pipeline converted failure into a plausible success.
#
# atlas_step keeps the "one broken step must not abort the rest of the run"
# behaviour, but CLASSIFIES the failure instead of swallowing it:
#   - ordinary/transient error  -> logged, counted, run continues
#   - PROVIDER EXHAUSTION       -> one PROVIDER_EXHAUSTED line to the shared
#     reliability ledger (same file the SEAL_FAILED alert + freshness watchdog
#     use) and the RUN exits non-zero at the end, so launchd records a failure.
# A run where MORE THAN HALF the guarded steps failed also exits non-zero.
ATLAS_ALERT_TAG="${ATLAS_ALERT_TAG:-atlas-topic}"
ATLAS_RELIABILITY_ALERTS_LOG="${ATLAS_RELIABILITY_ALERTS_LOG:-$HOME/AtlasLocalWorker/logs/reliability-alerts.log}"
_ATLAS_STEPS_ATTEMPTED=0
_ATLAS_STEPS_FAILED=0
_ATLAS_PROVIDER_EXHAUSTED=0
_ATLAS_FAILED_LABELS=""
_ATLAS_LAST_STEP_RC=0   # callers that need their own alert (seal) read this
# Providers refuse in a handful of dialects. Keep this TIGHT: exhaustion is
# fatal, so a bare "402" appearing in ordinary output (row counts, ids) must
# never trip it — 402 only matches when preceded by an http/status/code/error
# token.
_ATLAS_EXHAUSTED_RE='payment required|credit balance is too low|insufficient balance|insufficient_quota|quota exceeded|(http|status|code|error)[^0-9a-z]{0,8}402([^0-9]|$)'

atlas_alert() {  # ONE dated line to the shared reliability ledger + stderr
  local line
  line="$(date '+%Y-%m-%d %H:%M:%S') [$ATLAS_ALERT_TAG] $*"
  echo "$line" >&2
  mkdir -p "$(dirname "$ATLAS_RELIABILITY_ALERTS_LOG")" 2>/dev/null || true
  echo "$line" >> "$ATLAS_RELIABILITY_ALERTS_LOG" 2>/dev/null || true
}

# atlas_step <label> <cwd> <command...>
atlas_step() {
  local label="$1" cwd="$2"; shift 2
  local tmp rc had_e=0
  case "$-" in *e*) had_e=1 ;; esac
  tmp="$(mktemp -t atlas-step 2>/dev/null || echo "/tmp/atlas-step.$$")"
  _ATLAS_STEPS_ATTEMPTED=$((_ATLAS_STEPS_ATTEMPTED + 1))
  set +e
  # PYTHONUNBUFFERED so tee'ing through a pipe does not block-buffer a long
  # step's logs (the launchd log must stay live, not arrive at step end).
  ( cd "$cwd" && export PYTHONUNBUFFERED=1 && "$@" ) 2>&1 | tee "$tmp" >&2
  rc=${PIPESTATUS[0]}
  [ "$had_e" -eq 1 ] && set -e
  _ATLAS_LAST_STEP_RC="$rc"
  if [ "$rc" -ne 0 ]; then
    _ATLAS_STEPS_FAILED=$((_ATLAS_STEPS_FAILED + 1))
    _ATLAS_FAILED_LABELS="$_ATLAS_FAILED_LABELS $label"
    if grep -qiE "$_ATLAS_EXHAUSTED_RE" "$tmp" 2>/dev/null; then
      # Ledger the FIRST exhaustion only: when the provider is dry every LLM
      # step fails, and 6 identical lines is the ledger spam that hid the real
      # SEAL_FAILED alerts. The run verdict below names the full failed set.
      if [ "$_ATLAS_PROVIDER_EXHAUSTED" -eq 0 ]; then
        atlas_alert "PROVIDER_EXHAUSTED step=$label rc=$rc — LLM provider refused (payment/credit); this step produced NOTHING"
      else
        echo "[$ATLAS_ALERT_TAG] $label also hit provider exhaustion (rc=$rc)" >&2
      fi
      _ATLAS_PROVIDER_EXHAUSTED=1
    else
      echo "[$ATLAS_ALERT_TAG] $label failed (rc=$rc, non-fatal — run continues)" >&2
    fi
  fi
  rm -f "$tmp" 2>/dev/null || true
  return 0
}

atlas_run_verdict() {
  if [ "$_ATLAS_PROVIDER_EXHAUSTED" -eq 1 ]; then
    atlas_alert "RUN_FAILED provider exhausted — ${_ATLAS_STEPS_FAILED}/${_ATLAS_STEPS_ATTEMPTED} guarded steps failed (${_ATLAS_FAILED_LABELS# }); exiting non-zero so launchd records the failure"
    exit 1
  fi
  # >half = systemic breakdown, not a hiccup. The >=2 floor keeps ONE ordinary
  # transient error non-fatal (1/1 is technically "> half"): turning every
  # flake into a launchd failure rebuilds the alert fatigue this fix exists to
  # kill. A single step that is genuinely exhausted still exits above.
  if [ "$_ATLAS_STEPS_ATTEMPTED" -ge 2 ] \
     && [ "$((_ATLAS_STEPS_FAILED * 2))" -gt "$_ATLAS_STEPS_ATTEMPTED" ]; then
    atlas_alert "RUN_FAILED ${_ATLAS_STEPS_FAILED}/${_ATLAS_STEPS_ATTEMPTED} guarded steps failed (>half:${_ATLAS_FAILED_LABELS# }); exiting non-zero so launchd records the failure"
    exit 1
  fi
  exit 0
}

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
  atlas_step "scope-gate scoring" "$BACKEND_DIR" \
    "$MLVENV/bin/python" "$BACKEND_DIR/scripts/score_assignments_gate.py" \
    --window-hours "$GATE_WINDOW_HOURS" \
    --gate "$GATE_JSON" \
    --gate-id "$GATE_ID"
else
  echo "[atlas-topic] skip scope-gate: mlvenv or gate JSON missing ($MLVENV / $GATE_JSON)" >&2
fi

# Step 2b (2026-07-04, semantic assignment lane): a SECOND candidate lane —
# argmax anchor-cosine in OpenAI space with WILD-calibrated per-topic taus
# (docs/research/semantic-lane/2026-07-04-tau-sem-wild.md; e5 absolute cosine
# FAILED the noise floor and was rejected). Writes method='embedding',
# model_version='sem-assign-v0'; the gate then grades that lane like any
# candidate (--lane semantic). ~$0.001/cycle at a 1h window. Flag-gated +
# non-fatal. Reverse: ATLAS_SEM_LANE_ENABLED=false (existing rows are
# distinguishable by model_version; two-tier serving already labels them).
# Config lives in the TCC-allowed ALW tree (launchd cannot read Desktop/iCloud);
# re-sync from repo docs/research/semantic-lane + docs/research/taxonomy-revision
# whenever the calibration or taxonomy changes.
SEM_CALIB="${ATLAS_SEM_CALIB:-/Users/pedro/AtlasLocalWorker/config/2026-07-04-tau-sem-wild.json}"
SEM_TAX="${ATLAS_SEM_TAXONOMY:-/Users/pedro/AtlasLocalWorker/config/candidate-v2.json}"
if [[ "${ATLAS_SEM_LANE_ENABLED:-true}" == "true" && -n "${OPENAI_API_KEY:-}" \
      && -x "$MLVENV/bin/python" && -f "$SEM_CALIB" && -f "$SEM_TAX" ]]; then
  atlas_step "semantic lane pass" "$BACKEND_DIR" \
    "$MLVENV/bin/python" "$BACKEND_DIR/scripts/sem_assign_pass.py" \
    --calibration "$SEM_CALIB" --taxonomy "$SEM_TAX" \
    --window-hours "${ATLAS_SEM_WINDOW_HOURS:-1}" --write
  atlas_step "semantic lane gate scoring" "$BACKEND_DIR" \
    "$MLVENV/bin/python" "$BACKEND_DIR/scripts/score_assignments_gate.py" \
    --lane semantic \
    --window-hours "$GATE_WINDOW_HOURS" \
    --gate "$GATE_JSON" \
    --gate-id "$GATE_ID"
else
  echo "[atlas-topic] skip semantic lane (disabled, no OPENAI_API_KEY, or files missing)" >&2
fi

# Step 3: v2 force-fit reject (#204) — demote theme-hint-lex-v2 gate_kept rows the
# v2 e5 gate scores OUT_OF_SCOPE. Numpy-only on mlvenv, $0 (vec already persisted),
# flag-gated + reversible (tags gate_model=v2-gate-e5-lr-1). Query sees only
# gate_kept=true so re-runs are idempotent. Non-fatal.
V2_GATE_JSON="${ATLAS_V2_GATE_JSON:-/Users/pedro/AtlasLocalWorker/models/v2_gate.json}"
if [[ "${ATLAS_V2_GATE_ENABLED:-}" == "true" && -x "$MLVENV/bin/python" && -f "$V2_GATE_JSON" ]]; then
  atlas_step "v2 reject" "$BACKEND_DIR" \
    env ATLAS_V2_GATE_JSON="$V2_GATE_JSON" ATLAS_V2_GATE_ENABLED=true \
      "$MLVENV/bin/python" -m scripts.ensemble.apply_v2_reject \
        --apply --hours "${ATLAS_V2_GATE_REJECT_HOURS:-2}" \
        --threshold "${ATLAS_V2_GATE_THRESHOLD:-0.5}"
else
  echo "[atlas-topic] skip v2 reject (ATLAS_V2_GATE_ENABLED!=true or json missing)" >&2
fi

# Step 4: R3.1 incremental category typing (spec §3.1 mandates the 30-min cadence —
# nightly-only typing recreates the badge asymmetry as a TEMPORAL one, F-C4.2).
# --only-untyped: types ONLY topics with crisis_class IS NULL (new since the last
# pass), so steady-state is a single cheap SELECT and 0 DeepSeek calls. Runs from
# ROOT_DIR (module path backend.scripts.*, candidate-v2.json relative). Non-fatal.
if [[ -n "${DEEPSEEK_API_KEY:-}" && -x "$MLVENV/bin/python" ]]; then
  atlas_step "category typing" "$ROOT_DIR" \
    "$MLVENV/bin/python" -m backend.scripts.compute_category_typing \
      --deepseek --write --only-untyped
  # Step 4b (2026-07-14): give the just-typed NON-CRISIS topics an open category
  # label (Obituary & Tribute / Entertainment & Culture / ...) on the SAME 30-min
  # cadence — nightly-only left obituary/celebrity rows category=NULL for up to a
  # day, and a NULL category reads as the 'general' lane so eclipse surfaces them
  # (the 'Sam Neill' leak). Cheap: selects crisis_relevant=false AND category IS
  # NULL (a few new rows/cycle). Non-fatal.
  atlas_step "non-crisis domain labeling" "$ROOT_DIR" \
    "$MLVENV/bin/python" -m backend.scripts.type_noncrisis_domains --write
else
  echo "[atlas-topic] skip category typing (DEEPSEEK_API_KEY or mlvenv missing)" >&2
fi

# Step 5 (2026-07-20, council R2 N2): LABEL COURT on the 30-min cadence.
# --only-unchecked = incremental (label_status IS NULL only, i.e. topics
# promoted since the last pass — nightly court + this step share the stamp, so
# they never re-judge each other's work). --limit bounds one cycle's spend;
# incremental passes order id DESC (NEWEST-promoted first — the fold stays
# stamped, council-R2 N2) while full nightly runs stay biggest-first. Umbrella
# family bar + fallback receipts handled inside label_court.py. Proposals are
# NEVER applied here (ATLAS_LABEL_COURT_APPLY stays off — the court stamps,
# humans decide).
# Non-fatal; reverse: ATLAS_LABEL_COURT_ENABLED=false.
if [[ "${ATLAS_LABEL_COURT_ENABLED:-true}" == "true" \
      && -n "${DEEPSEEK_API_KEY:-}" && -x "$MLVENV/bin/python" ]]; then
  atlas_step "label court" "$ROOT_DIR" \
    "$MLVENV/bin/python" -m backend.scripts.label_court \
      --write --only-unchecked --limit "${ATLAS_LABEL_COURT_LIMIT:-40}"

  # Step 5b (2026-07-21): RELABEL the court-failed topics on the SAME 30-min
  # cadence — closes the detect->correct gap. The court MARKS a stale/over-merged
  # topic 'failed' every 30 min (e.g. 'Natalia Villalba Murder Case', born 07-01,
  # now holding diverse Colombia+Chile crimes), but until 2026-07-21 the RELABEL
  # that regenerates the served headline from the current receipts ran only
  # manually/nightly — so a failed topic kept serving its stale title for up to a
  # day. Now relabel_court_failed runs here: biggest-failed-first (agg_n_signals
  # DESC), bounded to ATLAS_RELABEL_LIMIT/cycle; it rewrites the label from the
  # receipts + resets label_status=NULL so the NEXT cycle's court re-judges the
  # new label. Reversible (JSONL ledger). Irreparable over-merges get a vague-blob
  # relabel here, which the nightly over-merge detector (Step 3.5c) then demotes —
  # a vague-honest label still beats a stale-lying one. Non-fatal; reverse:
  # ATLAS_RELABEL_ENABLED=false.
  if [[ "${ATLAS_RELABEL_ENABLED:-true}" == "true" ]]; then
    atlas_step "relabel court-failed" "$ROOT_DIR" \
      "$MLVENV/bin/python" -m backend.scripts.relabel_court_failed \
        --write --limit "${ATLAS_RELABEL_LIMIT:-20}"
  fi
else
  echo "[atlas-topic] skip label court (disabled, DEEPSEEK_API_KEY or mlvenv missing)" >&2
fi

# The run's verdict. A provider outage or a majority-failed run now exits
# non-zero — launchd records the failure instead of a plausible success.
atlas_run_verdict

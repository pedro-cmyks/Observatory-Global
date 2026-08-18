#!/usr/bin/env bash
set -uo pipefail   # NOT -e: a country/label hiccup must not abort the whole run

# R1 — scoped per-country emergent snapshot runner (#229). REPLACES the global
# com.atlas.emergent-snapshot (scoped is a superset: ~5.4× recall, ~54× more
# narratives, measured). Forms scoped topics for ALL countries under ONE snapshot,
# then projects into dynamic_topics (serving). MINDFUL (taskpolicy -b, efficiency
# cores) + heavy (multi-hour; remeasure after the uncapped atomic cutover) →
# schedule ONCE nightly, off-peak, in the embed gaps.
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
TOP_PER_COUNTRY="${ATLAS_SCOPED_TOP_PER_COUNTRY:-0}"
PER_COUNTRY_CAP="${ATLAS_SCOPED_CAP:-0}"
# Scoped regime: regional topics are 8-30 signals at ~0.97 cohesion; volume_min=30
# (global-regime default) starves them. 12 recalibrated + purity-verified (2026-07-01
# bootstrap: 256 admitted topics cohesion 0.969 / noise 0.081). persist_min stays the
# default 2 (dynamism — a NEW regional story proves across 2 nightly snapshots before
# it serves; the initial set was bootstrap-promoted once by hand).
VOLUME_MIN="${ATLAS_SCOPED_VOLUME_MIN:-12}"
MEMBERS_HOURS="${ATLAS_TOPIC_MEMBERS_HOURS:-336}"

export PATH="/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin:${PATH:-}"
mkdir -p "$LOG_DIR"

# EXECUTE-1 (2026-07-19): wall-time budget + checkpoint/resume state. The
# budget knobs (ATLAS_SNAPSHOT_RUN_BUDGET_MIN 150 / _COUNTRY_BUDGET_S 1800 /
# _N2_PER_SEC / _SUBPROC_MIN_N / _CAP_FLOOR_N / _RESUME) default IN the python
# writer; exporting the state dir here turns on checkpointing so a crashed
# pass resumes its snapshot instead of losing the night, and deferred/timed-
# out countries rotate to the front next pass. Reversible: unset the dir.
STATE_DIR="${ATLAS_SNAPSHOT_STATE_DIR:-$ROOT_DIR/state}"
mkdir -p "$STATE_DIR" 2>/dev/null || true
export ATLAS_SNAPSHOT_STATE_DIR="$STATE_DIR"

# Weekend compute mode (2026-07-19): weekends = performance cores + bigger
# budgets (scripts/weekend-mode.sh); weekdays keep the mindful discipline.
# Resolved at FIRE time, BEFORE the heavy-job mutex, and logged UNCONDITIONALLY —
# the 07-19 forensics showed a silent mode decision is invisible: a fire that
# gives up the lock (`|| exit 0`) used to exit with ZERO log lines, and a fire
# running pre-wire content looked identical to a weekday decision. The mode
# line below is the per-fire receipt; grep err.log for 'mode=' to audit any night.
if [[ -r "$SCRIPT_DIR/weekend-mode.sh" ]]; then
  source "$SCRIPT_DIR/weekend-mode.sh"
  atlas_weekend_env
  TASKPOLICY="$ATLAS_TASKPOLICY"
  if [[ "$ATLAS_WEEKEND" == "1" ]]; then MODE="weekend"; else MODE="weekday"; fi
else
  TASKPOLICY=""
  command -v taskpolicy >/dev/null 2>&1 && TASKPOLICY="taskpolicy -b"
  MODE="weekday-default(weekend-mode.sh missing)"
fi
echo "[scoped-snapshot] $(date '+%Y-%m-%d %H:%M:%S') mode=$MODE budget=${ATLAS_SNAPSHOT_RUN_BUDGET_MIN:-150}min taskpolicy=${TASKPOLICY:-performance-cores}" >&2
[[ "$MODE" == "weekend" ]] && echo "[scoped-snapshot] WEEKEND MODE: performance cores, run budget ${ATLAS_SNAPSHOT_RUN_BUDGET_MIN:-480}min" >&2

# PCA-128 clustering input (2026-07-20, #229 gold-gate verdict: WIRE) — per-
# country PCA reduction of the HDBSCAN INPUT to 128 dims. Measured on the
# same-as_of dry-run pair: 8.62x clustering speedup, yield +3.5% kept /
# +3.6% promotable, max cluster 276->92 (no blob), and the LLM gold judge
# passed the marginal clusters (57.5% same-story vs control 62.5% = -5.0pp,
# inside the 10pp bar; non-Latin stratum 65% >= 60%). Identity, gate,
# centroids, cohesion all stay raw e5 — only the HDBSCAN input changes.
# Artifact: docs/research/recall-229/2026-07-20-pca-verdict.md.
# ROLLBACK: set ATLAS_CLUSTER_PCA_DIM=0 below (or in the environment) —
# next snapshot clusters raw, byte-identical to the pre-wire path.
export ATLAS_CLUSTER_PCA_DIM="${ATLAS_CLUSTER_PCA_DIM:-128}"
echo "[scoped-snapshot] pca_dim=$ATLAS_CLUSTER_PCA_DIM (0 = raw/off)" >&2

# P1.1 heavy-job mutex: the multi-hour clustering chain must never overlap embed/
# matview/catchup on the shared Supabase (serving statement-timeout incidents).
if [[ -r "$SCRIPT_DIR/heavy-job-lock.sh" ]]; then
  source "$SCRIPT_DIR/heavy-job-lock.sh"
  atlas_heavy_lock "scoped-snapshot" wait 240 120 || exit 0
else
  echo "[scoped-snapshot] heavy-job-lock.sh missing — running UNSERIALIZED" >&2
fi

# ATLAS_CLAUDE_CLI* (2026-07-28): the insight chain's claude_cli failover leg
# (insight_llm.py) — the seal's synthesis step needs them; BIN is absolute
# because launchd's minimal PATH can't find `claude`.
for key in DATABASE_URL DEEPSEEK_API_KEY OPENAI_API_KEY ATLAS_CLAUDE_CLI ATLAS_CLAUDE_CLI_BIN ATLAS_LIFECYCLE_TICK_V2 ATLAS_SNAPSHOT_TAIL_RESERVE ATLAS_OVERMERGE_BLOB_STAMP ATLAS_LIFECYCLE_COUNTRY_CLOCK; do
  if [[ -z "${!key:-}" && -r "$LOCAL_ENV" ]]; then
    v="$(grep -E "^${key}=" "$LOCAL_ENV" | tail -n 1 | sed -E "s/^${key}=//" | tr -d '\r' || true)"
    [[ -n "$v" ]] && export "$key=$v"
  fi
done
if [[ -z "${DATABASE_URL:-}" || -z "${DEEPSEEK_API_KEY:-}" ]]; then
  echo "[scoped-snapshot] missing DATABASE_URL or DEEPSEEK_API_KEY" >&2; exit 2
fi

# ─── silent-failure guard (2026-07-27) ───────────────────────────────────────
# Identical to the guard in run-atlas-topic-classifier.sh (kept inline in both:
# each runner is hand-synced into the ALW tree on its own).
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
ATLAS_ALERT_TAG="${ATLAS_ALERT_TAG:-scoped-snapshot}"
# EXPORTED, not just a shell var: python writers (SNAPSHOT_UNLABELLED in
# run_scoped_snapshot / snapshot_emergent_topics) append to the same ledger.
export ATLAS_RELIABILITY_ALERTS_LOG="${ATLAS_RELIABILITY_ALERTS_LOG:-$HOME/AtlasLocalWorker/logs/reliability-alerts.log}"
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

# Step -1 (2026-07-20): COMMITTED-STATE SYNC — the durable cure for the
# recurring ALW-drift disease (07-19/20: umbrella build died on ImportError
# semantic_chunk_order, temporal_signature missing, narrative_lineage service
# absent — all because the executed ALW tree lagged the committed repo). Sync
# backend/app + backend/scripts from the canonical repo's COMMITTED HEAD (never
# the working tree — uncommitted parallel-session edits must not ship into a
# nightly). git archive is atomic-per-file via tar; the runner .sh itself is
# NOT in this set (it is synced by hand with tmp+mv). Non-fatal: a broken or
# absent repo must never kill the nightly — it just runs the last-synced code.
REPO_DIR="${ATLAS_REPO_DIR:-/Users/pedro/Desktop/PEDRO/Cursos/ObservatorioGlobal}"
if [[ "$ROOT_DIR" != "$REPO_DIR" && -d "$REPO_DIR/.git" ]]; then
  if _synced_sha="$(git -C "$REPO_DIR" rev-parse --short HEAD 2>/dev/null)" \
     && git -C "$REPO_DIR" archive HEAD backend/app backend/scripts 2>/dev/null \
        | tar -x -C "$ROOT_DIR" 2>/dev/null; then
    echo "[scoped-snapshot] ALW synced to committed HEAD ${_synced_sha}" >&2
  else
    echo "[scoped-snapshot] committed-state sync failed (non-fatal — running last-synced code)" >&2
  fi
fi

# Step 0 (2026-07-18 — the 2026-07-04 "durable plan" finally built): CHAIN
# embed→cluster. Clustering on stale embeddings wastes the whole night — the
# 07-17/18 runs spent 8h clustering old data while the embed cron starved
# behind this very mutex (24h embed coverage hit 0%). Embed the recent window
# FIRST, inside the same lock, so the country pass always clusters fresh
# signals. Same bounded incremental writer the embed cron runs; idempotent.
# Non-fatal: a partial embed still beats clustering nothing new.
( cd "$BACKEND_DIR" && $TASKPOLICY "$MLVENV/bin/python" -m scripts.embed_hot_corpus \
    --hours "${ATLAS_EMBED_WINDOW_HOURS:-168}" \
    --retention-days "${ATLAS_EMBED_RETENTION_DAYS:-7}" \
    --max-signals "${ATLAS_EMBED_MAX_SIGNALS:-60000}" ) \
  || echo "[scoped-snapshot] Step 0 embed catch-up failed (non-fatal — clustering may see stale embeds)" >&2

# Step 1: form + write the scoped snapshot (all countries, one snapshot_at).
# Time-budgeted (2026-07-19 forensics: US alone held the mutex 7+h inside one
# uninterruptible HDBSCAN call): run budget 150min · country budget 1800s ·
# big countries cluster their newest fitting slice in a hard-killable
# subprocess · every completed country commits incrementally. Worst case
# ≈ run budget + 1.5×country budget — the 240min mutex TTL is safe again.
cd "$ROOT_DIR"
if ! $TASKPOLICY "$MLVENV/bin/python" -m backend.scripts.run_scoped_snapshot \
  --min-embedded "$MIN_EMBEDDED" --top-per-country "$TOP_PER_COUNTRY" \
  --per-country-cap "$PER_COUNTRY_CAP" --gate "$GATE_JSON"; then
  echo "[scoped-snapshot] R1 write failed — stop before projection" >&2
  exit 1
fi

# Step 2: fold the just-written snapshot into dynamic_topics (serving) with the
# #224 anchor-guard + the retire/age lifecycle. Non-fatal.
# INCREMENTAL only — NEVER pass --rebuild here: --rebuild TRUNCATEs dynamic_topics
# (destroys topic history + resurrection identities). Incremental only appends/ages;
# retired topics stay in the table as resurrection targets (Pedro, 2026-07-01).
if [[ -f "$STUDENT_JSON" ]]; then
  ( cd "$BACKEND_DIR" && $TASKPOLICY "$MLVENV/bin/python" -m scripts.project_dynamic_topics \
      --student-model "$STUDENT_JSON" --volume-min "$VOLUME_MIN" ) \
    || echo "[scoped-snapshot] dynamic_topics projection failed (non-fatal)" >&2
else
  echo "[scoped-snapshot] student model missing ($STUDENT_JSON) — skip projection" >&2
fi

# Step 2.5: R3.1 — category typing (anchored-emergent + crisis-relevance lens) via
# DeepSeek, then emergent super-categories + open non-crisis domains. BEFORE the umbrella
# build so umbrellas inherit category/crisis_relevant. DeepSeek = cheap API, off-peak.
cd "$ROOT_DIR"
atlas_step "category typing" "$ROOT_DIR" \
  $TASKPOLICY "$MLVENV/bin/python" -m backend.scripts.compute_category_typing --deepseek --write
atlas_step "emergent labeling" "$ROOT_DIR" \
  $TASKPOLICY "$MLVENV/bin/python" -m backend.scripts.label_emergent_categories --write --threshold 0.95
atlas_step "non-crisis domains" "$ROOT_DIR" \
  $TASKPOLICY "$MLVENV/bin/python" -m backend.scripts.type_noncrisis_domains --write

# Step 2.6: LABEL COURT (#204/#224, council Move 1) — try each active topic's
# SERVED label against its own receipts (DeepSeek entailment, ~cents). Writes
# label_status (entailed/partial/failed) so L1 can refuse to lead with a failed
# label; on 'failed' proposes a receipt-derived neutral label (NEVER auto-served
# unless ATLAS_LABEL_COURT_APPLY=on) + logs the failure as #204 training data.
# Runs AFTER typing so the checked labels are the fresh ones. Non-fatal.
atlas_step "label court" "$ROOT_DIR" \
  $TASKPOLICY "$MLVENV/bin/python" -m backend.scripts.label_court --write

# Step 3: R2 — rebuild the umbrella hierarchy (centroid-of-centroids) over the fresh
# active set. Cheap (~hundreds of centroids, seconds). Collapses same-EVENT
# cross-country dups into parent umbrellas so the global list stays de-duped + gives
# the parent/child thread hierarchy. Idempotent + reversible (rebuilds only the
# DERIVED umbrella rows; never deletes a child). Threshold 0.98 = the measured
# same-event cut (complete-linkage; below it, diffuse centroids leak same-theme).
cd "$ROOT_DIR"
# gap-2 (2026-07-14): default grouping = the LLM same-event judge, which reconnects
# event fragments the centroid cut misses (US strikes / Hormuz / drone -> one
# US-Iran umbrella) and rolls their volume/breadth to the parent for the eclipse
# consumer. Reversible to the semantic cut: ATLAS_UMBRELLA_LINKAGE=complete.
# 2026-07-19: a judge outage now DEGRADES to the deterministic semantic
# complete-linkage (+ label-fold merge) instead of aborting — the old degraded
# path was gated on non-empty label-fold groups and THE RELABEL had emptied
# them, so the 07-18/19 outages left the umbrella layer stale. Restore the
# abort-on-outage behavior with ATLAS_UMBRELLA_DEGRADED_FALLBACK=off; either
# way a failed judge NEVER wipes existing umbrellas.
# 2026-07-19 (#261 slice 1): the judge is CHUNKED (~120 labels/prompt over a
# semantic co-location ordering) — one 830-label prompt truncated the 4k-token
# response and lost every LLM verdict to the degraded fallback. A failed chunk
# degrades alone; parsed chunks keep their verdicts.
$TASKPOLICY "$MLVENV/bin/python" -m backend.scripts.build_umbrella_topics \
  --linkage "${ATLAS_UMBRELLA_LINKAGE:-llm-event}" \
  --threshold "${ATLAS_UMBRELLA_THRESHOLD:-0.98}" \
  --judge-chunk-size "${ATLAS_UMBRELLA_JUDGE_CHUNK:-120}" \
  || echo "[scoped-snapshot] umbrella build failed (non-fatal)" >&2

# Step 3.5: project the just-refreshed thread identities into the shared typed
# membership table BEFORE movement, event binding, and the sealed publication.
# Previously this happened only on the separate embedding cadence, so raw ingest
# and dynamic_topics could be fresh while L1/L3 evidence remained a day behind.
( cd "$BACKEND_DIR" && $TASKPOLICY "$MLVENV/bin/python" -m scripts.etl_topic_members \
    --hours "$MEMBERS_HOURS" ) \
  || echo "[scoped-snapshot] ERROR topic_members ETL failed — typed evidence is STALE" >&2
# Step 3.5b (2026-07-20): FLAG + DEMOTE content-junk topics (listicle / feed-dump
# / mis-promoted category grab-bags). The mechanism (flag_junk_topics +
# topic_junk.classify_topic_junk) existed but was NEVER cron'd, so junk piled up
# in the served set and the is_junk column went stale (25 active junk found +
# demoted by hand this session). Runs AFTER the members ETL (needs the projected
# membership for the content-entropy signal). Reversible (UPDATE is_junk=false);
# non-fatal. NOT the over-merge class — that needs a membership-multimodality
# detector (separate lane); this is only the content-junk half.
( cd "$BACKEND_DIR" && $TASKPOLICY "$MLVENV/bin/python" -m scripts.flag_junk_topics \
    --sample "${ATLAS_JUNK_SAMPLE:-40}" ) \
  || echo "[scoped-snapshot] junk flag/demote failed (non-fatal — junk may still serve)" >&2
# Step 3.5c (2026-07-20): DETECT + DEMOTE OVER-MERGE blob topics — the OTHER half of
# identity retirement, the merge-sprint residual that 3.5b (content-junk) does NOT
# catch. A topic whose member embeddings split into 2+ well-separated substantial
# sub-clusters is a FUSION of distinct stories wearing a vague umbrella label
# ("Diverse Local Incidents Across Regions"). Every existing guard MISSES it: the
# label court passes it (a vague label trivially entails a diverse set), flag_junk
# passes it (each member is real news, not a feed-dump), and the M2 radial floor
# passes it (the centroid falls BETWEEN the sub-clusters). Signal = membership
# MULTIMODALITY (2-means gap_ratio + balance) with a country-dominant shared-actor
# veto and a DeepSeek "one story or two?" confirm judge. PRECISION-FIRST: a candidate
# demotes ONLY on a positive two_stories confirmation, so a missing/unhealthy judge
# demotes NOTHING (never a real story on the absence of a confirm) — a keyless M1
# nightly is safe. Two calls: audit (--judge writes the dated artifact) then --write
# (consumes it). --force-unsafe because this runs INSIDE the nightly, which already
# holds the heavy lock — the write guard is for EXTERNAL contention, not a sequential
# runner step. Reversible (active->candidate, never delete; --revert RUN_ID); the
# shared explicit --artifact survives a midnight date-rollover between the two calls.
# Non-fatal. ATLAS_OVERMERGE_ENABLED=off disables.
if [[ "${ATLAS_OVERMERGE_ENABLED:-on}" == "on" ]]; then
  OVERMERGE_ARTIFACT="$ROOT_DIR/docs/research/overmerge/$(date -u +%Y-%m-%d)-overmerge-audit.json"
  ( cd "$BACKEND_DIR" && $TASKPOLICY "$MLVENV/bin/python" -m scripts.detect_overmerge \
      --judge --artifact "$OVERMERGE_ARTIFACT" \
    && $TASKPOLICY "$MLVENV/bin/python" -m scripts.detect_overmerge \
      --write --force-unsafe --artifact "$OVERMERGE_ARTIFACT" ) \
    || echo "[scoped-snapshot] over-merge detect/demote failed (non-fatal — blobs may still serve)" >&2
else
  echo "[scoped-snapshot] skip over-merge detect (ATLAS_OVERMERGE_ENABLED=off)" >&2
fi
( cd "$BACKEND_DIR" && $TASKPOLICY "$MLVENV/bin/python" -m scripts.compute_topic_movement ) \
  || echo "[scoped-snapshot] ERROR topic movement failed — movement is STALE" >&2

# Step 3.6: NARRATIVE LINEAGE refresh (2026-07-18) — re-stitch live topics to
# the archive story units (narrative_lineage_census, OpenAI space, local
# disk/CPU; DB reads are 3 bounded SELECTs) and load the measured edges into
# narrative_lineage (mig 084) for GET /theme/{id}/lineage. Incremental by
# construction: the sha1 shard index reuses its fingerprint and the
# live-embed cache means only NEW topic member headlines hit the OpenAI API
# (--max-embed is the nightly cost guard). Skipped, non-fatal, when the
# external volume is unmounted or the key is missing — serving keeps the
# previous edges (stale lineage beats fabricated lineage).
if [[ "${ATLAS_LINEAGE_REFRESH:-on}" == "on" && -d /Volumes/Ext/Atlas/Embeddings/openai-3-small && -n "${OPENAI_API_KEY:-}" ]]; then
  # Cost guard is weekend-aware: a full-scale rebuild grows the member-headline
  # corpus past the 40k weekday cap (2026-07-20: aborted at "40542 exceeds
  # --max-embed 40000"). On weekends the durable rule grants the extra embed
  # budget (~$0.30 at 60k, OpenAI 3-small); weekdays stay lean. Explicit
  # ATLAS_LINEAGE_MAX_EMBED overrides both.
  if [[ -n "${ATLAS_LINEAGE_MAX_EMBED:-}" ]]; then
    LINEAGE_MAX_EMBED="$ATLAS_LINEAGE_MAX_EMBED"
  elif [[ "${ATLAS_WEEKEND:-0}" == "1" ]]; then
    LINEAGE_MAX_EMBED=60000
  else
    LINEAGE_MAX_EMBED=40000
  fi
  echo "[scoped-snapshot] lineage census --max-embed ${LINEAGE_MAX_EMBED} (mode=${MODE})" >&2
  ( cd "$ROOT_DIR" && $TASKPOLICY "$MLVENV/bin/python" -m backend.scripts.narrative_lineage_census all \
      --max-embed "${LINEAGE_MAX_EMBED}" ) \
    || echo "[scoped-snapshot] lineage census failed (non-fatal — lineage serves previous edges)" >&2
  ( cd "$ROOT_DIR" && $TASKPOLICY "$MLVENV/bin/python" -m backend.scripts.load_narrative_lineage --write --prune-stale ) \
    || echo "[scoped-snapshot] lineage load failed (non-fatal — lineage serves previous edges)" >&2
  # TEMPORAL SIGNATURE (Lane C, mig 085): classify every active topic's shape
  # in time (new/continuous/recurrent/resurrected) from the just-loaded
  # narrative_lineage edges + the census member-floor coverage. Cheap (pure
  # SQL reads + in-memory union-find); re-writes active topics each run, NULLs
  # the unclassifiable — a stale signature never outlives its lineage.
  ( cd "$ROOT_DIR" && $TASKPOLICY "$MLVENV/bin/python" -m backend.scripts.temporal_signature --write ) \
    || echo "[scoped-snapshot] temporal signature failed (non-fatal — chips simply don't render)" >&2
else
  echo "[scoped-snapshot] skip lineage refresh (off, volume unmounted, or no OPENAI key)" >&2
fi

# Step 3.9 (#256): the steps above mass-rewrote the exact tables the event binders
# read; stale planner stats after that rewrite were degrading the binding queries
# 30x+ into statement timeout (bindings silently stale 07-10 -> 07-12). Refresh
# stats BEFORE binding. Cheap (~seconds on these table sizes).
psql "$DATABASE_URL" -c "ANALYZE dynamic_topic_members, dynamic_topics, emergent_clusters, topic_members" \
  || echo "[scoped-snapshot] ERROR pre-bind ANALYZE failed (binders may hit stale stats)" >&2

# Step 4: R3.4b — bind events to topics PRECISELY via source_url (movement role,
# verified=false, #232). events_v2.source_url = signals_v2.source_url -> the article's
# topic. Non-fatal for the snapshot, but the failure must be LOUD (grep ERROR) —
# silent staleness was the #256 incident. Scripts emit RECEIPT lines (freshness lag).
$TASKPOLICY "$MLVENV/bin/python" -m backend.scripts.compute_event_movement --write \
  || echo "[scoped-snapshot] ERROR event movement bind failed — movement-v1 bindings are STALE (#256)" >&2

# Step 4b: disaster events (USGS+GDACS) -> disaster-category topics, geo-temporal
# (movement role, verified=false, event-source-eval §2). The hazards CAMEO can't
# represent (quake/flood/cyclone/wildfire). Ingest runs on Fly; this only BINDS the
# already-ingested rows to the fresh active topic set. Non-fatal but LOUD (#256).
( cd "$BACKEND_DIR" && $TASKPOLICY "$MLVENV/bin/python" -m scripts.bind_disaster_movement --write ) \
  || echo "[scoped-snapshot] ERROR disaster movement bind failed — disaster-v1 bindings are STALE (#256)" >&2

# Step 5: CATEGORY ROBOT (2026-07-06, supersedes the v0 name-first grow loop —
# Pedro: taxonomy is universal + dynamic; structure-first, over ALL history).
# robot_categories_v1: groups every dynamic_topics identity + the archive-era
# story units by content structure (measured cut), routes groups to three
# lanes (category -> atlas_topics origin='auto' cap 2/night; canonical event
# -> report/umbrella lane; same-story -> fusion work-list), with intra-batch
# dedup + LLM level check + blob guard. The 30-min typer reads the LIVE
# taxonomy, so new buckets receive stories the next cycle. Ledger + dated
# reports in docs/research/taxonomy-revision/. Disable: ATLAS_CATEGORY_GROWTH=off.
UNITS_JSONL="${ATLAS_ROBOT_UNITS:-/Volumes/Ext/Atlas/Embeddings/archive-story-units.jsonl}"
if [[ "${ATLAS_CATEGORY_GROWTH:-on}" == "on" && -n "${OPENAI_API_KEY:-}" && -n "${DEEPSEEK_API_KEY:-}" ]]; then
  ROBOT_ARGS=(--min-members 3 --max-new 2 --write)
  [[ -f "$UNITS_JSONL" ]] && ROBOT_ARGS+=(--units-jsonl "$UNITS_JSONL")
  atlas_step "category robot" "$ROOT_DIR" \
    $TASKPOLICY "$MLVENV/bin/python" -m backend.scripts.robot_categories_v1 "${ROBOT_ARGS[@]}"
else
  echo "[scoped-snapshot] skip category robot (off or keys missing)" >&2
fi

# Step 6: seal the shared L1/L3 PublicationPackage for this completed snapshot.
# This is intentionally the last database consumer in the mutex: it traverses
# the full active candidate set and stores one compact JSONB row. Vercel/Fly
# serving only reads that row; it never performs this work in an HTTP request.
# Guarded (2026-07-27): the seal is the step whose four-night silent death took
# the front page down. atlas_step classifies WHY it failed — a provider refusal
# now also fires PROVIDER_EXHAUSTED + a non-zero run exit, so launchd stops
# recording a dead seal as a successful night. SEAL_FAILED is kept verbatim:
# the weekly reliability read greps that exact token.
atlas_step "daily publication seal" "$BACKEND_DIR" \
  $TASKPOLICY "$MLVENV/bin/python" -m scripts.build_daily_publication --execute
if [ "$_ATLAS_LAST_STEP_RC" -ne 0 ]; then
  # Both markers kept verbatim: the ERROR line is frozen by
  # tests/test_daily_publication_artifact.py and greppable in the launchd err
  # log; SEAL_FAILED is the token the weekly reliability read greps.
  echo "[scoped-snapshot] ERROR daily publication artifact failed — L1 remains on the previous sealed edition" >&2
  atlas_alert "SEAL_FAILED daily publication artifact failed — L1 remains on the previous sealed edition"
fi

# Step 7 (2026-07-27): BUILD the universe field artifact.
#
# REPLACES the old "pre-warm the endpoint with curl" step, which could never
# work. The build MEASURES 75-84s (2,603 nodes / 6,306 edges / 3.96 MB) —
# longer than the Fly proxy holds a request open — so the warm curl was killed
# by the proxy every night (measured 2026-07-27: HTTP 000 after ~70s, 502 at
# 48.6s), the endpoint's in-process cache could never fill, and with nothing
# stored there was not even a stale payload to serve. /api/v2/universe sat at
# 0% availability and the UNIVERSE tab was permanently dark.
#
# Now the build runs HERE, on the M1, inside this mutex — like the daily
# publication seal above — and stores one compact row in
# universe_field_artifacts (mig 091). The endpoint is a pure read of that row:
# always fast, honest about the artifact's age, honest about its absence.
#
# Runs AFTER the members ETL + movement + typing so the field it freezes is
# the same substrate the rest of the night produced. Non-fatal: a failed build
# leaves the PREVIOUS artifact in place (serving degrades to an honestly
# stale field, never to a dark one). Disable with ATLAS_UNIVERSE_FIELD=off.
if [[ "${ATLAS_UNIVERSE_FIELD:-on}" == "on" ]]; then
  atlas_step "universe field artifact" "$BACKEND_DIR" \
    $TASKPOLICY "$MLVENV/bin/python" -m scripts.build_universe_field --execute
  if [ "$_ATLAS_LAST_STEP_RC" -ne 0 ]; then
    echo "[scoped-snapshot] ERROR universe field build failed — /api/v2/universe serves the PREVIOUS artifact (stale, not dark)" >&2
  fi
else
  echo "[scoped-snapshot] skip universe field build (ATLAS_UNIVERSE_FIELD=off)" >&2
fi

# Step 7b (2026-08-11, council R4 N26): WARM THE COUNTRY DOORS.
#
# GET /api/v2/country-edition answered 503 db_busy on cold open ON THE DAY
# COLOMBIA WAS THE STORY (measured from prod the same day: CO 110.8s -> 503,
# JP 21.7s -> 503, US 19.2s -> 503). The door composes country-scoped threads
# in-request, and that composition MEASURES 12-23s of scoped queries per
# country against a 15s budget; the 120s Redis layer never helped because
# nothing ever succeeded, so it never filled. The fast door failed exactly
# when the country was in the news.
#
# So the composition runs HERE, like the seal and the universe field above,
# and stores one compact row per door in country_edition_artifacts (mig 098).
# The endpoint reads that row and keeps its live build as the fallback.
#
# Runs AFTER the seal + universe on purpose: the doors then freeze the SAME
# substrate the rest of the night produced (this is the post-seal warm step
# the old "curl the endpoint to warm it" trick could never be — a warm curl
# dies in the proxy, an artifact does not).
#
# Doors = top-50 of the 24h field (88.9% of all signals; the curve is flat
# past there) + any country spiking >=1.5x its own baseline with >=150
# signals (the N26 case: the country that is the story without being big).
# Bounded by a 40-min wall clock at concurrency 3 and by an 80-door cap; a
# truncated run leaves the HEAD warm and NAMES every skipped door. Non-fatal:
# a failed build leaves the previous artifacts in place, and any door with no
# artifact simply falls back to today's live path. Disable with
# ATLAS_COUNTRY_EDITIONS=off.
if [[ "${ATLAS_COUNTRY_EDITIONS:-on}" == "on" ]]; then
  atlas_step "country edition artifacts" "$BACKEND_DIR" \
    $TASKPOLICY "$MLVENV/bin/python" -m scripts.build_country_editions --execute
  if [ "$_ATLAS_LAST_STEP_RC" -ne 0 ]; then
    echo "[scoped-snapshot] ERROR country edition build failed — the country doors serve the PREVIOUS artifacts (stale, labeled) or fall back to the live build" >&2
  fi
else
  echo "[scoped-snapshot] skip country edition artifacts (ATLAS_COUNTRY_EDITIONS=off)" >&2
fi

# Step 8 (2026-08-04): RECEIPT PRUNE — bound mig 097's sample_receipts growth.
# emergent_clusters never prunes rows (identity history: dynamic_topic_members
# references them) and the receipt writer stamps ~2,700 clusters/night, so the
# jsonb column grows unbounded on the shared Supabase. The policy is
# REFERENCE-STATE based, never cluster age alone (active topics reference
# member clusters back to 2026-05-31 — age-based pruning would eat reachable
# receipts of exactly the long stories mig 097 protects): NULL only where no
# non-retired topic references the cluster AND every referencing retirement
# (and the cluster itself) is older than 90d — outside the revival window.
# Ledgered + restorable (see the script docstring). Non-fatal: a skipped
# prune costs bytes, never correctness. Disable with ATLAS_RECEIPT_PRUNE=off.
if [[ "${ATLAS_RECEIPT_PRUNE:-on}" == "on" ]]; then
  atlas_step "sample-receipt prune" "$ROOT_DIR" \
    $TASKPOLICY "$MLVENV/bin/python" -m backend.scripts.prune_sample_receipts --execute
else
  echo "[scoped-snapshot] skip sample-receipt prune (ATLAS_RECEIPT_PRUNE=off)" >&2
fi

# Step 9 (2026-08-11, #235): PER-FEED FRESHNESS WATCHDOG — a stuck-cache feed
# is silent by construction (SANA's WordPress cache froze /en/feed/ on 07-28
# and yielded zero signals for six days with every layer reading healthy).
# Fetches each curated feed exactly as the ingestor would, reads the NEWEST
# item's own timestamp, ledgers one atlas_alert-format line per defective
# feed (FEED_STALE >7d / FEED_UNREACHABLE / FEED_UNPARSEABLE / FEED_EMPTY /
# FEED_UNDATED) to ATLAS_RELIABILITY_ALERTS_LOG. First live run 2026-08-11:
# 219 feeds -> 8 stale (chinadaily_cn 8.7 YEARS) · 11 unreachable · 5 undated.
# Network-bound ~1min, exit 0 always — the ledger is the alert channel.
if [[ "${ATLAS_FEED_WATCHDOG:-on}" == "on" ]]; then
  atlas_step "feed freshness watchdog" "$ROOT_DIR" \
    $TASKPOLICY "$MLVENV/bin/python" -m backend.scripts.rss_feed_freshness_watchdog
else
  echo "[scoped-snapshot] skip feed freshness watchdog (ATLAS_FEED_WATCHDOG=off)" >&2
fi

# Step 10 (2026-08-18, mig 102 / panel-ciego DEV-2): SUBJECT-COHERENCE store —
# measures per-topic receipt geography (the grab-bag detector, same measurement
# the seal runs) over ALL active topics and stores the glass-box result in
# dynamic_topic_subject_coherence, which live /threads rows serve as
# `subject_geography_grab_bag`. Full pass ~13min over WAN (measured — too
# heavy for the 30-min runner; the seal still measures fresh at 02:30, so the
# live chip is at most a night stale, declared). First fill 2026-08-18:
# 2,930 measured · 166 grab-bags (5.7%) · 975 sample-starved -> honest null.
# Non-fatal: a skipped pass leaves yesterday's rows serving, never a 500.
if [[ "${ATLAS_SUBJECT_COHERENCE:-on}" == "on" ]]; then
  atlas_step "subject-coherence store" "$ROOT_DIR" \
    $TASKPOLICY "$MLVENV/bin/python" -m backend.scripts.compute_subject_coherence --execute
else
  echo "[scoped-snapshot] skip subject-coherence store (ATLAS_SUBJECT_COHERENCE=off)" >&2
fi

# The run's verdict. A provider outage or a majority-failed run now exits
# non-zero — launchd records the failure instead of a plausible success. The
# heavy-lock EXIT trap still fires on this exit, so the mutex is released.
atlas_run_verdict

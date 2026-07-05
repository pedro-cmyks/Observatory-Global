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
# Scoped regime: regional topics are 8-30 signals at ~0.97 cohesion; volume_min=30
# (global-regime default) starves them. 12 recalibrated + purity-verified (2026-07-01
# bootstrap: 256 admitted topics cohesion 0.969 / noise 0.081). persist_min stays the
# default 2 (dynamism — a NEW regional story proves across 2 nightly snapshots before
# it serves; the initial set was bootstrap-promoted once by hand).
VOLUME_MIN="${ATLAS_SCOPED_VOLUME_MIN:-12}"

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
$TASKPOLICY "$MLVENV/bin/python" -m backend.scripts.compute_category_typing --deepseek --write \
  || echo "[scoped-snapshot] category typing failed (non-fatal)" >&2
$TASKPOLICY "$MLVENV/bin/python" -m backend.scripts.label_emergent_categories --write --threshold 0.95 \
  || echo "[scoped-snapshot] emergent labeling failed (non-fatal)" >&2
$TASKPOLICY "$MLVENV/bin/python" -m backend.scripts.type_noncrisis_domains --write \
  || echo "[scoped-snapshot] non-crisis domains failed (non-fatal)" >&2

# Step 3: R2 — rebuild the umbrella hierarchy (centroid-of-centroids) over the fresh
# active set. Cheap (~hundreds of centroids, seconds). Collapses same-EVENT
# cross-country dups into parent umbrellas so the global list stays de-duped + gives
# the parent/child thread hierarchy. Idempotent + reversible (rebuilds only the
# DERIVED umbrella rows; never deletes a child). Threshold 0.98 = the measured
# same-event cut (complete-linkage; below it, diffuse centroids leak same-theme).
cd "$ROOT_DIR"
$TASKPOLICY "$MLVENV/bin/python" -m backend.scripts.build_umbrella_topics \
  --threshold "${ATLAS_UMBRELLA_THRESHOLD:-0.98}" \
  || echo "[scoped-snapshot] umbrella build failed (non-fatal)" >&2

# Step 4: R3.4b — bind events to topics PRECISELY via source_url (movement role,
# verified=false, #232). events_v2.source_url = signals_v2.source_url -> the article's
# topic. Pure-SQL, cheap. Non-fatal.
$TASKPOLICY "$MLVENV/bin/python" -m backend.scripts.compute_event_movement --write \
  || echo "[scoped-snapshot] event movement bind failed (non-fatal)" >&2

# Step 4b: disaster events (USGS+GDACS) -> disaster-category topics, geo-temporal
# (movement role, verified=false, event-source-eval §2). The hazards CAMEO can't
# represent (quake/flood/cyclone/wildfire). Ingest runs on Fly; this only BINDS the
# already-ingested rows to the fresh active topic set. Pure-SQL, cheap. Non-fatal.
( cd "$BACKEND_DIR" && $TASKPOLICY "$MLVENV/bin/python" -m scripts.bind_disaster_movement --write ) \
  || echo "[scoped-snapshot] disaster movement bind failed (non-fatal)" >&2

# Step 5: anchored-emergent category GROWTH (Pedro 2026-07-04: the atlas
# corpus is not fixed in stone — neither a fixed count nor hand-updated).
# Aggregates the R3.1 typer's free-form categories; recurring ones (>=3
# stories, 30d) that clear a MEASURED overlap bar vs the existing anchors
# get a DeepSeek-drafted taxonomy entry and INSERT as origin='auto'
# (lexicon-less: born as a typing/semantic lens; the gate covers them as
# gold accumulates). Cap 2/night; ledger docs/research/taxonomy-revision/
# auto-growth-ledger.md. Seeds never touched. Disable: ATLAS_CATEGORY_GROWTH=off.
if [[ "${ATLAS_CATEGORY_GROWTH:-on}" == "on" && -n "${OPENAI_API_KEY:-}" && -n "${DEEPSEEK_API_KEY:-}" ]]; then
  ( cd "$ROOT_DIR" && $TASKPOLICY "$MLVENV/bin/python" -m backend.scripts.grow_atlas_categories --write ) \
    || echo "[scoped-snapshot] category growth failed (non-fatal)" >&2
else
  echo "[scoped-snapshot] skip category growth (off or keys missing)" >&2
fi

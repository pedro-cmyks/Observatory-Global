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

# P1.1 heavy-job mutex: the multi-hour clustering chain must never overlap embed/
# matview/catchup on the shared Supabase (serving statement-timeout incidents).
if [[ -r "$SCRIPT_DIR/heavy-job-lock.sh" ]]; then
  source "$SCRIPT_DIR/heavy-job-lock.sh"
  atlas_heavy_lock "scoped-snapshot" wait 240 120 || exit 0
else
  echo "[scoped-snapshot] heavy-job-lock.sh missing — running UNSERIALIZED" >&2
fi

for key in DATABASE_URL DEEPSEEK_API_KEY OPENAI_API_KEY; do
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
$TASKPOLICY "$MLVENV/bin/python" -m backend.scripts.compute_category_typing --deepseek --write \
  || echo "[scoped-snapshot] category typing failed (non-fatal)" >&2
$TASKPOLICY "$MLVENV/bin/python" -m backend.scripts.label_emergent_categories --write --threshold 0.95 \
  || echo "[scoped-snapshot] emergent labeling failed (non-fatal)" >&2
$TASKPOLICY "$MLVENV/bin/python" -m backend.scripts.type_noncrisis_domains --write \
  || echo "[scoped-snapshot] non-crisis domains failed (non-fatal)" >&2

# Step 2.6: LABEL COURT (#204/#224, council Move 1) — try each active topic's
# SERVED label against its own receipts (DeepSeek entailment, ~cents). Writes
# label_status (entailed/partial/failed) so L1 can refuse to lead with a failed
# label; on 'failed' proposes a receipt-derived neutral label (NEVER auto-served
# unless ATLAS_LABEL_COURT_APPLY=on) + logs the failure as #204 training data.
# Runs AFTER typing so the checked labels are the fresh ones. Non-fatal.
$TASKPOLICY "$MLVENV/bin/python" -m backend.scripts.label_court --write \
  || echo "[scoped-snapshot] label court failed (non-fatal)" >&2

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
# consumer. Reversible to the semantic cut: ATLAS_UMBRELLA_LINKAGE=complete. The
# builder aborts WITHOUT wiping umbrellas if the judge call fails (never dissolves
# the hierarchy on an LLM outage).
$TASKPOLICY "$MLVENV/bin/python" -m backend.scripts.build_umbrella_topics \
  --linkage "${ATLAS_UMBRELLA_LINKAGE:-llm-event}" \
  --threshold "${ATLAS_UMBRELLA_THRESHOLD:-0.98}" \
  || echo "[scoped-snapshot] umbrella build failed (non-fatal)" >&2

# Step 3.5: project the just-refreshed thread identities into the shared typed
# membership table BEFORE movement, event binding, and the sealed publication.
# Previously this happened only on the separate embedding cadence, so raw ingest
# and dynamic_topics could be fresh while L1/L3 evidence remained a day behind.
( cd "$BACKEND_DIR" && $TASKPOLICY "$MLVENV/bin/python" -m scripts.etl_topic_members \
    --hours "$MEMBERS_HOURS" ) \
  || echo "[scoped-snapshot] ERROR topic_members ETL failed — typed evidence is STALE" >&2
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
  ( cd "$ROOT_DIR" && $TASKPOLICY "$MLVENV/bin/python" -m backend.scripts.narrative_lineage_census all \
      --max-embed "${ATLAS_LINEAGE_MAX_EMBED:-40000}" ) \
    || echo "[scoped-snapshot] lineage census failed (non-fatal — lineage serves previous edges)" >&2
  ( cd "$ROOT_DIR" && $TASKPOLICY "$MLVENV/bin/python" -m backend.scripts.load_narrative_lineage --write --prune-stale ) \
    || echo "[scoped-snapshot] lineage load failed (non-fatal — lineage serves previous edges)" >&2
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
  ( cd "$ROOT_DIR" && $TASKPOLICY "$MLVENV/bin/python" -m backend.scripts.robot_categories_v1 "${ROBOT_ARGS[@]}" ) \
    || echo "[scoped-snapshot] category robot failed (non-fatal)" >&2
else
  echo "[scoped-snapshot] skip category robot (off or keys missing)" >&2
fi

# Step 6: seal the shared L1/L3 PublicationPackage for this completed snapshot.
# This is intentionally the last database consumer in the mutex: it traverses
# the full active candidate set and stores one compact JSONB row. Vercel/Fly
# serving only reads that row; it never performs this work in an HTTP request.
( cd "$BACKEND_DIR" && $TASKPOLICY "$MLVENV/bin/python" -m scripts.build_daily_publication --execute ) \
  || echo "[scoped-snapshot] ERROR daily publication artifact failed — L1 remains on the previous sealed edition" >&2

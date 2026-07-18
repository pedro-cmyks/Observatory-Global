#!/usr/bin/env bash
# Cron FRESHNESS watchdog (2026-07-04, extended 2026-07-18 #259). The
# nlp-fleet + embed-SERVICE watchdogs don't cover the batch data crons — so
# when scoped-snapshot / embed-hot-corpus stopped FIRING for ~20h (launchd
# scheduling broke after a manual reindex cycle), nothing caught it and the
# served data went thin (101 stories, stale embeddings). This checks DB
# FRESHNESS and kickstarts the relevant cron when a job has clearly missed
# its cadence — conservatively, and never two heavy jobs at once (the
# load-16 kernel-panic lesson).
#
# #259 extension: the embed probe is now the DATA-freshness alarm for the
# recurring silent-death class — lag > 6h logs LOUD ("EMBED STALE Nh") and
# integrates with the heavy-job mutex (/tmp/atlas-heavy-job.lock):
#   - lock FREE          → kickstart com.atlas.embed-hot-corpus
#   - lock HELD (in TTL) → holder is legitimate, wait for the next tick
#   - lock OVERDUE_ACTIVE→ NEVER kill a live owner; write a dated alert to
#     the reliability ledger (logs/reliability-alerts.log) for the weekly read.
# A watchdog must never crash-loop: DB probe failure = log + exit 0.
#
# Thresholds: clustering only kickstarts in the off-peak window (00:00-06:59)
# so a daytime stall waits for night, protecting the M1.
set -uo pipefail
UID_N=$(id -u)
ALW=/Users/pedro/AtlasLocalWorker
LOG=$ALW/logs/cron-freshness-watchdog.log
ALERTS=${ATLAS_RELIABILITY_ALERTS_LOG:-$ALW/logs/reliability-alerts.log}
ENV_FILE=$ALW/.env
LOCK_DIR=${ATLAS_HEAVY_LOCK_DIR:-/tmp/atlas-heavy-job.lock}
ts() { date '+%F %T'; }
alert() { # dated line to BOTH the watchdog log and the reliability ledger
  echo "$(ts) [freshness-watchdog] $*" >>"$LOG"
  echo "$(ts) [freshness-watchdog] $*" >>"$ALERTS" 2>/dev/null || true
}
[ -f "$ENV_FILE" ] && set -a && . "$ENV_FILE" && set +a

PSQL=$(command -v psql || echo /opt/homebrew/bin/psql)
age_h() { # $1 = SQL returning a timestamptz; prints integer hours, or NOTHING
  # on query failure (caller must treat empty = probe failed, never "stale").
  "$PSQL" "$DATABASE_URL" -tAc \
    "SELECT COALESCE(round(extract(epoch from (now()-($1)))/3600)::int, 9999)" 2>/dev/null \
    | tr -d '[:space:]'
}
running() { launchctl list | grep -q "[0-9].*$1"; }  # has a live PID
kick() { launchctl kickstart "gui/$UID_N/$1" >>"$LOG" 2>&1 && echo "$(ts) KICKSTARTED $1 ($2)" >>"$LOG"; }

heavy_lock_state() {
  # Prints one of:  FREE | HELD <job> <pid> <age_min> | OVERDUE <job> <pid> <age_min> <ttl>
  # Read-only view of the heavy-job mutex; a dead holder counts as FREE (the
  # next acquirer's own reclaim path removes it — the watchdog never rm's).
  [ -d "$LOCK_DIR" ] || { echo FREE; return; }
  local pid job started ttl now age_min
  pid=$(sed -n 's/^pid=//p' "$LOCK_DIR/info" 2>/dev/null | head -1)
  job=$(sed -n 's/^job=//p' "$LOCK_DIR/info" 2>/dev/null | head -1)
  started=$(sed -n 's/^started=//p' "$LOCK_DIR/info" 2>/dev/null | head -1)
  ttl=$(sed -n 's/^ttl=//p' "$LOCK_DIR/info" 2>/dev/null | head -1)
  if [ -z "$pid" ] || ! kill -0 "$pid" 2>/dev/null; then
    echo FREE; return
  fi
  now=$(date +%s)
  age_min=$(( (now - ${started:-$now}) / 60 ))
  if [ -n "$ttl" ] && [ "$age_min" -gt "$ttl" ] 2>/dev/null; then
    echo "OVERDUE ${job:-?} $pid $age_min $ttl"
  else
    echo "HELD ${job:-?} $pid $age_min"
  fi
}

EMBED_AGE=$(age_h "SELECT max(embedded_at) FROM signal_embeddings")
CLUSTER_AGE=$(age_h "SELECT max(last_seen) FROM dynamic_topics WHERE state='active'")
HOUR=$(date +%H)

# Defensive: a watchdog must never mistake its own DB failure for staleness.
if [ -z "$EMBED_AGE" ] || [ -z "$CLUSTER_AGE" ]; then
  echo "$(ts) DB probe FAILED (embed='${EMBED_AGE:-}' cluster='${CLUSTER_AGE:-}') — skipping this tick" >>"$LOG"
  exit 0
fi

# Never kickstart while ANY heavy batch job is already running (load safety).
if running com.atlas.embed-hot-corpus || running com.atlas.scoped-snapshot \
   || running com.atlas.emergent-snapshot; then
  echo "$(ts) heavy job running (launchd); skip (embed_age=${EMBED_AGE}h cluster_age=${CLUSTER_AGE}h)" >>"$LOG"
  exit 0
fi

# Embed DATA freshness (#259): the silent-death alarm. Mindful cron ~30min
# cadence; > 6h of no new embeddings = something upstream died quietly.
if [ "$EMBED_AGE" -gt 6 ]; then
  LOCK_STATE=$(heavy_lock_state)
  case "$LOCK_STATE" in
    FREE)
      alert "EMBED STALE ${EMBED_AGE}h — heavy lock free, kickstarting embed-hot-corpus"
      kick com.atlas.embed-hot-corpus "embeddings ${EMBED_AGE}h stale"
      ;;
    OVERDUE*)
      # A live-but-overdue owner is an incident to SURFACE, never to evict.
      alert "EMBED STALE ${EMBED_AGE}h + OVERDUE_ACTIVE heavy lock (${LOCK_STATE#OVERDUE }) — NOT killing a live owner; investigate"
      ;;
    HELD*)
      echo "$(ts) EMBED STALE ${EMBED_AGE}h but heavy lock held in-TTL (${LOCK_STATE#HELD }); waiting" >>"$LOG"
      ;;
  esac
  exit 0  # one heavy job at a time — clustering waits for the next tick
fi

# Clustering: heavy. Only kickstart in the off-peak window and only when it has
# clearly missed a daily slot (> 30h), so it never fires during Pedro's hours.
if [ "$CLUSTER_AGE" -gt 30 ] && [ "$HOUR" -ge 0 ] && [ "$HOUR" -le 6 ]; then
  LOCK_STATE=$(heavy_lock_state)
  case "$LOCK_STATE" in
    FREE)
      kick com.atlas.scoped-snapshot "dynamic_topics ${CLUSTER_AGE}h stale (off-peak)"
      ;;
    OVERDUE*)
      alert "CLUSTER STALE ${CLUSTER_AGE}h + OVERDUE_ACTIVE heavy lock (${LOCK_STATE#OVERDUE }) — NOT killing a live owner; investigate"
      ;;
    HELD*)
      echo "$(ts) cluster stale ${CLUSTER_AGE}h but heavy lock held in-TTL (${LOCK_STATE#HELD }); waiting" >>"$LOG"
      ;;
  esac
  exit 0
fi

echo "$(ts) ok (embed_age=${EMBED_AGE}h cluster_age=${CLUSTER_AGE}h hour=${HOUR})" >>"$LOG"

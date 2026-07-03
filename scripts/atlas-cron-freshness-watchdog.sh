#!/usr/bin/env bash
# Cron FRESHNESS watchdog (2026-07-04). The nlp-fleet + embed-SERVICE watchdogs
# don't cover the batch data crons — so when scoped-snapshot / embed-hot-corpus
# stopped FIRING for ~20h (launchd scheduling broke after a manual reindex
# cycle), nothing caught it and the served data went thin (101 stories, stale
# embeddings). This checks DB FRESHNESS and kickstarts the relevant cron when a
# job has clearly missed its cadence — conservatively, and never two heavy jobs
# at once (the load-16 kernel-panic lesson).
#
# Thresholds are deliberately loose (more than a cadence) so a healthy off-peak
# schedule never false-fires. Clustering only kickstarts in the off-peak window
# (00:00-06:59) so a daytime stall waits for night, protecting the M1.
set -uo pipefail
UID_N=$(id -u)
LOG=/Users/pedro/AtlasLocalWorker/logs/cron-freshness-watchdog.log
ENV_FILE=/Users/pedro/AtlasLocalWorker/.env
ts() { date '+%F %T'; }
[ -f "$ENV_FILE" ] && set -a && . "$ENV_FILE" && set +a

PSQL=$(command -v psql || echo /opt/homebrew/bin/psql)
age_h() { # $1 = SQL returning a timestamptz; prints integer hours or 9999
  "$PSQL" "$DATABASE_URL" -tAc \
    "SELECT COALESCE(round(extract(epoch from (now()-($1)))/3600)::int, 9999)" 2>/dev/null \
    | tr -d '[:space:]' || echo 9999
}
running() { launchctl list | grep -q "[0-9].*$1"; }  # has a live PID
kick() { launchctl kickstart "gui/$UID_N/$1" >>"$LOG" 2>&1 && echo "$(ts) KICKSTARTED $1 ($2)" >>"$LOG"; }

EMBED_AGE=$(age_h "SELECT max(embedded_at) FROM signal_embeddings")
CLUSTER_AGE=$(age_h "SELECT max(last_seen) FROM dynamic_topics WHERE state='active'")
HOUR=$(date +%H)

# Never kickstart while ANY heavy batch job is already running (load safety).
if running com.atlas.embed-hot-corpus || running com.atlas.scoped-snapshot \
   || running com.atlas.emergent-snapshot; then
  echo "$(ts) heavy job running; skip (embed_age=${EMBED_AGE}h cluster_age=${CLUSTER_AGE}h)" >>"$LOG"
  exit 0
fi

# Embed: mindful ~30min, tolerable any hour. Stale > 14h = a missed run.
if [ "$EMBED_AGE" -gt 14 ]; then
  kick com.atlas.embed-hot-corpus "embeddings ${EMBED_AGE}h stale"
  exit 0  # one heavy job at a time — clustering waits for the next tick
fi

# Clustering: heavy. Only kickstart in the off-peak window and only when it has
# clearly missed a daily slot (> 30h), so it never fires during Pedro's hours.
if [ "$CLUSTER_AGE" -gt 30 ] && [ "$HOUR" -ge 0 ] && [ "$HOUR" -le 6 ]; then
  kick com.atlas.scoped-snapshot "dynamic_topics ${CLUSTER_AGE}h stale (off-peak)"
  exit 0
fi

echo "$(ts) ok (embed_age=${EMBED_AGE}h cluster_age=${CLUSTER_AGE}h hour=${HOUR})" >>"$LOG"

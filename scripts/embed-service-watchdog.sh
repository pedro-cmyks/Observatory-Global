#!/usr/bin/env bash
# Embed-service watchdog (#240 / master-consolidation T4.1).
#
# The Fly `nlp_worker` process hosts the e5 embed service that powers the
# research semantic lane + on-demand connection embedding. It has silently
# STOPPED before (2026-06-25) and stayed down for a day — there is no
# min_machines / restart policy on that process. This watchdog notices and
# restarts the MAIN nlp_worker machine (never the standby).
#
# Install via scripts/install-embed-watchdog-launchd.sh (runs every 15 min).
set -uo pipefail

APP="${ATLAS_FLY_APP:-atlas-api-pedro}"
LOGDIR="${ATLAS_LOCAL_LOG_DIR:-$HOME/AtlasLocalWorker/logs}"
mkdir -p "$LOGDIR"
LOG="$LOGDIR/embed-watchdog.log"
ts() { date "+%Y-%m-%dT%H:%M:%S"; }

if ! command -v fly >/dev/null 2>&1; then
  echo "$(ts) fly CLI not found" >> "$LOG"; exit 0
fi

# MAIN nlp_worker = proc=nlp_worker AND not a standby AND not already started.
down="$(fly machine list -a "$APP" --json 2>/dev/null | python3 -c "
import sys, json
try:
    ms = json.load(sys.stdin)
except Exception:
    sys.exit(0)
for m in ms:
    cfg = m.get('config', {}) or {}
    md = cfg.get('metadata', {}) or {}
    is_worker = md.get('fly_process_group') == 'nlp_worker'
    is_standby = bool(cfg.get('standbys'))
    if is_worker and not is_standby and m.get('state') != 'started':
        print(m['id'])
" 2>/dev/null)"

if [ -z "${down:-}" ]; then
  echo "$(ts) embed-service up" >> "$LOG"
  exit 0
fi

for id in $down; do
  if fly machine start "$id" -a "$APP" >> "$LOG" 2>&1; then
    echo "$(ts) RESTARTED embed-service machine $id" >> "$LOG"
  else
    echo "$(ts) FAILED to restart $id" >> "$LOG"
  fi
done

#!/usr/bin/env bash
# NLP-fleet watchdog (the M1 analog of embed-service-watchdog / #240).
#
# The M1 fleet (com.atlas.nlp-fleet) died SILENTLY on 2026-06-29 (SIGTERM;
# KeepAlive did not resurrect it) and NER starved for 2 days — discovered by
# accident during the multilingual flip. Same failure class as the embed
# service (#240). Belt + suspenders, every 15 min:
#   (a) job not loaded            -> bootstrap the plist
#   (b) loaded but no PID         -> kickstart
#   (c) heartbeat log stale >45m  -> kickstart -k (restart)
# The supervisor/worker writes to nlp-fleet.err.log every cycle (~169-600s even
# in gentle mode), so a 45-min stale threshold never false-fires on a healthy
# fleet; after machine sleep a spurious kickstart is harmless (idempotent start).
set -uo pipefail

LABEL="com.atlas.nlp-fleet"
ALW="${ATLAS_LOCAL_WORKER_DIR:-$HOME/AtlasLocalWorker}"
PLIST="$HOME/Library/LaunchAgents/$LABEL.plist"
LOGDIR="${ATLAS_LOCAL_LOG_DIR:-$ALW/logs}"
mkdir -p "$LOGDIR"
LOG="$LOGDIR/nlp-fleet-watchdog.log"
HEARTBEAT="$LOGDIR/nlp-fleet.err.log"
STALE_MIN="${ATLAS_FLEET_STALE_MIN:-45}"
UID_N="$(id -u)"
ts() { date "+%Y-%m-%dT%H:%M:%S"; }

# (a) job not loaded at all (the 06-29 failure mode: booted out, never back)
if ! launchctl print "gui/$UID_N/$LABEL" >/dev/null 2>&1; then
  if [ -f "$PLIST" ]; then
    launchctl bootstrap "gui/$UID_N" "$PLIST" >> "$LOG" 2>&1 \
      && echo "$(ts) BOOTSTRAPPED $LABEL (was not loaded)" >> "$LOG" \
      || echo "$(ts) FAILED to bootstrap $LABEL" >> "$LOG"
  else
    echo "$(ts) $LABEL not loaded and plist missing at $PLIST" >> "$LOG"
  fi
  exit 0
fi

# (b) loaded but not running (no PID in launchctl list)
pid="$(launchctl list | awk -v l="$LABEL" '$3==l {print $1}')"
if [ -z "$pid" ] || [ "$pid" = "-" ]; then
  launchctl kickstart "gui/$UID_N/$LABEL" >> "$LOG" 2>&1 \
    && echo "$(ts) KICKSTARTED $LABEL (loaded, no PID)" >> "$LOG" \
    || echo "$(ts) FAILED to kickstart $LABEL" >> "$LOG"
  exit 0
fi

# (c) running but heartbeat stale (hung worker / wedged supervisor)
if [ -f "$HEARTBEAT" ] && [ -z "$(find "$HEARTBEAT" -mmin "-$STALE_MIN" 2>/dev/null)" ]; then
  launchctl kickstart -k "gui/$UID_N/$LABEL" >> "$LOG" 2>&1 \
    && echo "$(ts) RESTARTED $LABEL (heartbeat >${STALE_MIN}m stale)" >> "$LOG" \
    || echo "$(ts) FAILED to restart $LABEL" >> "$LOG"
  exit 0
fi

echo "$(ts) nlp-fleet up (pid $pid)" >> "$LOG"

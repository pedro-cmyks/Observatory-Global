# heavy-job-lock.sh — ONE heavy job at a time on the M1 (roadmap P1.1).
#
# Why: the M1 batch jobs (embed cron, scoped/emergent snapshot, matview
# refresh, goldgrowth, hot-cold catchup) all hammer the SAME shared Supabase.
# Two at once → statement timeouts on the serving path → prod 500s
# (fourth incident the week of 2026-07-11: /api/v2/signals TimeoutError at
# night while embed + matview + catchup stacked). This library serializes
# them: a runner either QUEUES (wait mode) or SKIPS (skip mode) while another
# heavy job holds the lock — never two concurrently.
#
# Usage (source from a runner, AFTER set -euo pipefail):
#   source "$SCRIPT_DIR/heavy-job-lock.sh"
#   atlas_heavy_lock "embed-hot-corpus" wait 240 || exit 0
#     args: <job-name> <wait|skip> [ttl-minutes] [wait-max-minutes]
#   - wait: poll every 60s until free (up to wait-max, default 90 min),
#     then give up with a log line (exit 0 — the next scheduled fire retries).
#   - skip: one attempt; if held, log and return 1 (caller exits 0).
#   Returns 0 = lock acquired (EXIT trap releases it), 1 = not acquired.
#
# Stale-lock recovery: the lock dir carries the holder PID + start epoch.
#   - holder PID dead  → crashed run, reclaim immediately.
#   - lock older than TTL → hung run (or PID reuse), log LOUD and reclaim.
#     TTL is per-job (pass a generous one: a legit long job past its TTL is
#     itself the incident we want surfaced).
#
# NOTE for runners that `exec` their payload: exec replaces the shell, so the
# EXIT trap never fires and the lock leaks until TTL. Call the payload as a
# normal command instead (goldgrowth runner was changed for this).
#
# macOS has no flock(1); atomic mkdir is the portable primitive (same pattern
# refresh-country-hourly.sh already used for self-overlap).

ATLAS_HEAVY_LOCK_DIR="${ATLAS_HEAVY_LOCK_DIR:-/tmp/atlas-heavy-job.lock}"
ATLAS_HEAVY_LOCK_LOG="${ATLAS_HEAVY_LOCK_LOG:-$HOME/AtlasLocalWorker/logs/heavy-lock.log}"
# Reliability ledger (#259): OVERDUE_ACTIVE incidents also land here so the
# weekly read has ONE place to grep (shared with the freshness watchdog).
ATLAS_RELIABILITY_ALERTS_LOG="${ATLAS_RELIABILITY_ALERTS_LOG:-$HOME/AtlasLocalWorker/logs/reliability-alerts.log}"
_ATLAS_HEAVY_LOCK_HELD=""
# TRANSITION-ONLY ledgering (2026-07-27). The overdue check below runs on EVERY
# 60s poll and used to append to the reliability ledger each tick: 398 of 402
# ledger lines were this ONE incident repeating, which is exactly what buried
# the 4 real SEAL_FAILED lines of the four-night outage. The ledger now records
# the TRANSITIONS (entered-overdue / cleared) only; the per-tick heartbeat goes
# to the heavy-lock debug log and never to the ledger.
_ATLAS_HEAVY_OVERDUE_MARKER="overdue-reported"   # dir inside the lock dir
_ATLAS_HEAVY_OVERDUE_TICKS=0
_ATLAS_HEAVY_HEARTBEAT_EVERY="${ATLAS_HEAVY_HEARTBEAT_EVERY:-15}"   # ticks (~min)

_atlas_heavy_log() {
  local line
  line="$(date '+%F %T') [heavy-lock] $*"
  echo "$line" >&2
  if [ -d "$(dirname "$ATLAS_HEAVY_LOCK_LOG")" ]; then
    echo "$line" >> "$ATLAS_HEAVY_LOCK_LOG" 2>/dev/null || true
  fi
}

_atlas_heavy_debug() {
  # Debug log ONLY — never stderr, never the alerts ledger. This is where a
  # still-ongoing incident may repeat.
  if [ -d "$(dirname "$ATLAS_HEAVY_LOCK_LOG")" ]; then
    echo "$(date '+%F %T') [heavy-lock] $*" >> "$ATLAS_HEAVY_LOCK_LOG" 2>/dev/null || true
  fi
}

_atlas_heavy_alert() {
  # ONE line to the shared reliability ledger. Callers MUST gate this on a
  # state transition — anything that can repeat per tick belongs in
  # _atlas_heavy_debug.
  if [ -d "$(dirname "$ATLAS_RELIABILITY_ALERTS_LOG")" ]; then
    echo "$(date '+%F %T') [heavy-lock] $*" >> "$ATLAS_RELIABILITY_ALERTS_LOG" 2>/dev/null || true
  fi
}

_atlas_heavy_holder_info() {
  # Echo "pid|job|started_epoch|owner_ttl_minutes" from the lock, empty fields
  # if unreadable. The OWNER'S TTL travels with the lock: a short-cadence
  # contender must never evict a legitimate long-running owner.
  local pid="" job="" started="" owner_ttl=""
  if [ -r "$ATLAS_HEAVY_LOCK_DIR/info" ]; then
    pid="$(sed -n 's/^pid=//p' "$ATLAS_HEAVY_LOCK_DIR/info" 2>/dev/null | head -1)"
    job="$(sed -n 's/^job=//p' "$ATLAS_HEAVY_LOCK_DIR/info" 2>/dev/null | head -1)"
    started="$(sed -n 's/^started=//p' "$ATLAS_HEAVY_LOCK_DIR/info" 2>/dev/null | head -1)"
    owner_ttl="$(sed -n 's/^ttl=//p' "$ATLAS_HEAVY_LOCK_DIR/info" 2>/dev/null | head -1)"
  fi
  echo "${pid}|${job}|${started}|${owner_ttl}"
}

_atlas_heavy_try_reclaim() {
  # Reclaim only a crashed holder (PID dead). A live-but-overdue owner is an
  # incident to surface, not permission to create the concurrent heavy jobs
  # this mutex exists to prevent. Returns 0 only if the lock was removed.
  local info pid rest job started owner_ttl now age_min
  info="$(_atlas_heavy_holder_info)"
  pid="${info%%|*}"
  rest="${info#*|}"; job="${rest%%|*}"
  rest="${rest#*|}"; started="${rest%%|*}"
  owner_ttl="${rest##*|}"
  if [ -z "$pid" ] || ! kill -0 "$pid" 2>/dev/null; then
    # A crashed holder ends any overdue incident it was carrying — report the
    # cleared transition before the marker dies with the lock dir.
    if [ -d "$ATLAS_HEAVY_LOCK_DIR/$_ATLAS_HEAVY_OVERDUE_MARKER" ]; then
      _atlas_heavy_alert "OVERDUE_CLEARED job=${job:-?} pid=${pid:-?} — overdue holder is DEAD, lock reclaimed"
    fi
    _atlas_heavy_log "stale lock (holder pid=${pid:-?} job=${job:-?} DEAD) — reclaiming"
    rm -rf "$ATLAS_HEAVY_LOCK_DIR" 2>/dev/null
    _ATLAS_HEAVY_OVERDUE_TICKS=0
    return 0
  fi
  now="$(date +%s)"
  if [ -n "$started" ] && [ -n "$owner_ttl" ] \
      && [ "$(( (now - started) / 60 ))" -gt "$owner_ttl" ]; then
    age_min="$(( (now - started) / 60 ))"
    # mkdir is atomic: exactly ONE waiter reports the entered-overdue
    # transition for a given lock, no matter how many are polling. The marker
    # lives inside the lock dir, so release/reclaim clears it by construction.
    if mkdir "$ATLAS_HEAVY_LOCK_DIR/$_ATLAS_HEAVY_OVERDUE_MARKER" 2>/dev/null; then
      _atlas_heavy_log "OVERDUE_ACTIVE lock (job=$job pid=$pid age=${age_min}m > owner_ttl=${owner_ttl}m) — NOT reclaiming a live owner; investigate"
      _atlas_heavy_alert "OVERDUE_ACTIVE job=$job pid=$pid age=${age_min}m owner_ttl=${owner_ttl}m — live owner NOT evicted"
    else
      # Already reported. Heartbeat to the DEBUG log only, throttled — the
      # ledger must stay a list of transitions, not a per-minute tape.
      _ATLAS_HEAVY_OVERDUE_TICKS=$((_ATLAS_HEAVY_OVERDUE_TICKS + 1))
      if [ "$_ATLAS_HEAVY_HEARTBEAT_EVERY" -gt 0 ] \
         && [ "$((_ATLAS_HEAVY_OVERDUE_TICKS % _ATLAS_HEAVY_HEARTBEAT_EVERY))" -eq 0 ]; then
        _atlas_heavy_debug "still OVERDUE (job=$job pid=$pid age=${age_min}m) — already reported, heartbeat only"
      fi
    fi
  fi
  return 1
}

atlas_heavy_lock_release() {
  if [ -n "$_ATLAS_HEAVY_LOCK_HELD" ]; then
    # Close the incident: if this lock was reported OVERDUE while we held it,
    # emit the matching cleared transition so the ledger reads as a PAIR
    # (entered / cleared) instead of one line per minute of overrun.
    if [ -d "$ATLAS_HEAVY_LOCK_DIR/$_ATLAS_HEAVY_OVERDUE_MARKER" ]; then
      local info started age_min="?"
      info="$(_atlas_heavy_holder_info)"
      started="$(echo "$info" | cut -d'|' -f3)"
      if [ -n "$started" ]; then
        age_min="$(( ($(date +%s) - started) / 60 ))"
      fi
      _atlas_heavy_alert "OVERDUE_CLEARED job=$_ATLAS_HEAVY_LOCK_HELD pid=$$ age=${age_min}m — overdue holder finished, lock released"
    fi
    rm -rf "$ATLAS_HEAVY_LOCK_DIR" 2>/dev/null
    _atlas_heavy_log "released by $_ATLAS_HEAVY_LOCK_HELD (pid $$)"
    _ATLAS_HEAVY_LOCK_HELD=""
  fi
}

atlas_heavy_lock() {
  local job="$1" mode="${2:-skip}" ttl_min="${3:-240}" wait_max_min="${4:-90}"
  local waited=0 info pid holder_job

  while :; do
    if mkdir "$ATLAS_HEAVY_LOCK_DIR" 2>/dev/null; then
      {
        echo "pid=$$"
        echo "job=$job"
        echo "started=$(date +%s)"
        echo "ttl=$ttl_min"
      } > "$ATLAS_HEAVY_LOCK_DIR/info"
      _ATLAS_HEAVY_LOCK_HELD="$job"
      # shellcheck disable=SC2064
      trap 'atlas_heavy_lock_release' EXIT
      _atlas_heavy_log "acquired by $job (pid $$, mode=$mode)"
      return 0
    fi

    # Held — crashed/hung holder is reclaimable, then loop retries mkdir.
    if _atlas_heavy_try_reclaim; then
      continue
    fi

    info="$(_atlas_heavy_holder_info)"
    pid="${info%%|*}"; holder_job="$(echo "$info" | cut -d'|' -f2)"

    if [ "$mode" != "wait" ]; then
      _atlas_heavy_log "$job SKIPPED — lock held by ${holder_job:-?} (pid ${pid:-?})"
      return 1
    fi
    if [ "$waited" -ge "$wait_max_min" ]; then
      _atlas_heavy_log "$job GAVE UP after ${waited}m waiting on ${holder_job:-?} (pid ${pid:-?})"
      return 1
    fi
    if [ "$waited" -eq 0 ]; then
      _atlas_heavy_log "$job queued behind ${holder_job:-?} (pid ${pid:-?}), waiting up to ${wait_max_min}m"
    fi
    sleep 60
    waited=$((waited + 1))
  done
}

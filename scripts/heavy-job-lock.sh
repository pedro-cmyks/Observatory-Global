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
_ATLAS_HEAVY_LOCK_HELD=""

_atlas_heavy_log() {
  local line
  line="$(date '+%F %T') [heavy-lock] $*"
  echo "$line" >&2
  if [ -d "$(dirname "$ATLAS_HEAVY_LOCK_LOG")" ]; then
    echo "$line" >> "$ATLAS_HEAVY_LOCK_LOG" 2>/dev/null || true
  fi
}

_atlas_heavy_holder_info() {
  # Echo "pid|job|started_epoch" from the lock, empty fields if unreadable.
  local pid="" job="" started=""
  if [ -r "$ATLAS_HEAVY_LOCK_DIR/info" ]; then
    pid="$(sed -n 's/^pid=//p' "$ATLAS_HEAVY_LOCK_DIR/info" 2>/dev/null | head -1)"
    job="$(sed -n 's/^job=//p' "$ATLAS_HEAVY_LOCK_DIR/info" 2>/dev/null | head -1)"
    started="$(sed -n 's/^started=//p' "$ATLAS_HEAVY_LOCK_DIR/info" 2>/dev/null | head -1)"
  fi
  echo "${pid}|${job}|${started}"
}

_atlas_heavy_try_reclaim() {
  # Reclaim if the holder crashed (PID dead) or overran its TTL.
  # $1 = ttl minutes. Returns 0 if the lock was removed.
  local ttl_min="$1" info pid job started now age_min
  info="$(_atlas_heavy_holder_info)"
  pid="${info%%|*}"; job="$(echo "$info" | cut -d'|' -f2)"; started="${info##*|}"
  if [ -z "$pid" ] || ! kill -0 "$pid" 2>/dev/null; then
    _atlas_heavy_log "stale lock (holder pid=${pid:-?} job=${job:-?} DEAD) — reclaiming"
    rm -rf "$ATLAS_HEAVY_LOCK_DIR" 2>/dev/null
    return 0
  fi
  now="$(date +%s)"
  if [ -n "$started" ] && [ "$(( (now - started) / 60 ))" -gt "$ttl_min" ]; then
    age_min="$(( (now - started) / 60 ))"
    _atlas_heavy_log "OVERDUE lock (job=$job pid=$pid age=${age_min}m > ttl=${ttl_min}m) — reclaiming; investigate the hung job"
    rm -rf "$ATLAS_HEAVY_LOCK_DIR" 2>/dev/null
    return 0
  fi
  return 1
}

atlas_heavy_lock_release() {
  if [ -n "$_ATLAS_HEAVY_LOCK_HELD" ]; then
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
      } > "$ATLAS_HEAVY_LOCK_DIR/info"
      _ATLAS_HEAVY_LOCK_HELD="$job"
      # shellcheck disable=SC2064
      trap 'atlas_heavy_lock_release' EXIT
      _atlas_heavy_log "acquired by $job (pid $$, mode=$mode)"
      return 0
    fi

    # Held — crashed/hung holder is reclaimable, then loop retries mkdir.
    if _atlas_heavy_try_reclaim "$ttl_min"; then
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

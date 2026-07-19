#!/usr/bin/env bash
# Weekend compute mode (Pedro, 2026-07-19): weekends the M1 works FULL — all
# day, performance cores, bigger budgets — to clear the week's backlog. The
# weekday discipline (mindful, efficiency cores, off-peak) stays untouched.
#
# Window: Friday >=14:00 through Monday <06:00, America/Bogota (UTC-5).
# Source this file, then:
#   atlas_weekend_now            → exit 0 (weekend) | 1 (weekday)
#   $ATLAS_TASKPOLICY            → "" on weekends, "taskpolicy -b" on weekdays
#   atlas_weekend_env            → exports the bigger weekend budgets
#
# Override for testing / manual control: ATLAS_FORCE_WEEKEND=on|off.

atlas_weekend_now() {
  case "${ATLAS_FORCE_WEEKEND:-}" in
    on)  return 0 ;;
    off) return 1 ;;
  esac
  local dow hour
  dow=$(TZ=America/Bogota date +%u)   # 1=Mon .. 7=Sun
  hour=$(TZ=America/Bogota date +%H)
  # Friday from 14:00
  [ "$dow" -eq 5 ] && [ "$hour" -ge 14 ] && return 0
  # Saturday + Sunday, all day
  [ "$dow" -eq 6 ] && return 0
  [ "$dow" -eq 7 ] && return 0
  # Monday before 06:00
  [ "$dow" -eq 1 ] && [ "$hour" -lt 6 ] && return 0
  return 1
}

if atlas_weekend_now; then
  ATLAS_TASKPOLICY=""                # performance cores
  ATLAS_WEEKEND=1
else
  ATLAS_TASKPOLICY="taskpolicy -b"   # mindful efficiency cores
  ATLAS_WEEKEND=0
fi
export ATLAS_WEEKEND

atlas_weekend_env() {
  # Bigger budgets when the machine is ours all day. Every knob here is the
  # same env the runners already read — weekend just raises the ceilings.
  if [ "$ATLAS_WEEKEND" = "1" ]; then
    export ATLAS_SNAPSHOT_RUN_BUDGET_MIN="${ATLAS_SNAPSHOT_RUN_BUDGET_MIN:-480}"   # 8h vs 150min
    export ATLAS_SNAPSHOT_COUNTRY_BUDGET_S="${ATLAS_SNAPSHOT_COUNTRY_BUDGET_S:-5400}" # 90min vs 30
    export ATLAS_EMBED_MAX_SIGNALS="${ATLAS_EMBED_MAX_SIGNALS:-200000}"            # vs 60k
  fi
}

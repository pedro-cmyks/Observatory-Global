#!/bin/bash
# L4 markets — daily accumulator runner (the #226 gate prerequisite + descriptive push).
# Off-peak cron target (Atlas discipline: 17:30+, mindful). Versioned in the repo; the M1
# cron executes a synced copy from ~/AtlasLocalWorker, same as the other runners.
#
# Steps (each best-effort, one failing never blocks the next):
#   1. accumulate  — Yahoo prices (first run backfills ~4mo) + point-in-time news intensity
#                    → markets-side sqlite ($ATLAS_MARKETS_DB).
#   2. push        — thin descriptive snapshot (last_close + 30d spark) → Atlas DB market_series
#                    so the product surface (Brief strip / dock tab) reads fresh prices. The ONE
#                    allowed crossing (design §6); runs only if DATABASE_URL + psql are present.
# Pure descriptive accumulation. No claims, no engine touch. Reads Yahoo + the Atlas public API.
set -uo pipefail

# launchd gives a minimal PATH (no /opt/homebrew/bin) → psql/brew tools go missing and
# the DB push silently skips. Restore Homebrew + local bins first.
export PATH="/opt/homebrew/bin:/usr/local/bin:$PATH"

# source local env for DATABASE_URL (same pattern as the other AtlasLocalWorker runners)
[ -f "$HOME/AtlasLocalWorker/.env" ] && set -a && . "$HOME/AtlasLocalWorker/.env" && set +a

# cd to whichever nearby dir contains the markets/ package (repo OR ~/AtlasLocalWorker layout)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BASE=""
for cand in "$SCRIPT_DIR" "$SCRIPT_DIR/.."; do
  if [ -f "$cand/markets/accumulate.py" ]; then BASE="$(cd "$cand" && pwd)"; break; fi
done
[ -n "$BASE" ] || { echo "markets/ package not found near $SCRIPT_DIR" >&2; exit 2; }
cd "$BASE" || exit 2

PY="python3"
[ -x "$HOME/AtlasLocalWorker/mlvenv/bin/python" ] && PY="$HOME/AtlasLocalWorker/mlvenv/bin/python"

# 1. accumulate (mindful: efficiency cores + nice)
taskpolicy -b "$PY" -m markets.accumulate

# 2. descriptive push → Atlas DB (stdlib emits SQL, psql applies — no asyncpg dep)
if [ -n "${DATABASE_URL:-}" ] && command -v psql >/dev/null 2>&1; then
  "$PY" -m markets.push_atlas_db --emit-sql | psql "$DATABASE_URL" -q \
    && echo "market_series pushed to Atlas DB" \
    || echo "market_series push failed (non-fatal)" >&2
else
  echo "skip Atlas-DB push (no DATABASE_URL or psql)" >&2
fi

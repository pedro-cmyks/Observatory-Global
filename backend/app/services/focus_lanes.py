"""Bounded lane execution for `/api/v2/focus` — Council R4 DESKTOP-N26.

THE DEFECT this closes. `/api/v2/focus` ran six lanes sequentially on one
connection with NO statement_timeout, every lane carrying the person
predicate spelled `EXISTS (SELECT 1 FROM unnest(persons) p WHERE LOWER(p)
LIKE LOWER($1))`. That spelling is unindexable, so each lane seq-scanned
`signals_v2` and the handler held the request open for as long as it took —
45-120s for a ubiquitous name, behind a frontend skeleton with no time
bound. Sibling panels (the C4a timeline, voice-mix) degraded honestly on
the SAME data; only this endpoint hung.

TWO fixes, both measured (2026-08-11, prod, 24h window):

1. THE PREDICATE. Migration 090 indexed `f_unaccent(lower(f_arr_text(
   persons)))` with a trigram GIN, and a trigram index only serves a
   predicate matching its expression character for character. Re-spelling
   the filter as `PERSON_MATCH_EXPR` moves the `nodes` lane from a seq scan
   to `BitmapAnd(idx_signals_v2_persons_text_trgm, idx_signals_v2_timestamp)`
   — prod EXPLAIN (ANALYZE) for `%trump%`: **576ms warm**, 2,737 matching
   rows. This is the same spelling `search.py` and `focus_timeline.py`
   already use; it now lives here so there is ONE person predicate in the
   codebase, not three.

2. THE BOUNDS. Even index-backed, a COLD trigram index page-in is real: the
   first `%trump%` touch of the session measured 14,543ms on the `nodes`
   lane alone (warm: 576ms). So every lane runs under its own
   `statement_timeout` and the handler carries a global deadline. Budgets
   below are set from the measured distribution, not guessed.

MEASURED per-lane cost, 10 persons, 24h window, index-backed predicate
(cold-ish — one fresh connection per query):

    person       TOTAL   nodes  related sources headlines persons  ner
    trump        19113   14543    358     311      415      745    2741
    sheinbaum     8906    7615    218     218      217      334     304
    zelenskyy     5287    4023    254     249      248      257     257
    netanyahu     3158    1987    228     235      233      248     227
    al-sisi       3116    2010    222     207      227      224     226
    starmer       2130     877    244     232      313      231     233
    petro         2088     869    224     215      216      348     217
    mbappe        1598     527    199     214      212      224     222
    macron        1543     500    210     205      203      211     214
    lula          1412     284    228     224      230      232     214

Reading: `nodes` owns the variance (284ms -> 14.5s) because it is the only
unbounded lane (GROUP BY over every matching row, no LIMIT); every other
lane is LIMIT-bounded and sits at ~200-400ms with a 2,741ms worst case
(trump's `ner`, which unrolls a jsonb array). Budgets give `nodes` room for
a cold page-in and hold the rest near 4x their observed worst case.

WHY ONE CONNECTION, NOT SIX. The obvious speedup is to fan the lanes out
concurrently, but the pool is `max_size=10` (main_v2.py) — six connections
per request would let two concurrent focus requests exhaust it and convert a
slow panel into a site-wide outage. Lanes therefore stay sequential on the
single connection the handler already holds, and the GLOBAL deadline is what
bounds total wall time. Lanes are ordered by VALUE so that when the deadline
bites, what survives is what the panel most needs.

asyncpg's pool issues `RESET ALL` on release, so a per-lane
`statement_timeout` never leaks to the next borrower of the connection.
"""
from __future__ import annotations

import logging
import re
import time
from typing import Any, Optional

import asyncpg

from app.core.search_normalization import normalize_search_text

logger = logging.getLogger(__name__)

# The ONE person predicate, spelled EXACTLY as migration 090 indexed the
# column. `f_arr_text` is the IMMUTABLE array_to_string wrapper 090 had to
# add because array_to_string itself is only STABLE and cannot appear in an
# index expression. A trigram GIN only serves a predicate that matches its
# expression character for character, so this string is load-bearing — do
# not "simplify" it back to unnest/ILIKE, which is exactly the regression
# that produced the N26 hang.
PERSON_MATCH_EXPR = "persons IS NOT NULL AND f_unaccent(lower(f_arr_text(persons))) LIKE"

_LIKE_SPECIALS = re.compile(r"([\\%_])")


def person_like_needle(name: str) -> Optional[str]:
    """Fold a person ref into the LIKE needle the mig-090 index expects.

    The indexed side is accent-folded and lowercased, so the needle must be
    too or an accented ref silently matches nothing (the "Mbappé hole"
    `search.py` documents). The fold is `normalize_search_text` — the SAME
    helper /search/thread builds its persons patterns with, one normalizer
    rather than two.

    ONE adjustment on top of it, measured: `normalize_search_text` squashes
    every non-alphanumeric run to a SPACE, but the stored person value keeps
    its punctuation — 808 of 68,643 distinct values in a 24h window are
    hyphenated ('abdel fattah al-sisi'), i.e. mostly Arabic names. A
    literal-space needle MISSES all of them, so a plain reuse would be a
    silent recall REGRESSION for that 1.2%. Substituting LIKE's
    single-character wildcard `_` for the space bridges both spellings and
    still takes the index. It is strictly wider than the old `unnest` +
    `LIKE` predicate, never narrower.

    Falls back to a plain lowercase when the fold comes back empty — that
    happens for a name written wholly in a non-Latin script, where the
    squash would erase everything and leave the needle '%%', silently
    matching the entire corpus. `f_unaccent` is the identity for those
    scripts, so lower() alone already matches the indexed expression. The
    fallback escapes LIKE metacharacters because, unlike the folded path, it
    has not been through a character filter.
    """
    folded = normalize_search_text(name)
    if folded:
        return "%" + folded.replace(" ", "_") + "%"
    fallback = _LIKE_SPECIALS.sub(r"\\\1", name.strip().lower())
    return f"%{fallback}%" if fallback else None


# Per-lane statement_timeout, milliseconds. Set from the measured table in
# the module docstring, not guessed.
#
# `nodes`: the only unbounded lane and the panel's primary content (the
#   country list the map re-scopes on). 6000ms covers every warm case with
#   ~10x headroom and most cold page-ins; a genuinely cold trump (14.5s
#   measured) degrades honestly rather than holding the user for 14s.
# `persons` / `ner`: LIMIT 40 but they unroll an array / jsonb array per
#   row. Worst measured 2,741ms (trump ner) -> 3000ms.
# `headlines` / `sources` / `related`: LIMIT-bounded, worst measured 415ms
#   -> 2000-2500ms is ~5x headroom, matching `focus_timeline.py`'s
#   `_SCAN_TIMEOUT_MS = 3000` precedent for raw signals_v2 scans.
LANE_BUDGETS_MS: dict[str, int] = {
    "nodes": 6000,
    "persons": 3000,
    "ner": 3000,
    "headlines": 2500,
    "sources": 2000,
    "related": 2000,
}

# Total wall-clock bound for the whole handler. The sum of the budgets is
# 18.5s; this deadline is what actually holds the endpoint, cutting the
# remaining lanes once it is spent. Chosen to sit just under the frontend's
# 8s "measuring a heavy subject" notice plus a beat, so the honest slow
# message is followed by a real payload rather than replacing it.
GLOBAL_DEADLINE_MS = 9000

# Bound on WAITING FOR A CONNECTION.
#
# Measured in the browser against the deployed fix: under load the endpoint
# returned an honest all-degraded 200 but took 23.4s to say it, because
# `statement_timeout` bounds SQL EXECUTION and nothing bounded the wait to
# GET a connection. The deadline clock also started after `pool.acquire()`
# returned, so that wait was invisible to the mechanism meant to bound it.
#
# The first attempt gave the acquire its own 3s budget. Deployed, that
# degraded EVERY request (8/8 runs at a flat 3.34s, all six lanes db_busy) —
# a fast wrong answer is still a wrong answer. On this deployment a real
# acquire (Fly -> Supabase pooler, TLS, possibly opening a new connection)
# routinely costs more than 3s, so the separate budget was simply set below
# the true cost.
#
# So there is ONE budget, not two competing ones: the acquire is bounded by
# whatever remains of the global deadline, and time it consumes is charged
# to the lanes that follow. Total wall time stays bounded by
# GLOBAL_DEADLINE_MS either way, which is the property that matters — and a
# genuinely saturated pool still degrades honestly instead of hanging.
POOL_ACQUIRE_TIMEOUT_S = GLOBAL_DEADLINE_MS / 1000.0

# Lane order = VALUE order. When the deadline bites, the lanes that survive
# are the ones the panel most needs: the countries (which the map and the
# evidence route both read), then the receipts, then the subjects, and only
# then the two lanes that feed secondary chips.
LANE_ORDER = ("nodes", "headlines", "persons", "ner", "sources", "related")

_DB_BUSY_ERRORS = (
    asyncpg.exceptions.QueryCanceledError,
    asyncpg.exceptions.TooManyConnectionsError,
    asyncpg.exceptions.ConnectionDoesNotExistError,
    TimeoutError,
)

LANE_LIVE = "live"
LANE_DEGRADED = "degraded"


class LaneRunner:
    """Runs `/api/v2/focus`'s lanes on ONE connection under a global
    deadline, each lane bounded by its own `statement_timeout`.

    A lane never raises: it returns `[]` and records a status of
    `degraded` with a named reason. Callers distinguish "measured empty"
    from "could not measure" via `status(lane)` / `degraded_lanes` — the
    zero-as-fact trap this class exists to prevent.
    """

    def __init__(self, conn: Any, *, deadline_ms: int = GLOBAL_DEADLINE_MS,
                 clock: Any = time.monotonic, started_at: Optional[float] = None,
                 budgets: Optional[dict[str, int]] = None):
        self._conn = conn
        self._deadline_ms = deadline_ms
        self._clock = clock
        # Per-lane budgets, defaulting to /api/v2/focus's measured table. The
        # Atlas Query Protocol (`services/query_verbs.py`) runs its own lanes
        # with their own measured budgets through this SAME runner rather than
        # growing a second bounded-lane mechanism — the "one predicate, not
        # three" rule of this module applied to the runner itself.
        self._budgets = budgets if budgets is not None else LANE_BUDGETS_MS
        # `started_at` lets the caller start the clock at REQUEST ENTRY
        # rather than here. That difference is load-bearing: time spent
        # queueing for a pool connection is time the user is staring at a
        # skeleton, so the deadline has to include it or the bound is a
        # fiction under exactly the conditions that make it matter.
        self._started = started_at if started_at is not None else clock()
        self._status: dict[str, str] = {}
        self._reasons: dict[str, str] = {}

    def elapsed_ms(self) -> float:
        return (self._clock() - self._started) * 1000.0

    def remaining_ms(self) -> float:
        return self._deadline_ms - self.elapsed_ms()

    async def run(self, lane: str, sql: str, *params: Any) -> list:
        """Execute one lane. Returns rows, or `[]` when the lane degraded.

        The effective timeout is the lane's own budget clamped to whatever
        remains of the global deadline, so a late lane cannot overrun the
        handler's total bound.
        """
        budget = self._budgets.get(lane, 2000)
        remaining = self.remaining_ms()
        if remaining <= 0:
            # Deadline already spent — do not even issue the query. This is
            # a distinct reason from db_busy: nothing was slow, we simply
            # ran out of budget upstream.
            self._status[lane] = LANE_DEGRADED
            self._reasons[lane] = "deadline"
            logger.info("focus lane %s skipped: global deadline spent", lane)
            return []

        effective = int(min(budget, remaining))
        try:
            await self._conn.execute(f"SET statement_timeout = {effective}")
            rows = await self._conn.fetch(sql, *params)
            self._status[lane] = LANE_LIVE
            return list(rows)
        except _DB_BUSY_ERRORS as exc:
            self._status[lane] = LANE_DEGRADED
            self._reasons[lane] = "db_busy"
            logger.warning("focus lane %s degraded (%s) after %.0fms budget %dms",
                           lane, type(exc).__name__, self.elapsed_ms(), effective)
            return []
        except Exception as exc:  # pragma: no cover - defensive I/O
            self._status[lane] = LANE_DEGRADED
            self._reasons[lane] = "db_error"
            logger.warning("focus lane %s failed: %s", lane, str(exc)[:200])
            return []

    def status(self, lane: str) -> str:
        return self._status.get(lane, LANE_DEGRADED)

    def is_live(self, lane: str) -> bool:
        return self._status.get(lane) == LANE_LIVE

    @property
    def statuses(self) -> dict[str, str]:
        return dict(self._status)

    @property
    def degraded_lanes(self) -> list[str]:
        return [k for k, v in self._status.items() if v != LANE_LIVE]

    @property
    def reasons(self) -> dict[str, str]:
        return dict(self._reasons)

    def any_degraded(self) -> bool:
        return bool(self.degraded_lanes)

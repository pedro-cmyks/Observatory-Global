"""EXECUTE-1 (2026-07-19) — wall-time budget + checkpoint math for the scoped
snapshot (the failure-budget philosophy extended to TIME).

Forensics (ASSESS-A, 2026-07-19): the nightly per-country HDBSCAN pass is
O(n²·d) brute-MST, single-threaded, nice-10 on efficiency cores — measured
~1.15-1.25e9 n²-units/hour. The US country alone (n≈80-100k post-dedupe) is
~51% of the whole night's Σn² and ran 7+ hours INSIDE one uninterruptible
Cython call while holding the heavy-job mutex (TTL 240 min). Nothing was
committed until the very end, so killed runs lost everything (07-17/18).

This module is the PURE planning layer (no numpy/hdbscan/DB — tests run in
any venv):

  - ``predict_seconds`` / ``fit_cap``: quadratic cost model over a
    self-calibrating rate (``RateEstimator``, EMA over measured runs);
  - ``plan_country``: cap a too-expensive country's clustering INPUT to its
    newest-first fitting slice; first-fit-defer what cannot fit the remaining
    run budget (smaller countries later may still fit); defer instead of
    clustering a garbage sliver when the budget can't buy the floor;
  - ``Checkpoint`` (+ save/load/should_resume): after every committed country
    the run records snapshot_at / done countries / next cluster-id base, so a
    crashed run RESUMES the same snapshot instead of losing the night;
  - rotation file: deferred/timed-out countries get next-night priority so
    first-fit deferral never chronically starves the same countries;
  - ``split_tail_first`` / ``tail_reserve_seconds`` (P3, 2026-07-30): rotation
    alone still spends the weekday budget on the head and leaves the thin
    countries to weekend mode — the tail lane runs FIRST on a bounded slice so
    a small country is clustered EVERY pass.

Everything is env-reversible at the call site (run_scoped_snapshot.py):
budget 0 = off, state dir unset = no checkpointing.
"""
from __future__ import annotations

import json
import math
import os
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path

_CHECKPOINT_VERSION = 1

# Hard-timeout shaping: the subprocess kill is a BACKSTOP for a mis-calibrated
# rate, not the planning target — give it headroom over the prediction but
# never let one country exceed 1.5× its budget.
_TIMEOUT_HEADROOM = 3.0
_TIMEOUT_FLOOR_S = 300.0
_TIMEOUT_BUDGET_MULT = 1.5


class CountryDeferred(Exception):
    """Planned out before clustering (run budget / floor) — NOT a failure.

    Deferred countries are ledgered loudly, age one lifecycle tick exactly
    like the existing gap budget, get rotation priority next night, and never
    count toward the all-or-nothing discard budget."""

    def __init__(self, reason: str, n_eff: int):
        super().__init__(reason)
        self.reason = reason
        self.n_eff = n_eff


class CountryTimeGap(Exception):
    """Clustering was attempted and HARD-KILLED at its wall-time budget (after
    one halved retry) — an honest time-gap, same ledger treatment as
    CountryDeferred."""


def predict_seconds(n: int, rate_n2_per_s: float) -> float:
    """Predicted brute-MST clustering seconds for an n-row input."""
    if rate_n2_per_s <= 0:
        return 0.0
    return (float(n) * float(n)) / float(rate_n2_per_s)


def fit_cap(budget_s: float, rate_n2_per_s: float) -> int:
    """Largest input size whose predicted cost fits ``budget_s``. 0 = nothing
    fits (degenerate budget/rate)."""
    if budget_s <= 0 or rate_n2_per_s <= 0:
        return 0
    return int(math.sqrt(float(budget_s) * float(rate_n2_per_s)))


class RateEstimator:
    """EMA of the measured clustering rate in n²-units/second.

    The forensics calibrated ~320-347k n²/s at nice-10 on efficiency cores;
    the initial value only matters until the first real country lands — every
    measured (n, seconds) pulls the estimate toward the machine's actual
    nightly rate (contention, PCA dim, priority class all folded in).
    Clamped to sane bounds so one garbage measurement can never convince the
    planner the machine is infinitely fast (or dead)."""

    MIN_RATE = 30_000.0
    MAX_RATE = 30_000_000.0
    _MIN_N = 2_000          # micro countries are overhead-dominated → ignored
    _ALPHA = 0.5

    def __init__(self, initial: float):
        self._rate = min(max(float(initial), self.MIN_RATE), self.MAX_RATE)

    @property
    def rate(self) -> float:
        return self._rate

    def update(self, n: int, seconds: float) -> None:
        if n < self._MIN_N or seconds <= 0:
            return
        measured = (float(n) * float(n)) / float(seconds)
        blended = self._ALPHA * measured + (1.0 - self._ALPHA) * self._rate
        self._rate = min(max(blended, self.MIN_RATE), self.MAX_RATE)


@dataclass
class BudgetContext:
    """Per-country view of the run's budget state (built fresh each country —
    ``remaining_run_s`` shrinks; ``rate`` is the shared estimator)."""

    country_budget_s: float          # 0 = no per-country budget
    remaining_run_s: float | None    # None = no run budget
    rate: "RateEstimator"
    min_cluster_n: int               # never cluster a slice thinner than this
    subproc_min_n: int               # 0 = never isolate in a subprocess


@dataclass(frozen=True)
class CountryPlan:
    action: str          # "cluster" | "defer"
    n_use: int
    capped: bool
    predicted_s: float
    hard_timeout_s: float  # 0 = no hard kill
    reason: str


def _hard_timeout(predicted_s: float, country_budget_s: float) -> float:
    """Backstop kill deadline: 3× the prediction, floored at 300s (tiny
    countries finish in ~1s — a false kill there would be pure noise), and
    ALWAYS capped at 1.5× the country budget — the documented worst case any
    single country can cost the night."""
    if country_budget_s <= 0:
        return 0.0
    ceiling = _TIMEOUT_BUDGET_MULT * country_budget_s
    return min(max(_TIMEOUT_HEADROOM * predicted_s, _TIMEOUT_FLOOR_S), ceiling)


def plan_country(n_eff: int, *, remaining_run_s: float | None,
                 country_budget_s: float, rate: float,
                 min_cluster_n: int) -> CountryPlan:
    """Decide what (if anything) of an n_eff-row country to cluster.

    Order of concerns:
      1. run budget exhausted → defer everything remaining;
      2. per-country budget → cap the input to its newest-first fitting slice
         (fit_cap), or defer when even the floor doesn't fit (a garbage
         sliver of a huge country is a gap, not a topic pass);
      3. first-fit vs the remaining run budget → defer a country whose
         PLANNED cost cannot fit what's left (a smaller one later may fit).
    """
    if remaining_run_s is not None and remaining_run_s <= 0:
        return CountryPlan("defer", 0, False, 0.0, 0.0, "run_budget_exhausted")

    n_use = n_eff
    capped = False
    if country_budget_s > 0:
        cap = fit_cap(country_budget_s, rate)
        if cap < n_eff:
            if cap < min_cluster_n:
                return CountryPlan("defer", 0, False,
                                   predict_seconds(min_cluster_n, rate), 0.0,
                                   "budget_below_floor")
            n_use = cap
            capped = True

    predicted = predict_seconds(n_use, rate)
    if remaining_run_s is not None and predicted > remaining_run_s:
        return CountryPlan("defer", n_use, capped, predicted, 0.0,
                           "run_budget_first_fit")

    return CountryPlan("cluster", n_use, capped, predicted,
                       _hard_timeout(predicted, country_budget_s), "fits")


def order_countries(ccs: list[str], priority: list[str]) -> list[str]:
    """Rotation fairness: countries deferred/timed-out LAST night go first
    tonight (in their given order), the rest keep their n-DESC order."""
    eligible = set(ccs)
    pri = [c for c in priority if c in eligible]
    pri_set = set(pri)
    return pri + [c for c in ccs if c not in pri_set]


# --------------------------------------------------------- tail reserve (P3)
#
# The rotation above is FAIR but not SUFFICIENT (threading-floor diagnosis,
# 2026-07-29 §P3): the 150-min weekday budget defers 130-154 countries a night
# and rotation only decides WHICH big countries run — a thin country is
# clustered on weekend-mode nights only (07-28 reached 16 countries, 07-29 32,
# neither reached the tail), so `persist_min=2` is unreachable for BO/ML by
# construction. The tail does not starve because it is expensive; it starves
# because the clock runs out on the head first.
#
# TAIL = countries whose cost is OVERHEAD, not clustering. The boundary is
# ``RateEstimator._MIN_N`` (2000): below it the rate estimator refuses to even
# learn from a country because it is "overhead-dominated" — the same class
# whose deferral buys the run nothing. Measured on the 07-27 full pass (152
# countries, Σn² = 12 470 M):
#
#     n < 1 000 →  69 countries, Σn² =  16 M (0.13 % of the pass), 229 clusters
#     n < 2 000 →  98 countries, Σn² =  86 M (0.69 % of the pass), 449 clusters
#     n < 4 000 → 116 countries, Σn² = 233 M (1.87 % of the pass), 667 clusters
#
# Every diagnosis witness sits 3-15× under the default (BO 745, ML 571, BF 373,
# MM 162, NE 133). Running the whole tail first costs the head ~0.7 % of its
# clustering budget — the real cost is per-country fetch + labeling overhead,
# which is why the lane is CAPPED by a reserve slice rather than trusted to be
# free, and ordered CHEAPEST-FIRST so the thin end always runs.
TAIL_MAX_N_DEFAULT = 2_000


def tail_reserve_seconds(run_budget_s: float, fraction: float) -> float:
    """Wall-seconds of the run budget the TAIL lane may spend before the head
    starts (a CEILING, not an allocation — the lane hands the rest back).

    0 = uncapped lane: the feature is off (fraction ≤ 0) or there is no run
    budget to slice. >1 clamps to the whole budget."""
    if fraction <= 0 or run_budget_s <= 0:
        return 0.0
    return float(run_budget_s) * min(float(fraction), 1.0)


def split_tail_first(ccs: list[str], sizes: dict[str, int], *,
                     tail_max_n: int) -> tuple[list[str], int]:
    """Reorder one pass's countries into TAIL-FIRST lanes.

    Returns ``(ordered, tail_cut)`` — ``ordered[:tail_cut]`` is the tail lane,
    ``ordered[tail_cut:]`` the head lane.

      - tail = ``sizes[cc] < tail_max_n``; an UNKNOWN size is head (never put
        an unmeasured country in the cheap lane);
      - the tail is sorted ASCENDING by n so the thinnest countries — the ones
        that cannot recover, and the ones the reserve is for — run first even
        if the slice runs out mid-lane;
      - the head keeps its incoming order EXACTLY (n-DESC, rotation priority
        first). It starts later; nothing else about it moves. US/TR must keep
        clustering: gate TF-4 pre-registers a ≤10 % no-regression bar on them,
        so a global cheapest-first sort — which would defer the US — is
        forbidden however tempting its symmetry.
      - ``list.sort`` is stable, so equal-n countries keep the rotation order
        they arrived in: the rotation file remains the tie-break inside each
        lane rather than being overridden by it.

    HONEST RESIDUAL: cheapest-first makes the thin end DETERMINISTIC (the point
    of P3) at the cost of making rotation non-binding inside the lane — if the
    reserve slice is chronically too small, the countries just under
    ``tail_max_n`` starve in the same way the head used to starve the tail.
    They are the richest countries in the lane, so the levers are a bigger
    slice or a lower ``tail_max_n``; the ``TAIL LANE`` ledger line reports the
    miss count every pass so the condition cannot go unnoticed.

    ``tail_max_n <= 0`` returns the input order with cut 0 (feature off)."""
    if tail_max_n <= 0:
        return list(ccs), 0
    tail: list[str] = []
    head: list[str] = []
    for cc in ccs:
        n = sizes.get(cc)
        (tail if n is not None and n < tail_max_n else head).append(cc)
    tail.sort(key=lambda c: sizes[c])
    return tail + head, len(tail)


# ------------------------------------------------------------ checkpoint I/O

@dataclass
class Checkpoint:
    snapshot_at: str            # ISO — adopted verbatim on resume
    hours: int                  # window; a different window never resumes
    started_at: str             # ISO — resume freshness guard
    next_base: int              # next per-country cluster_id block
    done: dict = field(default_factory=dict)   # cc -> "ok" | "no_clusters"
    complete: bool = False      # budget-stop/finish = complete (never resumed)
    version: int = _CHECKPOINT_VERSION


def save_checkpoint(path: Path | str, ck: Checkpoint) -> None:
    """Atomic (tmp+rename) — a crash mid-write must never corrupt the file."""
    path = Path(path)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(asdict(ck), ensure_ascii=False), encoding="utf-8")
    os.replace(tmp, path)


def load_checkpoint(path: Path | str) -> Checkpoint | None:
    """None on missing/corrupt/version-mismatch — never crash a nightly run
    over checkpoint state."""
    try:
        raw = json.loads(Path(path).read_text(encoding="utf-8"))
        if raw.get("version") != _CHECKPOINT_VERSION:
            return None
        return Checkpoint(
            snapshot_at=str(raw["snapshot_at"]),
            hours=int(raw["hours"]),
            started_at=str(raw["started_at"]),
            next_base=int(raw["next_base"]),
            done=dict(raw.get("done") or {}),
            complete=bool(raw.get("complete", False)),
        )
    except Exception:
        return None


def should_resume(ck: Checkpoint, *, now: datetime, hours: int,
                  max_age_h: float) -> bool:
    """Resume ONLY a fresh, incomplete, same-window checkpoint that banked at
    least one country. A budget-stop marks complete=True (deliberate partial
    commit, next night starts fresh); only crashes leave complete=False."""
    if ck.complete or ck.hours != hours or not ck.done:
        return False
    try:
        started = datetime.fromisoformat(ck.started_at)
    except ValueError:
        return False
    age_h = (now - started).total_seconds() / 3600.0
    return 0 <= age_h <= max_age_h


def empty_pass_is_benign(ck: Checkpoint, prev: Checkpoint | None, *,
                         now: datetime, max_age_h: float) -> bool:
    """Classify a pass that COMPLETED nothing (everything deferred/time-gapped).

    Benign — the runner must exit 0 and proceed to projection + the daily
    seal, because a fresh banked snapshot already exists — when either:

      - this run RESUMED a checkpoint with banked countries (``ck.done``
        non-empty: the adopted snapshot_at has committed rows), or
      - the previous cycle's checkpoint (``prev``) banked countries and is
        fresh (started within ``max_age_h``): the classic case is a
        watchdog/operator re-fire IMMEDIATELY after a complete cycle — the
        new pass defers everything, but the just-sealed-worthy snapshot is
        sitting in the database waiting for post-steps.

    True misconfig (caller keeps exit 1, projection skipped): nothing banked
    this run AND no fresh prior bank — the budget cannot fit ANY country
    from a cold start (2026-07-19: this guard used to fire for BOTH cases,
    silently starving the sealed edition after every benign re-fire).
    ``prev.complete`` is deliberately ignored: banked rows exist whether the
    previous run budget-stopped or crashed mid-pass."""
    if ck.done:
        return True
    if prev is None or not prev.done:
        return False
    try:
        started = datetime.fromisoformat(prev.started_at)
    except ValueError:
        return False
    age_h = (now - started).total_seconds() / 3600.0
    return 0 <= age_h <= max_age_h


# -------------------------------------------------------------- rotation I/O

def save_rotation(path: Path | str, ccs: list[str]) -> None:
    path = Path(path)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps({"priority": list(ccs)}), encoding="utf-8")
    os.replace(tmp, path)


def load_rotation(path: Path | str) -> list[str]:
    try:
        raw = json.loads(Path(path).read_text(encoding="utf-8"))
        return [str(c) for c in raw.get("priority") or []]
    except Exception:
        return []

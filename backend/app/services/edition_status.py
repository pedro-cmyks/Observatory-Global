"""Graded seal status — contract `atlas-edition-status-v1`.

WHY THIS EXISTS. The seal used to answer one unreachable question: is every
readiness dimension `ready`? Two of the five (`who`, `where`) were computed as
an all-nodes conjunction over the edition's 12 story nodes, while per-node
attribution runs ~50% (verified subjects come from NER — the #184 throughput
backlog — and verified subject countries from subject geography, #238). An
all-or-nothing conjunction over 12 nodes turns ~50% per-node coverage into a
~0% edition pass rate (0.5^12 ~= 0.02%), and it did: **25 of 25 sealed editions
carried `status='degraded'`**, so the Brief served live threads and the seal's
correct Pareto selection never reached a reader. The one edition that DID reach
unanimity (2026-07-13, 12/12 actors and 12/12 geography) still sealed
`degraded` — its `data_lag_hours` was 8.455 > 6.

WHAT REPLACED IT (Pedro, policy a+b). Readiness reports the FRACTION it
measured (`{ready, total, fraction, basis}` per dimension) and the status is
graded from that fraction against bars taken from the real histogram — the
pooled `who`+`where` distribution over the 21 non-empty sealed editions
(42 dimension-points, quantised to k/12):

    k/12:   0   2   3   4   5   6   7   8   9  10  12
    count:  2   1   1   4  11   9   6   3   2   1   2

Every step from 4/12 to 10/12 is occupied — there is NO natural split in the
body, so the bars are the pooled TERTILES (0.417 / 0.556), each placed in the
adjacent EMPTY interval so a one-node wobble cannot flip an edition's grade:

    PARTIAL bar 0.40  in the empty (0.333, 0.417) interval
    FULL    bar 0.55  in the empty (0.500, 0.583) interval

They reproduce the tertile split exactly: >=0.55 -> 14/42 (33.3%),
[0.40, 0.55) -> 20/42 (47.6%), <0.40 -> 8/42 (19.0%).

RULES THAT ARE NOT NEGOTIABLE HERE.
  * `data_lag_hours` is a labelled FACT. Above the bar it adds the `data_lag`
    reason and nothing else — it never lowers a grade and never voids a seal.
  * `SEAL_FAILED` (emitted by the runner into the reliability ledger) remains
    the ONLY night-voiding marker. Nothing in this module voids a night.
  * `degraded` is never emitted. It is only ACCEPTED, from rows sealed before
    this contract, and remapped readably by `normalize_stored_status`.

Measured (`docs/research/brief-daily/2026-08-12-m0-measurement.md` addendum §D
+ the 25-edition fraction histogram): under these bars the 25 stored editions
grade 6 full / 10 partial / 9 thin (4 of the thin are structurally empty
editions with zero story nodes).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping

EDITION_STATUS_CONTRACT = "atlas-edition-status-v1"

# Measured bars — see the histogram in this module's docstring. Do not round
# them without re-running the measurement: 0.42 would flip ten editions,
# because 5/12 = 0.4166... sits directly under it.
READINESS_PARTIAL_BAR = 0.40
READINESS_FULL_BAR = 0.55

# Freshness is reported, never enforced: the bar exists so the reason can be
# named, not so an edition can be voided by it.
DATA_LAG_BAR_HOURS = 6.0

# `why` is excluded by construction: it is forced to `partial` for every
# edition (Atlas never claims causality), so requiring it would recreate the
# unreachable binary on another axis.
REQUIRED_DIMENSIONS = ("who", "what", "when", "where", "how")

SEALED_FULL = "sealed_full"
SEALED_PARTIAL = "sealed_partial"
SEALED_THIN = "sealed_thin"
STATUS_VALUES = (SEALED_FULL, SEALED_PARTIAL, SEALED_THIN)

_RANK = {SEALED_FULL: 2, SEALED_PARTIAL: 1, SEALED_THIN: 0}

# Rows sealed before this contract. The remap keeps serving readable; the
# `legacy_status_not_graded` reason keeps it from being read as a measurement.
LEGACY_STATUS_MAP = {"ready": SEALED_FULL, "degraded": SEALED_PARTIAL}


@dataclass(frozen=True)
class EditionGrade:
    status: str
    reasons: list[str] = field(default_factory=list)
    dimensions: dict[str, dict[str, Any]] = field(default_factory=dict)
    facts: dict[str, Any] = field(default_factory=dict)
    contract: str = EDITION_STATUS_CONTRACT


def _get(item: Any, key: str, default: Any = None) -> Any:
    if isinstance(item, Mapping):
        return item.get(key, default)
    return getattr(item, key, default)


def _fraction(item: Any) -> float | None:
    """The measured fraction for one dimension, or None when unmeasured."""
    measured = _get(item, "measured")
    if measured is None:
        return None
    total = _get(measured, "total") or 0
    if not total:
        return None
    fraction = _get(measured, "fraction")
    if isinstance(fraction, (int, float)):
        return float(fraction)
    ready = _get(measured, "ready") or 0
    return float(ready) / float(total)


def _grade_dimension(dim: str, item: Any) -> tuple[str, str | None, dict[str, Any]]:
    """(status, reason, detail) for one readiness dimension."""
    if item is None:
        return SEALED_THIN, f"{dim}_missing", {"fraction": None, "status": "missing"}

    fraction = _fraction(item)
    item_status = _get(item, "status")
    detail: dict[str, Any] = {"fraction": fraction, "status": item_status}
    measured = _get(item, "measured")
    if measured is not None:
        detail["ready"] = _get(measured, "ready")
        detail["total"] = _get(measured, "total")
        detail["basis"] = _get(measured, "basis")

    if fraction is None:
        # Nothing measurable (no denominator). Fall back to the dimension's own
        # verdict rather than inventing a fraction for it.
        if item_status == "missing":
            return SEALED_THIN, f"{dim}_missing", detail
        if item_status == "partial":
            return SEALED_PARTIAL, f"{dim}_below_full_bar", detail
        return SEALED_FULL, None, detail

    if fraction >= READINESS_FULL_BAR:
        return SEALED_FULL, None, detail
    if fraction >= READINESS_PARTIAL_BAR:
        return SEALED_PARTIAL, f"{dim}_below_full_bar", detail
    if fraction <= 0 and item_status == "missing":
        return SEALED_THIN, f"{dim}_missing", detail
    return SEALED_THIN, f"{dim}_below_bar", detail


def grade_edition(
    readiness: Mapping[str, Any] | None,
    completion: Mapping[str, Any] | None = None,
) -> EditionGrade:
    """Grade one sealed edition from its MEASURED readiness fractions.

    `readiness` accepts either the in-process `ReadinessItem` models or the
    stored (jsonb) dict shape, so the same grading runs at seal time and over
    an artifact read back from `atlas_daily_editions`.
    """
    readiness = readiness or {}
    completion = completion or {}

    status = SEALED_FULL
    reasons: list[str] = []
    dimensions: dict[str, dict[str, Any]] = {}

    for dim in REQUIRED_DIMENSIONS:
        dim_status, reason, detail = _grade_dimension(dim, readiness.get(dim))
        dimensions[dim] = {**detail, "grade": dim_status}
        if reason:
            reasons.append(reason)
        if _RANK[dim_status] < _RANK[status]:
            status = dim_status

    # Evidence incompleteness is a real shortfall of the edition's own
    # receipts, so it caps the grade — but it never voids the seal. Measured:
    # 0 of the 25 stored editions ever failed this arm.
    completion_incomplete = bool(completion.get("receipt_fetch_error")) or not completion.get(
        "cursor_exhausted", True
    )
    if completion_incomplete:
        reasons.append("receipts_incomplete")
        if status == SEALED_FULL:
            status = SEALED_PARTIAL

    data_lag = completion.get("data_lag_hours")
    data_lag = float(data_lag) if isinstance(data_lag, (int, float)) else None
    if data_lag is not None and data_lag > DATA_LAG_BAR_HOURS:
        # A labelled fact, never a voider: the one edition in 25 that reached
        # unanimity sealed `degraded` on this alone.
        reasons.append("data_lag")

    facts = {
        "data_lag_hours": data_lag,
        "data_lag_bar_hours": DATA_LAG_BAR_HOURS,
        "readiness_partial_bar": READINESS_PARTIAL_BAR,
        "readiness_full_bar": READINESS_FULL_BAR,
        "receipt_fetch_error": completion.get("receipt_fetch_error"),
        "cursor_exhausted": completion.get("cursor_exhausted"),
    }
    return EditionGrade(status=status, reasons=reasons, dimensions=dimensions, facts=facts)


def normalize_stored_status(stored: str | None) -> dict[str, Any]:
    """Read one stored `atlas_daily_editions.status` in the graded vocabulary.

    Serving must not break on the 25 rows sealed under the old binary, and the
    remap must never be mistaken for a measurement — hence the explicit
    `legacy_status_not_graded` reason. Re-grading a legacy row honestly means
    re-running `grade_edition` over its stored package, which the request path
    deliberately does not do.
    """
    if stored in STATUS_VALUES:
        return {"status": stored, "stored_status": stored, "reasons": []}
    if stored in LEGACY_STATUS_MAP:
        return {
            "status": LEGACY_STATUS_MAP[stored],
            "stored_status": stored,
            "reasons": ["legacy_status_not_graded"],
        }
    if stored is None:
        return {"status": SEALED_THIN, "stored_status": None, "reasons": ["no_stored_status"]}
    return {
        "status": SEALED_THIN,
        "stored_status": stored,
        "reasons": ["unrecognized_stored_status"],
    }

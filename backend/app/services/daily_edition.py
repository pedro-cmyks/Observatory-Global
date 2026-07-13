"""Daily-edition adapter over Atlas's existing shared movement contract.

No semantic category, harm-potential flag, or raw-volume importance judgment is
made here.  `topic_movement` is authoritative; relative changed_10h is the
documented same-lineage fallback.  The score is a current-state ordering for a
finite newspaper layout, never a prediction, and the complete ledger travels
with the selected rows.
"""
from __future__ import annotations

from datetime import datetime, timezone
import math
import re
from typing import Any, Literal

from pydantic import BaseModel, Field


_DAILY_CANDIDATE_BATCH_SQL = """
SELECT
    dt.id,
    ('dynamic-topic-' || dt.id::text) AS thread_id,
    dt.label,
    dt.category,
    dt.crisis_relevant,
    dt.is_roundup,
    dt.is_junk,
    dt.mean_cohesion AS coherence,
    dt.noise_rate,
    dt.first_seen,
    dt.last_seen,
    COALESCE(dt.agg_n_signals, 0)::int AS current_signals,
    0::int AS prior_signals,
    0::int AS source_breadth,
    0::int AS source_origins,
    NULL::int AS fallback_changed_10h,
    movement.velocity AS kalman_velocity,
    movement.surprise AS kalman_surprise,
    movement.uncertainty AS kalman_uncertainty,
    COALESCE(movement.n_observations, 0) AS kalman_observations
FROM dynamic_topics dt
LEFT JOIN LATERAL (
    SELECT velocity, surprise, uncertainty, n_observations
    FROM topic_movement
    WHERE topic_id = ('dynamic-topic-' || dt.id::text)
      AND engine_version = 'movement-kalman-v1'
    ORDER BY window_end DESC
    LIMIT 1
) movement ON TRUE
WHERE dt.state = 'active'
  AND dt.parent_id IS NULL
  AND dt.last_seen >= $4::timestamptz - ($1::int * INTERVAL '1 hour')
  AND dt.last_seen <= $4::timestamptz
  AND dt.id > $2
ORDER BY dt.id
LIMIT $3
"""


class DailyCandidate(BaseModel):
    thread_id: str
    label: str
    category: str | None = None
    crisis_relevant: bool | None = None
    is_roundup: bool = False
    is_junk: bool = False
    current_signals: int = 0
    prior_signals: int = 0
    source_breadth: int = 0
    source_origins: int = 0
    fallback_changed_10h: int | None = None
    coherence: float | None = None
    noise_rate: float | None = None
    kalman_velocity: float | None = None
    kalman_surprise: float | None = None
    kalman_uncertainty: float | None = None
    kalman_observations: int = 0
    first_seen: datetime | None = None
    last_seen: datetime | None = None
    snapshot: dict[str, Any] = Field(default_factory=dict)


def apply_sample_coverage(
    candidates: list[DailyCandidate],
    *,
    sources_by_topic: dict[str, set[str]],
    origins_by_topic: dict[str, set[str]],
) -> list[DailyCandidate]:
    """Attach measured receipt-sample breadth without mutating candidates.

    The counts are confidence dimensions, not importance or exhaustive source
    counts. The sampling method and completion travel with the package.
    """
    return [
        candidate.model_copy(update={
            "source_breadth": len(sources_by_topic.get(candidate.thread_id, set())),
            "source_origins": len(origins_by_topic.get(candidate.thread_id, set())),
        })
        for candidate in candidates
    ]


class DailyLedgerRow(BaseModel):
    thread_id: str
    label: str
    status: Literal["selected", "downranked", "unresolved"]
    score: float
    components: dict[str, Any]
    reason_codes: list[str]


class DailyEditionSelection(BaseModel):
    selected_ids: list[str]
    ledger: list[DailyLedgerRow]
    completion: dict[str, int | bool]
    method: dict[str, Any]


async def fetch_daily_candidates(
    conn,
    *,
    hours: int = 24,
    batch_size: int = 100,
    edition_end: datetime | None = None,
) -> tuple[list[DailyCandidate], dict[str, Any]]:
    """Cursor-exhaust the eligible daily story universe.

    `batch_size` bounds each database operation, not the semantic result. The
    cursor continues until an empty batch and completion explicitly says so.
    """
    cursor = 0
    batches = 0
    rows_scanned = 0
    candidates: list[DailyCandidate] = []
    edition_end = edition_end or datetime.now(timezone.utc)
    if edition_end.tzinfo is None:
        edition_end = edition_end.replace(tzinfo=timezone.utc)
    while True:
        rows = await conn.fetch(
            _DAILY_CANDIDATE_BATCH_SQL, hours, cursor, batch_size, edition_end,
        )
        batches += 1
        if not rows:
            break
        rows_scanned += len(rows)
        for raw in rows:
            data = dict(raw)
            data.pop("id", None)
            candidate = DailyCandidate.model_validate(data)
            if candidate.current_signals > 0:
                candidates.append(candidate)
        cursor = max(int(dict(row)["id"]) for row in rows)
    return candidates, {
        "batches": batches,
        "rows_scanned": rows_scanned,
        "candidate_count": len(candidates),
        "edition_end": edition_end.isoformat(),
        "cursor_exhausted": True,
        "truncated": False,
    }


def _candidate_state(
    row: DailyCandidate,
    *,
    measured_at: datetime,
) -> tuple[dict[str, float], dict[str, Any], list[str]]:
    reasons: list[str] = []
    if row.kalman_velocity is not None and row.kalman_observations >= 3:
        movement = float(row.kalman_velocity)
        surprise = max(0.0, float(row.kalman_surprise or 0.0))
        uncertainty = max(0.0, float(row.kalman_uncertainty or 0.0))
        movement_source = "topic_movement"
        reasons.append("kalman_velocity")
        if surprise:
            reasons.append("kalman_surprise")
        if uncertainty >= 1.0:
            reasons.append("uncertainty_penalty")
    else:
        if row.fallback_changed_10h is not None:
            movement = float(row.fallback_changed_10h) / max(row.current_signals, 1)
            fallback_reason = "relative_changed_10h_fallback"
        elif row.prior_signals or row.current_signals:
            denominator = max(row.current_signals + row.prior_signals, 1)
            movement = (row.current_signals - row.prior_signals) / denominator
            fallback_reason = "relative_changed_10h_fallback"
        else:
            movement = 0.0
            fallback_reason = "movement_unavailable"
        surprise = 0.0
        # Fallback is less certain by construction; it remains usable and named.
        uncertainty = 1.0
        movement_source = (
            "relative_changed_10h" if fallback_reason == "relative_changed_10h_fallback"
            else "unavailable"
        )
        reasons.extend([fallback_reason, "uncertainty_penalty"])

    # Volume is only a saturating evidence-sufficiency floor.  Once twenty
    # receipts exist, 40 and 40,000 signals receive exactly the same factor.
    evidence_floor = min(1.0, max(0, row.current_signals) / 20.0)
    outlet_breadth = min(1.0, max(0, row.source_breadth) / 4.0)
    origin_breadth = min(1.0, max(0, row.source_origins) / 3.0)
    source_confidence = 0.75 * outlet_breadth + 0.25 * origin_breadth
    if row.source_breadth < 2:
        reasons.append("thin_source_breadth")
    coherence = max(0.0, min(1.0, float(row.coherence if row.coherence is not None else 0.5)))
    if row.noise_rate is not None:
        coherence *= max(0.0, min(1.0, 1.0 - float(row.noise_rate)))
    if row.is_roundup:
        coherence = 0.0
        reasons.append("do_not_promote_roundup")
    if row.is_junk:
        coherence = 0.0
        reasons.append("junk_quality_lane")
    if row.source_breadth == 0:
        reasons.append("coverage_breadth_not_precomputed")
    uncertainty_confidence = 1.0 / (1.0 + uncertainty)

    # The edition keeps a vector. Rising and decaying quickly are both movement;
    # trend direction remains visible in `velocity`. No semantic class decides
    # whether that state matters.
    movement_now = math.tanh(abs(movement))
    surprise_now = surprise / (1.0 + surprise)
    evidence_quality = evidence_floor * coherence
    persistence_days = 0.0
    if row.first_seen is not None:
        first_seen = row.first_seen
        if first_seen.tzinfo is None:
            first_seen = first_seen.replace(tzinfo=timezone.utc)
        persistence_days = max(0.0, (measured_at - first_seen).total_seconds() / 86_400)
    persistence = min(1.0, persistence_days / 7.0)
    state = {
        "movement_magnitude": movement_now,
        "surprise": surprise_now,
        "measurement_confidence": uncertainty_confidence,
        "evidence_quality": evidence_quality,
        "coverage_breadth": source_confidence,
        "persistence": persistence,
    }
    components = {
        "movement_source": movement_source,
        "velocity": round(movement, 6),
        "surprise": round(surprise, 6),
        "uncertainty": round(uncertainty, 6),
        "evidence_floor": round(evidence_floor, 6),
        "source_confidence": round(source_confidence, 6),
        "coherence_confidence": round(coherence, 6),
        "persistence_days": round(persistence_days, 4),
        "state_vector": {key: round(value, 6) for key, value in state.items()},
        "category_weight": 0.0,
        "crisis_relevant_weight": 0.0,
        "raw_volume_importance_weight": 0.0,
    }
    return state, components, reasons


def _dominates(a: dict[str, float], b: dict[str, float]) -> bool:
    keys = tuple(a)
    return all(a[key] >= b[key] for key in keys) and any(a[key] > b[key] for key in keys)


def _pareto_fronts(states: list[dict[str, float]]) -> list[int]:
    fronts = [-1] * len(states)
    remaining = set(range(len(states)))
    front_n = 0
    while remaining:
        current = [
            i for i in sorted(remaining)
            if not any(_dominates(states[j], states[i]) for j in remaining if j != i)
        ]
        # Defensive: floating comparisons should always leave at least one
        # nondominated row, but never turn a bad numeric input into a loop.
        if not current:
            current = sorted(remaining)
        for i in current:
            fronts[i] = front_n
            remaining.remove(i)
        front_n += 1
    return fronts


def _equal_rank_aggregate(states: list[dict[str, float]]) -> list[float]:
    """Scale-free, equal-dimension percentile aggregation for deterministic
    ordering inside Pareto fronts. It is a disclosed layout tie-break, not an
    editorial truth score."""
    if not states:
        return []
    keys = tuple(states[0])
    totals = [0.0] * len(states)
    for key in keys:
        unique = sorted({state[key] for state in states})
        rank = {value: (unique.index(value) / max(1, len(unique) - 1)) for value in unique}
        for i, state in enumerate(states):
            totals[i] += rank[state[key]]
    return [total / len(keys) for total in totals]


def order_spine_by_publishability(
    selected_ids: list[str],
    publishability_by_id: dict[str, dict[str, bool]],
) -> list[tuple[str, str]]:
    """Reorder the already-selected daily stories for the newspaper spine so the
    lead and top slots are the most publishable — subject-geography verified and
    not an incoherent grab-bag umbrella — while preserving the editorial rank
    within each tier. Pure layout: every selected story stays, nothing is
    dropped, and each placement is reason-coded. Returns (thread_id,
    layout_reason) in spine order.
    """
    reason_by_tier = {
        0: "spine_lead_subject_geography_verified",
        1: "spine_supporting",
        2: "spine_demoted_grab_bag_umbrella",
    }

    def tier(thread_id: str) -> int:
        flags = publishability_by_id.get(thread_id) or {}
        if flags.get("grab_bag"):
            return 2
        if flags.get("subject_verified"):
            return 0
        return 1

    ordered = sorted(
        enumerate(selected_ids), key=lambda item: (tier(item[1]), item[0]),
    )
    return [(thread_id, reason_by_tier[tier(thread_id)]) for _, thread_id in ordered]


def select_daily_edition(
    candidates: list[DailyCandidate],
    *,
    display_slots: int = 12,
    receipt_eligible_ids: set[str] | None = None,
    receipt_checked_ids: set[str] | None = None,
    quality_ledger_by_id: dict[str, dict[str, Any]] | None = None,
) -> DailyEditionSelection:
    measured_at = max(
        (row.last_seen for row in candidates if row.last_seen is not None),
        default=datetime.now(timezone.utc),
    )
    if measured_at.tzinfo is None:
        measured_at = measured_at.replace(tzinfo=timezone.utc)
    prepared: list[tuple[DailyCandidate, dict[str, float], dict[str, Any], list[str]]] = []
    for candidate in candidates:
        state, components, reasons = _candidate_state(candidate, measured_at=measured_at)
        prepared.append((candidate, state, components, reasons))
    states = [row[1] for row in prepared]
    fronts = _pareto_fronts(states)
    aggregates = _equal_rank_aggregate(states)
    scored: list[tuple[int, float, DailyCandidate, dict[str, Any], list[str]]] = []
    for index, (candidate, _state, components, reasons) in enumerate(prepared):
        components = dict(components)
        components["pareto_front"] = fronts[index]
        components["rank_aggregate"] = round(aggregates[index], 9)
        scored.append((fronts[index], aggregates[index], candidate, components, reasons))
    scored.sort(key=lambda item: (
        -item[0],
        item[1],
        item[2].last_seen.isoformat() if item[2].last_seen else "",
        item[2].thread_id,
    ), reverse=True)

    selected_ids: list[str] = []
    selected_label_owner: dict[str, str] = {}
    duplicate_of: dict[str, str] = {}
    for _front, _aggregate, candidate, _components, _reasons in scored:
        if receipt_eligible_ids is not None and candidate.thread_id not in receipt_eligible_ids:
            continue
        normalized_label = re.sub(r"\s+", " ", candidate.label.strip().casefold())
        if normalized_label in selected_label_owner:
            duplicate_of[candidate.thread_id] = selected_label_owner[normalized_label]
            continue
        if len(selected_ids) >= max(0, display_slots):
            continue
        selected_ids.append(candidate.thread_id)
        selected_label_owner[normalized_label] = candidate.thread_id
    selected_set = set(selected_ids)
    ledger: list[DailyLedgerRow] = []
    for front, aggregate, candidate, components, reasons in scored:
        status: Literal["selected", "downranked", "unresolved"] = (
            "selected" if candidate.thread_id in selected_set else "downranked"
        )
        reason_codes = list(reasons)
        quality_receipt = (
            quality_ledger_by_id.get(candidate.thread_id)
            if quality_ledger_by_id is not None else None
        )
        if quality_receipt is not None:
            components = dict(components)
            components["publication_evidence_fit"] = quality_receipt
            reason_codes.extend(quality_receipt.get("reason_codes") or [])
        reason_codes.extend([f"pareto_front_{front}", "equal_dimension_rank_aggregation"])
        if status == "selected":
            reason_codes.append("daily_layout_selected")
        else:
            reason_codes.append("layout_disclosure")
        if candidate.thread_id in duplicate_of:
            reason_codes.extend([
                "duplicate_label_sibling",
                f"represented_by:{duplicate_of[candidate.thread_id]}",
            ])
        if (
            receipt_checked_ids is not None
            and candidate.thread_id in receipt_checked_ids
            and receipt_eligible_ids is not None
            and candidate.thread_id not in receipt_eligible_ids
        ):
            reason_codes.append("no_current_receipt_sample")
        ledger.append(DailyLedgerRow(
            thread_id=candidate.thread_id,
            label=candidate.label,
            status=status,
            score=round(aggregate, 9),
            components=components,
            reason_codes=reason_codes,
        ))

    completion: dict[str, int | bool] = {
        "candidate_count": len(candidates),
        "scored_count": len(scored),
        "selected_count": len(selected_ids),
        "downranked_count": len(scored) - len(selected_ids),
        "unresolved_count": 0,
        "truncated": False,
    }
    if receipt_checked_ids is not None:
        completion["receipt_checked_count"] = len(receipt_checked_ids)
    if receipt_eligible_ids is not None:
        completion["receipt_eligible_count"] = len(receipt_eligible_ids)

    return DailyEditionSelection(
        selected_ids=selected_ids,
        ledger=ledger,
        completion=completion,
        method={
            "movement_provider": "topic_movement movement-kalman-v1",
            "fallback": "relative_changed_10h_same_signals_v2_lineage",
            "prediction_claim": False,
            "selection_method": "pareto_frontier_equal_rank_aggregation_v1",
            "state_dimensions": [
                "movement_magnitude", "surprise", "measurement_confidence",
                "evidence_quality", "coverage_breadth", "persistence",
            ],
            "rank_aggregation": "equal percentile rank within disclosed Pareto fronts",
            "measured_at": measured_at.isoformat(),
            "category_weight": 0.0,
            "crisis_relevant_weight": 0.0,
            "raw_volume_importance_weight": 0.0,
            "display_slots": display_slots,
            "omission_ledger": "complete",
            "receipt_eligibility": (
                "current_window_snapshot_sample_required"
                if receipt_eligible_ids is not None else "not_applied"
            ),
        },
    )

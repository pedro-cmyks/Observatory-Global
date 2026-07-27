"""Track C3 — the read layer over the C1 edge-snapshot store.

Spec: docs/superpowers/specs/2026-07-21-time-axis-versioned-relationships.md
§2 (two contexts: ambient REPLAY vs focused DIFF), §5(a), §7 (honesty).
Sibling: `app/services/edge_diff.py` (Track C2 — the pure churn-vs-narrative
classifier this router calls).

Two endpoints, both read-only over `topic_edge_snapshots` /
`entity_backbone_edges` (migration 089, Track C1) — neither recomputes the
walk graph nor touches any existing serving path:

  - GET /api/v2/edges/replay            — the ambient REPLAY (spec §2): the
    kinship edge set at the snapshot nearest a given date. Extends
    `GET /api/v2/map/replay` (node/heat volume scrub, `app/routers/geo.py`)
    to EDGES, the same "reconstructed from snapshots" honesty model.
  - GET /api/v2/focus/{ref}/edge-diff   — the focused DIFF (spec §2): for one
    topic, everything that changed since a date — formed / weakened /
    narrative-change / substrate-churn (Track C2's classifier) — plus any
    DORMANT backbone relationships touching it. This is what a future
    activity-timeline diff render (C4, not built here) would consume.

Honest-empty by construction (spec §7): no DB, no snapshot near the date, or
a ref that resolves to nothing all return a 200 with an explicit `reason`,
never a 500 or a fabricated row.
"""
from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, HTTPException, Query

from app import db
from app.main_v2 import app
from app.services.edge_diff import (
    DormantRelationship,
    EdgeChange,
    classify_dormant_relationships,
    classify_edge_changes,
    describe_snapshot_interval,
    parse_dynamic_topic_id,
    snapshot_interval_out,
    strip_focus_suffix,
)
from app.services.subjects import classify_subject
from app.services.thread_intelligence import topic_members_engine_version

router = APIRouter()
logger = logging.getLogger(__name__)

REPLAY_CONTRACT = "edges-replay-v0"
DIFF_CONTRACT = "focus-edge-diff-v0"

_REPLAY_CACHE_TTL_S = 900     # 15 min — a snapshot pass is at most nightly
_DIFF_CACHE_TTL_S = 300       # 5 min — bounded scans, don't recompute per click

# Entity-backbone window, matching the writer's default rolling window
# (`scripts/snapshot_topic_edges.py --window-hours`, default 720h = 30d) so
# "currently appears in" means the same thing on both sides of the join.
_ENTITY_WINDOW_HOURS = 720
# Bound on how many backbone partner entities feed the dormant check per
# focus (mindful — mirrors the writer's own DEFAULT_TOP_ENTITIES_PER_TOPIC /
# DEFAULT_MAX_BACKBONE_EDGES sparsity discipline, applied per-request here).
_DORMANT_BACKBONE_LIMIT = 50
_FOCUS_ENTITIES_LIMIT = 8


async def _cache_get(key: str) -> Optional[dict]:
    if not hasattr(app.state, "redis") or not app.state.redis:
        return None
    try:
        raw = await app.state.redis.get(key)
        return json.loads(raw) if raw else None
    except Exception as exc:
        logger.debug("edges cache read failed: %s", exc)
        return None


async def _cache_set(key: str, payload: dict, ttl: int) -> None:
    if not hasattr(app.state, "redis") or not app.state.redis:
        return
    try:
        await app.state.redis.setex(key, ttl, json.dumps(payload, default=str))
    except Exception as exc:
        logger.debug("edges cache write failed: %s", exc)


def _parse_iso(raw: str, *, param: str) -> datetime:
    try:
        dt = datetime.fromisoformat(raw.strip())
    except ValueError:
        raise HTTPException(status_code=422, detail=f"{param} must be an ISO-8601 timestamp")
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


def _edge_out(r) -> dict:
    return {
        "identity_key_a": r["identity_key_a"],
        "identity_key_b": r["identity_key_b"],
        "topic_id_a": r["topic_id_a"],
        "topic_id_b": r["topic_id_b"],
        "degree": r["degree"],
        "weight": float(r["weight"]),
        "basis": r["basis"],
    }


# ---------------------------------------------------------------- C3(a) replay
_NEAREST_SNAPSHOT_SQL = """
    SELECT snapshot_at
    FROM topic_edge_snapshots
    GROUP BY snapshot_at
    ORDER BY abs(extract(epoch FROM (snapshot_at - $1::timestamptz)))
    LIMIT 1
"""

_EDGES_AT_SQL = """
    SELECT identity_key_a, identity_key_b, topic_id_a, topic_id_b, degree, weight, basis
    FROM topic_edge_snapshots
    WHERE snapshot_at = $1
    ORDER BY weight DESC
    LIMIT $2
"""

# The neighbouring stored passes around the served one. A scrubber stepping
# snapshot-to-snapshot is performing an implicit diff, so it has to know how
# wide its next/previous step actually is — 2026-07-25 was deleted, making
# 07-24 -> 07-26 a 48h step between CONSECUTIVE rows.
_NEIGHBOUR_SNAPSHOTS_SQL = """
    SELECT
      (SELECT MAX(snapshot_at) FROM topic_edge_snapshots WHERE snapshot_at < $1) AS prev_at,
      (SELECT MIN(snapshot_at) FROM topic_edge_snapshots WHERE snapshot_at > $1) AS next_at
"""


@router.get("/api/v2/edges/replay")
async def edges_replay(
    at: str = Query(..., description="ISO-8601 date/time to replay the kinship graph at"),
    limit: int = Query(500, ge=1, le=2000),
):
    """Ambient REPLAY (spec §2): the kinship edge set nearest `at`, read
    straight from the C1 snapshot store — the edge extension of
    `/api/v2/map/replay`'s node/heat volume scrub. Never recomputes the walk
    graph; a pure point-in-time read.

    Honesty (spec §7): `matched_snapshot_at` + `distance_hours` are always
    returned alongside the edges so the caller (and the UI scrubber) knows
    exactly how far the served pass is from the requested date — "absent =
    absent, never faked": when the store has NO snapshot at all, or the DB is
    unavailable, the response says so explicitly (`reason`) rather than
    silently serving nothing.

    This endpoint reads ONE pass; it does not diff. But a scrubber stepping
    from pass to pass is diffing implicitly, and stored passes are NOT evenly
    spaced (2026-07-25's half-written snapshot was deleted, so 07-24 -> 07-26
    are consecutive rows 48h apart). `previous_snapshot_at`/`next_snapshot_at`
    plus their `interval_from_previous`/`interval_to_next` descriptors let the
    caller label a wide step as wide instead of animating it like a day.
    """
    requested = _parse_iso(at, param="at")
    cache_key = f"edges:replay:v0:{requested.isoformat()}:{limit}"
    cached = await _cache_get(cache_key)
    if cached is not None:
        return cached

    empty = {
        "contract": REPLAY_CONTRACT,
        "requested_at": requested.isoformat(),
        "matched_snapshot_at": None,
        "distance_hours": None,
        "previous_snapshot_at": None,
        "next_snapshot_at": None,
        "interval_from_previous": None,
        "interval_to_next": None,
        "basis": "reconstructed from snapshots",
        "edges": [],
    }
    if db.pool is None:
        return {**empty, "reason": "db_unavailable"}

    try:
        async with db.pool.acquire() as conn:
            await conn.execute("SET statement_timeout = 8000")
            nearest = await conn.fetchrow(_NEAREST_SNAPSHOT_SQL, requested)
            if nearest is None:
                return {**empty, "reason": "no_snapshots_stored"}
            snap_at = nearest["snapshot_at"]
            rows = await conn.fetch(_EDGES_AT_SQL, snap_at, limit)
            neighbours = await conn.fetchrow(_NEIGHBOUR_SNAPSHOTS_SQL, snap_at)
    except Exception as exc:  # pragma: no cover - defensive I/O
        logger.warning("edges/replay query failed: %s", str(exc)[:200])
        return {**empty, "reason": "db_error"}

    prev_at = neighbours["prev_at"] if neighbours else None
    next_at = neighbours["next_at"] if neighbours else None
    distance_hours = round(abs((snap_at - requested).total_seconds()) / 3600.0, 2)
    payload = {
        "contract": REPLAY_CONTRACT,
        "requested_at": requested.isoformat(),
        "matched_snapshot_at": snap_at.isoformat(),
        "distance_hours": distance_hours,
        # neighbouring stored passes — the scrub step is the implicit diff
        "previous_snapshot_at": prev_at.isoformat() if prev_at else None,
        "next_snapshot_at": next_at.isoformat() if next_at else None,
        "interval_from_previous": (
            snapshot_interval_out(describe_snapshot_interval(prev_at, snap_at))
            if prev_at else None
        ),
        "interval_to_next": (
            snapshot_interval_out(describe_snapshot_interval(snap_at, next_at))
            if next_at else None
        ),
        "basis": "reconstructed from snapshots",
        "edges": [_edge_out(r) for r in rows],
    }
    await _cache_set(cache_key, payload, _REPLAY_CACHE_TTL_S)
    return payload


# ---------------------------------------------------------------- C3(b) diff
_RESOLVE_BY_ID_SQL = "SELECT id, identity_key, state FROM dynamic_topics WHERE id = $1"
_RESOLVE_BY_KEY_SQL = "SELECT id, identity_key, state FROM dynamic_topics WHERE identity_key = $1"

_LATEST_SNAPSHOT_SQL = "SELECT MAX(snapshot_at) AS s FROM topic_edge_snapshots"
_NEAREST_SNAPSHOT_BEFORE_SQL = """
    SELECT snapshot_at
    FROM topic_edge_snapshots
    GROUP BY snapshot_at
    ORDER BY abs(extract(epoch FROM (snapshot_at - $1::timestamptz)))
    LIMIT 1
"""

_FOCUS_EDGES_AT_SQL = """
    SELECT identity_key_a, identity_key_b, topic_id_a, topic_id_b, degree, weight, basis
    FROM topic_edge_snapshots
    WHERE snapshot_at = $1 AND (identity_key_a = $2 OR identity_key_b = $2)
"""

_LIFECYCLE_SQL = "SELECT identity_key, state FROM dynamic_topics WHERE identity_key = ANY($1::text[])"

# Stored passes strictly BETWEEN the two compared stamps. 0 = a consecutive
# pair (which is what a same-day diff assumes); >0 = this diff AGGREGATES real
# intermediate passes. Together with the raw interval this separates a store
# GAP (wide step, no intermediates — the 07-25 case) from a deliberately wide
# `since` window. `count(DISTINCT ...)` because one pass writes many rows.
_SNAPSHOTS_BETWEEN_SQL = """
    SELECT count(DISTINCT snapshot_at) AS n
    FROM topic_edge_snapshots
    WHERE snapshot_at > $1 AND snapshot_at < $2
"""

_FOCUS_ENTITIES_SQL = """
    SELECT s.persons
    FROM topic_members tm
    JOIN signals_v2 s ON s.id = tm.signal_id
    WHERE tm.topic_id = $1
      AND tm.role = 'evidence'
      AND tm.engine_version = $2
      AND tm.quarantined IS NOT TRUE
      AND tm.assigned_at > NOW() - ($3::int * INTERVAL '1 hour')
      AND s.persons IS NOT NULL
"""

_BACKBONE_FOR_ENTITIES_SQL = """
    SELECT entity_a, entity_b, cooccur_count, rarity_weight
    FROM entity_backbone_edges
    WHERE window_end = (SELECT MAX(window_end) FROM entity_backbone_edges)
      AND (entity_a = ANY($1::text[]) OR entity_b = ANY($1::text[]))
    ORDER BY rarity_weight DESC
    LIMIT $2
"""

# Reconstructs "which identity_keys currently contain this entity" — the join
# the pure backbone rows do not carry. Scoped to ACTIVE topics only (an
# entity's appearance in a retired topic cannot bridge anything live). Same
# evidence-role/engine-version/quarantine hygiene as the C1 writer.
_ENTITY_ACTIVE_TOPICS_SQL = """
    SELECT dt.identity_key, s.persons
    FROM topic_members tm
    JOIN signals_v2 s ON s.id = tm.signal_id
    JOIN dynamic_topics dt ON tm.topic_id = ('dynamic-topic-' || dt.id::text)
    WHERE tm.role = 'evidence'
      AND tm.engine_version = $1
      AND tm.quarantined IS NOT TRUE
      AND dt.state = 'active'
      AND tm.assigned_at > NOW() - ($2::int * INTERVAL '1 hour')
      AND s.persons IS NOT NULL
"""


def _diff_empty(ref: str, reason: str) -> dict:
    return {
        "contract": DIFF_CONTRACT,
        "ref": ref,
        "changes": [],
        "dormant": [],
        "reason": reason,
    }


def _clean_persons(raw) -> list[str]:
    out: list[str] = []
    for p in (raw or []):
        name = (p or "").strip().lower()
        if name and classify_subject(name) == "person":
            out.append(name)
    return out


async def _resolve_focus(conn, ref: str) -> Optional[dict]:
    """Resolve a focus ref (raw `dynamic-topic-<n>`, an `identity_key`, or a
    served `<slug>--<cc>` id — the same convention `dossier._base_topic_id`
    and `threads.get_topic_relationship` already use) to its current
    dynamic_topics row. C1's edge-snapshot store is keyed to `identity_key`
    and scoped to story-level (non-umbrella) `dynamic_topics` rows only —
    an atlas category slug legitimately resolves to nothing here (it was
    never in this store), which the caller reports as an honest empty
    reason, not an error."""
    base = strip_focus_suffix(ref)
    numeric_id = parse_dynamic_topic_id(base)
    row = (
        await conn.fetchrow(_RESOLVE_BY_ID_SQL, numeric_id)
        if numeric_id is not None
        else await conn.fetchrow(_RESOLVE_BY_KEY_SQL, base)
    )
    return dict(row) if row else None


async def _dormant_for_focus(
    conn, focus_topic_id: str, engine_version: str, edges_t1: list,
) -> list[DormantRelationship]:
    """Best-effort DORMANT lookup (spec §4 divergence-as-signal). Wrapped by
    the caller in a try/except: any failure here degrades to an empty list,
    never blocks the formed/weakened/churn diff that IS the endpoint's core
    contract."""
    entity_rows = await conn.fetch(
        _FOCUS_ENTITIES_SQL, focus_topic_id, engine_version, _ENTITY_WINDOW_HOURS,
    )
    counts: dict[str, int] = {}
    for r in entity_rows:
        for name in _clean_persons(r["persons"]):
            counts[name] = counts.get(name, 0) + 1
    focus_entities = [n for n, _ in sorted(counts.items(), key=lambda kv: -kv[1])]
    focus_entities = focus_entities[:_FOCUS_ENTITIES_LIMIT]
    if not focus_entities:
        return []

    backbone_rows = await conn.fetch(
        _BACKBONE_FOR_ENTITIES_SQL, focus_entities, _DORMANT_BACKBONE_LIMIT,
    )
    if not backbone_rows:
        return []

    all_entities = set(focus_entities)
    for r in backbone_rows:
        all_entities.add(str(r["entity_a"]))
        all_entities.add(str(r["entity_b"]))

    active_rows = await conn.fetch(
        _ENTITY_ACTIVE_TOPICS_SQL, engine_version, _ENTITY_WINDOW_HOURS,
    )
    entity_active_keys: dict[str, set] = {}
    for r in active_rows:
        ik = r["identity_key"]
        for name in _clean_persons(r["persons"]):
            if name in all_entities:
                entity_active_keys.setdefault(name, set()).add(ik)

    dormant = classify_dormant_relationships(
        [dict(r) for r in backbone_rows], entity_active_keys, edges_t1,
    )
    return dormant


@router.get("/api/v2/focus/{ref}/edge-diff")
async def focus_edge_diff(
    ref: str,
    since: str = Query(..., description="ISO-8601 date/time — changes since this point"),
):
    """Focused DIFF (spec §2): for one topic, the kinship-edge changes since
    `since` — formed / weakened / narrative-change / substrate-churn (Track
    C2's classifier, `app.services.edge_diff.classify_edge_changes`) — plus
    any DORMANT backbone relationships touching it (§4 divergence-as-signal).

    `ref` accepts a raw `dynamic-topic-<n>` id, a bare `identity_key`, or a
    served `<slug>--<cc>` thread id (the `--cc` suffix is stripped, same
    convention as `/api/v2/topic/{id}/relationship`). Honest-empty (never a
    500): no DB, no ref match, or no snapshot coverage all return a 200 with
    an explicit `reason` and empty `changes`/`dormant` lists.
    """
    since_dt = _parse_iso(since, param="since")
    cache_key = f"edges:diff:v0:{ref}:{since_dt.isoformat()}"
    cached = await _cache_get(cache_key)
    if cached is not None:
        return cached

    if db.pool is None:
        return _diff_empty(ref, "db_unavailable")

    try:
        async with db.pool.acquire() as conn:
            await conn.execute("SET statement_timeout = 10000")
            focus_row = await _resolve_focus(conn, ref)
            if focus_row is None:
                return _diff_empty(ref, "topic_not_found")
            focus_identity_key = focus_row["identity_key"]
            focus_topic_id = f"dynamic-topic-{focus_row['id']}"

            latest = await conn.fetchrow(_LATEST_SNAPSHOT_SQL)
            t1 = latest["s"] if latest else None
            if t1 is None:
                return _diff_empty(ref, "no_snapshots_stored")

            nearest_t0 = await conn.fetchrow(_NEAREST_SNAPSHOT_BEFORE_SQL, since_dt)
            t0 = nearest_t0["snapshot_at"] if nearest_t0 else None
            if t0 is None:
                return _diff_empty(ref, "no_snapshots_stored")

            # t0 is always <= t1 (t1 is the table MAX); when they coincide
            # (e.g. only one pass exists, or `since` lands on the latest
            # pass) the two fetches naturally return the same rows and the
            # classifier reports zero changes — the honest answer when there
            # is nothing earlier to diff against, never a fabricated FORMED
            # burst from an empty T0.
            edges_t1 = [
                dict(r) for r in
                await conn.fetch(_FOCUS_EDGES_AT_SQL, t1, focus_identity_key)
            ]
            edges_t0 = edges_t1 if t0 == t1 else [
                dict(r) for r in
                await conn.fetch(_FOCUS_EDGES_AT_SQL, t0, focus_identity_key)
            ]

            # How wide the compared step really is (see `SnapshotInterval`):
            # the passes are NOT evenly spaced, so the interval travels with
            # the diff rather than being assumed to be one night.
            between_row = (
                None if t0 == t1
                else await conn.fetchrow(_SNAPSHOTS_BETWEEN_SQL, t0, t1)
            )
            intermediate = int(between_row["n"]) if between_row else 0

            touched = {focus_identity_key}
            for row in edges_t0 + edges_t1:
                touched.add(row["identity_key_a"])
                touched.add(row["identity_key_b"])
            lifecycle_rows = await conn.fetch(_LIFECYCLE_SQL, list(touched))
            lifecycle = {r["identity_key"]: r["state"] for r in lifecycle_rows}

            engine_version = topic_members_engine_version()
            dormant: list[DormantRelationship] = []
            dormant_reason = None
            try:
                dormant = await _dormant_for_focus(
                    conn, focus_topic_id, engine_version, edges_t1,
                )
            except Exception as exc:  # pragma: no cover - defensive I/O
                logger.warning("focus edge-diff dormant lookup failed (degrading "
                               "to empty): %s", str(exc)[:200])
                dormant_reason = "dormant_lookup_unavailable"
    except HTTPException:
        raise
    except Exception as exc:  # pragma: no cover - defensive I/O
        logger.warning("focus edge-diff query failed: %s", str(exc)[:200])
        return _diff_empty(ref, "db_error")

    changes: list[EdgeChange] = classify_edge_changes(edges_t0, edges_t1, lifecycle)

    payload = {
        "contract": DIFF_CONTRACT,
        "ref": ref,
        "focus_identity_key": focus_identity_key,
        "since": since_dt.isoformat(),
        "matched_since_snapshot_at": t0.isoformat(),
        "latest_snapshot_at": t1.isoformat(),
        # The measured distance between the two compared passes. The changes
        # below accumulated over THIS interval, not over the standard nightly
        # step a reader assumes — 07-25's deleted partial snapshot makes
        # 07-24 -> 07-26 a 48h "consecutive" pair (measured on prod: ~+50%
        # more `formed` edges than either adjacent 24h step).
        "interval": snapshot_interval_out(describe_snapshot_interval(
            t0, t1, intermediate_snapshots=intermediate,
        )),
        "changes": [
            {
                "identity_key_a": c.identity_key_a,
                "identity_key_b": c.identity_key_b,
                "change_type": c.change_type,
                "weight_t0": c.weight_t0,
                "weight_t1": c.weight_t1,
                "delta": c.delta,
                "reason": c.reason,
                "basis": c.basis,
            }
            for c in changes
        ],
        "dormant": [
            {
                "entity_a": d.entity_a,
                "entity_b": d.entity_b,
                "cooccur_count": d.cooccur_count,
                "rarity_weight": d.rarity_weight,
                "reason": d.reason,
            }
            for d in dormant
        ],
    }
    if dormant_reason:
        payload["dormant_reason"] = dormant_reason
    await _cache_set(cache_key, payload, _DIFF_CACHE_TTL_S)
    return payload

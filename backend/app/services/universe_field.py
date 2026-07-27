"""Universe field (contract universe-v0) — the BUILD half.

Spec: docs/specs/2026-07-02-universe-view.md. The whole living story
population as one navigable field: every active dynamic topic is a body,
positioned by a projection of its REAL e5 centroid, related by nearest
neighbors measured in the FULL 768-dim space (the projection is a map,
the edges are the territory), and carrying its own activity timeline so
time is legible inside the view (§I time model).

WHY THIS LIVES IN A SERVICE, NOT THE ROUTER (2026-07-27)
--------------------------------------------------------
The build MEASURES ~40s of database work (5 bounded SELECTs over the active
topic set + per-snapshot centroids) plus PCA/neighbour math. That is longer
than the Fly proxy will hold an HTTP request open, so a request-path build can
NEVER finish: every cold attempt died at the proxy, the in-process cache could
therefore never fill, and with no stored artifact there was not even a stale
payload to fall back on. Measured 2026-07-27: `/api/v2/universe` was at 0%
availability in production (502 / connection-closed on every attempt).

Raising the statement timeout (20s -> 90s, commit ae877dee) could not fix it:
the ceiling was the PROXY, not Postgres.

So the build moved off the request path entirely. `scripts/build_universe_field
.py` runs it on the M1 (inside the nightly heavy-job mutex) and stores ONE
compact JSON artifact; the endpoint is a pure artifact read that always answers
fast and labels the artifact's age honestly. Same shape as the daily edition
(`build_daily_publication.py` -> `atlas_daily_editions`).

Honesty constraints (unchanged from the request-path build):
- Edges: top-k cosine neighbors computed in full space, never from the 2D
  projection (PCA top-2 explains ~17% of variance — measured 2026-07-02).
- Positions: global PCA blended toward the topic's category mean so
  categories read as constellations; positions are APPROXIMATE by design
  and labeled as such in the payload meta.
- No fabricated bodies: umbrellas (ephemeral roll-ups) are excluded, only
  story-level topics render.
- Nothing is dropped to make the build fast. The node set is exactly the
  active non-umbrella topics with a centroid; if that ever changes, it must be
  stated in `meta` (see `bounded` below) as well as in the build receipt.

This module must stay import-light (no fastapi): the builder runs under the M1
`mlvenv`, which has torch/numpy/asyncpg but no web stack.
"""
from __future__ import annotations

import json
import math
from datetime import datetime, timezone
from typing import Any, Optional

from app import db

CONTRACT = "universe-v0"

# Position blend: how much a body is pulled toward its category anchor.
CATEGORY_PULL = 0.55
NEIGHBORS_PER_NODE = 3
TIMELINE_DAYS = 30

# Build-side statement timeout. This runs on the M1 under the heavy-job mutex,
# never inside an HTTP request, so it can afford the measured ~40s with real
# headroom. Genuine pool pressure still trips it and fails the build loudly
# instead of storing a half-built field.
BUILD_STATEMENT_TIMEOUT_MS = 300_000


def _project_universe(vectors, categories):
    """Global PCA top-3 (numpy SVD) blended toward per-category anchors.

    Pure given (vectors, categories); returns (positions[n,3], anchors:
    {category: [x, y, z]}). Positions normalized to [0, 1]^3 — the third
    component gives the cloud REAL rotatable depth (spec §7.2): the frontend
    yaws the cloud around its vertical axis, separating points any single 2D
    projection overlaps.
    """
    import numpy as np

    M = np.asarray(vectors, dtype=np.float32)
    M = M / np.linalg.norm(M, axis=1, keepdims=True)
    mean = M.mean(axis=0)
    centered = M - mean
    U, S, Vt = np.linalg.svd(centered, full_matrices=False)
    xyz = U[:, :3] * S[:3]

    anchors: dict = {}
    for cat in set(categories):
        mask = [c == cat for c in categories]
        anchors[cat] = xyz[mask].mean(axis=0)
    blended = np.array([
        (1 - CATEGORY_PULL) * xyz[i] + CATEGORY_PULL * anchors[categories[i]]
        for i in range(len(categories))
    ])
    lo = blended.min(axis=0)
    span = blended.max(axis=0) - lo
    span[span < 1e-9] = 1.0
    positions = (blended - lo) / span
    anchor_positions = {
        cat: ((a - lo) / span).tolist() for cat, a in anchors.items()
    }
    # Basis so HISTORICAL centroids project into the SAME frame (trajectories):
    # normalize → subtract mean → Vt3 → blend to the topic's anchor → lo/span.
    basis = {"mean": mean, "vt3": Vt[:3], "anchors_xyz": anchors, "lo": lo, "span": span}
    return positions, anchor_positions, M, basis


def _project_history(vector, category, basis):
    """Project one historical centroid into the current layout frame (pure)."""
    import numpy as np

    v = np.asarray(vector, dtype=np.float32)
    norm = np.linalg.norm(v)
    if norm < 1e-9:
        return None
    v = v / norm
    xyz = (v - basis["mean"]) @ basis["vt3"].T
    anchor = basis["anchors_xyz"].get(category)
    if anchor is not None:
        xyz = (1 - CATEGORY_PULL) * xyz + CATEGORY_PULL * anchor
    out = (xyz - basis["lo"]) / basis["span"]
    return [round(float(out[0]), 4), round(float(out[1]), 4), round(float(out[2]), 4)]


def _nearest_edges(M, ids, k: int = NEIGHBORS_PER_NODE):
    """Top-k cosine neighbors per node in FULL space; deduped undirected.

    Also returns each node's best-neighbor sim (nn_sim) — a node whose best
    neighbor is far is a semantic ORPHAN (spec §7.2), a story unlike every
    other living story.
    """
    import numpy as np

    sims = M @ M.T
    np.fill_diagonal(sims, -1.0)
    nn_sims = [round(float(sims[i].max()), 4) for i in range(len(ids))]
    edges: dict = {}
    for i in range(len(ids)):
        for j in np.argsort(-sims[i])[:k]:
            j = int(j)
            key = (min(i, j), max(i, j))
            edges[key] = float(sims[i][j])
    edge_list = [
        {"a": ids[i], "b": ids[j], "sim": round(sim, 4)}
        for (i, j), sim in sorted(edges.items(), key=lambda kv: -kv[1])
    ]
    return edge_list, nn_sims


def empty_payload() -> dict:
    return {"contract": CONTRACT, "nodes": [], "edges": [], "anchors": [], "meta": None}


async def build_universe_payload(days: int = TIMELINE_DAYS) -> dict:
    """Build the full universe payload. Raises on DB failure — the caller
    (the BUILDER, never a request) owns the failure decision.

    Nothing is sampled or truncated: every active non-umbrella topic carrying a
    centroid becomes a node. `meta.bounded` records that explicitly so a future
    bound cannot be introduced silently.
    """
    async with db.pool.acquire() as conn:
            await conn.execute(f"SET statement_timeout = {BUILD_STATEMENT_TIMEOUT_MS}")
            rows = await conn.fetch("""
                SELECT id, label, category, crisis_relevant, agg_n_signals,
                       first_seen, last_seen, centroid_vec, label_status
                FROM dynamic_topics
                WHERE state = 'active' AND NOT is_umbrella
                  AND centroid_vec IS NOT NULL
                ORDER BY id
            """)
            if len(rows) < 3:
                return {**empty_payload(), "reason": "not_enough_topics"}

            # Trajectories + growth: per-snapshot cluster centroids give each
            # topic a REAL path through the field (spec §7.2), and ec.n_signals
            # gives its SIZE over time — the honest growth curve (the assigned_at
            # timeline collapsed to one bucket after an ETL re-stamp; snapshots
            # are the durable source). One pull feeds track + timeline + velocity.
            history = await conn.fetch(f"""
                SELECT dtm.dynamic_topic_id, ec.snapshot_at, ec.centroid_vec,
                       ec.n_signals
                FROM dynamic_topic_members dtm
                JOIN emergent_clusters ec ON ec.id = dtm.emergent_cluster_id
                JOIN dynamic_topics dt ON dt.id = dtm.dynamic_topic_id
                WHERE dt.state = 'active' AND NOT dt.is_umbrella
                  AND ec.snapshot_at > NOW() - INTERVAL '{int(days)} days'
                  AND ec.centroid_vec IS NOT NULL
                ORDER BY dtm.dynamic_topic_id, ec.snapshot_at
            """)

            # Per-node entity membership → the INVERSE-FOCUS lens (Pedro
            # 2026-07-03): focusing a country/person elsewhere in Atlas lights
            # THAT entity's stories in the field. Countries by code, persons by
            # name; both cheap over the small topic_members set.
            entity_rows = await conn.fetch(f"""
                WITH mem AS (
                    SELECT tm.topic_id, s.country_code, s.persons
                    FROM topic_members tm JOIN signals_v2 s ON s.id = tm.signal_id
                    WHERE tm.topic_id LIKE 'dynamic-topic-%' AND tm.role = 'evidence'
                      AND tm.quarantined IS NOT TRUE
                      AND tm.assigned_at > NOW() - INTERVAL '{int(days)} days'
                )
                SELECT topic_id, country_code, persons FROM mem
            """)

            # Attention velocity = the SHARED movement field (#219 Kalman,
            # topic_movement) — the smoothed velocity/surprise over the SAME
            # signals_v2 volume lineage the whole product speaks. One movement
            # number everywhere (Pedro 2026-07-03: kill the split-brain).
            # Fallback to a live relative changed_10h when a topic has no
            # Kalman row yet (fresh topic between cron runs).
            kalman_rows = await conn.fetch("""
                SELECT DISTINCT ON (topic_id) topic_id, velocity, surprise, trend
                FROM topic_movement
                WHERE engine_version = 'movement-kalman-v1'
                ORDER BY topic_id, window_end DESC
            """)
            movement_rows = await conn.fetch("""
                SELECT tm.topic_id,
                       COUNT(*) FILTER (WHERE s.timestamp >= NOW() - INTERVAL '10 hours')
                         - COUNT(*) FILTER (
                             WHERE s.timestamp < NOW() - INTERVAL '10 hours'
                               AND s.timestamp >= NOW() - INTERVAL '20 hours'
                           ) AS changed_10h,
                       COUNT(*) FILTER (WHERE s.timestamp >= NOW() - INTERVAL '20 hours') AS recent_vol
                FROM topic_members tm JOIN signals_v2 s ON s.id = tm.signal_id
                WHERE tm.topic_id LIKE 'dynamic-topic-%' AND tm.role = 'evidence'
                  AND tm.quarantined IS NOT TRUE
                GROUP BY tm.topic_id
            """)

    # Aggregate top countries + persons per topic (bounded).
    country_ct: dict = {}
    person_ct: dict = {}
    for r in entity_rows:
        tid = r["topic_id"]
        cc = (r["country_code"] or "").strip().upper()
        if cc:
            country_ct.setdefault(tid, {})[cc] = country_ct.setdefault(tid, {}).get(cc, 0) + 1
        for p in (r["persons"] or []):
            name = (p or "").strip().lower()
            if name:
                person_ct.setdefault(tid, {})[name] = person_ct.setdefault(tid, {}).get(name, 0) + 1
    countries_by_topic = {
        tid: [c for c, _ in sorted(cc.items(), key=lambda kv: -kv[1])[:6]]
        for tid, cc in country_ct.items()
    }
    persons_by_topic = {
        tid: [p for p, _ in sorted(pp.items(), key=lambda kv: -kv[1])[:8]]
        for tid, pp in person_ct.items()
    }

    categories = [r["category"] or "Uncategorized" for r in rows]
    positions, anchors, M, basis = _project_universe(
        [list(r["centroid_vec"]) for r in rows], categories,
    )
    ids = [f"dynamic-topic-{r['id']}" for r in rows]
    edges, nn_sims = _nearest_edges(M, ids)

    # Per-topic daily size series from snapshots (durable growth curve) →
    # timeline for the scrubber + attention velocity.
    size_series: dict = {}  # tid -> {day: max n_signals that day}
    snapshots_by_topic: dict = {}
    category_by_topic = {int(r["id"]): categories[i] for i, r in enumerate(rows)}
    for h in history:
        tid = int(h["dynamic_topic_id"])
        if tid not in category_by_topic:
            continue
        snapshots_by_topic.setdefault(tid, {}).setdefault(h["snapshot_at"], []).append(h["centroid_vec"])
        day = h["snapshot_at"].date().isoformat()
        n = int(h["n_signals"] or 0)
        cur = size_series.setdefault(tid, {})
        cur[day] = max(cur.get(day, 0), n)

    timeline_by_topic: dict = {}
    for tid, by_day in size_series.items():
        timeline_by_topic[f"dynamic-topic-{tid}"] = [
            {"day": d, "n": by_day[d]} for d in sorted(by_day)
        ]

    # Velocity: the shared movement field (#219 Kalman) first, live relative
    # changed_10h as the fallback. Kalman velocity is in log-intensity/6h;
    # squash to a comparable ~[-1,1] with tanh so the frontend's rank/halo
    # scale is stable regardless of source.
    velocity_by_topic: dict = {}
    trend_by_topic: dict = {}
    # velocity_basis: which lineage produced each node's velocity — 'kalman'
    # (the smoothed #219 field) or 'changed_10h' (the live relative fallback).
    # Lets the constellation frontend label the two honestly instead of
    # presenting the raw-delta fallback as if it were the smoothed field (P1-8).
    velocity_basis_by_topic: dict = {}
    for k in kalman_rows:
        tid_text = k["topic_id"]
        if not tid_text.startswith("dynamic-topic-"):
            continue
        tid = int(tid_text[len("dynamic-topic-"):])
        velocity_by_topic[tid] = round(math.tanh(float(k["velocity"] or 0.0)), 4)
        trend_by_topic[tid] = k["trend"]
        velocity_basis_by_topic[tid] = "kalman"
    for m in movement_rows:  # fallback for topics with no Kalman row yet
        tid_text = m["topic_id"]
        if not tid_text.startswith("dynamic-topic-"):
            continue
        tid = int(tid_text[len("dynamic-topic-"):])
        if tid in velocity_by_topic:
            continue
        recent = int(m["recent_vol"] or 0)
        ch = int(m["changed_10h"] or 0)
        velocity_by_topic[tid] = round(ch / max(6, recent), 4) if recent else 0.0
        velocity_basis_by_topic[tid] = "changed_10h"
    track_by_topic: dict = {}
    for tid, by_snapshot in snapshots_by_topic.items():
        cat = category_by_topic.get(tid)
        if cat is None:
            continue
        points = []
        for snap_at in sorted(by_snapshot):
            vecs = by_snapshot[snap_at]
            mean_vec = [sum(col) / len(col) for col in zip(*vecs)] if len(vecs) > 1 else list(vecs[0])
            pos = _project_history(mean_vec, cat, basis)
            if pos:
                points.append({"t": snap_at.isoformat(), "x": pos[0], "y": pos[1], "z": pos[2]})
        if len(points) > 16:
            step = (len(points) - 1) / 15
            points = [points[round(i * step)] for i in range(16)]
        track_by_topic[tid] = points

    nodes = [
        {
            "id": ids[i],
            "label": r["label"],
            # Label Court verdict (N15): entailed/partial/failed, NULL until
            # the court has judged this topic — the hover card renders the
            # shared under-review marker on failed/partial.
            "label_status": r["label_status"],
            "category": categories[i],
            "crisis_relevant": bool(r["crisis_relevant"])
                if r["crisis_relevant"] is not None else None,
            "n": int(r["agg_n_signals"] or 0),
            "x": round(float(positions[i][0]), 4),
            "y": round(float(positions[i][1]), 4),
            "z": round(float(positions[i][2]), 4),
            "nn_sim": nn_sims[i],
            "first_seen": r["first_seen"].isoformat() if r["first_seen"] else None,
            "last_seen": r["last_seen"].isoformat() if r["last_seen"] else None,
            "timeline": timeline_by_topic.get(ids[i], []),
            "track": track_by_topic.get(int(r["id"]), []),
            "countries": countries_by_topic.get(ids[i], []),
            "persons": persons_by_topic.get(ids[i], []),
            "velocity": velocity_by_topic.get(int(r["id"]), 0.0),
            "velocity_basis": velocity_basis_by_topic.get(int(r["id"])),
            "trend": trend_by_topic.get(int(r["id"])),
        }
        for i, r in enumerate(rows)
    ]

    payload = {
        "contract": CONTRACT,
        "nodes": nodes,
        "edges": edges,
        "anchors": [
            {"category": cat, "x": round(a[0], 4), "y": round(a[1], 4),
             "z": round(a[2], 4),
             "count": sum(1 for c in categories if c == cat)}
            for cat, a in anchors.items()
        ],
        "meta": {
            "topic_count": len(nodes),
            "edge_basis": f"top-{NEIGHBORS_PER_NODE} cosine neighbors in full 768-dim space",
            "position_basis": "global PCA top-3 blended to category anchors — approximate by design; z = rotatable depth",
            "timeline_days": days,
            # Explicitly false: every active non-umbrella topic with a centroid
            # is a node. Any future sampling/cap MUST flip this and say what it
            # dropped — a silently thinned field is a fabricated one.
            "bounded": False,
        },
    }
    return payload


# ---------------------------------------------------------------------------
# Artifact store + read. The endpoint never builds; it reads exactly this.
# ---------------------------------------------------------------------------

async def store_universe_artifact(
    payload: dict,
    *,
    days: int,
    build_seconds: float,
    generated_at: Optional[datetime] = None,
) -> None:
    """Upsert ONE compact artifact row, keyed by the timeline window."""
    generated_at = generated_at or datetime.now(timezone.utc)
    meta = payload.get("meta") or {}
    async with db.pool.acquire() as conn:
        await conn.execute(
            """
            INSERT INTO universe_field_artifacts
                (days, generated_at, contract, node_count, edge_count,
                 build_seconds, payload, updated_at)
            VALUES ($1, $2, $3, $4, $5, $6, $7::jsonb, now())
            ON CONFLICT (days) DO UPDATE SET
                generated_at = EXCLUDED.generated_at,
                contract = EXCLUDED.contract,
                node_count = EXCLUDED.node_count,
                edge_count = EXCLUDED.edge_count,
                build_seconds = EXCLUDED.build_seconds,
                payload = EXCLUDED.payload,
                updated_at = now()
            """,
            int(days),
            generated_at,
            payload.get("contract") or CONTRACT,
            int(meta.get("topic_count") or len(payload.get("nodes") or [])),
            len(payload.get("edges") or []),
            float(build_seconds),
            json.dumps(payload),
        )


def _json_value(value: Any) -> Any:
    return json.loads(value) if isinstance(value, (str, bytes)) else value


# How old an artifact may be before the payload is labeled stale. The builder
# runs once nightly inside the scoped-snapshot chain, so anything past ~a day
# and a half means a night was missed — the reader deserves to know.
STALE_AFTER_HOURS = 36.0


def _age_hours(generated_at: datetime, *, now: Optional[datetime] = None) -> float:
    now = now or datetime.now(timezone.utc)
    if generated_at.tzinfo is None:
        generated_at = generated_at.replace(tzinfo=timezone.utc)
    return max(0.0, (now - generated_at).total_seconds() / 3600.0)


async def fetch_stored_universe(
    days: int = TIMELINE_DAYS, *, now: Optional[datetime] = None,
) -> dict:
    """Serving path: read the precomputed field. Never builds, never hangs.

    Order of truth:
      1. the artifact for exactly this window,
      2. the freshest artifact for ANY window (honestly relabeled — the reader
         gets a real field with `meta.days_requested` telling them the window
         they asked for was not the one on disk),
      3. an honest empty payload with a reason.
    """
    if db.pool is None:
        return {**empty_payload(), "reason": "no_db"}

    async with db.pool.acquire() as conn:
        row = await conn.fetchrow(
            """
            SELECT days, generated_at, contract, node_count, edge_count,
                   build_seconds, payload, updated_at
            FROM universe_field_artifacts
            WHERE days = $1
            """,
            int(days),
            timeout=5,
        )
        if row is None:
            row = await conn.fetchrow(
                """
                SELECT days, generated_at, contract, node_count, edge_count,
                       build_seconds, payload, updated_at
                FROM universe_field_artifacts
                ORDER BY generated_at DESC
                LIMIT 1
                """,
                timeout=5,
            )

    if row is None:
        # Nothing has EVER been built. Say so — this is a build-pipeline state
        # ("the nightly has not run here yet"), not a database failure.
        return {**empty_payload(), "reason": "not_precomputed"}

    payload = _json_value(row["payload"])
    age_hours = _age_hours(row["generated_at"], now=now)
    meta = dict(payload.get("meta") or {})
    meta.update({
        "generated_at": row["generated_at"].isoformat(),
        "age_hours": round(age_hours, 2),
        "stale": age_hours > STALE_AFTER_HOURS,
        "stale_after_hours": STALE_AFTER_HOURS,
        "source": "precomputed_artifact",
        "build_seconds": (
            round(float(row["build_seconds"]), 2)
            if row["build_seconds"] is not None else None
        ),
    })
    if int(row["days"]) != int(days):
        # Honest window mismatch: serve the field we HAVE and name the gap
        # instead of pretending the timeline covers the requested span.
        meta["days_requested"] = int(days)
        meta["days_served"] = int(row["days"])
    return {
        **payload,
        "generated_at": row["generated_at"].isoformat(),
        "stale": meta["stale"],
        "age_hours": meta["age_hours"],
        "meta": meta,
    }

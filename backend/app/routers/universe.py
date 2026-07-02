"""Universe view (contract universe-v0).

Spec: docs/specs/2026-07-02-universe-view.md. The whole living story
population as one navigable field: every active dynamic topic is a body,
positioned by a projection of its REAL e5 centroid, related by nearest
neighbors measured in the FULL 768-dim space (the projection is a map,
the edges are the territory), and carrying its own activity timeline so
time is legible inside the view (§I time model).

Honesty constraints:
- Edges: top-k cosine neighbors computed in full space, never from the 2D
  projection (PCA top-2 explains ~17% of variance — measured 2026-07-02).
- Positions: global PCA blended toward the topic's category mean so
  categories read as constellations; positions are APPROXIMATE by design
  and labeled as such in the payload meta.
- No fabricated bodies: umbrellas (ephemeral roll-ups) are excluded, only
  story-level topics render.
"""
import logging
import time
from typing import Optional

from fastapi import APIRouter, Query

from app import db

logger = logging.getLogger(__name__)

router = APIRouter()

# Position blend: how much a body is pulled toward its category anchor.
CATEGORY_PULL = 0.55
NEIGHBORS_PER_NODE = 3
TIMELINE_DAYS = 30
_CACHE_TTL_S = 600

_cache: dict = {"at": 0.0, "payload": None}


def _project_universe(vectors, categories):
    """Global PCA (numpy SVD) blended toward per-category anchors.

    Pure given (vectors, categories); returns (positions[n,2], anchors:
    {category: [x, y]}). Positions normalized to [0, 1]^2.
    """
    import numpy as np

    M = np.asarray(vectors, dtype=np.float32)
    M = M / np.linalg.norm(M, axis=1, keepdims=True)
    centered = M - M.mean(axis=0)
    U, S, _ = np.linalg.svd(centered, full_matrices=False)
    xy = U[:, :2] * S[:2]

    anchors: dict = {}
    for cat in set(categories):
        mask = [c == cat for c in categories]
        anchors[cat] = xy[mask].mean(axis=0)
    blended = np.array([
        (1 - CATEGORY_PULL) * xy[i] + CATEGORY_PULL * anchors[categories[i]]
        for i in range(len(categories))
    ])
    lo = blended.min(axis=0)
    span = blended.max(axis=0) - lo
    span[span < 1e-9] = 1.0
    positions = (blended - lo) / span
    anchor_positions = {
        cat: ((a - lo) / span).tolist() for cat, a in anchors.items()
    }
    return positions, anchor_positions, M


def _nearest_edges(M, ids, k: int = NEIGHBORS_PER_NODE):
    """Top-k cosine neighbors per node in FULL space; deduped undirected."""
    import numpy as np

    sims = M @ M.T
    np.fill_diagonal(sims, -1.0)
    edges: dict = {}
    for i in range(len(ids)):
        for j in np.argsort(-sims[i])[:k]:
            j = int(j)
            key = (min(i, j), max(i, j))
            edges[key] = float(sims[i][j])
    return [
        {"a": ids[i], "b": ids[j], "sim": round(sim, 4)}
        for (i, j), sim in sorted(edges.items(), key=lambda kv: -kv[1])
    ]


@router.get("/api/v2/universe")
async def get_universe(days: int = Query(TIMELINE_DAYS, ge=7, le=90)):
    """The living story universe: bodies + full-space relations + time."""
    now = time.monotonic()
    if _cache["payload"] is not None and now - _cache["at"] < _CACHE_TTL_S:
        return _cache["payload"]

    empty = {"contract": "universe-v0", "nodes": [], "edges": [], "meta": None}
    try:
        async with db.pool.acquire() as conn:
            await conn.execute("SET statement_timeout = 20000")
            rows = await conn.fetch("""
                SELECT id, label, category, crisis_relevant, agg_n_signals,
                       first_seen, last_seen, centroid_vec
                FROM dynamic_topics
                WHERE state = 'active' AND NOT is_umbrella
                  AND centroid_vec IS NOT NULL
                ORDER BY id
            """)
            if len(rows) < 3:
                return {**empty, "reason": "not_enough_topics"}

            activity = await conn.fetch(f"""
                SELECT topic_id, date_trunc('day', assigned_at) AS day,
                       count(*) AS n
                FROM topic_members
                WHERE topic_id LIKE 'dynamic-topic-%'
                  AND role = 'evidence'
                  AND assigned_at > NOW() - INTERVAL '{int(days)} days'
                GROUP BY 1, 2
            """)
    except Exception as exc:
        logger.error("universe query failed: %s", exc)
        return {**empty, "reason": "error"}

    categories = [r["category"] or "Uncategorized" for r in rows]
    positions, anchors, M = _project_universe(
        [list(r["centroid_vec"]) for r in rows], categories,
    )
    ids = [f"dynamic-topic-{r['id']}" for r in rows]
    edges = _nearest_edges(M, ids)

    timeline_by_topic: dict = {}
    for a in activity:
        timeline_by_topic.setdefault(a["topic_id"], []).append(
            {"day": a["day"].date().isoformat(), "n": int(a["n"])}
        )
    for tl in timeline_by_topic.values():
        tl.sort(key=lambda d: d["day"])

    nodes = [
        {
            "id": ids[i],
            "label": r["label"],
            "category": categories[i],
            "crisis_relevant": bool(r["crisis_relevant"])
                if r["crisis_relevant"] is not None else None,
            "n": int(r["agg_n_signals"] or 0),
            "x": round(float(positions[i][0]), 4),
            "y": round(float(positions[i][1]), 4),
            "first_seen": r["first_seen"].isoformat() if r["first_seen"] else None,
            "last_seen": r["last_seen"].isoformat() if r["last_seen"] else None,
            "timeline": timeline_by_topic.get(ids[i], []),
        }
        for i, r in enumerate(rows)
    ]

    payload = {
        "contract": "universe-v0",
        "nodes": nodes,
        "edges": edges,
        "anchors": [
            {"category": cat, "x": round(a[0], 4), "y": round(a[1], 4),
             "count": sum(1 for c in categories if c == cat)}
            for cat, a in anchors.items()
        ],
        "meta": {
            "topic_count": len(nodes),
            "edge_basis": f"top-{NEIGHBORS_PER_NODE} cosine neighbors in full 768-dim space",
            "position_basis": "global PCA blended to category anchors — approximate by design",
            "timeline_days": days,
        },
    }
    _cache["at"] = now
    _cache["payload"] = payload
    return payload

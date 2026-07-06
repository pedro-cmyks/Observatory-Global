"""Dossier connection analysis (contract dossier-connections-v0).

The L3 wedge: a dossier is not a flat list of pins — it is a CONNECTED
investigation. Given the topic ids an analyst pinned, this endpoint measures
HOW those stories relate so the analyst can validate the hypothesis "do these
form one narrative, and which sub-clusters connect?".

Three relation bases, all MEASURED (never fabricated):
  - semantic: pairwise cosine between the topics' real e5 centroids
    (dynamic_topics.centroid_vec — the same lineage the universe view relates
    bodies by, scoped to just this investigation).
  - shared_country: overlap of the countries each story touches.
  - shared_person: overlap of DISTINCTIVE persons — rarity-weighted so a
    ubiquitous actor (present in every pin) never launders a relation
    (#234 lesson: "donald trump" DF 14/30 linked everything).

Plus per-node + aggregate distributions (country / language / role=press-vs-
public / sentiment / combined timeline) for the dossier charts. Measured at
generation time; the frozen pin core (lib/dossier.ts) never depends on this.
"""
from __future__ import annotations

import logging
import math
import time
from typing import Any

from fastapi import APIRouter
from pydantic import BaseModel, Field

from app import db

router = APIRouter(prefix="/api/v2/dossier", tags=["dossier"])
logger = logging.getLogger(__name__)

MAX_PINS = 16
ROWS_PER_TOPIC = 300          # cap member rows aggregated per topic/role
SEM_EDGE_THRESHOLD = 0.88     # centroid cosine above which two stories "connect"
TOP_COUNTRIES = 4             # per-node top countries used for shared-country edges
CACHE_TTL_S = 120

_cache: dict = {}


class ConnectionsRequest(BaseModel):
    topic_ids: list[str] = Field(..., min_length=1, max_length=64)
    days: int = Field(30, ge=7, le=90)


def _base_topic_id(raw: str) -> str:
    """A pin id may carry a `slug--cc` country scope; membership keys on the
    bare topic id, so strip the `--cc` suffix for the query (keep the raw id as
    the node id so the frontend can map results back to its pins)."""
    s = raw.strip()
    if "--" in s:
        return s.split("--", 1)[0]
    return s


def _cosine(a: list[float], b: list[float]) -> float:
    import numpy as np

    va = np.asarray(a, dtype=np.float32)
    vb = np.asarray(b, dtype=np.float32)
    na = float(np.linalg.norm(va))
    nb = float(np.linalg.norm(vb))
    if na < 1e-9 or nb < 1e-9:
        return 0.0
    return float(np.dot(va, vb) / (na * nb))


def _project_positions(centroids: dict[str, list[float]]) -> dict[str, dict]:
    """PCA top-2 of the pinned centroids → an approximate 2D field position per
    node, normalized to [0,1]^2. Positions are approximate (same honesty as the
    universe view); the EDGES carry the exact relation. Needs ≥3 centroids."""
    import numpy as np

    ids = list(centroids)
    if len(ids) < 3:
        return {}
    M = np.asarray([centroids[i] for i in ids], dtype=np.float32)
    M = M / np.clip(np.linalg.norm(M, axis=1, keepdims=True), 1e-9, None)
    centered = M - M.mean(axis=0)
    try:
        _U, _S, Vt = np.linalg.svd(centered, full_matrices=False)
    except Exception:
        return {}
    xy = centered @ Vt[:2].T
    lo = xy.min(axis=0)
    span = xy.max(axis=0) - lo
    span[span < 1e-9] = 1.0
    norm = (xy - lo) / span
    return {ids[i]: {"x": round(float(norm[i][0]), 4), "y": round(float(norm[i][1]), 4)}
            for i in range(len(ids))}


@router.post("/connections")
async def dossier_connections(req: ConnectionsRequest):
    """Measure how the pinned stories relate + their distributions."""
    # Normalize + dedupe (map base id -> the raw pin id the frontend sent).
    base_to_raw: dict[str, str] = {}
    for raw in req.topic_ids:
        base = _base_topic_id(raw)
        if base and base not in base_to_raw:
            base_to_raw[base] = raw
        if len(base_to_raw) >= MAX_PINS:
            break
    base_ids = list(base_to_raw)

    empty = {"contract": "dossier-connections-v0", "nodes": [], "edges": [],
             "distributions": None, "unresolved": [r for r in req.topic_ids]}
    if not base_ids:
        return {**empty, "reason": "no_topic_ids"}
    if db.pool is None:
        return {**empty, "reason": "no_db"}

    cache_key = (tuple(sorted(base_ids)), req.days)
    hit = _cache.get(cache_key)
    if hit and time.monotonic() - hit[0] < CACHE_TTL_S:
        return hit[1]

    dyn_ids = [int(b[len("dynamic-topic-"):]) for b in base_ids
               if b.startswith("dynamic-topic-") and b[len("dynamic-topic-"):].isdigit()]

    try:
        async with db.pool.acquire() as conn:
            await conn.execute("SET statement_timeout = 20000")

            centroid_rows = []
            label_rows = []
            if dyn_ids:
                centroid_rows = await conn.fetch(
                    """
                    SELECT id, label, category, centroid_vec
                    FROM dynamic_topics
                    WHERE id = ANY($1::int[]) AND centroid_vec IS NOT NULL
                    """,
                    dyn_ids,
                )
                label_rows = await conn.fetch(
                    "SELECT id, label, category FROM dynamic_topics WHERE id = ANY($1::int[])",
                    dyn_ids,
                )

            # Capped member rows per topic/role → all the aggregations.
            member_rows = await conn.fetch(
                f"""
                WITH ranked AS (
                    SELECT tm.topic_id, tm.role,
                           s.country_code, s.source_lang, s.persons,
                           COALESCE(s.nlp_sentiment, s.sentiment) AS sentiment,
                           s.timestamp,
                           ROW_NUMBER() OVER (
                               PARTITION BY tm.topic_id, tm.role
                               ORDER BY s.timestamp DESC
                           ) AS rn
                    FROM topic_members tm
                    JOIN signals_v2 s ON s.id = tm.signal_id
                    WHERE tm.topic_id = ANY($1::text[])
                      AND tm.engine_version = 'v1-compat'
                      AND tm.role IN ('evidence','discussion','mood')
                      AND tm.assigned_at > NOW() - INTERVAL '{int(req.days)} days'
                )
                SELECT topic_id, role, country_code, source_lang, persons,
                       sentiment, timestamp
                FROM ranked WHERE rn <= {ROWS_PER_TOPIC}
                """,
                base_ids,
            )
    except Exception as exc:
        logger.error("dossier connections query failed: %s", exc)
        return {**empty, "reason": "error"}

    labels: dict[str, dict] = {}
    for r in label_rows:
        labels[f"dynamic-topic-{r['id']}"] = {"label": r["label"], "category": r["category"]}
    centroids: dict[str, list[float]] = {}
    for r in centroid_rows:
        centroids[f"dynamic-topic-{r['id']}"] = [float(x) for x in r["centroid_vec"]]

    # ── Aggregate member rows per base topic id ──────────────────────────────
    agg: dict[str, dict] = {b: {
        "country": {}, "lang": {}, "person": {}, "role": {},
        "sent_sum": 0.0, "sent_n": 0, "day": {}, "n": 0,
    } for b in base_ids}
    # Person document-frequency across the pin set → rarity weighting.
    person_docs: dict[str, set] = {}

    for row in member_rows:
        tid = row["topic_id"]
        a = agg.get(tid)
        if a is None:
            continue
        role = row["role"]
        a["role"][role] = a["role"].get(role, 0) + 1
        if role == "evidence":
            a["n"] += 1
            cc = (row["country_code"] or "").strip().upper()
            if cc:
                a["country"][cc] = a["country"].get(cc, 0) + 1
            lang = (row["source_lang"] or "").strip().lower()
            if lang and lang != "xx":
                a["lang"][lang] = a["lang"].get(lang, 0) + 1
            sent = row["sentiment"]
            if sent is not None:
                a["sent_sum"] += float(sent)
                a["sent_n"] += 1
            ts = row["timestamp"]
            if ts is not None:
                day = ts.date().isoformat()
                a["day"][day] = a["day"].get(day, 0) + 1
            for p in (row["persons"] or []):
                name = (p or "").strip().lower()
                if name:
                    a["person"][name] = a["person"].get(name, 0) + 1
                    person_docs.setdefault(name, set()).add(tid)

    def _top(counts: dict, k: int) -> list:
        return sorted(counts.items(), key=lambda kv: -kv[1])[:k]

    n_pins = len(base_ids)
    # A person is DISTINCTIVE if it appears in a minority of the pinned stories
    # (df ≤ min(3, ~40% of pins)) — the rarity gate that stops a ubiquitous
    # actor from linking unrelated pins.
    distinct_df_max = max(1, min(3, math.ceil(0.4 * n_pins)))

    nodes = []
    unresolved = []
    for base in base_ids:
        raw_id = base_to_raw[base]
        a = agg[base]
        meta = labels.get(base, {})
        if a["n"] == 0 and base not in centroids and not meta:
            unresolved.append(raw_id)
            continue
        top_persons = [p for p, _ in _top(a["person"], 10)]
        nodes.append({
            "id": raw_id,
            "base_id": base,
            "label": meta.get("label") or raw_id,
            "category": meta.get("category"),
            "pos": None,  # filled below when a centroid exists
            "countries": [{"cc": c, "n": n} for c, n in _top(a["country"], 6)],
            "persons": top_persons,
            "languages": [{"lang": l, "n": n} for l, n in _top(a["lang"], 6)],
            "sentiment": round(a["sent_sum"] / a["sent_n"], 4) if a["sent_n"] else None,
            "roleCounts": {
                "evidence": a["role"].get("evidence", 0),
                "discussion": a["role"].get("discussion", 0),
                "mood": a["role"].get("mood", 0),
            },
            "timeline": [{"day": d, "n": a["day"][d]} for d in sorted(a["day"])],
            "has_centroid": base in centroids,
            "n": a["n"],
        })

    node_by_base = {n["base_id"]: n for n in nodes}

    # Positions: PCA of the resolved centroids (only for nodes that HAVE one).
    pos_by_base = _project_positions(
        {b: v for b, v in centroids.items() if b in node_by_base})
    for base, pos in pos_by_base.items():
        node_by_base[base]["pos"] = pos

    # ── Edges ────────────────────────────────────────────────────────────────
    edges: list[dict] = []
    bases = [n["base_id"] for n in nodes]
    top_country_sets = {
        n["base_id"]: {c["cc"] for c in n["countries"][:TOP_COUNTRIES]} for n in nodes
    }
    person_sets = {n["base_id"]: set(n["persons"]) for n in nodes}

    for i in range(len(bases)):
        for j in range(i + 1, len(bases)):
            bi, bj = bases[i], bases[j]
            basis: list[str] = []
            sim = None
            if bi in centroids and bj in centroids:
                sim = round(_cosine(centroids[bi], centroids[bj]), 4)
            shared_countries = sorted(top_country_sets[bi] & top_country_sets[bj])
            shared_persons_all = person_sets[bi] & person_sets[bj]
            shared_persons = sorted(
                p for p in shared_persons_all
                if len(person_docs.get(p, ())) <= distinct_df_max
            )
            weight = 0.0
            semantic = sim is not None and sim >= SEM_EDGE_THRESHOLD
            if semantic:
                basis.append("semantic")
                weight = max(weight, float(sim))
            if shared_countries:
                basis.append("shared_country")
                weight = max(weight, 0.6 + 0.1 * len(shared_countries))
            if shared_persons:
                basis.append("shared_person")
                # rarity weight: rarer shared actor => stronger link
                rarity = sum(1.0 / max(1, len(person_docs.get(p, ()))) for p in shared_persons)
                weight = max(weight, min(0.98, 0.65 + 0.15 * rarity))
            if not basis:
                continue
            edges.append({
                "a": node_by_base[bi]["id"],
                "b": node_by_base[bj]["id"],
                "basis": basis,
                "weight": round(min(1.0, weight), 4),
                "semantic_sim": sim,
                "shared_countries": shared_countries,
                "shared_persons": shared_persons,
            })

    edges.sort(key=lambda e: -e["weight"])

    # ── Aggregate distributions ──────────────────────────────────────────────
    country_total: dict = {}
    lang_total: dict = {}
    press = public = 0
    timeline_total: dict = {}
    for n in nodes:
        for c in n["countries"]:
            country_total[c["cc"]] = country_total.get(c["cc"], 0) + c["n"]
        for l in n["languages"]:
            lang_total[l["lang"]] = lang_total.get(l["lang"], 0) + l["n"]
        press += n["roleCounts"]["evidence"]
        public += n["roleCounts"]["discussion"] + n["roleCounts"]["mood"]
        for t in n["timeline"]:
            timeline_total[t["day"]] = timeline_total.get(t["day"], 0) + t["n"]

    distributions = {
        "countries": [{"cc": c, "n": v} for c, v in _top(country_total, 12)],
        "languages": [{"lang": l, "n": v} for l, v in _top(lang_total, 10)],
        "roles": {"press": press, "public": public},
        "sentimentByNode": [
            {"id": n["id"], "label": n["label"], "sentiment": n["sentiment"]}
            for n in nodes if n["sentiment"] is not None
        ],
        "timeline": [{"day": d, "n": timeline_total[d]} for d in sorted(timeline_total)],
    }

    payload = {
        "contract": "dossier-connections-v0",
        "measured_at": __import__("datetime").datetime.utcnow().isoformat() + "Z",
        "nodes": nodes,
        "edges": edges,
        "distributions": distributions,
        "unresolved": unresolved,
        "meta": {
            "pin_count": n_pins,
            "resolved": len(nodes),
            "semantic_threshold": SEM_EDGE_THRESHOLD,
            "distinctive_person_df_max": distinct_df_max,
            "position_basis": "PCA top-2 of pinned e5 centroids — approximate; edges are exact",
        },
    }
    _cache[cache_key] = (time.monotonic(), payload)
    return payload

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

import html
import json
import logging
import math
import os
import re
import time
from typing import Any

from fastapi import APIRouter
from pydantic import BaseModel, Field

from app import db
from app.services.constellation_walk import (
    WalkParams,
    actor_edge_weight,
    blob_connector_flags,
    build_knn_graph,
    match_destination,
    walk_constellation,
)
from app.services.insight_llm import generate_insight
from app.services.publication_synthesis import (  # noqa: F401 (re-exported for tests + endpoint)
    SynthConnection,
    SynthConnectionNode,
    SynthEvidenceItem,
    SynthPin,
    SynthesizeRequest,
    _SYNTH_SYSTEM,
    _as_paragraphs,
    _citation_table,
    _resolve_citations,
    _synth_user,
    synthesize_publication_article,
)
from app.services.subjects import classify_subject

router = APIRouter(prefix="/api/v2/dossier", tags=["dossier"])
logger = logging.getLogger(__name__)

MAX_PINS = 64
ROWS_PER_TOPIC = 300          # cap member rows aggregated per topic/role
SEM_EDGE_THRESHOLD = 0.88     # RAW centroid cosine — legacy/fallback connect gate
# Whitened connect gate. Raw e5 centroid cosine floods 0.88-0.96 (every pin
# "connects"); the GLOBAL all-but-top(k=1) whitening (app/data/e5_whitening.npz)
# de-compresses the anisotropic cone so a real edge separates from a spurious one.
# MEASURED on the LatAm head-to-head pins (dt-1419 Keiko ↔ dt-792 Milei = 0.655
# REAL; dt-52 Cepeda ↔ either = 0.36-0.40 SPURIOUS) — tau 0.50 sits in the wide
# 0.40→0.655 margin. Raw cosine stays the DISPLAY semantic_sim; whitened drives
# the connect decision + semantic weight. Reversible: ATLAS_DOSSIER_WHITENED_EDGES=0.
SEM_EDGE_WHITENED_THRESHOLD = 0.50
TOP_COUNTRIES = 4             # per-node top countries used for shared-country edges
CACHE_TTL_S = 120

_cache: dict = {}


class ConnectionsRequest(BaseModel):
    topic_ids: list[str] = Field(..., min_length=1, max_length=MAX_PINS)
    days: int = Field(30, ge=7, le=90)
    # F3a (spec 2026-07-20 §6): per-pin FROZEN evidence urls — lets the mention
    # scan read the fetched article BODIES (pinned_articles cache) in addition
    # to headlines. Optional + backward compatible; body basis is labeled
    # `body_mention`, never silently mixed with the headline `text_mention`.
    evidence_urls: dict[str, list[str]] = Field(default_factory=dict)
    # Constellation assembly (2026-07-06): when a pin is a child of an umbrella
    # (an assembled big story), fold it into ONE umbrella node exposing typed
    # sub-facets, instead of N noisy near-duplicate nodes. Off = legacy flat view.
    collapse_umbrellas: bool = True


def _base_topic_id(raw: str) -> str:
    """A pin id may carry a `slug--cc` country scope; membership keys on the
    bare topic id, so strip the `--cc` suffix for the query (keep the raw id as
    the node id so the frontend can map results back to its pins)."""
    s = raw.strip()
    if "--" in s:
        return s.split("--", 1)[0]
    return s


def _distinctive_df_max(n_display: int) -> int:
    """Max document-frequency for a shared person to count as DISTINCTIVE.

    The rarity gate stops a ubiquitous actor from linking MANY pins (#234:
    "donald trump" DF 14/30). At exactly 2 display nodes that logic inverts —
    any actor shared by both pins has df=2, so a df≤1 gate makes shared-actor
    edges structurally impossible (the NATO-Ankara N=2 artifact: erdogan in
    both pins, verdict still "no confirmed common actor"). With 2 pins there
    is no "ubiquitous across many" to guard against, so df=2 is allowed."""
    if n_display <= 2:
        return 2
    return max(1, min(3, math.ceil(0.4 * n_display)))


# ── Junk-actor filter (Frank v2 blocker 2) ───────────────────────────────────
# NER junk leaked into CONFIRMED verdicts ("marea neagra" — the Black Sea in
# Romanian; "states states" — a tokenizer artifact) and led the link line before
# the real actor. Shared actors shown/used anywhere in this payload must clear
# the person gate (_is_valid_person → repeated tokens, articles, photo credits)
# + the subjects gazetteer (place/org/event names are never actors) + a
# multilingual geo-feature token guard for forms the EN gazetteer can't know.
_ACTOR_GEO_FEATURE_TOKENS: set[str] = {
    # water/terrain feature words across languages ("marea neagra", "mar negro")
    "sea", "ocean", "gulf", "strait", "river", "lake", "island", "peninsula",
    "mount", "mountain", "desert", "valley", "coast",
    "mar", "marea", "mare", "mer", "meer", "deniz", "bahr", "golfo", "golfe",
    "rio", "río", "reka", "laut", "oceano", "océano",
}


def _is_clean_actor(name: str) -> bool:
    """True when `name` is plausibly a real person/actor — not NER junk."""
    if classify_subject(name) != "person":
        return False
    return not any(t in _ACTOR_GEO_FEATURE_TOKENS for t in name.split())


# ── Text-level cross-reference (Frank v2 blocker 1) ──────────────────────────
# The entity lens can miss what a headline states verbatim: the tariff pin was
# declared "isolated — no evidence links them" while its own headline read
# "… during NATO summit". Cheap token cross-ref, no LLM: does pin A's evidence
# TEXT mention pin B's label key-tokens (≥2, or the label's single key-token)
# or one of B's top actors? Emits edge basis `text_mention` — weaker than
# shared_person, stronger than semantic-only.
_LABEL_STOPWORDS: set[str] = {
    "the", "a", "an", "of", "and", "or", "in", "on", "for", "with", "to", "at",
    "as", "by", "from", "over", "after", "before", "amid", "during", "between",
    "against", "under", "into", "near", "his", "her", "its", "their",
    "news", "update", "updates", "report", "reports", "latest", "live",
    "daily", "roundup", "new", "crisis", "situation", "developments",
    "coverage", "story", "stories", "talks",
    "de", "del", "la", "el", "los", "las", "le", "les", "du", "des", "und",
}


def _label_key_tokens(label: str) -> list[str]:
    toks = re.split(r"[^\w]+", (label or "").lower())
    return [t for t in toks if len(t) >= 3 and t not in _LABEL_STOPWORDS]


def _mention_terms(
    headlines: list[tuple[str, frozenset]],
    label_tokens: list[str],
    actor_names: list[str],
) -> list[str]:
    """Terms of the OTHER pin found verbatim in these evidence headlines.
    Label match needs ≥2 key-tokens in one headline (or the single token of a
    1-token label) so a generic shared word never fires alone."""
    terms: list[str] = []
    for h, hset in headlines:
        matched = [t for t in label_tokens if t in hset]
        if matched and (len(matched) >= 2 or len(label_tokens) == 1):
            term = " ".join(matched[:3])
            if term not in terms:
                terms.append(term)
        for actor in actor_names:
            if actor in h and actor not in terms:
                terms.append(actor)
    return terms[:4]


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


def _connection_mds_positions(nodes: list[dict], edges: list[dict]) -> tuple[dict, dict | None]:
    """Distance-preserving 3D placement of the pinned stories (pure).

    The endpoint already collapses its measured bases into ONE scalar per pair
    (`edge.weight` = max over the basis weights), so the distance is
    d = clamp(1 - weight, 0, 1) and a pair with NO measured relation keeps the
    maximum distance — honest absence, never fabricated closeness. Position
    encodes HOW related overall; the per-edge basis chips still carry WHY.

    The basis label says FIVE, not the "6-basis" of the older prose: the edge
    builder appends exactly five (semantic, shared_country, shared_person,
    text_mention, body_mention). A glass-box field that miscounts its own
    evidence is the kind of small dishonesty this product exists to avoid.
    """
    from app.services.mds import edge_weight_distance_matrix, mds_3d, to_unit_cube

    ids = [n["id"] for n in nodes]
    result = mds_3d(edge_weight_distance_matrix(ids, edges))
    if result is None:
        return {}, None
    coords = to_unit_cube(result.coords)
    meta = {
        "stress": result.stress,
        "basis": "edge-weight-5basis",
        "n": result.n,
        "collapse": (
            "d = 1 - max(per-basis edge weights); a pair with no measured "
            "relation keeps the maximum distance 1.0"
        ),
    }
    return dict(zip(ids, coords)), meta


@router.post("/connections")
async def dossier_connections(req: ConnectionsRequest):
    """Measure how the pinned stories relate + their distributions."""
    # Normalize + dedupe (map base id -> the raw pin id the frontend sent).
    # The request contract itself is 64, so nothing valid is silently dropped.
    base_to_raw: dict[str, str] = {}
    for raw in req.topic_ids:
        base = _base_topic_id(raw)
        if base and base not in base_to_raw:
            base_to_raw[base] = raw
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

    def _tid(i: int) -> str:
        return f"dynamic-topic-{i}"

    try:
        async with db.pool.acquire() as conn:
            await conn.execute("SET statement_timeout = 20000")

            pin_rows = []
            if dyn_ids:
                pin_rows = await conn.fetch(
                    """
                    SELECT id, label, category, centroid_vec, parent_id,
                           is_umbrella, facet, first_seen
                    FROM dynamic_topics
                    WHERE id = ANY($1::int[])
                    """,
                    dyn_ids,
                )

            # ── Constellation assembly: resolve each pin to a DISPLAY node ──────
            # A pinned CHILD of an umbrella (parent_id) folds into that umbrella;
            # a pinned umbrella stays; anything else is a standalone node. We then
            # pull the umbrella's FULL child set so the node shows the assembled
            # story (all facets), not just the pinned fragments.
            pin_meta = {int(r["id"]): r for r in pin_rows}
            umbrella_ids: set[int] = set()      # umbrellas to render (collapsed)
            standalone_bases: list[str] = []    # non-umbrella pins with no parent
            collapsed_from: dict[int, list[str]] = {}  # umbrella id -> pin raw ids
            unresolved: list[str] = []

            for base in base_ids:
                raw = base_to_raw[base]
                if not base.startswith("dynamic-topic-"):
                    standalone_bases.append(base)
                    continue
                iid = int(base[len("dynamic-topic-"):]) if base[len("dynamic-topic-"):].isdigit() else None
                meta = pin_meta.get(iid) if iid is not None else None
                if meta is None:
                    standalone_bases.append(base)  # aggregate-only; may resolve via members
                    continue
                if req.collapse_umbrellas and meta["is_umbrella"]:
                    umbrella_ids.add(iid)
                    collapsed_from.setdefault(iid, []).append(raw)
                elif req.collapse_umbrellas and meta["parent_id"]:
                    up = int(meta["parent_id"])
                    umbrella_ids.add(up)
                    collapsed_from.setdefault(up, []).append(raw)
                else:
                    standalone_bases.append(base)

            # Umbrella rows (label/category/centroid) + their FULL children.
            umb_rows = {}
            child_rows = []
            if umbrella_ids:
                for r in await conn.fetch(
                    "SELECT id, label, category, centroid_vec, first_seen FROM dynamic_topics "
                    "WHERE id = ANY($1::int[])", list(umbrella_ids),
                ):
                    umb_rows[int(r["id"])] = r
                child_rows = await conn.fetch(
                    "SELECT id, label, category, facet, parent_id FROM dynamic_topics "
                    "WHERE parent_id = ANY($1::int[])", list(umbrella_ids),
                )
            children_of: dict[int, list] = {}
            child_topic_to_umb: dict[str, int] = {}
            child_facet: dict[str, str] = {}
            child_label: dict[str, str] = {}
            for r in child_rows:
                up = int(r["parent_id"])
                children_of.setdefault(up, []).append(r)
                cs = _tid(int(r["id"]))
                child_topic_to_umb[cs] = up
                child_facet[cs] = r["facet"] or "core"
                child_label[cs] = r["label"]

            # Underlying topic ids to aggregate = all umbrella children + standalones.
            underlying: list[str] = list(child_topic_to_umb.keys()) + standalone_bases

            member_rows = []
            if underlying:
                member_rows = await conn.fetch(
                    f"""
                    WITH ranked AS (
                        SELECT tm.topic_id, tm.role,
                               s.country_code, s.source_lang, s.persons,
                               s.headline,
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
                          AND tm.quarantined IS NOT TRUE
                          AND tm.assigned_at > NOW() - INTERVAL '{int(req.days)} days'
                    )
                    SELECT topic_id, role, country_code, source_lang, persons,
                           headline, sentiment, timestamp
                    FROM ranked WHERE rn <= {ROWS_PER_TOPIC}
                    """,
                    underlying,
                )
    except Exception as exc:
        logger.error("dossier connections query failed: %s", exc)
        return {**empty, "reason": "error"}

    # display-node key: umbrellas keyed by their own dynamic-topic id; standalones
    # by their base id. Member rows map to a display key via child→umbrella folding.
    def _display_key(topic_id: str) -> str:
        up = child_topic_to_umb.get(topic_id)
        return _tid(up) if up is not None else topic_id

    labels: dict[str, dict] = {}
    centroids: dict[str, list[float]] = {}

    def _fs(r) -> str | None:
        v = r["first_seen"] if "first_seen" in dict(r) else None
        return v.isoformat() if hasattr(v, "isoformat") else v

    for uid, r in umb_rows.items():
        k = _tid(uid)
        labels[k] = {"label": r["label"], "category": r["category"], "first_seen": _fs(r)}
        if r["centroid_vec"] is not None:
            centroids[k] = [float(x) for x in r["centroid_vec"]]
    for base in standalone_bases:
        r = pin_meta.get(int(base[len("dynamic-topic-"):])) if base.startswith("dynamic-topic-") and base[len("dynamic-topic-"):].isdigit() else None
        if r is not None:
            labels[base] = {"label": r["label"], "category": r["category"], "first_seen": _fs(r)}
            if r["centroid_vec"] is not None:
                centroids[base] = [float(x) for x in r["centroid_vec"]]

    display_keys = [_tid(u) for u in umbrella_ids] + standalone_bases

    # ── Aggregate member rows per DISPLAY node + per (umbrella, facet) ─────────
    agg: dict[str, dict] = {k: {
        "country": {}, "lang": {}, "person": {}, "role": {},
        "sent_sum": 0.0, "sent_n": 0, "day": {}, "n": 0, "headlines": [],
    } for k in display_keys}
    facet_agg: dict[tuple, dict] = {}   # (umbrella_key, facet) -> {country,n,topics}
    person_docs: dict[str, set] = {}
    _actor_ok_cache: dict[str, bool] = {}  # names repeat heavily across rows

    def _actor_ok(name: str) -> bool:
        v = _actor_ok_cache.get(name)
        if v is None:
            v = _actor_ok_cache[name] = _is_clean_actor(name)
        return v

    HEADLINES_PER_NODE = 150  # text cross-ref corpus per display node

    for row in member_rows:
        tid = row["topic_id"]
        key = _display_key(tid)
        a = agg.get(key)
        if a is None:
            continue
        role = row["role"]
        a["role"][role] = a["role"].get(role, 0) + 1
        fkey = None
        if tid in child_topic_to_umb:
            fkey = (key, child_facet.get(tid, "core"))
            fa = facet_agg.setdefault(fkey, {"country": {}, "n": 0, "topics": set()})
            fa["topics"].add(tid)
        if role == "evidence":
            a["n"] += 1
            cc = (row["country_code"] or "").strip().upper()
            if cc:
                a["country"][cc] = a["country"].get(cc, 0) + 1
                if fkey:
                    facet_agg[fkey]["country"][cc] = facet_agg[fkey]["country"].get(cc, 0) + 1
            if fkey:
                facet_agg[fkey]["n"] += 1
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
            if len(a["headlines"]) < HEADLINES_PER_NODE:
                h = html.unescape(row["headline"] or "").lower().strip()
                if h:
                    a["headlines"].append((h, frozenset(re.split(r"[^\w]+", h))))
            for p in (row["persons"] or []):
                name = (p or "").strip().lower()
                # junk-actor gate: NER junk ("marea neagra", "states states")
                # never enters node.persons / shared_persons / the verdict.
                if name and _actor_ok(name):
                    a["person"][name] = a["person"].get(name, 0) + 1
                    person_docs.setdefault(name, set()).add(key)

    def _top(counts: dict, k: int) -> list:
        return sorted(counts.items(), key=lambda kv: -kv[1])[:k]

    n_pins = len(base_ids)
    # A person is DISTINCTIVE if it appears in a minority of the display nodes
    # (df ≤ min(3, ~40%); df ≤ 2 when only 2 nodes — see _distinctive_df_max).
    distinct_df_max = _distinctive_df_max(len(display_keys))
    # #234 rarity normalization reference (spec §2.4): df_max in
    # norm_rarity = (1/df − 1/df_max)/(1 − 1/df_max) is the MAX actor
    # document-frequency in view. ≥1 guard when no actors were aggregated.
    df_max_view = max((len(v) for v in person_docs.values()), default=1)

    def _facets_for(ukey: str, uid: int) -> list[dict]:
        """Typed sub-facets of an umbrella: the assembled constellation by angle."""
        out = []
        for (k, facet), fa in facet_agg.items():
            if k != ukey:
                continue
            out.append({
                "facet": facet,
                "topic_count": len(fa["topics"]),
                "evidence_n": fa["n"],
                "countries": [{"cc": c, "n": v} for c, v in _top(fa["country"], 5)],
                "topics": [{"id": t, "label": child_label.get(t, t)}
                           for t in sorted(fa["topics"],
                                           key=lambda t: -facet_agg[(ukey, facet)]["n"])][:8],
            })
        # facets with children but no member rows in-window still exist — include them
        seen = {f["facet"] for f in out}
        by_facet: dict[str, list] = {}
        for r in children_of.get(uid, []):
            by_facet.setdefault(r["facet"] or "core", []).append(r)
        for facet, rs in by_facet.items():
            if facet in seen:
                continue
            out.append({
                "facet": facet, "topic_count": len(rs), "evidence_n": 0,
                "countries": [],
                "topics": [{"id": _tid(int(r["id"])), "label": r["label"]} for r in rs[:8]],
            })
        out.sort(key=lambda f: (-f["evidence_n"], -f["topic_count"]))
        return out

    nodes = []
    for key in display_keys:
        a = agg[key]
        meta = labels.get(key, {})
        is_umb = key in {_tid(u) for u in umbrella_ids}
        if a["n"] == 0 and key not in centroids and not meta and not is_umb:
            # standalone that resolved to nothing
            unresolved.append(base_to_raw.get(key, key))
            continue
        uid = int(key[len("dynamic-topic-"):]) if is_umb else None
        top_persons = [p for p, _ in _top(a["person"], 10)]
        node = {
            "id": (base_to_raw.get(key) or key) if not is_umb else key,
            "base_id": key,
            "label": meta.get("label") or key,
            "category": meta.get("category"),
            "is_umbrella": is_umb,
            "pos": None,
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
            "has_centroid": key in centroids,
            "n": a["n"],
            # story window start (P0.3): dynamic_topics.first_seen; last activity
            # is the tail of `timeline` (frontend renders firstSeen → last day).
            "first_seen": meta.get("first_seen"),
        }
        if is_umb:
            node["child_count"] = len(children_of.get(uid, []))
            node["collapsed_from"] = collapsed_from.get(uid, [])
            node["facets"] = _facets_for(key, uid)
        nodes.append(node)

    node_by_base = {n["base_id"]: n for n in nodes}

    # Positions: PCA of the resolved centroids (only for nodes that HAVE one).
    pos_by_base = _project_positions(
        {b: v for b, v in centroids.items() if b in node_by_base})
    for base, pos in pos_by_base.items():
        node_by_base[base]["pos"] = pos

    # ── Whitened centroids for the connect gate (global asset, batch once) ────
    # Apply the ONE stored transform (fit on ~100k signal vectors) to the pin
    # centroids; output rows are unit-norm so a dot product is the whitened
    # cosine. Falls back to the raw gate if the flag is off or the asset is
    # unavailable — the CONNECT decision degrades gracefully, never 500s.
    use_whitened_edges = os.getenv("ATLAS_DOSSIER_WHITENED_EDGES", "1").lower() not in ("0", "false", "no", "")
    wcentroids: dict[str, Any] = {}
    if use_whitened_edges and centroids:
        try:
            from app.services.whitening import load_whitening, apply_whitening
            import numpy as np
            _w = load_whitening()
            _keys = list(centroids)
            _wm = apply_whitening(np.asarray([centroids[k] for k in _keys], dtype=np.float32), _w)
            wcentroids = {_keys[i]: _wm[i] for i in range(len(_keys))}
        except Exception as exc:
            logger.warning("dossier whitened edges unavailable, raw gate: %s", exc)
            wcentroids = {}

    # ── Edges ────────────────────────────────────────────────────────────────
    edges: list[dict] = []
    bases = [n["base_id"] for n in nodes]
    top_country_sets = {
        n["base_id"]: {c["cc"] for c in n["countries"][:TOP_COUNTRIES]} for n in nodes
    }
    person_sets = {n["base_id"]: set(n["persons"]) for n in nodes}
    # Text cross-ref inputs per display node: label key-tokens + top clean
    # actors (already junk-filtered at aggregation) + evidence headlines.
    label_tokens_by_base = {
        n["base_id"]: _label_key_tokens(str(n["label"])) for n in nodes
    }
    actors_by_base = {n["base_id"]: n["persons"][:8] for n in nodes}
    headlines_by_base = {
        n["base_id"]: agg.get(n["base_id"], {}).get("headlines", []) for n in nodes
    }

    # F3a: fetched-body texts per base (same (text_lower, tokenset) shape the
    # headline scan uses — _mention_terms works verbatim on both). A paragraph-6
    # mention of the other pin's actor is exactly what headlines hide. Best
    # effort: no fetched text → empty list → zero body edges, never an error.
    bodies_by_base: dict[Any, list[tuple[str, frozenset]]] = {n["base_id"]: [] for n in nodes}
    bodies_raw_by_base: dict[Any, list[str]] = {n["base_id"]: [] for n in nodes}   # F3b embeds
    if req.evidence_urls:
        try:
            from app.services.article_fetch import full_texts_for
            base_by_raw = {n["id"]: n["base_id"] for n in nodes}
            url_to_base: dict[str, Any] = {}
            for raw, urls in req.evidence_urls.items():
                b = base_by_raw.get(raw)
                if b is None:
                    continue
                for u in (urls or [])[:4]:
                    u = str(u or "").strip()
                    if u.startswith("http"):
                        url_to_base.setdefault(u, b)
            texts = await full_texts_for(list(url_to_base)[:64], cap_chars=6000) if url_to_base else {}
            for u, art in texts.items():
                raw_text = (art.get("text") or "")
                low = raw_text.lower()
                if low:
                    bodies_by_base[url_to_base[u]].append(
                        (low, frozenset(re.split(r"[^\w]+", low))))
                    bodies_raw_by_base[url_to_base[u]].append(raw_text)
        except Exception as exc:
            logger.warning("connections body-mention load failed: %s", str(exc)[:200])

    for i in range(len(bases)):
        for j in range(i + 1, len(bases)):
            bi, bj = bases[i], bases[j]
            basis: list[str] = []
            sim = None       # RAW cosine — display only
            wsim = None      # whitened cosine — drives the connect decision
            if bi in centroids and bj in centroids:
                sim = round(_cosine(centroids[bi], centroids[bj]), 4)
                if bi in wcentroids and bj in wcentroids:
                    wsim = round(float(wcentroids[bi] @ wcentroids[bj]), 4)
            shared_countries = sorted(top_country_sets[bi] & top_country_sets[bj])
            # #234 (spec §2.4): SOFTEN the old hard-exclude to a thin CONTINUOUS
            # link. ALL shared actors participate (rarest first) and the rarity
            # FORMULA — not a binary df gate — sets the weight, so a ubiquitous-only
            # pair gets a thin link (no longer a false "isolated" verdict — the N=2
            # erdogan artifact) yet cannot launder a relation. The DISTINCTIVE subset
            # (df ≤ gate) stays the CONFIRMING receipt that drives the 'strong' tier.
            shared_persons_all = sorted(
                person_sets[bi] & person_sets[bj],
                key=lambda p: len(person_docs.get(p, ())),
            )
            # GDELT truncation variants ("tayyip erdo" ‖ "tayyip erdogan") read
            # as two actors in the verdict — keep only the longest form.
            shared_persons_all = [
                p for p in shared_persons_all
                if not any(q != p and q.startswith(p) for q in shared_persons_all)
            ]
            shared_persons = [
                p for p in shared_persons_all
                if len(person_docs.get(p, ())) <= distinct_df_max
            ]
            weight = 0.0
            # Whitened gate when available; raw ≥ 0.88 fallback otherwise.
            if wsim is not None:
                semantic = wsim >= SEM_EDGE_WHITENED_THRESHOLD
                sem_weight = wsim
            else:
                semantic = sim is not None and sim >= SEM_EDGE_THRESHOLD
                sem_weight = sim
            if semantic:
                basis.append("semantic")
                weight = max(weight, float(sem_weight))
            if shared_countries:
                basis.append("shared_country")
                weight = max(weight, 0.6 + 0.1 * len(shared_countries))
            if shared_persons_all:
                basis.append("shared_person")
                # #234 LOCKED (spec §2.4): weight = 0.30 + 0.68·norm_rarity over the
                # RAREST shared actor — trump df=29 → 0.300 (thin, below the 0.50
                # gate, barely propagates); a distinctive df=2 → 0.628. The old
                # 0.65-base formula scored even a ubiquitous actor 0.66 (glue).
                dfs = [len(person_docs.get(p, ())) for p in shared_persons_all]
                weight = max(weight, actor_edge_weight(dfs, df_max_view))
            # Text-level cross-check (Frank v2 blocker 1): before this pair can
            # read "isolated/similar-only", ask whether either pin's evidence
            # TEXT mentions the other pin's label tokens or top actors.
            text_terms: list[str] = []
            for t in (
                _mention_terms(headlines_by_base[bi], label_tokens_by_base[bj], actors_by_base[bj])
                + _mention_terms(headlines_by_base[bj], label_tokens_by_base[bi], actors_by_base[bi])
            ):
                if t not in text_terms:
                    text_terms.append(t)
            text_terms = text_terms[:4]
            if text_terms:
                basis.append("text_mention")
                # weaker than shared_person (0.65+), stronger than a bare
                # semantic pass at the 0.50 whitened threshold.
                weight = max(weight, 0.55)
            # F3a: the same scan over fetched BODY texts — catches the
            # paragraph-6 reference no headline carries. Distinct basis +
            # slightly weaker than a headline mention (deep-text reference).
            body_terms: list[str] = []
            if bodies_by_base.get(bi) or bodies_by_base.get(bj):
                for t in (
                    _mention_terms(bodies_by_base.get(bi, []), label_tokens_by_base[bj], actors_by_base[bj])
                    + _mention_terms(bodies_by_base.get(bj, []), label_tokens_by_base[bi], actors_by_base[bi])
                ):
                    if t not in body_terms and t not in text_terms:
                        body_terms.append(t)
                body_terms = body_terms[:4]
            if body_terms:
                basis.append("body_mention")
                weight = max(weight, 0.52)
            if not basis:
                continue
            edges.append({
                "a": node_by_base[bi]["id"],
                "b": node_by_base[bj]["id"],
                "basis": basis,
                "weight": round(min(1.0, weight), 4),
                "semantic_sim": sim,
                "whitened_sim": wsim,
                "shared_countries": shared_countries,
                "shared_persons": shared_persons,
                "text_mentions": text_terms,
                "body_mentions": body_terms,
            })

    edges.sort(key=lambda e: -e["weight"])

    # Distance-preserving 3D layout over the measured edges. Best effort: a
    # failure leaves the payload exactly as before (the frontend keeps its 2D
    # field), never a 500.
    mds_meta = None
    try:
        pos3_by_id, mds_meta = _connection_mds_positions(nodes, edges)
        for n in nodes:
            pos3 = pos3_by_id.get(n["id"])
            if pos3 is not None:
                n["pos3"] = pos3
    except Exception as exc:
        logger.warning("dossier connections mds layout failed: %s", exc)

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

    # ── Neighbors: the nearest UNPINNED stories to each pin — the background
    # field that makes this a CONSTELLATION (context + bridges), not 3 lonely
    # dots. A neighbor near >1 pin is a bridge (an unpinned link you didn't pin).
    neighbors: list[dict] = []
    neighbor_candidate_count = 0
    body_lane_pins = 0
    if centroids:
        exclude_ids = set(dyn_ids) | set(umbrella_ids) | {
            int(t[len("dynamic-topic-"):]) for t in child_topic_to_umb
            if t.startswith("dynamic-topic-") and t[len("dynamic-topic-"):].isdigit()
        }
        try:
            # dynamic_topics.centroid_vec is real[] (no pgvector index), so we
            # scan candidate centroids and cosine them in Python (same _cosine as
            # the pin↔pin edges). ~1.6k candidates × few pins = cheap.
            async with db.pool.acquire() as conn:
                await conn.execute("SET statement_timeout = 15000")
                cand = await conn.fetch(
                    """
                    SELECT id, label, category, centroid_vec
                    FROM dynamic_topics
                    WHERE centroid_vec IS NOT NULL AND NOT (id = ANY($1::int[]))
                    """,
                    list(exclude_ids),
                )
            import numpy as np
            pin_keys = list(centroids.keys())
            pin_ids = [node_by_base.get(k, {}).get("id", k) for k in pin_keys]
            pin_mat = np.asarray([centroids[k] for k in pin_keys], dtype=np.float32)
            cand_ids = [int(r["id"]) for r in cand]
            cand_mat = np.asarray([[float(x) for x in r["centroid_vec"]] for r in cand], dtype=np.float32)
            # all-but-the-top (k=1) WHITENING. The e5 centroid space is an
            # anisotropic cone (same/diff cosine ~0.91/0.87 — raw cosine floods
            # with generic-central topics like "Kate Middleton"). Removing the
            # top-1 principal direction de-compresses it — MEASURED same/diff gap
            # +0.04→+0.31, AUC 0.80→0.87 (backend/scripts/measure_embedding_
            # separation.py) — so a fixed threshold separates real neighbors from
            # noise, AND surfaces genuine bridges (e.g. "Milei attends Fujimori").
            mu = cand_mat.mean(0, keepdims=True)
            _, _, Vt = np.linalg.svd(cand_mat - mu, full_matrices=False)
            pc = Vt[0]
            def _wnorm(M):
                Y = M - mu
                Y = Y - np.outer(Y @ pc, pc)
                n = np.linalg.norm(Y, axis=1, keepdims=True)
                n[n == 0] = 1.0
                return Y / n
            sims = _wnorm(cand_mat) @ _wnorm(pin_mat).T   # (N_cand, N_pin) whitened cosine
            NEIGHBOR_TAU = 0.40
            nb: dict[int, dict] = {}
            for ci in range(len(cand_ids)):
                for pj in range(len(pin_keys)):
                    s = float(sims[ci, pj])
                    if s < NEIGHBOR_TAU:
                        continue
                    cid = cand_ids[ci]
                    e = nb.get(cid)
                    if e is None:
                        e = nb[cid] = {"base_id": _tid(cid), "label": cand[ci]["label"],
                                       "category": cand[ci]["category"], "links": []}
                    e["links"].append({"pin": pin_ids[pj], "sim": round(s, 4),
                                       "basis": "centroid"})
            # ── F3b body-informed neighbors (measurement gate PASSED 2026-07-20:
            # whitened body AUC 0.9983 vs headline 0.9208, pos@tau 94%/neg 0.7% —
            # docs/research/body-embed/2026-07-20-body-embed-measurement.json).
            # Pins with fetched bodies get a SECOND representation (mean body
            # embed) run through the SAME whitening + tau; links labeled
            # basis='body-e5-whitened', never mixed with centroid links.
            try:
                b_keys = [k for k in pin_keys if bodies_raw_by_base.get(k)]
                if b_keys:
                    import asyncio
                    from app.services.research_semantic import embed_texts as _embed_texts
                    to_embed: list[str] = []
                    owners: list[Any] = []
                    for bkey in b_keys:
                        for raw_text in bodies_raw_by_base[bkey][:3]:
                            to_embed.append("passage: " + raw_text[:4000])
                            owners.append(bkey)
                    vecs = await asyncio.to_thread(_embed_texts, to_embed) if to_embed else None
                    if vecs:
                        acc: dict[Any, list] = {}
                        for bkey, v in zip(owners, vecs):
                            acc.setdefault(bkey, []).append(np.asarray(v, dtype=np.float32))
                        eb_keys = list(acc.keys())
                        body_lane_pins = len(eb_keys)
                        eb_ids = [node_by_base.get(k, {}).get("id", k) for k in eb_keys]
                        b_mat = np.asarray([np.mean(np.stack(vs), axis=0) for vs in acc.values()],
                                           dtype=np.float32)
                        b_sims = _wnorm(cand_mat) @ _wnorm(b_mat).T
                        for ci in range(len(cand_ids)):
                            for pj in range(len(eb_keys)):
                                s = float(b_sims[ci, pj])
                                if s < NEIGHBOR_TAU:
                                    continue
                                cid = cand_ids[ci]
                                e = nb.get(cid)
                                if e is None:
                                    e = nb[cid] = {"base_id": _tid(cid), "label": cand[ci]["label"],
                                                   "category": cand[ci]["category"], "links": []}
                                if not any(l["pin"] == eb_ids[pj] and l.get("basis") == "body-e5-whitened"
                                           for l in e["links"]):
                                    e["links"].append({"pin": eb_ids[pj], "sim": round(s, 4),
                                                       "basis": "body-e5-whitened"})
            except Exception as exc:
                # body lane is additive — its failure never costs centroid neighbors
                logger.warning("body-embed neighbor lane unavailable: %s", str(exc)[:200])
            neighbor_candidate_count = len(nb)
            # bridges (near >1 pin) first, then strongest single link; cap 8.
            neighbors = sorted(
                nb.values(),
                key=lambda e: (-len(e["links"]), -max(l["sim"] for l in e["links"])),
            )[:8]
        except Exception as exc:
            logger.warning("dossier neighbors query failed: %s", exc)
            neighbors = []

    payload = {
        # v1: umbrella collapse + typed facets (constellation assembly, 2026-07-06).
        "contract": "dossier-connections-v1",
        "measured_at": __import__("datetime").datetime.utcnow().isoformat() + "Z",
        "nodes": nodes,
        "edges": edges,
        "neighbors": neighbors,
        "mds": mds_meta,
        "distributions": distributions,
        "unresolved": unresolved,
        "meta": {
            "pin_count": n_pins,
            "resolved": len(nodes),
            "umbrellas_collapsed": len(umbrella_ids),
            "collapse_umbrellas": req.collapse_umbrellas,
            "semantic_threshold": SEM_EDGE_WHITENED_THRESHOLD if wcentroids else SEM_EDGE_THRESHOLD,
            "semantic_space": "whitened-e5-k1" if wcentroids else "raw-e5",
            "distinctive_person_df_max": distinct_df_max,
            "text_mention": "one pin's evidence headlines contain the other pin's label key-tokens or a top actor — weaker than shared_person, stronger than semantic-only; pure token match",
            "body_mention": "one pin's FETCHED ARTICLE BODY (pinned_articles cache) contains the other pin's label key-tokens or a top actor — the paragraph-6 reference headlines hide; pure token match, weaker than a headline text_mention, never mixed with it",
            "actor_filter": "shared/top actors pass the person gate + subjects gazetteer + geo-feature token guard (NER junk excluded)",
            "position_basis": "PCA top-2 of pinned e5 centroids — approximate; edges are exact",
            "position_basis_3d": "classical metric MDS over d = 1 - combined edge weight; spatial distance IS the measured relation, `mds.stress` is the distortion",
            "member_selection": {
                "method": "most_recent_per_topic_and_role",
                "rows_per_topic_role": ROWS_PER_TOPIC,
                "complete_member_universe": False,
            },
            "neighbor_selection": {
                "candidate_count": neighbor_candidate_count,
                "returned_count": len(neighbors),
                "display_slots": 8,
                "method": "bridges_first_then_strongest_similarity",
                "truncated": neighbor_candidate_count > len(neighbors),
                # F3b: per-link basis 'centroid' | 'body-e5-whitened' (mean of
                # the pin's fetched-body embeds, same whitening + tau; gate
                # measurement docs/research/body-embed/2026-07-20).
                "body_lane_pins": body_lane_pins,
            },
        },
    }
    _cache[cache_key] = (time.monotonic(), payload)
    return payload


# ── The walked constellation (multi-hop transitive kinship) ──────────────────
# Spec: docs/superpowers/specs/2026-07-21-multi-hop-transitive-chains.md. The
# Universe is the map; an investigation is a ROUTE through it. From the analyst's
# pins, walk outward over the whitened topic kNN graph (the ONE global whitening —
# NOT the raw universe graph, NOT the connections per-request refit; spec §2.2),
# max-product with the LOCKED brake (REL_FLOOR 0.35 + HOP_CAP 3). A reached story
# is labeled by honest DISTANCE: hermano (a direct measured edge) or primo Nº (only
# reachable transitively — "no direct line, only this trail"). Every hop carries a
# receipt (the whitened cosine); v1 is UNDIRECTED (no causal arrow). Math-first,
# NO LLM on the walk. Reversible: ATLAS_WALK_* env knobs.

_WALK_CACHE: dict = {}
_WALK_CACHE_TTL_S = 120
# The active-topic universe query the probe locked on (universe.py serving rule):
# story-level (not umbrella) topics with a centroid. Bounded scan, Python cosine.
_WALK_TOPICS_SQL = """
    SELECT id, label, category, centroid_vec
    FROM dynamic_topics
    WHERE state = 'active' AND NOT is_umbrella AND centroid_vec IS NOT NULL
"""

# Blob CONFIRMER (spec §2.4 A2 followup): the cheap entropy first-pass
# (`blob_connector_flags`) flags CANDIDATES; this bounded fetch is the ONLY
# member-embedding I/O the walk does, and only for those candidates — never
# every node (mindful). Mirrors `scripts/detect_overmerge.py`'s member fetch:
# topic_members JOIN signal_embeddings, engine_version v1-compat = the serving
# default, quarantined rows excluded. Capped per-topic via ROW_NUMBER so one
# giant candidate topic can't blow the query's cost or memory.
BLOB_CONFIRM_MAX_CANDIDATES = 40   # never confirm more than this many candidates
                                   # per walk — bounds the fetch even if the
                                   # entropy pass flags a large set.
BLOB_CONFIRM_MEMBERS_CAP = 200     # member rows per candidate topic (well above
                                   # overmerge.MIN_MEMBERS=12, bounded query cost)
_WALK_BLOB_MEMBERS_SQL = """
    WITH ranked AS (
        SELECT (split_part(tm.topic_id, '-', 3))::int AS tid,
               se.vec::text AS vec,
               ROW_NUMBER() OVER (
                   PARTITION BY tm.topic_id ORDER BY tm.signal_id
               ) AS rn
        FROM topic_members tm
        JOIN signal_embeddings se ON se.signal_id = tm.signal_id
        WHERE tm.topic_id = ANY($1::text[])
          AND tm.role = 'evidence'
          AND tm.engine_version = 'v1-compat'
          AND tm.quarantined IS NOT TRUE
    )
    SELECT tid, vec FROM ranked WHERE rn <= $2
"""


class WalkRequest(BaseModel):
    topic_ids: list[str] = Field(..., min_length=1, max_length=MAX_PINS)
    # "¿hasta dónde caminar?" — the relative-floor slider (spec §2.3). Lower =
    # walk further out; HOP_CAP is fixed. Clamped to a sane range.
    rel_floor: float = Field(0.35, ge=0.10, le=0.90)


def _walk_empty(topic_ids: list[str], reason: str) -> dict:
    return {"contract": "constellation-walk-v0", "seeds": [], "kin": [],
            "unresolved": topic_ids, "meta": {"reason": reason}}


@router.post("/walk")
async def dossier_walk(req: WalkRequest):
    """From-pins multi-hop kinship walk. Returns hermanos + primos with degree,
    accumulated weight (the trail thickness), per-hop receipts, blob flags and
    same-event fold counts — everything the radial constellation renders. Honest
    orphan state when a pin has no measured kin (spec §8)."""
    base_to_raw: dict[str, str] = {}
    for raw in req.topic_ids:
        base = _base_topic_id(raw)
        if base and base not in base_to_raw:
            base_to_raw[base] = raw
    seed_bases = [b for b in base_to_raw
                  if b.startswith("dynamic-topic-") and b[len("dynamic-topic-"):].isdigit()]
    if not seed_bases:
        return _walk_empty(req.topic_ids, "no_topic_centroids")
    if db.pool is None:
        return _walk_empty(req.topic_ids, "no_db")

    cache_key = (tuple(sorted(seed_bases)), round(req.rel_floor, 3))
    hit = _WALK_CACHE.get(cache_key)
    if hit and time.monotonic() - hit[0] < _WALK_CACHE_TTL_S:
        return hit[1]

    seed_ids = {int(b[len("dynamic-topic-"):]) for b in seed_bases}
    try:
        async with db.pool.acquire() as conn:
            await conn.execute("SET statement_timeout = 15000")
            rows = await conn.fetch(_WALK_TOPICS_SQL)
            # ensure every pinned seed is a node even if it just left 'active'
            present = {int(r["id"]) for r in rows}
            missing = [i for i in seed_ids if i not in present]
            if missing:
                extra = await conn.fetch(
                    "SELECT id, label, category, centroid_vec FROM dynamic_topics "
                    "WHERE id = ANY($1::int[]) AND centroid_vec IS NOT NULL",
                    missing,
                )
                rows = list(rows) + list(extra)
    except Exception as exc:  # pragma: no cover - defensive I/O
        logger.warning("walk topic fetch failed: %s", str(exc)[:200])
        return _walk_empty(req.topic_ids, "db_error")

    import numpy as np

    ids: list[int] = []
    labels: list[str] = []
    cats: list[str | None] = []
    vecs: list[list[float]] = []
    for r in rows:
        v = r["centroid_vec"]
        if v is None or len(v) != 768:
            continue
        ids.append(int(r["id"]))
        labels.append(r["label"] or "")
        cats.append(r["category"])
        vecs.append([float(x) for x in v])
    idx = {tid: i for i, tid in enumerate(ids)}
    seeds = [idx[i] for i in seed_ids if i in idx]
    resolved_seed_bases = {f"dynamic-topic-{i}" for i in seed_ids if i in idx}
    unresolved = [raw for base, raw in base_to_raw.items()
                  if base not in resolved_seed_bases]
    if not seeds:
        return _walk_empty(req.topic_ids, "seeds_have_no_centroid")

    try:
        from app.services.whitening import apply_whitening, load_whitening
        whitened = apply_whitening(np.asarray(vecs, dtype=np.float32), load_whitening())
    except Exception as exc:  # pragma: no cover - asset missing
        logger.warning("walk whitening unavailable: %s", str(exc)[:200])
        return _walk_empty(req.topic_ids, "whitening_unavailable")

    import dataclasses
    params = dataclasses.replace(WalkParams.from_env(), rel_floor=req.rel_floor)

    # Blob CONFIRMER (spec §2.4 A2 followup): run the cheap entropy first-pass
    # here (not inside walk_constellation) so we know the CANDIDATE set before
    # bounding a DB fetch to just those topics' member embeddings — membership
    # multimodality (overmerge.decide, no LLM) then confirms or spares each one.
    # Graceful fallback by construction: any failure below (no candidates, the
    # fetch errors, a candidate has too few embedded members) leaves
    # `member_vecs` empty for that node and `walk_constellation` falls back to
    # the entropy-only flag — never crashes, never blocks the walk.
    graph = build_knn_graph(whitened, k=params.k)
    blob_candidates = blob_connector_flags(graph, cats, params)
    member_vecs: dict[int, np.ndarray] = {}
    if blob_candidates:
        try:
            # bound even the candidate set itself (mindful: never an unbounded
            # fetch), preferring the strongest connectors if there are many.
            capped = sorted(blob_candidates, key=lambda i: -int(graph.indeg[i]))
            capped = capped[:BLOB_CONFIRM_MAX_CANDIDATES]
            idx_by_db_id = {ids[i]: i for i in capped}
            candidate_topic_ids = [f"dynamic-topic-{ids[i]}" for i in capped]
            async with db.pool.acquire() as conn:
                await conn.execute("SET statement_timeout = 8000")
                member_rows = await conn.fetch(
                    _WALK_BLOB_MEMBERS_SQL, candidate_topic_ids, BLOB_CONFIRM_MEMBERS_CAP,
                )
            by_idx: dict[int, list] = {}
            for r in member_rows:
                node_i = idx_by_db_id.get(int(r["tid"]))
                if node_i is None:
                    continue
                try:
                    vec = np.asarray(json.loads(r["vec"]), dtype=np.float32)
                except Exception:
                    continue
                by_idx.setdefault(node_i, []).append(vec)
            member_vecs = {i: np.vstack(v) for i, v in by_idx.items() if v}
        except Exception as exc:  # pragma: no cover - defensive I/O
            logger.warning("walk blob-confirm member fetch failed (entropy-only "
                           "fallback): %s", str(exc)[:200])
            member_vecs = {}

    result = walk_constellation(whitened, cats, seeds, params, graph=graph,
                                blob_candidates=blob_candidates,
                                member_vecs=member_vecs)

    seed_payload = [
        {"id": f"dynamic-topic-{ids[s]}", "label": labels[s], "category": cats[s]}
        for s in seeds
    ]
    # Typed energy/oil destinations (spec §2.7) — word-boundary term match, so the
    # analyst's marquee (Iran → Hormuz → oil price) reads as a typed arrival.
    _ENERGY_TERMS = ("oil", "crude", "petroleum", "brent", "opec", "hormuz",
                     "energy exports", "fuel", "gas price", "strait")
    _ENERGY_CATS = {"Oil and gas supply risk", "Fuel subsidy unrest"}

    kin: list[dict] = []
    for rep in result.reps:
        node = result.reached[rep]
        parent = node.via_parent
        folded = result.fold_map.get(rep, [])
        # blob provenance (spec §2.4 A2): via_parent is the node whose OUTWARD
        # hop was penalized when through_blob is set — look up how THAT
        # decision was made (entropy-only vs multimodality-confirmed) so the
        # receipt is never a silent penalty.
        parent_confirm = result.blob_confirmations.get(parent) if parent is not None else None
        kin.append({
            "id": f"dynamic-topic-{ids[rep]}",
            "label": labels[rep],
            "category": cats[rep],
            "degree": node.degree,
            "kinship": node.kinship,           # hermano | primo
            "acc_weight": node.acc_weight,     # trail thickness (spec §1.5)
            "via": {
                "parent_id": f"dynamic-topic-{ids[parent]}" if parent is not None else None,
                "parent_label": labels[parent] if parent is not None else None,
                # v1 receipt basis = whitened semantic cosine (the walk graph is
                # semantic); the value is the honest measured quantity of the hop.
                "basis": "semantic",
                "weight": node.via_weight,
                "through_blob": node.through_blob,
                "blob_basis": parent_confirm.basis if (node.through_blob and parent_confirm) else None,
            },
            "is_blob": rep in result.blob_flags,
            "blob_basis": result.blob_confirmations[rep].basis if rep in result.blob_flags else None,
            "folded_count": len(folded),
            "folded_labels": [labels[f] for f in folded][:6],
            "destination": match_destination(labels[rep], cats[rep], _ENERGY_TERMS,
                                              categories=_ENERGY_CATS),
        })
    kin.sort(key=lambda k: (k["degree"], -k["acc_weight"]))

    blob_bases = [c.basis for c in result.blob_confirmations.values() if c.confirmed]
    payload = {
        "contract": "constellation-walk-v0",
        "seeds": seed_payload,
        "kin": kin,
        "unresolved": unresolved,
        "meta": {
            "reason": None if kin else "no_measured_kin",
            "topic_universe": len(ids),
            "rel_floor": req.rel_floor,
            "hop_cap": params.hop_cap,
            "k_neighbors": params.k,
            "blob_connectors": len(result.blob_flags),
            # spec §2.4 A2: how many confirmed blobs were actually structurally
            # confirmed via member-embedding multimodality vs. fell back to the
            # entropy-only flag (no DB / no embedded members / an old topic).
            "blob_candidates": len(blob_candidates),
            "blob_multimodality_confirmed": sum(1 for b in blob_bases if b == "multimodality_confirmed"),
            "blob_entropy_only_fallback": sum(1 for b in blob_bases if b == "entropy_only"),
            "dedup_tau": params.dedup_tau,
            "reached_before_dedup": len(result.reached),
            "hermanos": sum(1 for k in kin if k["kinship"] == "hermano"),
            "primos": sum(1 for k in kin if k["kinship"] == "primo"),
            "max_degree": max((k["degree"] for k in kin), default=0),
            "semantic_space": "whitened-e5-k1-global",
            "walk": "from-pins max-product; brake REL_FLOOR+HOP_CAP; undirected; no LLM",
        },
    }
    _WALK_CACHE[cache_key] = (time.monotonic(), payload)
    return payload


# ── Dossier synthesis (standalone brief) ─────────────────────────────────────
# The report must STAND ALONE (Frank test): a stranger reading only the brief
# should understand the story. The templated one-liner can't do that. This runs
# ONE grounded LLM pass over the FROZEN pin evidence + the MEASURED connection
# verdict → a headline, a synthesis that names the non-obvious finding, and the
# key gap. Measured at generation time (labeled as such); never fabricates beyond
# the evidence; degrades to absence so the frozen report always stands.

# ── Web corroboration (P0.6b — the manual NATO-Ankara run, productized) ──────
# Backend-first, math+search: per pin, 1-2 focused queries → the #161
# external-depth lane (GDELT DOC 2.0 — free, no key, credibility-tiered) →
# source-INDEPENDENCE weighting (G2: syndicated wire collapses to one source,
# independently-operated outlets are counted, never articles). LLM is used for
# ONE thing only: phrasing the coverage-asymmetry note over the gathered titles
# (glass-box — only from supplied titles; ai_cost surface 'dossier-corroborate').
#
# Search-path note: no generic web-search key (SERP/Brave/Bing) is configured on
# this deploy — GDELT DOC 2.0 is the free news-search executor. Setting
# ATLAS_WEB_SEARCH_* in the future upgrades the lane; meanwhile the contract
# also accepts CLIENT-SUPPLIED results (`supplied_results`) so an agent or the
# frontend can paste an external search run into the same math.

class CorrobPin(BaseModel):
    id: str
    label: str
    anchor_type: str | None = None
    actors: list[str] = Field(default_factory=list)   # measured actors (optional)
    evidence: list[str] = Field(default_factory=list)  # frozen headlines (asymmetry input)


class CorrobSuppliedResult(BaseModel):
    pin_id: str
    title: str
    url: str = ""
    outlet: str | None = None


class CorroborateRequest(BaseModel):
    pins: list[CorrobPin] = Field(..., min_length=1)
    days: int = Field(14, ge=3, le=30)
    supplied_results: list[CorrobSuppliedResult] = Field(default_factory=list)
    force: bool = False   # bypass the server cache (the frontend's re-run)


_CORROB_CACHE: dict = {}
_CORROB_CACHE_TTL_S = 900
_ASYMMETRY_SYSTEM = (
    "You compare what an analyst's PINNED evidence emphasizes versus what WEB "
    "coverage titles emphasize, per story and overall. STRICT RULES: use ONLY "
    "the supplied titles — never invent events, actors, or framings not present "
    "in them; name which side (pinned set vs web) carries an emphasis the other "
    "lacks; if no clear asymmetry is visible from the titles, say exactly that. "
    "Answer in 2-4 plain sentences, no preamble, no JSON."
)


def _asymmetry_user(pins: list[CorrobPin], web_titles: dict[str, list[str]]) -> str:
    parts: list[str] = []
    for p in pins:
        titles = web_titles.get(p.id) or []
        if not p.evidence and not titles:
            continue
        parts.append(f"STORY: {p.label}")
        for h in p.evidence[:4]:
            parts.append(f"  pinned: {h}")
        for t in titles[:6]:
            parts.append(f"  web: {t}")
    parts.append(
        "\nWhat does the web coverage emphasize that the pinned evidence does "
        "not, and vice versa?")
    return "\n".join(parts)


@router.post("/corroborate")
async def dossier_corroborate(req: CorroborateRequest):
    """Per-pin web corroboration with source-independence weighting."""
    import asyncio

    from app.services.corroboration import (
        MAX_CITATIONS_PER_PIN, build_pin_queries, independence, pin_status,
        ESTABLISHED_MIN_OUTLETS,
    )
    from app.services.external_depth import fetch_external_depth
    from app.services.source_tiers import ownership_group, tier_payload

    pins = req.pins
    timespan = f"{req.days}d"

    cache_key = (tuple(sorted(
        (p.id, p.label, p.anchor_type, tuple(p.actors), tuple(p.evidence))
        for p in pins
    )), req.days,
                 tuple(sorted((s.pin_id, s.title) for s in req.supplied_results)))
    if not req.force:
        hit = _CORROB_CACHE.get(cache_key)
        if hit and time.monotonic() - hit[0] < _CORROB_CACHE_TTL_S:
            return hit[1]

    # 1-2 focused queries per pin, all fetched concurrently (DOC 2.0 p50 is
    # 16-35s per query — sequential would take minutes).
    pin_queries: dict[str, list[str]] = {
        p.id: (
            build_pin_queries(p.label, p.actors, p.evidence)
            if p.evidence else []
        )
        for p in pins
    }
    tasks: list = []
    task_owner: list[tuple[str, str]] = []   # (pin_id, query)
    for p in pins:
        for q in pin_queries[p.id]:
            tasks.append(fetch_external_depth(p.label, raw_query=q, timespan=timespan))
            task_owner.append((p.id, q))
    results = await asyncio.gather(*tasks, return_exceptions=True) if tasks else []

    any_lane_ok = False
    lane_ok_by_pin: dict[str, bool] = {p.id: False for p in pins}
    articles_by_pin: dict[str, list[dict]] = {p.id: [] for p in pins}
    seen_urls: dict[str, set] = {p.id: set() for p in pins}
    for (pin_id, _q), res in zip(task_owner, results):
        if isinstance(res, Exception) or res is None:
            continue
        any_lane_ok = True
        lane_ok_by_pin[pin_id] = True
        for item in res.get("items", []):
            u = item.get("url") or ""
            if u and u in seen_urls[pin_id]:
                continue
            seen_urls[pin_id].add(u)
            articles_by_pin[pin_id].append({
                "title": item["title"],
                "url": u,
                "outlet": item.get("domain") or "",
                "language": item.get("language"),
                "seendate": item.get("seendate"),
                "credibility": item.get("credibility"),
                "lane": "gdelt-doc-2.0",
            })

    # Client-supplied lane (contract v0): merged into the same independence math.
    supplied_any = False
    for s in req.supplied_results:
        if s.pin_id not in articles_by_pin:
            continue
        outlet = (s.outlet or "").strip().lower()
        if not outlet and s.url:
            import urllib.parse as _up
            outlet = _up.urlparse(s.url).netloc.removeprefix("www.")
        articles_by_pin[s.pin_id].append({
            "title": s.title, "url": s.url, "outlet": outlet,
            "language": None, "seendate": None, "credibility": None,
            "lane": "client-supplied",
        })
        lane_ok_by_pin[s.pin_id] = True
        supplied_any = True

    search_available = any_lane_ok or supplied_any

    pin_payloads: list[dict] = []
    web_titles: dict[str, list[str]] = {}
    for p in pins:
        arts = articles_by_pin[p.id]
        # corroborate-v2 R1: outlets in one state apparatus collapse to ONE
        # voice, and every citation ships its ownership group + tier so the
        # render can SAY why three receipts counted once.
        ind = independence(arts, group_fn=ownership_group)
        pin_search_available = lane_ok_by_pin[p.id]
        applicable = bool(p.evidence)
        status, note = pin_status(
            ind["independent_voices"],
            pin_search_available,
            applicable=applicable,
            outlets=ind["independent_outlets"],
            state_collapsed=ind["state_collapsed"],
        )
        citations = [{
            "title": c["title"], "url": c["url"], "outlet": c["outlet"],
            "language": c.get("language"), "seendate": c.get("seendate"),
            "lane": c.get("lane"),
            "ownership_group": c.get("ownership_group"),
            "credibility": tier_payload(c.get("outlet")),
        } for c in ind["citations"][:MAX_CITATIONS_PER_PIN]]
        web_titles[p.id] = [f"{c['title']} — {c['outlet']}" for c in citations]
        pin_payloads.append({
            "id": p.id,
            "label": p.label,
            "status": status,
            "independent_outlets": ind["independent_outlets"],
            "independent_voices": ind["independent_voices"],
            "state_collapsed": ind["state_collapsed"],
            "total_articles": ind["total_articles"],
            "syndicated_clusters": ind["syndicated_clusters"],
            # Voices, not outlets: three same-state outlets ARE one source
            # (corroborate-v2 R1 — the bar and this flag must agree).
            "single_source": (
                applicable
                and pin_search_available
                and ind["independent_voices"] <= 1
            ),
            "citations": citations,
            "note": note,
            "queries": pin_queries[p.id],
        })

    # ONE LLM call, phrasing only — the coverage-asymmetry slot (glass-box:
    # built strictly from the gathered titles + pinned headlines).
    asymmetry = None
    if search_available and any(wt for wt in web_titles.values()):
        try:
            measured_pins = [p for p in pins if lane_ok_by_pin[p.id]]
            text, provider, _err, _usage = await generate_insight(
                _ASYMMETRY_SYSTEM, _asymmetry_user(measured_pins, web_titles),
                max_tokens=300, surface="dossier-corroborate",
            )
            if text:
                asymmetry = {"note": text.strip(), "provider": provider}
        except Exception as exc:  # noqa: BLE001 — never blocks the math
            logger.warning("corroboration asymmetry pass failed: %s", exc)

    payload = {
        "contract": "dossier-corroboration-v1",
        "measured_at": __import__("datetime").datetime.utcnow().isoformat() + "Z",
        "search_available": search_available,
        "search_source": "gdelt-doc-2.0" if any_lane_ok else
                         ("client-supplied" if supplied_any else None),
        "window_days": req.days,
        "pins": pin_payloads,
        "coverage_asymmetry": asymmetry,
        "meta": {
            "independence_rule": (
                "near-identical headlines (syndicated wire) collapse to one "
                "source; independently-operated outlets are counted, never "
                "articles (G2); outlets in the same-state apparatus then "
                "collapse to ONE voice — ria + tass + rt writing separately "
                "is three outlets but one government speaking (v2 R1)"),
            "status_rule": (
                f"established = ≥{ESTABLISHED_MIN_OUTLETS} independent VOICES "
                "(ownership-collapsed outlets, not articles); unverified "
                "otherwise; 'contested' is reserved for stance detection "
                "(not emitted by this math); metadata-only context with no "
                "frozen evidence is not_applicable"),
            "dropped_pins": 0,
            "search_note": (
                None
                if search_available
                else (
                    "no evidence-bearing pins — context remains in the dossier "
                    "but has no frozen claim to corroborate"
                    if not any(p.evidence for p in pins)
                    else (
                        "no server-side web-search path answered — GDELT DOC "
                        "2.0 unreachable and no supplied results; a SERP/Brave "
                        "key would add a generic-web lane"
                    )
                )
            ),
        },
    }
    _CORROB_CACHE[cache_key] = (time.monotonic(), payload)
    return payload


@router.post("/synthesize")
async def dossier_synthesize(req: SynthesizeRequest):
    return await synthesize_publication_article(req)

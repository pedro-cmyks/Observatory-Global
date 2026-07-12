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
from app.services.insight_llm import generate_insight
from app.services.subjects import classify_subject

router = APIRouter(prefix="/api/v2/dossier", tags=["dossier"])
logger = logging.getLogger(__name__)

MAX_PINS = 16
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
    topic_ids: list[str] = Field(..., min_length=1, max_length=64)
    days: int = Field(30, ge=7, le=90)
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
            shared_persons_all = person_sets[bi] & person_sets[bj]
            shared_persons = sorted(
                p for p in shared_persons_all
                if len(person_docs.get(p, ())) <= distinct_df_max
            )
            # GDELT truncation variants ("tayyip erdo" ‖ "tayyip erdogan") read
            # as two actors in the verdict — keep only the longest form.
            shared_persons = [
                p for p in shared_persons
                if not any(q != p and q.startswith(p) for q in shared_persons)
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
            if shared_persons:
                basis.append("shared_person")
                # rarity weight: rarer shared actor => stronger link
                rarity = sum(1.0 / max(1, len(person_docs.get(p, ()))) for p in shared_persons)
                weight = max(weight, min(0.98, 0.65 + 0.15 * rarity))
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

    # ── Neighbors: the nearest UNPINNED stories to each pin — the background
    # field that makes this a CONSTELLATION (context + bridges), not 3 lonely
    # dots. A neighbor near >1 pin is a bridge (an unpinned link you didn't pin).
    neighbors: list[dict] = []
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
                    e["links"].append({"pin": pin_ids[pj], "sim": round(s, 4)})
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
            "actor_filter": "shared/top actors pass the person gate + subjects gazetteer + geo-feature token guard (NER junk excluded)",
            "position_basis": "PCA top-2 of pinned e5 centroids — approximate; edges are exact",
        },
    }
    _cache[cache_key] = (time.monotonic(), payload)
    return payload


# ── Dossier synthesis (standalone brief) ─────────────────────────────────────
# The report must STAND ALONE (Frank test): a stranger reading only the brief
# should understand the story. The templated one-liner can't do that. This runs
# ONE grounded LLM pass over the FROZEN pin evidence + the MEASURED connection
# verdict → a headline, a synthesis that names the non-obvious finding, and the
# key gap. Measured at generation time (labeled as such); never fabricates beyond
# the evidence; degrades to absence so the frozen report always stands.

class SynthEvidenceItem(BaseModel):
    # P0.6a: structured frozen evidence — the citation table for the mini-article.
    # The server numbers these [1..N] in the prompt and resolves the model's [n]
    # markers back against THIS table (never trusting an echoed citation list).
    headline: str
    source: str | None = None
    date: str | None = None
    url: str | None = None


class SynthPin(BaseModel):
    label: str
    type: str | None = None
    evidence: list[str] = Field(default_factory=list)  # frozen headlines (may carry "— source")
    # Structured variant of `evidence` (preferred when present) — enables the
    # authoritative numbered-receipts table. Legacy `evidence` strings still work.
    evidence_items: list[SynthEvidenceItem] = Field(default_factory=list)
    note: str | None = None
    # Server-side low-coherence flag on the pin's thread (a conflated black-hole
    # whose evidence is a mix of unrelated events). Optional — set by a parallel
    # task; the prompt-level evidence-to-label self-check runs regardless.
    low_coherence: bool = False


class SynthConnectionNode(BaseModel):
    # Per-pin connectedness from the MEASURED relation graph — the fix for the
    # over-claim failure: the whole set can read 'grounded' off ONE confirmed edge
    # while a third pin hangs on only similarity-only edges. This tells the prompt
    # which pins are the confirmed spine and which are merely topically adjacent.
    label: str
    connectedness: str | None = None   # 'confirmed' | 'text-linked' | 'similar-only' | 'isolated'
    confirmed_with: list[str] = Field(default_factory=list)  # shared-actor/place partners
    similar_with: list[str] = Field(default_factory=list)    # semantic-only partners
    # Frank v2 blocker 1: verbatim evidence-text mentions of another pin
    # ("evidence text mentions 'nato summit' (NATO Summit Ankara)"). A pin with
    # one of these must NEVER be narrated as "no evidence links them".
    text_mentions: list[str] = Field(default_factory=list)


class SynthConnection(BaseModel):
    # 'grounded' (shared actors/places) | 'similar-only' (semantic proximity only)
    # | 'split' | 'isolated' — the basis-weighted verdict from the frontend.
    state: str | None = None
    nodes: list[SynthConnectionNode] = Field(default_factory=list)  # per-pin connectedness
    links: list[str] = Field(default_factory=list)     # "A ↔ B — shared actor X"
    countries: list[str] = Field(default_factory=list)
    languages: list[str] = Field(default_factory=list)
    press: int = 0
    public: int = 0
    bridges: list[str] = Field(default_factory=list)    # unpinned stories nearby
    # Frank v2 blocker 6: automatic coverage-lens note when one language/origin
    # dominates the pinned evidence (math-only, computed client-side).
    lens_note: str | None = None


class SynthesizeRequest(BaseModel):
    title: str = ""
    pins: list[SynthPin] = Field(..., min_length=1, max_length=32)
    connection: SynthConnection | None = None
    gaps: list[str] = Field(default_factory=list)


_SYNTH_SYSTEM = (
    "You are a news-desk editor writing a PUBLISHABLE STANDALONE mini-article from "
    "an analyst's pinned evidence. A stranger reading ONLY your article must "
    "understand the story AND must NOT be misled into thinking loosely-related pins "
    "form one confirmed narrative. You are given the pinned stories with their "
    "frozen evidence headlines — each NUMBERED '[n]' and possibly ending "
    "'— <outlet>, <YYYY-MM-DD>' — a MEASURED connection verdict, and PER-PIN "
    "connectedness. Rules:\n"
    "0. ARTICLE FORM WITH RECEIPTS. Write a dated lede (1-2 sentences answering "
    "who/what/when/where from the DATED evidence) and a short body (2-4 short "
    "paragraphs). EVERY factual claim in the lede and body must end with the "
    "inline citation marker(s) '[n]' of the numbered evidence line(s) supporting "
    "it (e.g. 'ordered the cutoff [2]', multiple allowed '[1][4]'). You may cite "
    "ONLY the supplied numbered evidence — never outside knowledge, never a number "
    "that was not supplied. A sentence you cannot back with a supplied [n] does "
    "not belong in the body. If the evidence is THIN, write a SHORTER body — never "
    "pad, never generalize to fill space.\n"
    "1. GROUND everything in the supplied evidence — never invent facts, numbers, "
    "actors, events, dates, or outcomes that are not in the headlines.\n"
    "2. LEAD WITH THE CONFIRMED SPINE. Build the through-line ONLY from pins whose "
    "per-pin connectedness is 'confirmed' (they share a real actor or place); name "
    "that shared actor/place. A pin marked 'similar-only' shares NO actor or place "
    "with the others — it is topically or linguistically adjacent, NOT confirmed "
    "connected. You MUST explicitly bracket such a pin: say it is 'topically "
    "adjacent, not confirmed connected — possibly an artifact of shared language/"
    "topic', and do NOT weave it into the main narrative as if the link were proven. "
    "Even when the overall state is 'grounded', a single confirmed edge does not make "
    "every pin part of one story. If the state is 'split' or 'isolated', say the pins "
    "do not form one story.\n"
    "2b. TEXT MENTIONS OVERRIDE 'no link' CLAIMS. A pin may carry evidence-text "
    "mentions ('evidence text mentions …'): its headline TEXT references another "
    "pinned story even though entity extraction found no shared actor. Describe such "
    "a pin exactly that way — 'isolated by entity extraction, but its evidence text "
    "references <term> — verify' — and NEVER write 'no evidence links them' or "
    "'isolated, unconnected' about a pin that carries a text mention. A 'text-linked' "
    "connectedness is weaker than 'confirmed' but stronger than 'similar-only'.\n"
    "2c. GLASS BOX ON LINK NAMES. When naming WHAT links two pins, quote ONLY the "
    "exact measured tokens handed to you (the shared actor/place names or mention "
    "terms in 'links' / per-pin connectedness). Never substitute, embellish, or "
    "infer different actor names for a link, even if they read more naturally.\n"
    "3. CHECK EVIDENCE-TO-LABEL FIT. For each pin, verify its evidence headlines "
    "actually name the actors or place in the pin's OWN label. If a pin's bullets do "
    "NOT support its label (they describe unrelated actors/events — a conflated or "
    "mis-labelled thread), or the pin is flagged LOW-COHERENCE, do NOT narrate its "
    "content as if it were about the label: flag that pin as UNRELIABLE (state that "
    "its evidence does not match its label) and exclude it from the finding.\n"
    "4. DO NOT ASSERT CONTESTED OUTCOMES AS FACT. Election results, concessions, "
    "inaugurations, and transfers of power are claims, not givens. Do NOT state one "
    "as settled fact unless an evidence headline DIRECTLY states it happened. "
    "Attribute contested or single-sourced outcomes to their source ('reported by "
    "<outlet>', 'per <outlet>') and prefer hedged phrasing ('reportedly', 'is said "
    "to') when a headline announces rather than confirms. Surface a date if a "
    "headline carries one (evidence lines may end '— <outlet>, <YYYY-MM-DD>'); date "
    "contested outcomes with it; if outcomes are undated, say the timing is unclear.\n"
    "5. SURFACE THE NON-OBVIOUS insight visible only across pins (a self-declared "
    "alignment, a coverage asymmetry, an actor bridging two CONFIRMED stories) — but "
    "only over the confirmed spine, never over a bracketed or unreliable pin.\n"
    "6. UNKNOWNS — 'what we don't know'. 2-4 short bullet-style sentences naming "
    "what is missing or unproven: missing voices (no public/forum signal, absent "
    "languages/origins), unverified or single-sourced claims, undated outcomes, "
    "pins frozen metadata-only (no evidence captured), isolated or text-linked-only "
    "pins (with their verify caveat). When a 'coverage lens' note is supplied, one "
    "unknown MUST carry it (the evidence leans one language/origin — say so).\n"
    "Output STRICT JSON only, no prose around it: "
    '{"headline": "<=14 words, the confirmed finding", '
    '"lede": "1-2 sentences, dated, who/what/when/where, with [n] markers", '
    '"body": ["2-4 short paragraphs, every claim ending with its [n] marker(s)"], '
    '"unknowns": ["2-4 sentences"]}.'
)


# Legacy folded evidence string "headline — outlet, YYYY-MM-DD" (the frontend
# folds attribution into the string; structured evidence_items are preferred).
_LEGACY_EVIDENCE_RE = re.compile(
    r"^(?P<headline>.+?)\s+—\s+(?:(?P<source>.+?),\s+)?(?P<date>\d{4}-\d{2}-\d{2})$"
)


def _citation_table(req: SynthesizeRequest) -> list[dict]:
    """Global numbered receipts [1..N] across pins, in prompt order. This table
    is AUTHORITATIVE: the model's [n] markers resolve against it — an echoed or
    invented citation can never enter the response."""
    table: list[dict] = []
    for pin_i, p in enumerate(req.pins):
        if p.evidence_items:
            items = [
                {"headline": e.headline, "source": e.source, "date": e.date, "url": e.url}
                for e in p.evidence_items[:6]
            ]
        else:
            items = []
            for h in p.evidence[:6]:
                m = _LEGACY_EVIDENCE_RE.match(h)
                if m:
                    items.append({"headline": m.group("headline"),
                                  "source": m.group("source"),
                                  "date": m.group("date"), "url": None})
                else:
                    items.append({"headline": h, "source": None, "date": None, "url": None})
        for it in items:
            table.append({"n": len(table) + 1, "pin": p.label, "pin_i": pin_i, **it})
    return table


def _synth_user(req: SynthesizeRequest) -> str:
    parts: list[str] = []
    if req.title:
        parts.append(f"Investigation title: {req.title}")
    table = _citation_table(req)
    by_pin: dict[int, list[dict]] = {}
    for row in table:
        by_pin.setdefault(row["pin_i"], []).append(row)
    parts.append("\nPINNED STORIES + frozen evidence (numbered — cite as [n]):")
    for i, p in enumerate(req.pins, 1):
        flag = " [⚠ LOW-COHERENCE thread — evidence may be a conflated mix]" if p.low_coherence else ""
        parts.append(f"{i}. {p.label}" + (f" [{p.type}]" if p.type else "") + flag)
        rows = by_pin.get(i - 1, [])
        if not rows:
            parts.append("   (metadata only — no frozen evidence captured for this pin)")
        for row in rows:
            attribution = ""
            if row["source"] or row["date"]:
                bits = [b for b in (row["source"], row["date"]) if b]
                attribution = " — " + ", ".join(bits)
            parts.append(f"   [{row['n']}] {row['headline']}{attribution}")
        if p.note:
            parts.append(f"   note: {p.note}")
    c = req.connection
    if c:
        parts.append("\nMEASURED CONNECTION VERDICT:")
        parts.append(f"  state: {c.state or 'unknown'}")
        if c.nodes:
            parts.append("  per-pin connectedness (from the measured relation graph):")
            for nd in c.nodes:
                line = f"    - {nd.label}: {nd.connectedness or 'unknown'}"
                if nd.confirmed_with:
                    line += " — confirmed link (shared actor/place) to " + ", ".join(nd.confirmed_with[:6])
                if nd.similar_with:
                    line += " — similarity-only proximity to " + ", ".join(nd.similar_with[:6])
                parts.append(line)
                for tm in nd.text_mentions[:4]:
                    parts.append(f"      · {tm}")
        if c.links:
            parts.append("  links: " + " | ".join(c.links[:8]))
        if c.countries:
            parts.append("  countries touched: " + ", ".join(c.countries[:10]))
        if c.languages:
            parts.append("  coverage languages: " + ", ".join(c.languages[:8]))
        parts.append(f"  press signals: {c.press} · public/forum signals: {c.public}")
        if c.lens_note:
            parts.append(f"  coverage lens: {c.lens_note}")
        if c.bridges:
            parts.append("  nearby unpinned stories (bridges): " + " | ".join(c.bridges[:6]))
    if req.gaps:
        parts.append("\nKNOWN GAPS (from the frozen report):")
        for g in req.gaps[:6]:
            parts.append(f"  - {g}")
    return "\n".join(parts)


def _extract_json(text: str) -> dict | None:
    """Lenient — providers sometimes fence the JSON or add a sentence around it."""
    try:
        return json.loads(text)
    except Exception:
        pass
    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end != -1 and end > start:
        try:
            return json.loads(text[start:end + 1])
        except Exception:
            return None
    return None


_CITE_RE = re.compile(r"\[(\d{1,3})\]")


def _as_paragraphs(v) -> list[str] | None:
    """body/unknowns arrive as a list of strings or a single string — normalize
    to a clean list of non-empty paragraphs."""
    if isinstance(v, str):
        v = [s for s in re.split(r"\n{2,}|\n(?=- )", v)]
    if not isinstance(v, list):
        return None
    out = [str(s).strip().lstrip("- ").strip() for s in v if str(s).strip()]
    return out or None


def _resolve_citations(texts: list[str], table: list[dict]) -> list[dict]:
    """[n] markers found in the article, resolved against the AUTHORITATIVE
    numbered table (first-appearance order; out-of-range ns dropped). The model
    never gets to invent a receipt."""
    by_n = {row["n"]: row for row in table}
    seen: list[int] = []
    for t in texts:
        for m in _CITE_RE.finditer(t):
            n = int(m.group(1))
            if n in by_n and n not in seen:
                seen.append(n)
    return [
        {"n": n, "headline": by_n[n]["headline"], "source": by_n[n]["source"],
         "date": by_n[n]["date"], "url": by_n[n]["url"], "pin": by_n[n]["pin"]}
        for n in seen
    ]


@router.post("/synthesize")
async def dossier_synthesize(req: SynthesizeRequest):
    """One grounded LLM pass → publishable mini-article {headline, lede, body,
    unknowns, citations}; legacy {headline, synthesis, gap} passthrough when the
    model answers in the old shape."""
    contract = "dossier-synthesis-v2"
    empty = {"contract": contract, "headline": None, "lede": None, "body": None,
             "unknowns": None, "citations": None, "synthesis": None, "gap": None}
    text, provider, error, _usage = await generate_insight(
        _SYNTH_SYSTEM, _synth_user(req), max_tokens=1200, surface="dossier-synthesis",
    )
    if not text:
        return {**empty, "provider": None, "error": error or "insight_unavailable"}
    parsed = _extract_json(text)
    if not parsed:
        # non-JSON reply — still useful; hand the prose back as the legacy synthesis.
        return {**empty, "synthesis": text.strip(), "provider": provider, "error": None}
    lede = (parsed.get("lede") or "").strip() or None
    body = _as_paragraphs(parsed.get("body"))
    if lede or body:
        unknowns = _as_paragraphs(parsed.get("unknowns"))
        citations = _resolve_citations(
            ([lede] if lede else []) + (body or []), _citation_table(req))
        return {
            **empty,
            "headline": (parsed.get("headline") or None),
            "lede": lede,
            "body": body,
            "unknowns": unknowns,
            "citations": citations or None,
            "provider": provider,
            "error": None,
        }
    # Legacy shape — frontend falls back to the old renderer.
    return {
        **empty,
        "headline": (parsed.get("headline") or None),
        "synthesis": (parsed.get("synthesis") or None),
        "gap": (parsed.get("gap") or None),
        "provider": provider,
        "error": None,
    }

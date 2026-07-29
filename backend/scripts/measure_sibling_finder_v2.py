#!/usr/bin/env python3
"""Sibling-finder v2 — pre-registered measurement harness (READ-ONLY).

Pre-registration: docs/superpowers/specs/2026-07-29-sibling-finder-v2-preregistration.md
Trigger (the NO-GO under attack): docs/research/gold/2026-07-29-story-lens-navloss-check.md
Witness protocol: docs/superpowers/specs/2026-07-28-entity-overlap-identity-design.md §2.5

THE CLAIM UNDER TEST
--------------------
A candidate UNION — whitened-cos kNN (lane C, the shipped v1 walk) ∪ rare-shared-
entity (lane E) ∪ country+time proximity (lane G) — with union-aware scoring can
surface TRUE same-event siblings on the current shredded field, where cos-only
cannot.

FROZEN GATES (pre-registration §"Pre-registered gates"; NOT movable here)
-------------------------------------------------------------------------
  G1  per witness family: >=3 TRUE same-event fragments (hand-verified) in the
      TOP-8 siblings of at least one family anchor.  v1 baseline reported beside.
  G2  top-5 of 10 RANDOM active anchors = 50 rows; <=2/50 may be judged
      "unrelated story presented as kin". Unsure counts AGAINST (conservative).
  G3  is_blob incidence among G1's true-positive siblings; >50% => REPORT the
      flagger over-fires. Never tune it to pass G1/G2.
  K1  no operating point satisfies G1 AND G2 => NO-GO, "identity heals first".

READ-ONLY DISCIPLINE
--------------------
Every connection runs `SET default_transaction_read_only = on` before any query.
Zero writes. `backend/app/` is never modified by this script.

USAGE
-----
  set -a; . ~/AtlasLocalWorker/.env; set +a
  cd backend
  ./.venv/bin/python -m scripts.measure_sibling_finder_v2 --pull      # cache field
  ./.venv/bin/python -m scripts.measure_sibling_finder_v2 --families  # stage 1
  ./.venv/bin/python -m scripts.measure_sibling_finder_v2 --sweep     # stage 2
  ./.venv/bin/python -m scripts.measure_sibling_finder_v2 --g2-worksheet
  # -> hand-judge each row's `verdict` into sibling_v2_g2_judgments.json
  ./.venv/bin/python -m scripts.measure_sibling_finder_v2 --gates     # stage 3
  ./.venv/bin/python -m scripts.measure_sibling_finder_v2 --artifact  # repo JSON

Between --families and --sweep the harvested families must be HAND-VERIFIED
against their own evidence headlines (exclusions + the DEV/GATE split written
into sibling_v2_families.json). The verdicts for this run are recorded in
docs/research/recall-229/2026-07-29-sibling-finder-v2-measurement.md §1.
"""
from __future__ import annotations

import argparse
import asyncio
import json
import math
import os
import pickle
import random
import re
import sys
import unicodedata
from datetime import datetime, timezone
from collections import Counter, defaultdict
from dataclasses import dataclass, field as dc_field
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any, Iterable, Optional, Sequence

import numpy as np

try:
    from app.routers.dossier import _distinctive_df_max, _is_clean_actor
    from app.services.constellation_walk import (
        WalkParams,
        blob_connector_flags,
        build_knn_graph,
        norm_rarity,
        actor_edge_weight,
    )
    from app.services.story_siblings import DEFAULT_CAP, rank_siblings
    from app.services.whitening import apply_whitening, load_whitening
except ImportError:  # pragma: no cover
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from app.routers.dossier import _distinctive_df_max, _is_clean_actor
    from app.services.constellation_walk import (
        WalkParams, blob_connector_flags, build_knn_graph, norm_rarity, actor_edge_weight,
    )
    from app.services.story_siblings import DEFAULT_CAP, rank_siblings
    from app.services.whitening import apply_whitening, load_whitening

REPO_ROOT = Path(__file__).resolve().parents[2]
ARTIFACT_DIR = REPO_ROOT / "docs" / "research" / "recall-229"
ARTIFACT_STEM = "2026-07-29-sibling-finder-v2-measurement"
SCRATCH = Path(
    os.environ.get(
        "ATLAS_SIBLING_V2_SCRATCH",
        "/private/tmp/claude-501/-Users-pedro-Desktop-PEDRO-Cursos-ObservatorioGlobal/"
        "b09a9b6f-e30c-4679-936b-e9d46e3c40df/scratchpad",
    )
)
FIELD_CACHE = SCRATCH / "sibling_v2_field.pkl"
FAMILIES_JSON = SCRATCH / "sibling_v2_families.json"
SWEEP_JSON = SCRATCH / "sibling_v2_sweep.json"
G2_WORKSHEET = SCRATCH / "sibling_v2_g2_worksheet.json"
G2_JUDGMENTS = SCRATCH / "sibling_v2_g2_judgments.json"

# ---------------------------------------------------------------- FROZEN GATES
G1_TRUE_IN_TOP_K = 8          # "top-8 siblings"
G1_MIN_TRUE = 3               # ">=3 TRUE same-event fragments"
G2_ANCHORS = 10               # "10 random active anchors"
G2_TOP_K = 5                  # "top-5 siblings"
G2_MAX_FALSE = 2              # "<=2/50"
G3_BLOB_SHARE_TAU = 0.50      # ">50% => flagger over-fires"
G2_SEED = 20260729            # recorded RNG seed

# A family can only satisfy G1 if some anchor has >=G1_MIN_TRUE OTHER members.
FAMILY_MIN_SIZE_FOR_G1 = G1_MIN_TRUE + 1

# ------------------------------------------------- label rules (verbatim reuse)
# Identical to measure_evidence_fingerprint.py / measure_identity_whitening.py so
# the FALSE construction and the family-harvest rule are the SAME objects across
# harnesses (spec §2.5 "the same label-similarity rule the whitened-taus harness
# used").
SAME_LABEL_MIN = 0.80
DIFF_LABEL_MAX = 0.35
BLOCK_MIN_SHARED = 2
BLOCK_DF_MAX_SHARE = 0.05

_GENERIC_TOKENS = {
    "the", "and", "for", "with", "from", "over", "amid", "after", "before",
    "new", "news", "update", "updates", "report", "reports", "latest", "live",
    "crisis", "attack", "attacks", "talks", "case", "cases", "day", "days",
    "week", "year", "years", "man", "men", "woman", "women", "people",
    "government", "police", "court", "president", "minister", "official",
    "officials", "国", "des", "los", "las", "der", "die", "und", "para", "com",
}


def norm_label(s: str | None) -> str:
    if not s:
        return ""
    x = unicodedata.normalize("NFKC", s).lower()
    x = re.sub(r"[^\w\s]+", " ", x, flags=re.UNICODE)
    return re.sub(r"\s+", " ", x).strip()


def label_sim(a: str | None, b: str | None) -> float:
    na, nb = norm_label(a), norm_label(b)
    if not na or not nb:
        return 0.0
    if na == nb:
        return 1.0
    return SequenceMatcher(None, na, nb).ratio()


def subject_tokens(s: str | None) -> set[str]:
    toks = re.findall(r"[^\W\d_]{3,}", norm_label(s), re.UNICODE)
    return {t for t in toks if t not in _GENERIC_TOKENS}


def dominant_script(s: str | None) -> str:
    c: Counter = Counter()
    for ch in s or "":
        if not ch.isalpha():
            continue
        try:
            c[unicodedata.name(ch).split()[0].lower()] += 1
        except ValueError:
            continue
    return c.most_common(1)[0][0] if c else "none"


def different_story(la: str | None, lb: str | None) -> bool:
    """Mechanically 'not the same story' by LABEL alone — the whitened-taus
    harness's construction v1 rule, verbatim (same-script required)."""
    if not la or not lb:
        return False
    sa, sb = dominant_script(la), dominant_script(lb)
    if sa == "none" or sb == "none" or sa != sb:
        return False
    if label_sim(la, lb) >= DIFF_LABEL_MAX:
        return False
    return not (subject_tokens(la) & subject_tokens(lb))


def norm_entity(s: str | None) -> str:
    if not s:
        return ""
    x = unicodedata.normalize("NFKD", str(s))
    x = "".join(ch for ch in x if not unicodedata.combining(ch))
    x = re.sub(r"\s+", " ", x.lower()).strip()
    return x


class DSU:
    def __init__(self, n: int) -> None:
        self.p = list(range(n))

    def find(self, x: int) -> int:
        while self.p[x] != x:
            self.p[x] = self.p[self.p[x]]
            x = self.p[x]
        return x

    def union(self, a: int, b: int) -> None:
        ra, rb = self.find(a), self.find(b)
        if ra != rb:
            self.p[rb] = ra


# ------------------------------------------------------------------- DB pull
_TOPICS_SQL = """
    SELECT id, label, category, label_status, centroid_vec, first_seen, last_seen,
           agg_n_signals
    FROM dynamic_topics
    WHERE state = 'active' AND NOT is_umbrella AND centroid_vec IS NOT NULL
"""

# Member scoping is VERBATIM story.py `_COUNTRIES_SQL` (role/engine/quarantine/
# window) — the 2026-07-27 SNAPSHOT_UNLABELLED bug class was exactly this
# scoping done differently in two places.
_MEMBERS_SQL = """
    SELECT tm.topic_id,
           s.id AS signal_id,
           s.headline,
           s.country_code,
           s.source_name,
           s.source_lang,
           s.created_at,
           s.persons,
           s.nlp_persons
    FROM topic_members tm
    JOIN signals_v2 s ON s.id = tm.signal_id
    WHERE tm.topic_id = ANY($1::text[])
      AND tm.role = 'evidence'
      AND tm.engine_version = 'v1-compat'
      AND tm.quarantined IS NOT TRUE
      AND tm.assigned_at > NOW() - INTERVAL '7 days'
"""


async def pull_field() -> dict:
    import asyncpg

    dsn = os.environ.get("DATABASE_URL")
    if not dsn:
        raise SystemExit("DATABASE_URL not set (set -a; . ~/AtlasLocalWorker/.env; set +a)")
    conn = await asyncpg.connect(dsn, statement_cache_size=0)
    try:
        # READ-ONLY discipline: enforced on the connection before any query.
        await conn.execute("SET default_transaction_read_only = on")
        await conn.execute("SET statement_timeout = 240000")
        trows = await conn.fetch(_TOPICS_SQL)
        keys = [f"dynamic-topic-{int(r['id'])}" for r in trows]
        mrows = await conn.fetch(_MEMBERS_SQL, keys)
    finally:
        await conn.close()

    topics = []
    for r in trows:
        v = r["centroid_vec"]
        if v is None or len(v) != 768:
            continue
        tid = int(r["id"])
        topics.append(
            {
                "key": f"dynamic-topic-{tid}",
                "id": tid,
                "label": r["label"] or f"dynamic-topic-{tid}",
                "category": r["category"],
                "label_status": r["label_status"],
                "first_seen": r["first_seen"].isoformat() if r["first_seen"] else None,
                "last_seen": r["last_seen"].isoformat() if r["last_seen"] else None,
                "agg_n_signals": int(r["agg_n_signals"] or 0),
                "vec": [float(x) for x in v],
            }
        )
    members = []
    for r in mrows:
        npx = r["nlp_persons"]
        if isinstance(npx, str):
            try:
                npx = json.loads(npx)
            except Exception:  # noqa: BLE001
                npx = None
        members.append(
            {
                "topic_id": r["topic_id"],
                "signal_id": int(r["signal_id"]),
                "headline": r["headline"] or "",
                "cc": (r["country_code"] or "").strip().upper() or None,
                "source": r["source_name"],
                "lang": (r["source_lang"] or "").strip().lower() or None,
                "ts": r["created_at"].isoformat() if r["created_at"] else None,
                "persons": list(r["persons"] or []),
                "nlp_persons": [
                    (x or {}).get("name")
                    for x in (npx or [])
                    if isinstance(x, dict)
                ],
            }
        )
    return {"topics": topics, "members": members}


# --------------------------------------------------------------- field object
@dataclass
class Field:
    keys: list[str]
    labels: list[str]
    cats: list[Optional[str]]
    statuses: list[Optional[str]]
    first_seen: list[Optional[str]]
    n_signals: list[int]
    whitened: np.ndarray
    graph: Any
    blobs: set[int]
    params: WalkParams
    idx: dict[str, int]
    ents: list[set[str]]                 # per-topic cleaned entity set
    ent_df: dict[str, int]               # entity -> #topics containing it
    ent_inv: dict[str, list[int]]        # entity -> topic indices (df>=2 only)
    df_max: int
    cc_hist: list[dict[str, int]]        # country -> member count
    day_hist: list[dict[str, int]]       # YYYY-MM-DD -> member count
    headlines: list[list[str]]           # sample headlines for hand verification
    outlets: list[list[str]]
    n_members: list[int]


def build_field(raw: dict) -> Field:
    topics = raw["topics"]
    keys = [t["key"] for t in topics]
    labels = [t["label"] for t in topics]
    cats = [t["category"] for t in topics]
    statuses = [t["label_status"] for t in topics]
    first_seen = [t["first_seen"] for t in topics]
    n_signals = [t["agg_n_signals"] for t in topics]
    idx = {k: i for i, k in enumerate(keys)}
    n = len(keys)

    vecs = np.asarray([t["vec"] for t in topics], dtype=np.float32)
    whitening = load_whitening()
    whitened = apply_whitening(vecs, whitening)
    params = WalkParams()  # LOCKED defaults, NOT from_env — frozen for the gate
    graph = build_knn_graph(whitened, k=params.k)
    blobs = blob_connector_flags(graph, cats, params)

    ents: list[set[str]] = [set() for _ in range(n)]
    cc_hist: list[dict[str, int]] = [defaultdict(int) for _ in range(n)]
    day_hist: list[dict[str, int]] = [defaultdict(int) for _ in range(n)]
    headlines: list[list[str]] = [[] for _ in range(n)]
    outlets: list[list[str]] = [[] for _ in range(n)]
    n_members = [0] * n
    clean_cache: dict[str, bool] = {}

    def ok(name: str) -> bool:
        v = clean_cache.get(name)
        if v is None:
            try:
                v = _is_clean_actor(name)
            except Exception:  # noqa: BLE001
                v = False
            clean_cache[name] = v
        return v

    for m in raw["members"]:
        i = idx.get(m["topic_id"])
        if i is None:
            continue
        n_members[i] += 1
        if m["cc"]:
            cc_hist[i][m["cc"]] += 1
        if m["ts"]:
            day_hist[i][m["ts"][:10]] += 1
        h = (m["headline"] or "").strip()
        if h and len(headlines[i]) < 8:
            headlines[i].append(h)
            outlets[i].append(m["source"] or "?")
        # Lane E vocabulary: GDELT persons[] ∪ nlp_persons[].name.
        # organizations[] is DELIBERATELY EXCLUDED — measured 80.7% garbage at
        # df=1 (docs/research/recall-229/2026-07-30-evidence-rarity-calibration.md).
        for p in list(m["persons"]) + list(m["nlp_persons"]):
            e = norm_entity(p)
            if len(e) < 3:
                continue
            if not ok(e):
                continue
            ents[i].add(e)

    ent_df: Counter = Counter()
    for s in ents:
        for e in s:
            ent_df[e] += 1
    df_max = max(ent_df.values()) if ent_df else 1
    ent_inv: dict[str, list[int]] = defaultdict(list)
    for i, s in enumerate(ents):
        for e in s:
            if ent_df[e] >= 2:
                ent_inv[e].append(i)

    return Field(
        keys=keys, labels=labels, cats=cats, statuses=statuses,
        first_seen=first_seen, n_signals=n_signals, whitened=whitened,
        graph=graph, blobs=blobs, params=params, idx=idx, ents=ents,
        ent_df=dict(ent_df), ent_inv=dict(ent_inv), df_max=df_max,
        cc_hist=[dict(d) for d in cc_hist], day_hist=[dict(d) for d in day_hist],
        headlines=headlines, outlets=outlets, n_members=n_members,
    )


def cc_set(f: Field, i: int, min_share: float = 0.10, top: int = 3) -> set[str]:
    """A topic's country footprint: top-`top` countries holding >= `min_share`
    of its evidence. Mirrors story.py's `_countries` (top-3 by volume) with a
    share floor so a single stray signal never puts a country in the set."""
    h = f.cc_hist[i]
    tot = sum(h.values())
    if not tot:
        return set()
    ranked = sorted(h.items(), key=lambda kv: -kv[1])[:top]
    return {cc for cc, c in ranked if c / tot >= min_share}


def primary_cc(f: Field, i: int) -> Optional[str]:
    h = f.cc_hist[i]
    if not h:
        return None
    return max(h.items(), key=lambda kv: kv[1])[0]


def day_profile(f: Field, i: int) -> dict[str, float]:
    h = f.day_hist[i]
    tot = sum(h.values())
    if not tot:
        return {}
    return {d: c / tot for d, c in h.items()}


def peak_day(f: Field, i: int) -> Optional[str]:
    h = f.day_hist[i]
    if not h:
        return None
    return max(h.items(), key=lambda kv: (kv[1], kv[0]))[0]


def _daydiff(a: Optional[str], b: Optional[str]) -> Optional[int]:
    if not a or not b:
        return None
    import datetime as _dt

    da = _dt.date.fromisoformat(a)
    db = _dt.date.fromisoformat(b)
    return abs((da - db).days)


# ----------------------------------------------------------------- the lanes
@dataclass
class Cand:
    idx: int
    lane_c: float = 0.0
    lane_e: float = 0.0
    lane_g: float = 0.0
    receipts: dict = dc_field(default_factory=dict)


def lane_c_scores(f: Field, seed: int, cap: int = 200) -> dict[int, tuple[float, dict]]:
    """LANE C — the SHIPPED v1 walk, byte-for-byte (`rank_siblings`, WalkParams
    defaults k=6/rel_floor 0.35/hop_cap 3, dedup_tau 0.85). Score = the walk's
    accumulated weight, exactly the value v1 ranks on."""
    sibs = rank_siblings(
        seed, f.whitened, f.keys, f.labels, f.cats, f.params, cap=cap,
        graph=f.graph, blob_flags=f.blobs,
    )
    out: dict[int, tuple[float, dict]] = {}
    for s in sibs:
        j = f.idx.get(s.topic_key)
        if j is None:
            continue
        out[j] = (
            float(s.weight),
            {
                "basis": "whitened_cos",
                "value": f"{s.weight:.3f}",
                "kinship": s.kinship,
                "degree": s.degree,
                "via": s.via_parent_label,
            },
        )
    return out


def lane_c_nodedup(f: Field, seed: int) -> dict[int, tuple[float, dict]]:
    """Lane C candidates WITHOUT the same-event display fold.

    On a shredded field the 0.85 dedup suppresses exactly the fragments the lens
    exists to surface, so the union's candidate generation must not lose them.
    `rank_siblings` with a cap far above the reached-set size returns every
    representative; the folded members are recovered here from the same walk."""
    from app.services.constellation_walk import max_product_walk

    reached = max_product_walk([seed], f.graph, f.params, blob_flags=f.blobs)
    out: dict[int, tuple[float, dict]] = {}
    for j, node in reached.items():
        if j == seed:
            continue
        out[j] = (
            float(node.acc_weight),
            {
                "basis": "whitened_cos",
                "value": f"{node.acc_weight:.3f}",
                "kinship": node.kinship,
                "degree": int(node.degree),
                "via": f.labels[node.via_parent]
                if node.via_parent is not None and node.via_parent != seed else None,
            },
        )
    return out


def lane_e_scores(f: Field, seed: int, df_gate: int) -> dict[int, tuple[float, dict]]:
    """LANE E — rare shared entity.

    Candidates share >=1 entity whose field-wide document-frequency (documents =
    ACTIVE TOPICS) is <= `df_gate`. Score = `actor_edge_weight` from
    constellation_walk (LOCKED `0.30 + 0.68·norm_rarity`, taken over the RAREST
    shared entity) — reused verbatim, not re-derived.

    `df_gate` default is the `_distinctive_df_max` discipline over the display
    set (dossier.py): min(3, ceil(0.4·n)) = 3 for a field this size.
    """
    mine = f.ents[seed]
    hits: dict[int, list[str]] = defaultdict(list)
    for e in mine:
        d = f.ent_df.get(e, 0)
        if d < 2 or d > df_gate:
            continue
        for j in f.ent_inv.get(e, ()):
            if j != seed:
                hits[j].append(e)
    out: dict[int, tuple[float, dict]] = {}
    for j, shared in hits.items():
        dfs = [f.ent_df[e] for e in shared]
        w = actor_edge_weight(dfs, f.df_max)
        rarest = min(zip(dfs, shared))[1]
        out[j] = (
            float(w),
            {
                "basis": "shared_rare_actor",
                "value": f"{rarest} (df {f.ent_df[rarest]}) +{len(shared) - 1} more"
                if len(shared) > 1 else f"{rarest} (df {f.ent_df[rarest]})",
                "n_shared": len(shared),
                "shared": sorted(shared)[:6],
            },
        )
    return out


def lane_g_scores(f: Field, seed: int, max_day_gap: int = 2,
                  min_score: float = 0.0) -> dict[int, tuple[float, dict]]:
    """LANE G — country + time proximity.

    Membership rule: the anchor's PRIMARY country is inside the candidate's
    country footprint (`cc_set`, top-3 with a 10% share floor) — a superset of
    "same primary country", chosen for recall and recorded as such.
    Time rule: |peak_day(a) - peak_day(b)| <= `max_day_gap` days (the "+/-48h"
    of the pre-registration, read on the activity peak rather than `first_seen`
    — MEASURED reason: 1007 of 1022 active topics carry the SAME `last_seen`
    (tonight's snapshot) and a long-lived anchor's `first_seen` predates its own
    fresh fragments by weeks, so `first_seen`/`last_seen` cannot express "these
    were active together". The daily evidence histogram can.)
    Score = country Jaccard x day-histogram overlap, both in [0,1].
    """
    a_cc = cc_set(f, seed)
    a_prim = primary_cc(f, seed)
    a_days = day_profile(f, seed)
    a_peak = peak_day(f, seed)
    if not a_prim or not a_days:
        return {}
    out: dict[int, tuple[float, dict]] = {}
    for j in range(len(f.keys)):
        if j == seed:
            continue
        b_cc = cc_set(f, j)
        if a_prim not in b_cc:
            continue
        gap = _daydiff(a_peak, peak_day(f, j))
        if gap is None or gap > max_day_gap:
            continue
        union = a_cc | b_cc
        if not union:
            continue
        jac = len(a_cc & b_cc) / len(union)
        b_days = day_profile(f, j)
        overlap = sum(min(a_days.get(d, 0.0), b_days.get(d, 0.0))
                      for d in set(a_days) | set(b_days))
        s = jac * overlap
        if s < min_score:
            continue
        out[j] = (
            float(s),
            {
                "basis": "country_time",
                "value": f"{a_prim} · peak Δ{gap}d · cc-jaccard {jac:.2f} · "
                         f"time-overlap {overlap:.2f}",
                "gap_days": gap,
                "jaccard": round(jac, 4),
                "time_overlap": round(overlap, 4),
            },
        )
    return out


# ------------------------------------------------------------- union scoring
@dataclass(frozen=True)
class OpPoint:
    form: str                 # 'max' | 'sum' | 'rrf'
    w_c: float
    w_e: float
    w_g: float
    df_gate: int
    g_max_day_gap: int
    g_min_score: float
    c_dedup: bool
    rrf_k: int = 60

    def label(self) -> str:
        return (f"{self.form}|wC{self.w_c}|wE{self.w_e}|wG{self.w_g}|"
                f"dfE<={self.df_gate}|Ggap{self.g_max_day_gap}|Gmin{self.g_min_score}|"
                f"dedup{int(self.c_dedup)}")


def union_rank(f: Field, seed: int, op: OpPoint, k: int) -> list[dict]:
    """Rank the anchor's neighborhood under one operating point. Returns the
    top-k rows, each carrying every lane's receipt that fired."""
    lc = (lane_c_scores(f, seed) if op.c_dedup else lane_c_nodedup(f, seed))
    le = lane_e_scores(f, seed, op.df_gate) if op.w_e > 0 else {}
    lg = (lane_g_scores(f, seed, op.g_max_day_gap, op.g_min_score)
          if op.w_g > 0 else {})

    cands = set(lc) | set(le) | set(lg)
    if not cands:
        return []

    def ranks(d: dict[int, tuple[float, dict]]) -> dict[int, int]:
        # Explicit key tie-break. Without it the ordering of tied scores falls
        # back to dict insertion order, which for lane E derives from set
        # iteration over interned strings and is therefore PYTHONHASHSEED-
        # dependent — and lane E is nearly ALL ties (every df=2 shared actor
        # scores exactly 0.637), so RRF, which consumes ranks, would not
        # reproduce run to run. Caught by an unreproducible mech_false_rate.
        order = sorted(d, key=lambda j: (-d[j][0], f.keys[j]))
        return {j: r + 1 for r, j in enumerate(order)}

    rc, re_, rg = ranks(lc), ranks(le), ranks(lg)

    rows = []
    for j in cands:
        c = lc.get(j, (0.0, None))[0]
        e = le.get(j, (0.0, None))[0]
        g = lg.get(j, (0.0, None))[0]
        if op.form == "max":
            s = max(op.w_c * c, op.w_e * e, op.w_g * g)
        elif op.form == "sum":
            s = op.w_c * c + op.w_e * e + op.w_g * g
        elif op.form == "rrf":
            s = 0.0
            if j in rc:
                s += op.w_c / (op.rrf_k + rc[j])
            if j in re_:
                s += op.w_e / (op.rrf_k + re_[j])
            if j in rg:
                s += op.w_g / (op.rrf_k + rg[j])
        else:
            raise ValueError(f"unknown form {op.form}")
        receipts = [d[1] for d in (lc.get(j), le.get(j), lg.get(j)) if d and d[1]]
        rows.append(
            {
                "idx": j, "key": f.keys[j], "label": f.labels[j], "score": float(s),
                "lane_c": c, "lane_e": e, "lane_g": g,
                "is_blob": j in f.blobs, "receipts": receipts,
            }
        )
    rows.sort(key=lambda r: (-r["score"], r["key"]))
    return rows[:k]


def v1_rank(f: Field, seed: int, k: int) -> list[dict]:
    """The SHIPPED v1 baseline exactly as story.py serves it (cap DEFAULT_CAP,
    dedup on), truncated to the gate's top-k."""
    sibs = rank_siblings(
        seed, f.whitened, f.keys, f.labels, f.cats, f.params, cap=DEFAULT_CAP,
        graph=f.graph, blob_flags=f.blobs,
    )
    out = []
    for s in sibs[:k]:
        j = f.idx.get(s.topic_key)
        out.append(
            {
                "idx": j, "key": s.topic_key, "label": s.label,
                "score": float(s.weight), "lane_c": float(s.weight),
                "lane_e": 0.0, "lane_g": 0.0, "is_blob": bool(s.is_blob),
                "receipts": [dict(r) for r in s.reasons],
            }
        )
    return out


# ------------------------------------------------------------------ families
def family_by_pattern(f: Field, patterns: Sequence[Sequence[str]],
                      name: str) -> Optional[dict]:
    """A named witness family = the ACTIVE topics matching ANY of `patterns`,
    where a pattern is an AND over label tokens — spec §2.5's
    `find_pattern_family`, lifted from `emergent_clusters` onto `dynamic_topics`
    because the sibling finder's universe IS the active topic field, not one
    night's cluster snapshot.

    The OR over AND-patterns is the one extension to §2.5, and it exists for a
    MEASURED reason recorded before scoring: the Berlin Pride event carries TWO
    label vocabularies in the same field — the English "Pride" and the German
    "CSD" (Christopher Street Day, the same parade) — plus a vocabulary-free
    "Berlin Car Attack". A single AND-pattern files one event as two, which is
    the very failure under test. Every added member is hand-verified against its
    own receipts (see the artifact); an OR *within* one pattern is still
    forbidden (it is what would sweep in unrelated events)."""
    hit: list[int] = []
    matched: dict[int, str] = {}
    for toks in patterns:
        low = [t.lower() for t in toks]
        for i, lab in enumerate(f.labels):
            if i in matched:
                continue
            if all(t in (lab or "").lower() for t in low):
                hit.append(i)
                matched[i] = " AND ".join(toks)
    if not hit:
        return None
    hit.sort(key=lambda i: -f.n_signals[i])
    return {
        "name": name, "kind": "core",
        "pattern": " OR ".join("(" + " AND ".join(t) + ")" for t in patterns),
        "members": [f.keys[i] for i in hit],
        "member_idx": hit,
    }


def harvest_fresh_families(f: Field, exclude: set[int], min_size: int,
                           want: int) -> list[dict]:
    """Same-event families by the label-similarity rule the whitened-taus
    harness used: blocked candidate generation (>=2 shared distinctive tokens),
    SequenceMatcher >= SAME_LABEL_MIN, plus a SHARED COUNTRY (construction v1's
    D3). Connected components of that label graph ARE the families."""
    items = [i for i in range(len(f.keys)) if f.labels[i] and i not in exclude]
    tok_map = {i: subject_tokens(f.labels[i]) for i in items}
    df: Counter = Counter()
    for i in items:
        for t in tok_map[i]:
            df[t] += 1
    cap = max(2, int(BLOCK_DF_MAX_SHARE * len(items)))
    inv: dict[str, list[int]] = defaultdict(list)
    for i in items:
        for t in tok_map[i]:
            if df[t] <= cap:
                inv[t].append(i)
    pairs: Counter = Counter()
    for t, lst in inv.items():
        if len(lst) > 200:
            continue
        for a in range(len(lst)):
            for b in range(a + 1, len(lst)):
                pairs[(lst[a], lst[b])] += 1
    pos = {i: k for k, i in enumerate(items)}
    d = DSU(len(items))
    edges = 0
    for (i, j), shared in pairs.items():
        if shared < BLOCK_MIN_SHARED:
            continue
        if not (cc_set(f, i) & cc_set(f, j)):
            continue
        if label_sim(f.labels[i], f.labels[j]) < SAME_LABEL_MIN:
            continue
        d.union(pos[i], pos[j])
        edges += 1
    groups: dict[int, list[int]] = defaultdict(list)
    for i in items:
        groups[d.find(pos[i])].append(i)
    fams = [g for g in groups.values() if len(g) >= min_size]
    fams.sort(key=lambda g: (-len(g), min(g)))
    out = []
    used: set[str] = set()
    for g in fams[:want]:
        g = sorted(g, key=lambda i: -f.n_signals[i])
        base = f"fresh:{norm_label(f.labels[g[0]])[:38].replace(' ', '-')}"
        nm, kk = base, 2
        while nm in used:
            nm = f"{base}#{kk}"
            kk += 1
        used.add(nm)
        out.append({"name": nm, "kind": "fresh",
                    "members": [f.keys[i] for i in g], "member_idx": g})
    return out


def family_evidence(f: Field, fam: dict, n_head: int = 3) -> dict:
    """Hand-verification dump: label + first `n_head` member headlines per
    member, so every family membership claim in the artifact is checkable."""
    ev = []
    for i in fam["member_idx"]:
        ev.append(
            {
                "key": f.keys[i], "label": f.labels[i],
                "n_signals": f.n_signals[i], "n_members": f.n_members[i],
                "label_status": f.statuses[i], "category": f.cats[i],
                "first_seen": (f.first_seen[i] or "")[:10],
                "countries": sorted(cc_set(f, i)),
                "peak_day": peak_day(f, i),
                "is_blob": i in f.blobs,
                "headlines": [
                    f"{h[:150]}  [{o}]"
                    for h, o in zip(f.headlines[i][:n_head], f.outlets[i][:n_head])
                ],
            }
        )
    return {**{k: v for k, v in fam.items() if k != "member_idx"}, "evidence": ev}


# ------------------------------------------------------- mechanical false side
def mechanical_false_rate(f: Field, op: Optional[OpPoint], anchors: Sequence[int],
                          k: int) -> dict:
    """Scalable FALSE-side proxy used ONLY for operating-point selection (never
    as the G2 gate): the share of returned rows that are mechanically
    'not the same story' by LABEL alone (`different_story`, the whitened-taus
    construction v1 rule) — same-script, label-sim < 0.35, zero shared
    distinctive tokens. It UNDER-counts (cross-script and same-country false
    pairs slip through), which is why the frozen G2 gate is hand-judged."""
    tot = 0
    bad = 0
    for a in anchors:
        rows = (v1_rank(f, a, k) if op is None else union_rank(f, a, op, k))
        for r in rows:
            tot += 1
            if different_story(f.labels[a], r["label"]):
                bad += 1
    return {"rows": tot, "mechanically_different": bad,
            "rate": round(bad / tot, 4) if tot else None}


def family_recall(f: Field, fam: dict, op: Optional[OpPoint], k: int) -> dict:
    """Best-anchor recall for one family: for every member used as the anchor,
    how many OTHER members land in the top-k."""
    idxs = fam["member_idx"]
    best = {"anchor": None, "true_in_topk": -1, "rows": []}
    per_anchor = []
    for a in idxs:
        rows = (v1_rank(f, a, k) if op is None else union_rank(f, a, op, k))
        got = [r for r in rows if r["idx"] in set(idxs) and r["idx"] != a]
        per_anchor.append({"anchor": f.keys[a], "true_in_topk": len(got),
                           "true": [r["key"] for r in got]})
        if len(got) > best["true_in_topk"]:
            best = {"anchor": f.keys[a], "anchor_label": f.labels[a],
                    "true_in_topk": len(got), "rows": rows,
                    "true": [{"key": r["key"], "label": r["label"],
                              "rank": rows.index(r) + 1, "score": round(r["score"], 4),
                              "is_blob": r["is_blob"],
                              "receipts": r["receipts"]} for r in got]}
    return {"family": fam["name"], "size": len(idxs),
            "best": best, "per_anchor": per_anchor}


# --------------------------------------------------------------------- stages
def load_field() -> Field:
    if not FIELD_CACHE.exists():
        raise SystemExit(f"no field cache at {FIELD_CACHE} — run --pull first")
    with FIELD_CACHE.open("rb") as fh:
        return build_field(pickle.load(fh))


def stage_pull() -> None:
    SCRATCH.mkdir(parents=True, exist_ok=True)
    raw = asyncio.run(pull_field())
    with FIELD_CACHE.open("wb") as fh:
        pickle.dump(raw, fh)
    print(f"pulled {len(raw['topics'])} topics / {len(raw['members'])} member rows "
          f"-> {FIELD_CACHE}")


def stage_families(args) -> None:
    f = load_field()
    core_specs = [
        ([("berlin", "pride"), ("csd", "berlin"), ("berlin", "car attack")],
         "berlin-pride"),
        ([("iran", "ukrain"), ("caspian",)], "caspian"),
    ]
    fams = []
    used: set[int] = set()
    for tokens, name in core_specs:
        fam = family_by_pattern(f, tokens, name)
        if fam:
            fams.append(fam)
            used |= set(fam["member_idx"])
    fresh = harvest_fresh_families(f, exclude=used, min_size=4, want=args.fresh)
    fams.extend(fresh)
    out = {
        "field": {"n_topics": len(f.keys), "n_member_rows": sum(f.n_members),
                  "entity_vocab": len(f.ent_df), "entity_df_max": f.df_max,
                  "shared_entities_df_ge2": len(f.ent_inv),
                  "blob_flagged": len(f.blobs)},
        "families": [family_evidence(f, fam) for fam in fams],
    }
    FAMILIES_JSON.write_text(json.dumps(out, indent=2, ensure_ascii=False))
    print(json.dumps({"families": [(x["name"], len(x["evidence"]))
                                   for x in out["families"]]}, indent=2))
    print(f"-> {FAMILIES_JSON}")


def _families_from_disk(f: Field, keep: dict[str, list[str]]) -> list[dict]:
    """Rebuild family objects from the (possibly hand-curated) families JSON."""
    out = []
    for name, members in keep.items():
        idxs = [f.idx[k] for k in members if k in f.idx]
        out.append({"name": name, "members": [f.keys[i] for i in idxs],
                    "member_idx": idxs})
    return out


def grid() -> list[OpPoint]:
    """The sweep grid. Frozen before any gate is scored.

    `df_gate` 10 is a deliberately RELAXED rung beyond the `_distinctive_df_max`
    rarity discipline (=3 at this field size): the lane-E reachability
    diagnostic showed only 12/140 true family pairs share a df<=3 entity, so the
    relaxed rung is measured — with its own false-side number in the same pass —
    rather than left as an untested "we could have widened it".

    Pure-lane reference points (C alone, dedup on and off) are in the grid so
    the selection rule is applied over a COMPLETE set that includes the trivial
    ops: if simply removing the display fold were the whole win, the rule must
    be able to choose it.
    """
    ops: list[OpPoint] = [
        OpPoint("max", 1.0, 0.0, 0.0, 3, 2, 0.0, False),
        OpPoint("max", 1.0, 0.0, 0.0, 3, 2, 0.0, True),
    ]
    for dedup in (False, True):
        for df_gate in (2, 3, 5, 10):
            for form, weights in (
                ("max", [(1.0, 1.0, 1.0), (1.0, 1.4, 1.0), (1.0, 1.4, 1.4),
                         (1.0, 1.2, 0.0), (1.0, 0.0, 1.2)]),
                ("sum", [(1.0, 1.0, 1.0), (0.6, 1.0, 0.6), (1.0, 1.0, 0.0)]),
                ("rrf", [(1.0, 1.0, 1.0), (1.0, 1.5, 0.5), (1.0, 2.0, 1.0)]),
            ):
                for w_c, w_e, w_g in weights:
                    for gmin in (0.0, 0.15):
                        ops.append(OpPoint(form=form, w_c=w_c, w_e=w_e, w_g=w_g,
                                           df_gate=df_gate, g_max_day_gap=2,
                                           g_min_score=gmin, c_dedup=dedup))
    # de-dup identical points (w_g=0 makes g_min irrelevant)
    seen: set[str] = set()
    uniq = []
    for o in ops:
        lb = o.label() if o.w_g > 0 else o.label().replace(
            f"Gmin{o.g_min_score}", "Gmin-")
        if lb in seen:
            continue
        seen.add(lb)
        uniq.append(o)
    return uniq


def stage_sweep(args) -> None:
    f = load_field()
    fam_doc = json.loads(FAMILIES_JSON.read_text())
    keep = {x["name"]: [e["key"] for e in x["evidence"] if e.get("verified", True)]
            for x in fam_doc["families"]}
    fams = _families_from_disk(f, keep)
    by_name = {x["name"]: x for x in fams}

    dev_names = list(fam_doc.get("dev_families", []))
    gate_names = list(fam_doc.get("gate_families", []))
    if not dev_names or not gate_names:
        raise SystemExit("families JSON must declare dev_families and gate_families "
                         "BEFORE the sweep (selection/gate split, recorded)")

    rng = random.Random(G2_SEED)
    sel_anchors = rng.sample(range(len(f.keys)), 60)   # selection-only false probe

    rows = []
    base_dev = [family_recall(f, by_name[n], None, G1_TRUE_IN_TOP_K) for n in dev_names]
    base_false = mechanical_false_rate(f, None, sel_anchors, G2_TOP_K)
    for op in grid():
        dev = [family_recall(f, by_name[n], op, G1_TRUE_IN_TOP_K) for n in dev_names]
        fr = mechanical_false_rate(f, op, sel_anchors, G2_TOP_K)
        dev_hits = sum(1 for d in dev if d["best"]["true_in_topk"] >= G1_MIN_TRUE)
        rows.append(
            {
                "op": op.label(), "op_json": op.__dict__,
                "dev_families_passing": dev_hits,
                "dev_true_total": sum(d["best"]["true_in_topk"] for d in dev),
                "dev_detail": {d["family"]: d["best"]["true_in_topk"] for d in dev},
                "mech_false_rate": fr["rate"], "mech_false_rows": fr["rows"],
            }
        )
    out = {
        "baseline_v1": {
            "dev_families_passing": sum(
                1 for d in base_dev if d["best"]["true_in_topk"] >= G1_MIN_TRUE),
            "dev_detail": {d["family"]: d["best"]["true_in_topk"] for d in base_dev},
            "mech_false_rate": base_false["rate"],
        },
        "selection_rule": (
            "LEXICOGRAPHIC over DEV-only statistics: (1) max dev_families_passing; "
            "(2) max dev_true_total; (3) min mech_false_rate; (4) simplest op — "
            "fewest active lanes, then form order max < sum < rrf, then dedup as "
            "SHIPPED (True) before the changed behaviour (False). "
            "RECORDED CORRECTION: an absolute constraint mech_false_rate <= "
            f"{G2_MAX_FALSE / (G2_ANCHORS * G2_TOP_K):.3f} was written into this "
            "harness before the first run and is DISCARDED as unsatisfiable — the "
            "v1 baseline itself measures 0.62 on this proxy, i.e. the proxy's "
            "scale is not the hand-judged gate's scale, so the number could never "
            "have been a threshold on it. The proxy is kept as a RELATIVE "
            "false-side comparator (v1 vs each op) only. No frozen GATE moved. "
            "DEV families and the 60-anchor mechanical false probe are the ONLY "
            "inputs; no gate-family or G2 number produced by any union operating "
            "point was seen before this rule was applied."
        ),
        "sweep": rows,
    }
    _FORM_ORDER = {"max": 0, "sum": 1, "rrf": 2}

    def _key(r):
        o = r["op_json"]
        lanes = sum(1 for w in (o["w_c"], o["w_e"], o["w_g"]) if w > 0)
        return (-r["dev_families_passing"], -r["dev_true_total"],
                r["mech_false_rate"], lanes, _FORM_ORDER[o["form"]],
                0 if o["c_dedup"] else 1)

    ranked = sorted(rows, key=_key)
    chosen = ranked[0]["op_json"]
    out["chosen_op"] = chosen
    out["chosen_op_label"] = ranked[0]["op"]
    out["chosen_op_dev"] = {k: ranked[0][k] for k in
                            ("dev_families_passing", "dev_true_total",
                             "dev_detail", "mech_false_rate")}
    SWEEP_JSON.write_text(json.dumps(out, indent=2, ensure_ascii=False))
    print(json.dumps({"baseline_v1": out["baseline_v1"],
                      "n_ops": len(rows),
                      "chosen": ranked[0]["op"],
                      "chosen_dev": out["chosen_op_dev"],
                      "top6": [{k: r[k] for k in
                                ("op", "dev_families_passing", "dev_true_total",
                                 "mech_false_rate")} for r in ranked[:6]]},
                     indent=2))
    print(f"-> {SWEEP_JSON}")


def _chosen_op() -> OpPoint:
    doc = json.loads(SWEEP_JSON.read_text())
    if "chosen_op" not in doc:
        raise SystemExit("sweep JSON has no 'chosen_op' — freeze it before gating")
    return OpPoint(**doc["chosen_op"])


def stage_g2_worksheet(args) -> None:
    f = load_field()
    op = _chosen_op()
    rng = random.Random(G2_SEED)
    anchors = rng.sample(range(len(f.keys)), G2_ANCHORS)
    sheet = []
    for a in anchors:
        rows = union_rank(f, a, op, G2_TOP_K)
        sheet.append(
            {
                "anchor": f.keys[a], "anchor_label": f.labels[a],
                "anchor_countries": sorted(cc_set(f, a)),
                "anchor_headlines": f.headlines[a][:3],
                "siblings": [
                    {
                        "rank": n + 1, "key": r["key"], "label": r["label"],
                        "score": round(r["score"], 4),
                        "lane_c": round(r["lane_c"], 4),
                        "lane_e": round(r["lane_e"], 4),
                        "lane_g": round(r["lane_g"], 4),
                        "is_blob": r["is_blob"],
                        "receipts": r["receipts"],
                        "countries": sorted(cc_set(f, r["idx"])),
                        "headlines": f.headlines[r["idx"]][:3],
                        "verdict": None,   # 'related' | 'unrelated' | 'unsure'
                    }
                    for n, r in enumerate(rows)
                ],
            }
        )
    G2_WORKSHEET.write_text(json.dumps(
        {"seed": G2_SEED, "op": op.__dict__, "anchors": sheet},
        indent=2, ensure_ascii=False))
    print(f"{len(sheet)} anchors, "
          f"{sum(len(a['siblings']) for a in sheet)} rows -> {G2_WORKSHEET}")


def stage_gates(args) -> None:
    f = load_field()
    op = _chosen_op()
    fam_doc = json.loads(FAMILIES_JSON.read_text())
    keep = {x["name"]: [e["key"] for e in x["evidence"] if e.get("verified", True)]
            for x in fam_doc["families"]}
    fams = _families_from_disk(f, keep)
    by_name = {x["name"]: x for x in fams}
    gate_names = list(fam_doc["gate_families"])

    # ---- G1
    g1 = []
    for n in gate_names:
        fam = by_name[n]
        eligible = len(fam["member_idx"]) >= FAMILY_MIN_SIZE_FOR_G1
        v2 = family_recall(f, fam, op, G1_TRUE_IN_TOP_K)
        v1 = family_recall(f, fam, None, G1_TRUE_IN_TOP_K)
        g1.append(
            {
                "family": n, "size": len(fam["member_idx"]),
                "g1_eligible": eligible,
                "v2_best_anchor": v2["best"]["anchor"],
                "v2_best_anchor_label": v2["best"].get("anchor_label"),
                "v2_true_in_top8": v2["best"]["true_in_topk"],
                "v2_true": v2["best"].get("true", []),
                "v1_best_anchor": v1["best"]["anchor"],
                "v1_true_in_top8": v1["best"]["true_in_topk"],
                "v1_true": [t["key"] for t in v1["best"].get("true", [])],
                "passes": eligible and v2["best"]["true_in_topk"] >= G1_MIN_TRUE,
                "v2_per_anchor": v2["per_anchor"],
                "v2_top8_rows": [
                    {"rank": i + 1, "key": r["key"], "label": r["label"],
                     "score": round(r["score"], 4), "is_blob": r["is_blob"],
                     "lane_c": round(r["lane_c"], 4), "lane_e": round(r["lane_e"], 4),
                     "lane_g": round(r["lane_g"], 4)}
                    for i, r in enumerate(v2["best"].get("rows", []))
                ],
            }
        )
    eligible_fams = [x for x in g1 if x["g1_eligible"]]
    g1_pass = bool(eligible_fams) and all(x["passes"] for x in eligible_fams)

    # ---- G2 (hand-judged)
    g2: dict = {"status": "pending_judgments"}
    if G2_JUDGMENTS.exists():
        jd = json.loads(G2_JUDGMENTS.read_text())
        verdicts = []
        for a in jd["anchors"]:
            for s in a["siblings"]:
                verdicts.append((a["anchor"], s["key"], s.get("verdict")))
        n = len(verdicts)
        false_ct = sum(1 for _, _, v in verdicts if v in ("unrelated", "unsure", None))
        g2 = {
            "status": "judged", "rows": n, "false": false_ct,
            "max_allowed": G2_MAX_FALSE, "passes": false_ct <= G2_MAX_FALSE,
            "breakdown": dict(Counter(v for _, _, v in verdicts)),
        }

    # ---- G3
    tp_idx = []
    for x in g1:
        for t in x["v2_true"]:
            j = f.idx.get(t["key"])
            if j is not None:
                tp_idx.append(j)
    blob_tp = sum(1 for j in tp_idx if j in f.blobs)
    g3 = {
        "true_positive_siblings": len(tp_idx),
        "flagged_is_blob": blob_tp,
        "share": round(blob_tp / len(tp_idx), 4) if tp_idx else None,
        "over_fires": (blob_tp / len(tp_idx) > G3_BLOB_SHARE_TAU) if tp_idx else None,
        "field_blob_share": round(len(f.blobs) / len(f.keys), 4),
    }

    verdict = ("GO" if (g1_pass and g2.get("passes")) else
               "NO-GO" if g2.get("status") == "judged" else "PENDING")
    out = {
        "op": op.__dict__, "op_label": op.label(),
        "gate_families": gate_names,
        "G1": {"passes": g1_pass, "families": g1},
        "G2": g2, "G3": g3,
        "K1_verdict": verdict,
    }
    (SCRATCH / "sibling_v2_gates.json").write_text(
        json.dumps(out, indent=2, ensure_ascii=False))
    print(json.dumps({"G1": {"passes": g1_pass,
                             "per_family": [(x["family"], x["v2_true_in_top8"],
                                             x["v1_true_in_top8"], x["g1_eligible"])
                                            for x in g1]},
                      "G2": g2, "G3": g3, "K1": verdict}, indent=2))
    print(f"-> {SCRATCH / 'sibling_v2_gates.json'}")


def stage_artifact(args) -> None:
    """Assemble the repo-side machine summary from the stage outputs, so every
    number in the prose artifact has a generated counterpart (no transcription)."""
    f = load_field()
    op = _chosen_op()
    fam_doc = json.loads(FAMILIES_JSON.read_text())
    sweep = json.loads(SWEEP_JSON.read_text())
    gates = json.loads((SCRATCH / "sibling_v2_gates.json").read_text())
    jd = json.loads(G2_JUDGMENTS.read_text()) if G2_JUDGMENTS.exists() else None

    fams = {x["name"]: [e["key"] for e in x["evidence"] if e["verified"]]
            for x in fam_doc["families"]}
    gate_elig = [n for n in fam_doc["gate_families"] if len(fams.get(n, [])) >= 4]

    # G1 ceiling over the whole grid (post-hoc; NOT the pre-registered scoring).
    ceiling = []
    for o in [None] + grid():
        per = {}
        for n in gate_elig:
            idxs = [f.idx[k] for k in fams[n]]
            S = set(idxs)
            per[n] = max(
                len({r["idx"] for r in (v1_rank(f, a, G1_TRUE_IN_TOP_K) if o is None
                                        else union_rank(f, a, o, G1_TRUE_IN_TOP_K))}
                    & (S - {a}))
                for a in idxs)
        ceiling.append({"op": "v1-baseline" if o is None else o.label(),
                        "families_passing": sum(1 for v in per.values()
                                                if v >= G1_MIN_TRUE),
                        "true_sum": sum(per.values()), "per_family": per})

    lane_att = Counter()
    v1_overlap = []
    if jd:
        for a in jd["anchors"]:
            ai = f.idx[a["anchor"]]
            v1set = {r["key"] for r in v1_rank(f, ai, G2_TOP_K)}
            v1_overlap.append(len(v1set & {s["key"] for s in a["siblings"]}))
            for s in a["siblings"]:
                lane_att[("C-reachable" if s["lane_c"] > 0 else "E/G-only",
                          "false" if s["verdict"] in ("unrelated", "unsure")
                          else "true")] += 1

    lane_e_reach = {}
    for g in (2, 3, 5, 10, 20, 10**6):
        tot = pairs = 0
        for n, keys in fams.items():
            if len(keys) < 4:
                continue
            idxs = [f.idx[k] for k in keys]
            S = set(idxs)
            for a in idxs:
                tot += len(set(lane_e_scores(f, a, g)) & (S - {a}))
                pairs += len(S) - 1
        lane_e_reach[f"df<={g}"] = {"true_pairs_reached": tot, "true_pairs": pairs}

    out = {
        "contract": "sibling-finder-v2-measurement-v1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "field": {
            "n_active_story_topics": len(f.keys),
            "n_evidence_member_rows_7d": sum(f.n_members),
            "topics_with_members": sum(1 for n in f.n_members if n),
            "entity_vocab_post_junk_filter": len(f.ent_df),
            "entity_df_max": f.df_max,
            "topics_with_entity": sum(1 for s in f.ents if s),
            "topics_with_shared_entity": sum(
                1 for s in f.ents if any(f.ent_df[e] >= 2 for e in s)),
            "is_blob_flagged": len(f.blobs),
            "is_blob_share": round(len(f.blobs) / len(f.keys), 4),
        },
        "families": {x["name"]: {"harvested": len(x["evidence"]),
                                 "verified": x["verified_size"],
                                 "g1_eligible": x["g1_eligible"]}
                     for x in fam_doc["families"]},
        "split": {"dev": fam_doc["dev_families"], "gate": fam_doc["gate_families"],
                  "gate_eligible": gate_elig, "rules": fam_doc["curation"]},
        "operating_point": {"chosen": op.__dict__, "label": op.label(),
                            "selection_rule": sweep["selection_rule"],
                            "dev": sweep["chosen_op_dev"],
                            "baseline_v1_dev": sweep["baseline_v1"]},
        "lane_e_reachability": lane_e_reach,
        "mech_false_rate": {
            # Selection-only proxy (never the gate). "union_*" covers only ops
            # that actually activate lane E or lane G — the grid also holds two
            # pure-lane-C reference points, which ARE v1 and would otherwise
            # make the union's minimum look equal to the baseline by identity.
            "v1_baseline": sweep["baseline_v1"]["mech_false_rate"],
            "union_min": min(r["mech_false_rate"] for r in sweep["sweep"]
                             if r["op_json"]["w_e"] > 0 or r["op_json"]["w_g"] > 0),
            "union_max": max(r["mech_false_rate"] for r in sweep["sweep"]
                             if r["op_json"]["w_e"] > 0 or r["op_json"]["w_g"] > 0),
            "pure_lane_C_reference": min(r["mech_false_rate"] for r in sweep["sweep"]
                                         if r["op_json"]["w_e"] == 0
                                         and r["op_json"]["w_g"] == 0),
        },
        "G1": gates["G1"],
        "G1_ceiling_posthoc": {
            "n_ops": len(ceiling),
            "ops_reaching_all_gate_families": sum(
                1 for c in ceiling if c["families_passing"] == len(gate_elig)),
            "best_families_passing": max(c["families_passing"] for c in ceiling),
            "v1": next(c for c in ceiling if c["op"] == "v1-baseline"),
        },
        "G2": {**gates["G2"],
               "rows_reachable_by_lane_C": lane_att[("C-reachable", "false")]
               + lane_att[("C-reachable", "true")],
               "rows_introduced_by_E_or_G": lane_att[("E/G-only", "false")]
               + lane_att[("E/G-only", "true")],
               "false_rate_among_C_reachable": round(
                   lane_att[("C-reachable", "false")]
                   / max(1, lane_att[("C-reachable", "false")]
                         + lane_att[("C-reachable", "true")]), 4),
               "v1_top5_overlap_per_anchor": v1_overlap,
               "v1_top5_overlap_mean": round(
                   sum(v1_overlap) / len(v1_overlap), 2) if v1_overlap else None},
        "G3": gates["G3"],
        "K1_verdict": gates["K1_verdict"],
    }
    if jd:
        out["G3"]["g2_rows_flagged_blob"] = sum(
            1 for a in jd["anchors"] for s in a["siblings"] if s["is_blob"])
        out["G3"]["g2_true_rows_flagged_blob"] = sum(
            1 for a in jd["anchors"] for s in a["siblings"]
            if s["is_blob"] and s["verdict"] == "related")
        out["G3"]["g2_false_rows_flagged_blob"] = sum(
            1 for a in jd["anchors"] for s in a["siblings"]
            if s["is_blob"] and s["verdict"] != "related")
    path = ARTIFACT_DIR / f"{ARTIFACT_STEM}.json"
    path.write_text(json.dumps(out, indent=2, ensure_ascii=False, default=str))
    print(json.dumps({k: out[k] for k in
                      ("field", "mech_false_rate", "G1_ceiling_posthoc",
                       "K1_verdict")}, indent=2, default=str))
    print(f"-> {path}")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--pull", action="store_true")
    ap.add_argument("--families", action="store_true")
    ap.add_argument("--fresh", type=int, default=8)
    ap.add_argument("--sweep", action="store_true")
    ap.add_argument("--g2-worksheet", action="store_true")
    ap.add_argument("--gates", action="store_true")
    ap.add_argument("--artifact", action="store_true")
    args = ap.parse_args()
    if args.pull:
        stage_pull()
    if args.families:
        stage_families(args)
    if args.sweep:
        stage_sweep(args)
    if args.g2_worksheet:
        stage_g2_worksheet(args)
    if args.gates:
        stage_gates(args)
    if args.artifact:
        stage_artifact(args)


if __name__ == "__main__":
    main()

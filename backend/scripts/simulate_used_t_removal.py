#!/usr/bin/env python3
"""Offline simulation: what happens if `used_t` is dropped from
`project_dynamic_topics.process_snapshot`?

READ-ONLY. Writes no prod table (`SET default_transaction_read_only = on`).
Nothing in `project_dynamic_topics.py` is modified: the variant is a COPY of
`process_snapshot` with exactly ONE line removed, marked inline, and every other
constant (`MATCH_THRESHOLD` 0.88, `ANCHOR_THRESHOLD` 0.93, `Topic.attach`,
`next_state`, `LifecycleConfig`) is IMPORTED from the production module so the
two arms cannot drift.

THE QUESTION
------------
`process_snapshot` matches clusters to topics greedy 1-to-1: a matched cluster
is consumed (`used_c`) AND a matched topic is consumed (`used_t`). The second
half means a topic absorbs at most ONE cluster per snapshot, so N fragments of
one event cannot land on one identity in a night, by construction
(docs/research/recall-229/2026-07-28-identity-layer-raw-cosine.md, fix 2).

BASELINE = production. VARIANT = production minus `used_t` (one cluster still
attaches to at most one topic; the MATCH and ANCHOR gates still apply to every
cluster/topic pair; `merge_duplicates` is untouched and is not run — production
only runs it under `--rebuild`).

A STRUCTURAL FACT THIS HARNESS MAKES VISIBLE (not a bug in the sim): within one
snapshot, `pairs` is built against the topics that EXIST when the snapshot
starts; unmatched clusters found new topics only AFTER the match loop. So a
brand-new event whose N fragments all appear in the SAME snapshot founds N
topics in BOTH arms — `used_t` was never the binding constraint there. Dropping
`used_t` can only consolidate clusters onto a topic that already existed when
the night began.

METRICS (pre-registered in the task before this file was written; see the .md)
  1  witness reconvergence  — topics per event for the witness families
  2  false absorptions      — the topic-784 signature on multi-absorptions
  3  over-merge pressure    — overmerge.decide() over each arm's member sets
  4  absorption density     — max / p95 clusters absorbed per topic per night
  5  anchor-guard effect    — pairs the 0.93 anchor blocked that 0.88 admitted

Usage (M1 mlvenv; read-only):
  set -a; . ~/AtlasLocalWorker/.env; set +a
  cd backend && /Users/pedro/AtlasLocalWorker/mlvenv/bin/python \
      -m scripts.simulate_used_t_removal --window-start 2026-07-17 --mode all
"""
from __future__ import annotations

import argparse
import asyncio
import datetime as dt
import json
import os
import time
from collections import Counter, defaultdict
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any, Sequence

import numpy as np

# --- production module: every gate/constant/behaviour is imported, not copied --
from scripts.project_dynamic_topics import (  # noqa: E402
    ANCHOR_THRESHOLD,
    MATCH_THRESHOLD,
    LifecycleConfig,
    Topic,
    _subject_tokens,
    next_state,
)
from app.services.overmerge import (  # noqa: E402
    OverMergeParams,
    country_dominant_overlap,
    decide,
    partition,
)

REPO_ROOT = Path(__file__).resolve().parents[2]
OUT_DIR = REPO_ROOT / "docs" / "research" / "recall-229"
STEM = "2026-07-30-used-t-simulation"

# Pre-registered guard thresholds (frozen; not touched after seeing results).
GUARD_COUNTRY_SPAN = 3          # >= 3 distinct primary countries among absorbed
GUARD_LABEL_SIM_MAX = 0.40      # SequenceMatcher below this = incompatible
GUARD_OVERMERGE_RATIO_MAX = 1.5  # variant/baseline demote-eligible ratio kill
DENSITY_RED_FLAG = 10           # > this many clusters in one night = inspect


# ------------------------------------------------------------------ geometry
def _unit_rows(mat: np.ndarray) -> np.ndarray:
    """Row-wise L2 normalize — the matrix form of `_unit` in
    emergent_topic_identity_resolver (cosine = dot of unit vectors)."""
    n = np.linalg.norm(mat, axis=1, keepdims=True)
    return mat / np.maximum(n, 1e-12)


def candidate_pairs(cvecs: np.ndarray, tcent: np.ndarray, tanch: np.ndarray,
                    *, chunk: int = 768, probe_rows: Sequence[int] = (),
                    probe_out: dict[int, list] | None = None,
                    ) -> tuple[np.ndarray, np.ndarray, np.ndarray, dict[str, Any]]:
    """Vectorized equivalent of production's double loop + `pairs.sort(reverse=True)`.

    Returns (s, ci, ti) in production's exact iteration order and a diagnostic
    dict. Production sorts tuples `(s, ci, ti)` descending; np.lexsort with keys
    (-ti, -ci, -s) reproduces that ordering exactly (last key is primary).

    NUMERIC NOTE: production calls BLAS ddot per pair, this calls dgemm. The two
    can differ in the last ulp, so a pair sitting within ~1e-15 of a gate could
    in principle flip. `near_gate` counts pairs within 1e-12 of either gate; it
    is reported, and it is 0 in every run so far.
    """
    Cn = _unit_rows(cvecs)
    Tn = _unit_rows(tcent)
    An = _unit_rows(tanch)
    s_all: list[np.ndarray] = []
    ci_all: list[np.ndarray] = []
    ti_all: list[np.ndarray] = []
    near_gate = 0
    match_only = 0   # cos(centroid) passes, anchor blocks   (metric 5)
    anchor_only = 0  # anchor passes, cos(centroid) blocks
    for lo in range(0, Cn.shape[0], chunk):
        hi = min(lo + chunk, Cn.shape[0])
        S = Cn[lo:hi] @ Tn.T
        A = Cn[lo:hi] @ An.T
        ms = S >= MATCH_THRESHOLD
        ma = A >= ANCHOR_THRESHOLD
        match_only += int((ms & ~ma).sum())
        anchor_only += int((ma & ~ms).sum())
        near_gate += int((np.abs(S - MATCH_THRESHOLD) < 1e-12).sum())
        near_gate += int((np.abs(A - ANCHOR_THRESHOLD) < 1e-12).sum())
        m = ms & ma
        if probe_out is not None:
            for r in probe_rows:
                if lo <= r < hi:
                    row = r - lo
                    top = np.argsort(-S[row])[:12]
                    probe_out[r] = [
                        {"ti": int(j), "cos_centroid": round(float(S[row, j]), 5),
                         "cos_anchor": round(float(A[row, j]), 5),
                         "admissible": bool(m[row, j]),
                         "blocked_by": ("" if m[row, j] else
                                        ("anchor" if ms[row, j] else
                                         ("match" if ma[row, j] else "both")))}
                        for j in top]
        rr, tt = np.nonzero(m)
        if rr.size:
            s_all.append(S[rr, tt])
            ci_all.append(rr + lo)
            ti_all.append(tt)
    if not s_all:
        empty = np.array([], dtype=np.int64)
        return (np.array([], dtype=np.float64), empty, empty,
                {"near_gate": near_gate, "match_only_blocked_by_anchor": match_only,
                 "anchor_only_blocked_by_match": anchor_only, "n_pairs": 0})
    s = np.concatenate(s_all)
    ci = np.concatenate(ci_all).astype(np.int64)
    ti = np.concatenate(ti_all).astype(np.int64)
    order = np.lexsort((-ti, -ci, -s))
    return (s[order], ci[order], ti[order],
            {"near_gate": near_gate, "match_only_blocked_by_anchor": match_only,
             "anchor_only_blocked_by_match": anchor_only, "n_pairs": int(s.size)})


# ------------------------------------------------------------------ the two arms
def process_snapshot_sim(topics: list[Topic], snap_clusters: list[dict[str, Any]],
                         snap: str, cfg: LifecycleConfig, *, allow_multi: bool,
                         events: list[dict[str, Any]],
                         probe_cids: set[int] | None = None,
                         probe_store: dict[int, list] | None = None) -> dict[str, Any]:
    """COPY of `project_dynamic_topics.process_snapshot` with ONE line changed.

    The only difference from production is marked `### USED_T` below. Everything
    else — gates, order, attach, founding, state advance — is production's.
    """
    if not snap_clusters:
        return {"snapshot": snap, "n_clusters": 0}
    cvecs = np.stack([np.asarray(c["centroid"], dtype=np.float64) for c in snap_clusters])
    tcent = np.stack([t.centroid for t in topics]) if topics else np.zeros((0, cvecs.shape[1]))
    tanch = np.stack([t.anchor_centroid for t in topics]) if topics else np.zeros((0, cvecs.shape[1]))
    probe_rows = ([i for i, c in enumerate(snap_clusters) if c["id"] in probe_cids]
                  if probe_cids else [])
    probe_raw: dict[int, list] = {}
    if topics:
        s_arr, ci_arr, ti_arr, diag = candidate_pairs(
            cvecs, tcent, tanch, probe_rows=probe_rows,
            probe_out=(probe_raw if probe_rows else None))
        if probe_store is not None:
            for r, rows in probe_raw.items():
                probe_store[snap_clusters[r]["id"]] = [
                    {**x, "topic_identity": topics[x["ti"]].identity_key,
                     "topic_label": topics[x["ti"]].label} for x in rows]
    else:
        s_arr = np.array([]); ci_arr = np.array([], dtype=np.int64)
        ti_arr = np.array([], dtype=np.int64)
        diag = {"near_gate": 0, "match_only_blocked_by_anchor": 0,
                "anchor_only_blocked_by_match": 0, "n_pairs": 0}

    used_c: set[int] = set()
    used_t: set[int] = set()
    seen_topics: set[int] = set()
    absorbed: dict[int, list[int]] = defaultdict(list)
    for k in range(s_arr.size):
        s = float(s_arr[k]); ci = int(ci_arr[k]); ti = int(ti_arr[k])
        # ### USED_T — production: `if ci in used_c or ti in used_t: continue`
        if ci in used_c:
            continue
        if not allow_multi and ti in used_t:
            continue
        used_c.add(ci)
        used_t.add(ti)
        topics[ti].attach(snap_clusters[ci], snap, s)
        seen_topics.add(ti)
        absorbed[ti].append(ci)
        events.append({"snapshot": snap, "topic_idx": ti,
                       "topic_identity": topics[ti].identity_key,
                       "cluster_id": snap_clusters[ci]["id"], "score": round(s, 6),
                       "rank_in_topic": len(absorbed[ti])})

    founded = 0
    for ci, c in enumerate(snap_clusters):
        if ci not in used_c:
            t = Topic(
                identity_key=f"dyn-{c['snapshot_at']}-{c['cluster_id']}",
                label=c["label"], centroid=c["centroid"], snap=snap,
                n_signals=c["n_signals"], cohesion=c.get("cohesion"), noise=c.get("noise"),
                content_roundup=bool(c.get("content_roundup")),
            )
            t.members.append({"cluster_id": c["id"], "snapshot_at": snap, "match_score": 1.0})
            topics.append(t)
            seen_topics.add(len(topics) - 1)
            founded += 1

    for ti, t in enumerate(topics):
        seen = ti in seen_topics
        t.since_seen = 0 if seen else t.since_seen + 1
        new_state = next_state(
            t.state, seen_now=seen, n_snapshots=len(t.snapshots),
            mean_cohesion=t.mean_cohesion, agg_n_signals=t.agg_n_signals,
            is_roundup=t.is_roundup, since_seen=t.since_seen, cfg=cfg,
            noise_rate=t.noise_rate, is_junk=t.is_junk,
        )
        if new_state != t.state:
            t.state = new_state
            t.dirty = True

    sizes = [len(v) for v in absorbed.values()]
    return {
        "snapshot": snap, "n_clusters": len(snap_clusters), "n_topics_before": len(topics) - founded,
        "attached": len(used_c), "founded": founded,
        "topics_receiving": len(absorbed),
        "max_absorbed": max(sizes) if sizes else 0,
        "multi_absorb_topics": sum(1 for x in sizes if x > 1),
        "absorb_sizes": sizes,
        **diag,
    }


# ------------------------------------------------------------------ DB loading
async def load_clusters(conn, start: dt.datetime | None) -> list[dict[str, Any]]:
    sql = ("SELECT id, snapshot_at, cluster_id, label, n_signals, cohesion, "
           "sample_signal_ids, centroid_vec, role_noise_rate, top_country_codes "
           "FROM emergent_clusters WHERE centroid_vec IS NOT NULL ")
    args: list[Any] = []
    if start is not None:
        sql += "AND snapshot_at >= $1 "
        args.append(start)
    sql += "ORDER BY snapshot_at, cluster_id"
    rows = await conn.fetch(sql, *args)
    return [
        {
            "id": int(r["id"]), "snapshot_at": r["snapshot_at"].isoformat(),
            "snapshot_ts": r["snapshot_at"],
            "cluster_id": r["cluster_id"], "label": r["label"],
            "n_signals": int(r["n_signals"] or 0),
            "cohesion": float(r["cohesion"]) if r["cohesion"] is not None else None,
            "sample_signal_ids": [int(x) for x in (r["sample_signal_ids"] or [])],
            "centroid": np.array(r["centroid_vec"], dtype=np.float64),
            "noise": float(r["role_noise_rate"]) if r["role_noise_rate"] is not None else None,
            "cc": [str(x) for x in (r["top_country_codes"] or [])],
        }
        for r in rows
    ]


async def hydrate_as_of(conn, clusters_by_id: dict[int, dict[str, Any]],
                        cutoff: dt.datetime
                        ) -> tuple[list[Topic], dict[str, Any], set[str]]:
    """`project_dynamic_topics.hydrate_topics`, restricted to state AS OF `cutoff`.

    Same replay-through-attach reconstruction. Two as-of rules:
      * only member rows with snapshot_at < cutoff are replayed;
      * a topic whose FIRST member (or first_seen, for the members-gone fallback)
        is >= cutoff did not exist yet and is NOT loaded — the replay must found
        it, or not.
    """
    trows = await conn.fetch(
        "SELECT id, identity_key, state, snapshots_since_seen, label, "
        "centroid_vec, first_seen, last_seen, n_snapshots, agg_n_signals, "
        "mean_cohesion, noise_rate, is_junk, COALESCE(is_umbrella,false) AS is_umbrella "
        "FROM dynamic_topics")
    mrows = await conn.fetch(
        "SELECT dynamic_topic_id, emergent_cluster_id, snapshot_at "
        "FROM dynamic_topic_members WHERE snapshot_at < $1 ORDER BY snapshot_at", cutoff)
    members: dict[int, list[dict[str, Any]]] = defaultdict(list)
    for m in mrows:
        members[int(m["dynamic_topic_id"])].append(
            {"cluster_id": int(m["emergent_cluster_id"]),
             "snapshot_at": m["snapshot_at"].isoformat()})

    topics: list[Topic] = []
    umbrella_keys: set[str] = set()   # Topic uses __slots__: no side attributes
    meta = {"loaded_with_members": 0, "loaded_fallback": 0,
            "skipped_founded_in_window": 0, "skipped_no_centroid": 0,
            "umbrellas": 0}
    for tr in trows:
        tid = int(tr["id"])
        mem = [m for m in members.get(tid, []) if m["cluster_id"] in clusters_by_id]
        if not mem:
            # members gone (retention) OR founded inside the window
            if tr["first_seen"] is not None and tr["first_seen"] >= cutoff:
                meta["skipped_founded_in_window"] += 1
                continue
            if tr["centroid_vec"] is None:
                meta["skipped_no_centroid"] += 1
                continue
            t = Topic(identity_key=tr["identity_key"], label=tr["label"] or "",
                      centroid=tr["centroid_vec"],
                      snap=tr["last_seen"].isoformat() if tr["last_seen"] else "",
                      n_signals=int(tr["agg_n_signals"] or 0),
                      cohesion=tr["mean_cohesion"], noise=tr["noise_rate"])
            if tr["first_seen"]:
                t.first_seen = tr["first_seen"].isoformat()
            n_snaps = max(1, int(tr["n_snapshots"] or 1))
            t.snapshots = {f"restored:{i}" for i in range(n_snaps - 1)}
            t.snapshots.add(t.last_seen or "restored:last")
            meta["loaded_fallback"] += 1
        else:
            mem.sort(key=lambda m: m["snapshot_at"])
            first = clusters_by_id[mem[0]["cluster_id"]]
            t = Topic(identity_key=tr["identity_key"], label=first["label"],
                      centroid=first["centroid"], snap=mem[0]["snapshot_at"],
                      n_signals=first["n_signals"], cohesion=first.get("cohesion"),
                      noise=first.get("noise"))
            t.members.append({"cluster_id": first["id"],
                              "snapshot_at": mem[0]["snapshot_at"], "match_score": 1.0})
            for m in mem[1:]:
                t.attach(clusters_by_id[m["cluster_id"]], m["snapshot_at"], 1.0)
            meta["loaded_with_members"] += 1
        t.id = tid
        t.state = tr["state"]
        t.since_seen = int(tr["snapshots_since_seen"] or 0)
        t.is_junk = bool(tr["is_junk"])
        t.new = False
        t.members = []
        t.dirty = False
        if bool(tr["is_umbrella"]):
            umbrella_keys.add(t.identity_key)
            meta["umbrellas"] += 1
        topics.append(t)
    return topics, meta, umbrella_keys


# ------------------------------------------------------------------ families
def norm_label(s: str | None) -> str:
    import re
    return re.sub(r"[^a-z0-9]+", " ", (s or "").lower()).strip()


def label_sim(a: str | None, b: str | None) -> float:
    na, nb = norm_label(a), norm_label(b)
    if not na or not nb:
        return 0.0
    return SequenceMatcher(None, na, nb).ratio()


def pattern_family(clusters: list[dict[str, Any]], snap: str, tokens: Sequence[str],
                   name: str) -> dict[str, Any] | None:
    """`measure_evidence_fingerprint.find_pattern_family`: the snapshot's clusters
    whose label contains EVERY token (AND, not OR)."""
    hits = [c for c in clusters
            if c["snapshot_at"] == snap and c["label"]
            and all(t.lower() in c["label"].lower() for t in tokens)]
    if not hits:
        return None
    hits.sort(key=lambda c: -c["n_signals"])
    return {"name": name, "kind": "core", "pattern": " AND ".join(tokens),
            "cluster_ids": [c["id"] for c in hits],
            "labels": [c["label"] for c in hits][:8],
            "countries": sorted({x for c in hits for x in c["cc"]})[:6],
            "n_signals": sum(c["n_signals"] for c in hits)}


def fresh_families(clusters: list[dict[str, Any]], snap: str, exclude: set[int],
                   min_size: int, want: int) -> list[dict[str, Any]]:
    """`measure_evidence_fingerprint.find_fresh_families` discovery rule: label
    SequenceMatcher >= 0.80 AND a shared country; connected components ARE the
    families."""
    items = [c for c in clusters
             if c["snapshot_at"] == snap and c["label"] and c["id"] not in exclude]
    parent = list(range(len(items)))

    def find(x: int) -> int:
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(a: int, b: int) -> None:
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[rb] = ra

    for i in range(len(items)):
        for j in range(i + 1, len(items)):
            a, b = items[i], items[j]
            if not (set(a["cc"]) & set(b["cc"])):
                continue
            if label_sim(a["label"], b["label"]) >= 0.80:
                union(i, j)
    groups: dict[int, list[dict]] = defaultdict(list)
    for k in range(len(items)):
        groups[find(k)].append(items[k])
    fams = [g for g in groups.values() if len(g) >= min_size]
    fams.sort(key=lambda g: (-len(g), min(c["id"] for c in g)))
    out: list[dict[str, Any]] = []
    used: set[str] = set()
    for g in fams[:want]:
        g = sorted(g, key=lambda c: -c["n_signals"])
        base = f"fresh:{norm_label(g[0]['label'])[:38].replace(' ', '-')}"
        nm, k = base, 2
        while nm in used:
            nm = f"{base}#{k}"; k += 1
        used.add(nm)
        out.append({"name": nm, "kind": "fresh", "cluster_ids": [c["id"] for c in g],
                    "labels": [c["label"] for c in g][:8],
                    "countries": sorted({x for c in g for x in c["cc"]})[:6],
                    "n_signals": sum(c["n_signals"] for c in g)})
    return out


async def gq05_family(conn, clusters: list[dict[str, Any]], snaps_in_window: set[str],
                      pattern: str, hours: int) -> dict[str, Any] | None:
    """GQ-05 proxy: replayed-window clusters whose sample_signal_ids touch the
    `%espriella%` corpus.

    NOT the diagnosis's 21/33 offline fragments — those live outside
    `emergent_clusters` and cannot be nodes of a projection replay (the same
    limitation the witness-reconvergence artifact recorded). Stated, not hidden.
    Window-scoped because the 07-28 snapshot contains ZERO espriella-touching
    clusters (measured); a snapshot-scoped GQ-05 would be an empty family.
    """
    rows = await conn.fetch(
        "SELECT id FROM signals_v2 WHERE headline ILIKE $1 "
        "AND created_at > now() - ($2 || ' hours')::interval", f"%{pattern}%", str(hours))
    sids = {int(r["id"]) for r in rows}
    if not sids:
        return None
    hits = [c for c in clusters
            if c["snapshot_at"] in snaps_in_window and sids & set(c["sample_signal_ids"])]
    if not hits:
        return None
    hits.sort(key=lambda c: -c["n_signals"])
    return {"name": "GQ-05 [window]", "kind": "core", "scope": "window",
            "pattern": f"sample_signal_ids ∩ %{pattern}%",
            "corpus_signals": len(sids),
            "cluster_ids": [c["id"] for c in hits],
            "labels": [c["label"] for c in hits][:8],
            "nights": sorted({c["snapshot_at"][:10] for c in hits}),
            "countries": sorted({x for c in hits for x in c["cc"]})[:6],
            "n_signals": sum(c["n_signals"] for c in hits)}


def extend_to_window(fam: dict[str, Any], clusters: list[dict[str, Any]],
                     snaps_in_window: set[str], by_id: dict[int, dict]) -> dict[str, Any]:
    """Grow a snapshot-scoped family across the replay window by SAMPLE-SIGNAL
    OVERLAP (one hop), not by label.

    Label extension is impossible across 2026-07-23→27: those snapshots are 100%
    NULL-label (the DeepSeek 402 blackout), and they are exactly the nights on
    which the Berlin-Pride and Caspian identities were founded. Shared
    `sample_signal_ids` is a measured, language- and label-free link between two
    nights' clusters, so it reaches them. One hop, so the family cannot chain
    into a different event.
    """
    seed_sids: set[int] = set()
    for cid in fam["cluster_ids"]:
        seed_sids.update(by_id[cid]["sample_signal_ids"])
    hits = [c for c in clusters
            if c["snapshot_at"] in snaps_in_window and seed_sids & set(c["sample_signal_ids"])]
    hits.sort(key=lambda c: (c["snapshot_at"], -c["n_signals"]))
    return {"name": f'{fam["name"]} [window]', "kind": fam["kind"], "scope": "window",
            "pattern": f'{fam.get("pattern", "")} ⊕ sample-signal overlap (1 hop)',
            "cluster_ids": [c["id"] for c in hits],
            "labels": [c["label"] for c in hits if c["label"]][:8],
            "nights": sorted({c["snapshot_at"][:10] for c in hits}),
            "clusters_per_night": dict(Counter(c["snapshot_at"][:10] for c in hits)),
            "countries": sorted({x for c in hits for x in c["cc"]})[:6],
            "n_signals": sum(c["n_signals"] for c in hits)}


# ------------------------------------------------------------------ scoring
def topic_of_cluster(topics: list[Topic]) -> dict[int, int]:
    """cluster_id -> topic index, from the arm's in-memory member lists."""
    out: dict[int, int] = {}
    for ti, t in enumerate(topics):
        for m in t.members:
            out[int(m["cluster_id"])] = ti
    return out


def score_family(fam: dict[str, Any], topics: list[Topic],
                 owner: dict[int, int]) -> dict[str, Any]:
    """Topics per event for one family, in one arm."""
    cids = fam["cluster_ids"]
    holders = Counter()
    unassigned = 0
    for cid in cids:
        ti = owner.get(cid)
        if ti is None:
            unassigned += 1
        else:
            holders[ti] += 1
    live = [ti for ti in holders if topics[ti].state in ("active", "candidate")]
    biggest = holders.most_common(1)[0] if holders else (None, 0)
    return {
        "family": fam["name"], "clusters": len(cids),
        "topics_holding": len(holders),
        "live_topics_holding": len(live),
        "unassigned_clusters": unassigned,
        "largest_topic_share": round(biggest[1] / max(len(cids), 1), 4),
        "largest_topic_clusters": biggest[1],
        "largest_topic_label": (topics[biggest[0]].label if biggest[0] is not None else None),
        "largest_topic_identity": (topics[biggest[0]].identity_key if biggest[0] is not None else None),
        "holder_sizes": sorted(holders.values(), reverse=True),
    }


def guard_false_absorption(events: list[dict[str, Any]], clusters_by_id: dict[int, dict],
                           topics: list[Topic], df_tokens: Counter,
                           n_labels: int, umbrella_keys: set[str]) -> dict[str, Any]:
    """Metric 2 — the topic-784 signature on within-night multi-absorptions.

    For every (topic, night) that absorbed >= 2 clusters:
      * country span  — distinct primary countries among the absorbed clusters
      * label clash   — a pair with SequenceMatcher < 0.40 AND no shared
                        distinctive token (a token outside the top-decile df of
                        that snapshot's cluster-label vocabulary)
    """
    ubiquitous = {tok for tok, c in df_tokens.most_common(max(1, n_labels // 10))}
    groups: dict[tuple[str, int], list[int]] = defaultdict(list)
    for e in events:
        groups[(e["snapshot"], e["topic_idx"])].append(e["cluster_id"])
    flagged: list[dict[str, Any]] = []
    n_multi = 0
    for (snap, ti), cids in groups.items():
        if len(cids) < 2:
            continue
        n_multi += 1
        cs = [clusters_by_id[c] for c in cids]
        prim = [c["cc"][0] for c in cs if c["cc"]]
        span = len(set(prim))
        clashes: list[dict[str, Any]] = []
        for i in range(len(cs)):
            for j in range(i + 1, len(cs)):
                la, lb = cs[i]["label"], cs[j]["label"]
                if not la or not lb:
                    continue  # label blackout: undecidable, never counted as a clash
                sim = label_sim(la, lb)
                if sim >= GUARD_LABEL_SIM_MAX:
                    continue
                shared = (_subject_tokens(la) & _subject_tokens(lb)) - ubiquitous
                if shared:
                    continue
                clashes.append({"a": la, "b": lb, "sim": round(sim, 3)})
        if span >= GUARD_COUNTRY_SPAN or clashes:
            flagged.append({
                "snapshot": snap, "topic_identity": topics[ti].identity_key,
                "topic_label": topics[ti].label, "topic_state": topics[ti].state,
                "is_umbrella": topics[ti].identity_key in umbrella_keys,
                "absorbed": len(cids), "country_span": span,
                "primary_countries": sorted(set(prim)),
                "labels": [c["label"] for c in cs],
                "cluster_ids": cids,
                "label_clashes": clashes[:6],
                "signature": ("country_span" if span >= GUARD_COUNTRY_SPAN else "") +
                             ("+label_clash" if clashes else ""),
            })
    per_night: dict[str, dict[str, int]] = defaultdict(lambda: {"multi": 0, "flagged": 0})
    for (snap, _ti), cids in groups.items():
        if len(cids) > 1:
            per_night[snap[:10]]["multi"] += 1
    for f in flagged:
        per_night[f["snapshot"][:10]]["flagged"] += 1
    return {"multi_absorption_groups": n_multi, "flagged_784_class": len(flagged),
            "flagged_on_labelled_nights": sum(
                1 for f in flagged if any(clusters_by_id[c]["label"] for c in f["cluster_ids"])),
            "per_night": {k: v for k, v in sorted(per_night.items())},
            "flagged": flagged}


def lifetime_country_span(topics: list[Topic], clusters_by_id: dict[int, dict],
                          window_cids: set[int]) -> dict[str, Any]:
    """Context for metric 2: the ORIGINAL 784 signature — a topic whose absorbed
    clusters (over the whole replay, not one night) span >= 3 primary countries.
    Computed identically for both arms so the comparison is fair."""
    hits = []
    for t in topics:
        cids = [int(m["cluster_id"]) for m in t.members if int(m["cluster_id"]) in window_cids]
        if len(cids) < 2:
            continue
        prim = [clusters_by_id[c]["cc"][0] for c in cids if clusters_by_id[c]["cc"]]
        span = len(set(prim))
        if span >= GUARD_COUNTRY_SPAN:
            hits.append({"identity": t.identity_key, "label": t.label, "span": span,
                         "clusters": len(cids), "countries": sorted(set(prim))[:8]})
    hits.sort(key=lambda h: -h["span"])
    return {"topics_spanning_3plus_countries": len(hits), "top": hits[:15]}


def overmerge_pressure(topics: list[Topic], clusters_by_id: dict[int, dict],
                       emb: dict[int, np.ndarray], sig_meta: dict[int, tuple],
                       window_cids: set[int], params: OverMergeParams) -> dict[str, Any]:
    """Metric 3 — `overmerge.decide()` over each arm's simulated member sets.

    Members of a topic = the embedded sample signals of the clusters it holds
    inside the replay window. (detect_overmerge reads `topic_members`; that table
    is not written by this simulation, so the analogue is built from the same
    substrate the projection actually moves.) Both arms use the identical
    computation, so the RATIO is the pre-registered quantity.
    """
    verdicts = Counter()
    demote_eligible: list[dict[str, Any]] = []
    evaluated = 0
    # bucketed by how many clusters the topic actually fused — the variant's whole
    # effect lives in the high buckets, and `decide()` is documented to go blind
    # there (a 3+-story fusion has no clean bimodal split).
    by_bucket: dict[str, Counter] = defaultdict(Counter)
    gap_by_bucket: dict[str, list[float]] = defaultdict(list)
    for t in topics:
        sids: list[int] = []
        n_clusters = 0
        for m in t.members:
            cid = int(m["cluster_id"])
            if cid in window_cids:
                n_clusters += 1
                sids.extend(clusters_by_id[cid]["sample_signal_ids"])
        sids = [s for s in dict.fromkeys(sids) if s in emb]
        if len(sids) < params.min_members:
            continue
        evaluated += 1
        mat = np.stack([emb[s] for s in sids]).astype(np.float64)
        labels, stats = partition(mat, seed=params.seed)
        if labels is None or stats is None:
            continue
        acts_a: set[str] = set(); acts_b: set[str] = set()
        for k, sid in enumerate(sids):
            cc, persons = sig_meta.get(sid, (None, None))
            acts = set()
            if cc:
                acts.add(f"c:{cc.strip().upper()}")
            for p in (persons or []):
                if p and str(p).strip():
                    acts.add(f"p:{str(p).strip().lower()}")
            (acts_a if labels[k] == 0 else acts_b).update(acts)
        overlap = country_dominant_overlap(acts_a, acts_b)
        verdict, reason = decide(stats, overlap, params)
        verdicts[verdict] += 1
        bucket = ("1" if n_clusters <= 1 else "2-4" if n_clusters <= 4
                  else "5-9" if n_clusters <= 9 else "10+")
        by_bucket[bucket][verdict] += 1
        gap_by_bucket[bucket].append(stats.gap_ratio)
        if verdict in ("demote", "borderline"):
            demote_eligible.append({
                "identity": t.identity_key, "label": t.label, "verdict": verdict,
                "clusters": n_clusters,
                "n_members": len(sids), "gap_ratio": round(stats.gap_ratio, 3),
                "balance": round(stats.balance, 3), "overlap": round(overlap, 3),
                "reason": reason,
            })
    buckets = {}
    for b, c in by_bucket.items():
        tot = sum(c.values())
        g = gap_by_bucket[b]
        buckets[b] = {"topics": tot, **dict(c),
                      "demote_eligible_rate": round(
                          (c.get("demote", 0) + c.get("borderline", 0)) / max(tot, 1), 4),
                      "gap_ratio_median": round(float(np.median(g)), 3) if g else None}
    return {"topics_evaluated": evaluated, "verdicts": dict(verdicts),
            "demote_eligible": len(demote_eligible),
            "demote_only": verdicts.get("demote", 0),
            "demote_eligible_rate": round(len(demote_eligible) / max(evaluated, 1), 4),
            "by_cluster_bucket": buckets,
            "examples": sorted(demote_eligible, key=lambda d: -d["gap_ratio"])[:12]}


def probe_summary(fams: list[dict[str, Any]], probe: dict[int, list],
                  topics: list[Topic], owner: dict[int, int]) -> list[dict[str, Any]]:
    """WHY a family does not consolidate: was `used_t` the binding constraint, or
    the gates, or neither?

    For each family, take the topic that ends up holding the most of its clusters
    (the natural consolidation target) and ask, for every OTHER family cluster,
    what the geometry said about that target at match time:
      admissible          — the pair cleared MATCH and ANCHOR; only `used_t` (or a
                            higher-scoring rival) kept the cluster off it
      blocked_by=anchor   — cos(running centroid) >= 0.88 but anchor < 0.93
      blocked_by=match    — anchor >= 0.93 but cos(running centroid) < 0.88
      blocked_by=both     — neither gate cleared
      not_in_top12        — the target was not even among the cluster's 12 best
                            topics: the fragments do not share an argmax
    """
    out = []
    for fam in fams:
        cids = fam["cluster_ids"]
        holders = Counter(owner[c] for c in cids if c in owner)
        if not holders:
            continue
        target_ti = holders.most_common(1)[0][0]
        target = topics[target_ti].identity_key
        tally = Counter()
        scores: list[float] = []
        for cid in cids:
            rows = probe.get(cid)
            if rows is None:
                tally["no_probe_row"] += 1
                continue
            hit = next((r for r in rows if r["topic_identity"] == target), None)
            if hit is None:
                tally["not_in_top12"] += 1
                continue
            scores.append(hit["cos_centroid"])
            tally["admissible" if hit["admissible"] else f'blocked_by_{hit["blocked_by"]}'] += 1
        out.append({
            "family": fam["name"], "clusters": len(cids),
            "target_topic": target, "target_label": topics[target_ti].label,
            "target_holds": holders.most_common(1)[0][1],
            "distinct_holder_topics": len(holders),
            "vs_target": dict(tally),
            "cos_to_target": {
                "min": round(min(scores), 4), "max": round(max(scores), 4),
                "median": round(float(np.median(scores)), 4)} if scores else None,
        })
    return out


def density(per_snapshot: list[dict[str, Any]]) -> dict[str, Any]:
    sizes: list[int] = []
    for s in per_snapshot:
        sizes.extend(s.get("absorb_sizes", []))
    if not sizes:
        return {"n_absorbing_topic_nights": 0}
    arr = np.array(sizes)
    return {
        "n_absorbing_topic_nights": int(arr.size),
        "max": int(arr.max()),
        "p95": float(np.percentile(arr, 95)),
        "p99": float(np.percentile(arr, 99)),
        "mean": round(float(arr.mean()), 3),
        "topic_nights_over_flag": int((arr > DENSITY_RED_FLAG).sum()),
        "histogram": dict(Counter(sizes.copy() if isinstance(sizes, list) else sizes)),
    }


# ------------------------------------------------------------------ run
async def main_async(args: argparse.Namespace) -> int:
    import asyncpg
    db = os.environ.get("DATABASE_URL") or os.environ.get("SUPABASE_DB_URL")
    if not db:
        raise SystemExit("DATABASE_URL required")
    conn = await asyncpg.connect(db)
    await conn.execute("SET default_transaction_read_only = on")
    t_start = time.monotonic()
    try:
        cutoff = dt.datetime.fromisoformat(args.window_start).replace(tzinfo=dt.timezone.utc)
        clusters = await load_clusters(conn, None)
        clusters_by_id = {c["id"]: c for c in clusters}

        # snapshot inventory + label health
        snaps: dict[str, list[dict]] = defaultdict(list)
        for c in clusters:
            snaps[c["snapshot_at"]].append(c)
        inventory = []
        for snap in sorted(snaps):
            cs = snaps[snap]
            nulls = sum(1 for c in cs if not c["label"])
            inventory.append({"snapshot": snap, "clusters": len(cs), "null_labels": nulls,
                              "null_rate": round(nulls / len(cs), 4)})
        window_snaps = [i for i in inventory if i["snapshot"] >= cutoff.isoformat()]
        labelled = [i for i in window_snaps if i["null_rate"] == 0.0]
        if args.mode == "labelled":
            replay_snaps = [i["snapshot"] for i in labelled]
        else:
            replay_snaps = [i["snapshot"] for i in window_snaps]
        print(f"[inv] {len(inventory)} snapshots total; window >= {cutoff.date()}: "
              f"{len(window_snaps)} ({len(labelled)} labelled); replaying {len(replay_snaps)}")

        window_cids = {c["id"] for c in clusters if c["snapshot_at"] in set(replay_snaps)}

        # --- witness families, defined on the newest LABELLED snapshot ---
        newest_labelled = labelled[-1]["snapshot"] if labelled else None
        replay_set = set(replay_snaps)
        fams: list[dict[str, Any]] = []
        if newest_labelled:
            snap_scoped: list[dict[str, Any]] = []
            for toks, nm in ((("iran", "ukrain"), "GQ-12 caspian"),
                             (("berlin", "pride"), "berlin pride")):
                f = pattern_family(clusters, newest_labelled, toks, nm)
                if f:
                    f["scope"] = "snapshot"
                    snap_scoped.append(f)
            used = {cid for f in snap_scoped for cid in f["cluster_ids"]}
            snap_scoped.extend(fresh_families(clusters, newest_labelled, used,
                                              args.fresh_min, args.fresh_want))
            for f in snap_scoped:
                f.setdefault("scope", "snapshot")
            fams.extend(snap_scoped)
            # window-scoped twins: the object a MULTI-NIGHT used_t effect can act on
            fams.extend(extend_to_window(f, clusters, replay_set, clusters_by_id)
                        for f in snap_scoped)
            g = await gq05_family(conn, clusters, replay_set,
                                  args.gq05_pattern, args.gq05_hours)
            if g:
                fams.append(g)
        print(f"[fam] {len(fams)} witness families (seed snapshot {newest_labelled}): "
              + ", ".join(f'{f["name"]}({len(f["cluster_ids"])})' for f in fams))

        # --- label-token df for the guard's "distinctive token" test ---
        df_tokens: Counter = Counter()
        n_labels = 0
        for c in clusters:
            if c["snapshot_at"] == newest_labelled and c["label"]:
                n_labels += 1
                df_tokens.update(_subject_tokens(c["label"]))

        # --- embeddings + signal meta for metric 3 (bounded to window clusters) ---
        emb: dict[int, np.ndarray] = {}
        sig_meta: dict[int, tuple] = {}
        if not args.skip_overmerge:
            want = sorted({s for c in clusters if c["id"] in window_cids
                           for s in c["sample_signal_ids"]})
            print(f"[emb] fetching embeddings for {len(want)} window sample signals …")
            for i in range(0, len(want), 5000):
                chunk = want[i:i + 5000]
                for r in await conn.fetch(
                        "SELECT signal_id, vec::text AS v FROM signal_embeddings "
                        "WHERE signal_id = ANY($1::bigint[])", chunk):
                    v = np.asarray(json.loads(r["v"].replace("{", "[").replace("}", "]")),
                                   dtype=np.float32)
                    if v.size:
                        emb[int(r["signal_id"])] = v
                for r in await conn.fetch(
                        "SELECT id, country_code, persons FROM signals_v2 "
                        "WHERE id = ANY($1::bigint[])", chunk):
                    sig_meta[int(r["id"])] = (r["country_code"], r["persons"])
            print(f"[emb] {len(emb)} embedded / {len(want)} "
                  f"({100*len(emb)/max(len(want),1):.1f}%)")

        cfg = LifecycleConfig()
        params = OverMergeParams.from_env()
        arms: dict[str, dict[str, Any]] = {}
        for arm, allow_multi in (("baseline", False), ("variant", True)):
            topics, hmeta, umbrella_keys = await hydrate_as_of(conn, clusters_by_id, cutoff)
            events: list[dict[str, Any]] = []
            probe_store: dict[int, list] = {}
            probe_cids = {cid for f in fams for cid in f["cluster_ids"]}
            per_snap = []
            t0 = time.monotonic()
            for snap in replay_snaps:
                res = process_snapshot_sim(topics, snaps[snap], snap, cfg,
                                           allow_multi=allow_multi, events=events,
                                           probe_cids=probe_cids,
                                           probe_store=probe_store)
                per_snap.append(res)
                print(f"  [{arm}] {snap[:19]} clusters={res['n_clusters']:5d} "
                      f"attached={res.get('attached',0):5d} founded={res.get('founded',0):5d} "
                      f"multi={res.get('multi_absorb_topics',0):4d} "
                      f"max={res.get('max_absorbed',0):3d} topics={len(topics)}")
            owner = topic_of_cluster(topics)
            arms[arm] = {
                "hydrate": hmeta, "per_snapshot": per_snap,
                "seconds": round(time.monotonic() - t0, 1),
                "n_topics_end": len(topics),
                "states": dict(Counter(t.state for t in topics)),
                "attached_total": sum(s.get("attached", 0) for s in per_snap),
                "founded_total": sum(s.get("founded", 0) for s in per_snap),
                "families": [score_family(f, topics, owner) for f in fams],
                "why_no_consolidation": probe_summary(fams, probe_store, topics, owner),
                "density": density(per_snap),
                "false_absorption": guard_false_absorption(
                    events, clusters_by_id, topics, df_tokens, n_labels, umbrella_keys),
                "lifetime_country_span": lifetime_country_span(
                    topics, clusters_by_id, window_cids),
                "near_gate_pairs": sum(s.get("near_gate", 0) for s in per_snap),
                "anchor_blocked_pairs": sum(
                    s.get("match_only_blocked_by_anchor", 0) for s in per_snap),
                "match_blocked_pairs": sum(
                    s.get("anchor_only_blocked_by_match", 0) for s in per_snap),
                "candidate_pairs": sum(s.get("n_pairs", 0) for s in per_snap),
                "events": events,
            }
            if not args.skip_overmerge:
                arms[arm]["overmerge"] = overmerge_pressure(
                    topics, clusters_by_id, emb, sig_meta, window_cids, params)
            if arm == "baseline" and args.validate:
                arms[arm]["validation"] = await validate_against_prod(
                    conn, owner, topics, replay_snaps)

        result = {
            "generated_at": dt.datetime.now(dt.timezone.utc).isoformat(),
            "window_start": cutoff.isoformat(), "mode": args.mode,
            "replay_snapshots": replay_snaps,
            "snapshot_inventory": inventory[-20:],
            "labelled_in_window": [i["snapshot"] for i in labelled],
            "gates": {"MATCH_THRESHOLD": MATCH_THRESHOLD,
                      "ANCHOR_THRESHOLD": ANCHOR_THRESHOLD},
            "guards": {"country_span": GUARD_COUNTRY_SPAN,
                       "label_sim_max": GUARD_LABEL_SIM_MAX,
                       "overmerge_ratio_max": GUARD_OVERMERGE_RATIO_MAX},
            "families": fams,
            "arms": {k: {kk: vv for kk, vv in v.items() if kk != "events"}
                     for k, v in arms.items()},
            "absorption_events_variant": [
                e for e in arms["variant"]["events"] if e["rank_in_topic"] > 1],
            "total_seconds": round(time.monotonic() - t_start, 1),
        }
        result["verdict"] = verdict_block(result)
        OUT_DIR.mkdir(parents=True, exist_ok=True)
        suffix = "" if args.mode == "all" else f"-{args.mode}"
        (OUT_DIR / f"{STEM}{suffix}.json").write_text(
            json.dumps(result, indent=2, ensure_ascii=False, default=str), encoding="utf-8")
        print(json.dumps(result["verdict"], indent=2, ensure_ascii=False))
        print(f"[out] {OUT_DIR / (STEM + suffix + '.json')}")
        return 0
    finally:
        await conn.close()


async def validate_against_prod(conn, owner: dict[int, int], topics: list[Topic],
                                replay_snaps: list[str]) -> dict[str, Any]:
    """Harness fidelity: does the BASELINE arm reproduce prod's real assignments
    on the last replayed snapshot? Compares 'did this cluster attach to a
    PRE-EXISTING topic, and which one' against `dynamic_topic_members` (umbrella
    rows excluded — `build_umbrella_topics.py` writes those, not the projection)."""
    last = replay_snaps[-1]
    rows = await conn.fetch(
        """SELECT m.emergent_cluster_id AS cid, dt.id AS tid, dt.identity_key,
                  dt.first_seen
             FROM dynamic_topic_members m JOIN dynamic_topics dt ON dt.id = m.dynamic_topic_id
            WHERE m.snapshot_at = $1::timestamptz AND COALESCE(dt.is_umbrella,false) = false""",
        dt.datetime.fromisoformat(last))
    prod = {int(r["cid"]): r["identity_key"] for r in rows}
    agree = disagree = missing_sim = missing_prod = 0
    umbrella_side = 0
    examples = []
    for cid, key in prod.items():
        ti = owner.get(cid)
        if ti is None:
            missing_sim += 1
            continue
        sim_key = topics[ti].identity_key
        if sim_key == key:
            agree += 1
        else:
            disagree += 1
            if sim_key.startswith("umbrella:") or key.startswith("umbrella:"):
                umbrella_side += 1
            if len(examples) < 10:
                examples.append({"cluster": cid, "prod": key, "sim": sim_key})
    for cid, ti in owner.items():
        if cid not in prod:
            missing_prod += 1
    return {"snapshot": last, "prod_rows": len(prod), "agree": agree,
            "disagree": disagree, "disagree_involving_umbrella": umbrella_side,
            "in_prod_not_in_sim": missing_sim,
            "agreement_rate": round(agree / max(len(prod), 1), 4),
            "agreement_rate_excl_umbrella": round(
                agree / max(len(prod) - umbrella_side, 1), 4),
            "examples": examples}


def verdict_block(res: dict[str, Any]) -> dict[str, Any]:
    b, v = res["arms"]["baseline"], res["arms"]["variant"]
    fam_b = {f["family"]: f for f in b["families"]}
    fam_v = {f["family"]: f for f in v["families"]}
    core_snapshot = [nm for nm in fam_v
                     if nm in ("GQ-12 caspian", "berlin pride")]
    core_window = [nm for nm in fam_v
                   if nm in ("GQ-12 caspian [window]", "berlin pride [window]",
                             "GQ-05 [window]")]
    met_snapshot = sum(1 for nm in core_snapshot if fam_v[nm]["topics_holding"] <= 3)
    met = sum(1 for nm in core_window if fam_v[nm]["topics_holding"] <= 3)
    # a family already at <=3 in BASELINE is not a variant win — report both so the
    # bar cannot be read as met by a family the change never touched
    met_improved = sum(1 for nm in core_window
                       if fam_v[nm]["topics_holding"] <= 3
                       and fam_b[nm]["topics_holding"] > 3)
    kills: list[str] = []
    if v["false_absorption"]["flagged_784_class"] > 0:
        kills.append(f"GUARD 2 (false absorption): "
                     f"{v['false_absorption']['flagged_784_class']} new 784-class "
                     f"multi-absorptions (kill rule: >0)")
    om_b = (b.get("overmerge") or {}).get("demote_eligible")
    om_v = (v.get("overmerge") or {}).get("demote_eligible")
    ratio = None
    if om_b:
        ratio = round(om_v / om_b, 3)
        if ratio > GUARD_OVERMERGE_RATIO_MAX:
            kills.append(f"GUARD 3 (over-merge pressure): ratio {ratio} > "
                         f"{GUARD_OVERMERGE_RATIO_MAX}")
    return {
        "witness_core_window_at_or_below_3_topics_variant": met,
        "witness_core_window_improved_to_target_by_variant": met_improved,
        "witness_core_window_scored": len(core_window),
        "witness_core_snapshot_at_or_below_3_topics_variant": met_snapshot,
        "witness_core_snapshot_scored": len(core_snapshot),
        "family_topics_baseline": {k: fam_b[k]["topics_holding"] for k in fam_b},
        "family_topics_variant": {k: fam_v[k]["topics_holding"] for k in fam_v},
        "overmerge_demote_eligible": {"baseline": om_b, "variant": om_v, "ratio": ratio},
        "density_variant": {k: v["density"].get(k) for k in ("max", "p95", "mean")},
        "kills_fired": kills,
        "verdict": "NO-GO" if kills else (
            "GO" if met_improved >= 2 else "NO-GO (recall bar unmet)"),
    }


def parse_args() -> argparse.Namespace:
    ap = argparse.ArgumentParser(description="Simulate removing used_t from process_snapshot (read-only).")
    ap.add_argument("--window-start", default="2026-07-17",
                    help="replay snapshots >= this date; topic state hydrated as-of it")
    ap.add_argument("--mode", choices=("all", "labelled"), default="all",
                    help="'all' replays every snapshot in the window (faithful to prod, "
                         "attachment never reads labels); 'labelled' replays only "
                         "0%%-NULL-label snapshots (the T-A2 valid-night rule)")
    ap.add_argument("--gq05-pattern", default="espriella")
    ap.add_argument("--gq05-hours", type=int, default=168)
    ap.add_argument("--fresh-min", type=int, default=6)
    ap.add_argument("--fresh-want", type=int, default=4)
    ap.add_argument("--skip-overmerge", action="store_true")
    ap.add_argument("--validate", action="store_true",
                    help="compare the baseline arm's last-night assignments to prod")
    return ap.parse_args()


def main() -> None:
    raise SystemExit(asyncio.run(main_async(parse_args())))


if __name__ == "__main__":
    main()

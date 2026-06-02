#!/usr/bin/env python3
"""Emergent topic identity resolver (Phase 6, Sub-A', read-only).

Groups emergent_clusters across snapshots into stable topic identities by
centroid cosine similarity, and validates identity coherence from several
angles: sequential time-ordered linking vs global agglomerative
clustering, a threshold sweep, and signal-agreement diagnostics (does
label cosine / sample_signal_ids overlap agree with the centroid
decision?). No DB writes, no schema, no product change.

Run on the off-iCloud ML venv (asyncpg + numpy; e5/torch only used for
the optional label-cosine diagnostic):
  /Users/pedro/AtlasLocalWorker/mlvenv/bin/python -m scripts.emergent_topic_identity_resolver
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import statistics
from collections import defaultdict
from pathlib import Path
from typing import Any

import numpy as np

SWEEP = [0.70, 0.75, 0.80, 0.85, 0.90, 0.95]


# ---------- pure helpers (testable without DB) ----------

def _unit(v: np.ndarray) -> np.ndarray:
    n = np.linalg.norm(v)
    return v / n if n > 0 else v


def cosine(a: np.ndarray, b: np.ndarray) -> float:
    return float(np.dot(_unit(a), _unit(b)))


def jaccard(a: list[int], b: list[int]) -> float:
    sa, sb = set(a or []), set(b or [])
    if not sa and not sb:
        return 0.0
    inter = len(sa & sb)
    union = len(sa | sb)
    return inter / union if union else 0.0


def sequential_link(clusters: list[dict[str, Any]], threshold: float) -> list[dict[str, Any]]:
    """Time-ordered greedy 1-to-1 linking into identities.

    `clusters` must be sorted by snapshot_at. Each identity keeps a
    running centroid (mean of member centroids) for matching.
    """
    identities: list[dict[str, Any]] = []
    by_snap: dict[Any, list[dict[str, Any]]] = defaultdict(list)
    for c in clusters:
        by_snap[c["snapshot_at"]].append(c)

    for snap in sorted(by_snap):
        snap_clusters = by_snap[snap]
        # score every (cluster, identity) pair, then greedily assign best first
        pairs = []
        for ci, c in enumerate(snap_clusters):
            for ii, ident in enumerate(identities):
                s = cosine(c["centroid"], ident["centroid"])
                if s >= threshold:
                    pairs.append((s, ci, ii))
        pairs.sort(reverse=True)
        used_c: set[int] = set()
        used_i: set[int] = set()
        for s, ci, ii in pairs:
            if ci in used_c or ii in used_i:
                continue
            used_c.add(ci)
            used_i.add(ii)
            _attach(identities[ii], snap_clusters[ci], snap)
        for ci, c in enumerate(snap_clusters):
            if ci not in used_c:
                identities.append(_new_identity(c, snap))
    return identities


def _new_identity(c: dict[str, Any], snap: Any) -> dict[str, Any]:
    return {
        "members": [c],
        "centroid": np.array(c["centroid"], dtype=np.float64),
        "first_seen": snap,
        "last_seen": snap,
        "snapshots": {snap},
        "representative_label": c.get("label"),
    }


def _attach(ident: dict[str, Any], c: dict[str, Any], snap: Any) -> None:
    ident["members"].append(c)
    mat = np.vstack([m["centroid"] for m in ident["members"]])
    ident["centroid"] = mat.mean(axis=0)
    ident["last_seen"] = max(ident["last_seen"], snap)
    ident["first_seen"] = min(ident["first_seen"], snap)
    ident["snapshots"].add(snap)


def global_agglomerative(clusters: list[dict[str, Any]], threshold: float) -> list[list[int]]:
    """Single-linkage agglomerative over centroids by cosine >= threshold.

    Returns groups as lists of cluster indices. Simple union-find.
    """
    n = len(clusters)
    parent = list(range(n))

    def find(x: int) -> int:
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(a: int, b: int) -> None:
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[rb] = ra

    cents = [np.array(c["centroid"], dtype=np.float64) for c in clusters]
    for i in range(n):
        for j in range(i + 1, n):
            if cosine(cents[i], cents[j]) >= threshold:
                union(i, j)
    groups: dict[int, list[int]] = defaultdict(list)
    for i in range(n):
        groups[find(i)].append(i)
    return list(groups.values())


def identity_stats(identities: list[dict[str, Any]]) -> dict[str, Any]:
    lifespans = [len(i["snapshots"]) for i in identities]
    persistent = [i for i in identities if len(i["snapshots"]) >= 2]
    singletons = [i for i in identities if len(i["members"]) == 1]
    return {
        "n_identities": len(identities),
        "n_persistent": len(persistent),
        "n_singletons": len(singletons),
        "mean_lifespan": round(statistics.mean(lifespans), 3) if lifespans else 0.0,
        "max_lifespan": max(lifespans) if lifespans else 0,
    }


def intra_identity_variance(identities: list[dict[str, Any]]) -> float | None:
    """Mean within-identity cosine spread (1 - mean pairwise cosine) over
    multi-member identities. Lower = tighter/more coherent identities."""
    spreads = []
    for ident in identities:
        cents = [np.array(m["centroid"], dtype=np.float64) for m in ident["members"]]
        if len(cents) < 2:
            continue
        sims = [
            cosine(cents[i], cents[j])
            for i in range(len(cents))
            for j in range(i + 1, len(cents))
        ]
        spreads.append(1.0 - statistics.mean(sims))
    return round(statistics.mean(spreads), 4) if spreads else None


# ---------- DB load ----------

async def load_clusters() -> list[dict[str, Any]]:
    import asyncpg

    db = os.environ.get("DATABASE_URL") or os.environ.get("SUPABASE_DB_URL")
    if not db:
        raise SystemExit("DATABASE_URL required")
    conn = await asyncpg.connect(db)
    try:
        rows = await conn.fetch(
            "SELECT id, snapshot_at, cluster_id, label, description, n_signals, "
            "cohesion, top_country_codes, sample_signal_ids, centroid_vec "
            "FROM emergent_clusters ORDER BY snapshot_at, cluster_id"
        )
    finally:
        await conn.close()
    out = []
    skipped = 0
    for r in rows:
        cv = r["centroid_vec"]
        if not cv:
            skipped += 1
            continue
        out.append(
            {
                "id": int(r["id"]),
                "snapshot_at": r["snapshot_at"].isoformat(),
                "cluster_id": r["cluster_id"],
                "label": r["label"],
                "description": r["description"],
                "n_signals": int(r["n_signals"] or 0),
                "cohesion": float(r["cohesion"] or 0.0),
                "top_country_codes": list(r["top_country_codes"] or []),
                "sample_signal_ids": [int(x) for x in (r["sample_signal_ids"] or [])],
                "centroid": np.array(cv, dtype=np.float64),
            }
        )
    return out, skipped  # type: ignore[return-value]


# ---------- diagnostics ----------

def label_overlap_agreement(clusters: list[dict[str, Any]], threshold: float, label_emb: dict[int, np.ndarray] | None) -> dict[str, Any]:
    """For each centroid-accepted within-snapshot-adjacent pair, measure
    whether label cosine and sample-id Jaccard agree (>= a softer bar)."""
    idents = sequential_link(clusters, threshold)
    matched_pairs = []  # (a,b) cluster dicts that landed in same identity, consecutive members
    for ident in idents:
        members = ident["members"]
        for i in range(len(members) - 1):
            matched_pairs.append((members[i], members[i + 1]))
    if not matched_pairs:
        return {"matched_pairs": 0}
    label_sims, jac_sims = [], []
    for a, b in matched_pairs:
        jac_sims.append(jaccard(a["sample_signal_ids"], b["sample_signal_ids"]))
        if label_emb is not None:
            la, lb = label_emb.get(a["id"]), label_emb.get(b["id"])
            if la is not None and lb is not None:
                label_sims.append(cosine(la, lb))
    return {
        "matched_pairs": len(matched_pairs),
        "label_cosine_mean": round(statistics.mean(label_sims), 4) if label_sims else None,
        "label_agree_rate_ge_0.8": round(sum(1 for s in label_sims if s >= 0.8) / len(label_sims), 4) if label_sims else None,
        "jaccard_mean": round(statistics.mean(jac_sims), 4) if jac_sims else None,
        "jaccard_nonzero_rate": round(sum(1 for s in jac_sims if s > 0) / len(jac_sims), 4) if jac_sims else None,
    }


def _maybe_embed_labels(clusters: list[dict[str, Any]]) -> dict[int, np.ndarray] | None:
    try:
        from scripts.score_assignments_gate import _build_embedder
        embed, _ = _build_embedder("intfloat/multilingual-e5-base")
        texts = [f"query: {(c.get('label') or '').strip()}" for c in clusters]
        embs = embed(texts)
        return {c["id"]: embs[i] for i, c in enumerate(clusters)}
    except Exception as exc:  # diagnostic only; never fatal
        print(f"label embedding skipped: {exc}")
        return None


# ---------- report ----------

def build_report(clusters: list[dict[str, Any]], skipped: int, label_emb) -> dict[str, Any]:
    snapshots = sorted({c["snapshot_at"] for c in clusters})
    if len(snapshots) < 2:
        raise SystemExit("need >= 2 snapshots of emergent_clusters to resolve identity")

    sweep_rows = []
    best = None
    for thr in SWEEP:
        idents = sequential_link(clusters, thr)
        glob = global_agglomerative(clusters, thr)
        st = identity_stats(idents)
        st["threshold"] = thr
        st["global_n_groups"] = len(glob)
        st["intra_identity_spread"] = intra_identity_variance(idents)
        st.update({"signal_diag": label_overlap_agreement(clusters, thr, label_emb)})
        sweep_rows.append(st)

    # knee: the recurring-topic core (n_persistent) is threshold-robust, so the
    # knee is the largest threshold that still holds the max persistent count
    # while singletons have not yet overtaken it (over-fragmentation guard).
    max_persist = max((r["n_persistent"] for r in sweep_rows), default=0)
    knee_candidates = [
        r for r in sweep_rows
        if r["n_persistent"] == max_persist and r["n_singletons"] <= r["n_persistent"]
    ]
    knee = max(knee_candidates, key=lambda r: r["threshold"])["threshold"] if knee_candidates else None

    # timelines at the knee (or 0.85 default)
    chosen = knee or 0.85
    idents = sequential_link(clusters, chosen)
    idents.sort(key=lambda i: (len(i["snapshots"]), i["first_seen"]), reverse=True)
    timelines = [
        {
            "representative_label": i["representative_label"],
            "first_seen": i["first_seen"],
            "last_seen": i["last_seen"],
            "n_snapshots": len(i["snapshots"]),
            "n_member_clusters": len(i["members"]),
            "agg_n_signals": sum(m["n_signals"] for m in i["members"]),
            "member_labels": [m["label"] for m in i["members"]],
        }
        for i in idents
    ]

    return {
        "schema_version": "atlas-emergent-topic-identity-v1",
        "n_clusters": len(clusters),
        "n_snapshots": len(snapshots),
        "skipped_null_centroid": skipped,
        "threshold_sweep": sweep_rows,
        "knee_threshold": knee,
        "chosen_threshold": chosen,
        "n_identities_at_chosen": len(idents),
        "static_atlas_topics_note": "compare n_identities vs the static atlas_topics count to gauge coverage gap",
        "identity_timelines": timelines,
    }


async def run(args: argparse.Namespace) -> dict[str, Any]:
    clusters, skipped = await load_clusters()
    label_emb = None if args.no_label_diag else _maybe_embed_labels(clusters)
    return build_report(clusters, skipped, label_emb)


def parse_args() -> argparse.Namespace:
    ap = argparse.ArgumentParser(description="Emergent topic identity resolver (read-only).")
    ap.add_argument("--output", required=True, type=Path)
    ap.add_argument("--no-label-diag", action="store_true", help="skip e5 label-cosine diagnostic")
    return ap.parse_args()


def main() -> None:
    args = parse_args()
    report = asyncio.run(run(args))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, ensure_ascii=False, default=str) + "\n", encoding="utf-8")
    summary = {k: report[k] for k in ("n_clusters", "n_snapshots", "knee_threshold", "chosen_threshold", "n_identities_at_chosen")}
    print(json.dumps(summary, indent=2))
    print("\nthreshold sweep:")
    for r in report["threshold_sweep"]:
        print(f"  thr={r['threshold']} ident={r['n_identities']} persist={r['n_persistent']} singletons={r['n_singletons']} global={r['global_n_groups']} spread={r['intra_identity_spread']} jac_nz={r['signal_diag'].get('jaccard_nonzero_rate')} label_mean={r['signal_diag'].get('label_cosine_mean')}")


if __name__ == "__main__":
    main()

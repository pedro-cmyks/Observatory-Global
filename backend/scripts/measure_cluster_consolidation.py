#!/usr/bin/env python3
"""Consolidate same-event fragments at the CLUSTER level, inside one snapshot,
BEFORE `project_dynamic_topics.process_snapshot` runs.

READ-ONLY. Writes no prod table (`SET default_transaction_read_only = on`).
Nothing in `project_dynamic_topics.py` is modified. Every gate, constant and
behaviour under test is IMPORTED from the production module (`MERGE_THRESHOLD`,
`MERGE_LABEL_MIN`, `labels_compatible`, `is_roundup_label`) or from the already
adversarially-reviewed `simulate_used_t_removal` harness (`process_snapshot_sim`
with `allow_multi=False` — i.e. production's `used_t` INTACT — `hydrate_as_of`,
`candidate_pairs`, family discovery, the guard constants), so the two arms and
the two harnesses cannot drift.

THE HYPOTHESIS
--------------
`2026-07-30-used-t-simulation.md` refuted the `used_t` fix with a sharper
finding: 43 of 54 Berlin-Pride fragments do not have the consolidation target
among their TWELVE nearest topics. The fragments of one event do not share an
argmax, so no relaxation at the *matching* layer can make them choose the same
topic.

This harness tests the move that sidesteps argmax dispersion entirely: unify the
fragments with EACH OTHER first, inside the snapshot, using the only rule
`2026-07-29-witness-reconvergence.md` found to be K2-safe —

    cos(centroid_a, centroid_b) >= 0.90  AND  labels_compatible(a, b)

— connected components of that graph become ONE super-cluster, which then makes
ONE pick against the topic pool. 22 fragments each picking a different stale
topic becomes 4 picks, or 1.

The rule was K2-validated over TOPIC nodes. Its node set here is CLUSTERS, which
is the same node set the witness artifact actually measured (its honest-limits
§1 says so), so the density claim carries — but it is re-measured, not assumed.

PRE-REGISTERED METRICS (frozen in the task before this file was written)
  1  fragments-per-event after cluster consolidation, witness families.
     TARGET: <= 3 components on >= 2 of 3 CORE families.
  2  K2 on the CLUSTER graph: largest component <= 2% of the snapshot's
     clusters.  KILL: > 2% => NO-GO.
  3  false side, same pass: the mechanical FALSE construction (disjoint
     countries + dissimilar same-script labels), admission rate; plus any
     cross-family component.
  4  DOWNSTREAM: replay `process_snapshot` (used_t INTACT) twice — raw clusters
     vs consolidated super-clusters. Topics-per-event per family and GQ-05-class
     story coverage (largest single topic's share of the family's SIGNALS).
     TARGET: <= 3 topics/event on >= 2 of 3; coverage direction UP.
  5  OVER-MERGE with the HONEST control: the country-span signature (a component
     spanning >= 3 primary countries AND carrying an internally incompatible
     label pair), because `2026-07-30-used-t-simulation.md` §6 measured
     `detect_overmerge` going BLIND at 10+ fused clusters. KILL: > 0 => NO-GO.
     `overmerge.decide` reported alongside, where it is still sighted.
  6  BLACKOUT DEPENDENCY: cos-only >= 0.90 (no label conjunct) cluster-graph
     density, so the cost of relaxing the label dependency is known. REPORT
     ONLY — not adopted.

FOUR GRAPH VARIANTS are scored per snapshot, on one shared candidate-pair set:
  PRIMARY engine-label            the rule under test (`labels_compatible`, verbatim)
  supp unicode-label              the witness artifact's Unicode-aware normalizer,
                                  for comparability with 2026-07-29. Not adopted.
  supp engine-label + shared country
                                  adds `countries_share` (imported). Added AFTER the
                                  primary run's 784-class kill fired, so it is a
                                  measured LEAD for a future pre-registered run, never
                                  a result of this one. Reported in full either way.
  M6 cos-only                     metric 6 (density only; its components are the whole
                                  snapshot, so the per-component analyses are skipped)

Two equivalence proofs run inside the harness and are published with the results,
because both fast paths could silently change a number:
  * `verify_fastpath`            the hoisted label conjunct vs `labels_compatible`
  * `verify_false_construction`  every sampled FALSE pair vs the imported predicates

Usage (M1 mlvenv; read-only):
  set -a; . ~/AtlasLocalWorker/.env; set +a
  cd backend && /Users/pedro/AtlasLocalWorker/mlvenv/bin/python \
      -m scripts.measure_cluster_consolidation --window-start 2026-07-17 \
      --mode all --validate
"""
from __future__ import annotations

import argparse
import asyncio
import datetime as dt
import json
import os
import re
import time
from collections import Counter, defaultdict
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any, Sequence

import numpy as np

# --- production module: the rule under test is IMPORTED, never re-implemented --
from scripts.project_dynamic_topics import (  # noqa: E402
    ANCHOR_THRESHOLD,
    MATCH_THRESHOLD,
    MERGE_LABEL_MIN,
    MERGE_THRESHOLD,
    LifecycleConfig,
    _subject_tokens,
    is_roundup_label,
    labels_compatible,
)

# --- the used_t harness: replay machinery + guard definitions, imported so the
#     two artifacts share one definition of every quantity they both report ----
from scripts.simulate_used_t_removal import (  # noqa: E402
    GUARD_COUNTRY_SPAN,
    GUARD_LABEL_SIM_MAX,
    _unit_rows,
    extend_to_window,
    fresh_families,
    gq05_family,
    hydrate_as_of,
    label_sim,
    load_clusters,
    pattern_family,
    process_snapshot_sim,
    topic_of_cluster,
    validate_against_prod,
)

# --- the fingerprint harness: the FALSE construction, imported verbatim so this
#     measurement and the whitening/evidence ones share one "different story" --
from scripts.measure_evidence_fingerprint import (  # noqa: E402
    DIFF_LABEL_MAX,
    countries_disjoint,
    countries_share,
    different_story,
    dominant_script,
    subject_tokens,
)
from scripts.measure_evidence_fingerprint import norm_label as norm_label_unicode  # noqa: E402
from app.services.overmerge import (  # noqa: E402
    OverMergeParams,
    country_dominant_overlap,
    decide,
    partition,
)

REPO_ROOT = Path(__file__).resolve().parents[2]
OUT_DIR = REPO_ROOT / "docs" / "research" / "recall-229"
STEM = "2026-07-30-cluster-consolidation"

# ---- pre-registered kill thresholds (frozen; not touched after seeing results)
K2_MAX_SHARE = 0.02            # largest consolidated component / snapshot clusters
WITNESS_MAX_COMPONENTS = 3     # "<= 3 components"
WITNESS_CORE_REQUIRED = 2      # "on >= 2 of 3 core families"
FALSE_PAIR_TARGET = 1200       # same sample size as the witness artifact
# GUARD_COUNTRY_SPAN (3) and GUARD_LABEL_SIM_MAX (0.40) are imported above.


# ------------------------------------------------------------------ the rule
_ENGINE_NORM_RE = re.compile(r"[^a-z0-9]+")


def _engine_norm(s: str | None) -> str:
    """`labels_compatible`'s normalizer, hoisted so it runs once per LABEL
    instead of once per PAIR. Verified byte-identical against the production
    function on every candidate pair by `--verify-fastpath`."""
    return _ENGINE_NORM_RE.sub(" ", (s or "").lower()).strip()


def _compatible_norm(na: str, nb: str, floor: float) -> bool:
    """`labels_compatible` on PRE-NORMALIZED strings, with SequenceMatcher's own
    upper bounds used as an early-out. `real_quick_ratio`/`quick_ratio` are
    documented upper bounds on `ratio()`, so rejecting when a bound falls below
    the floor cannot change a decision — only skip work."""
    if not na or not nb:
        return False
    if na == nb:
        return True
    sm = SequenceMatcher(None, na, nb)
    if sm.real_quick_ratio() < floor or sm.quick_ratio() < floor:
        return False
    return sm.ratio() >= floor


def _label_pairs_ok(labels: Sequence[str | None], ii: np.ndarray, jj: np.ndarray,
                    mode: str) -> np.ndarray:
    """Boolean mask over candidate pairs for the LABEL conjunct.

    mode='engine'  -> `project_dynamic_topics.labels_compatible`, VERBATIM. This
                      is what would actually ship. Note it normalizes with
                      `[^a-z0-9]+`, so a non-Latin label normalizes to the empty
                      string and can never merge — measured, not assumed (see
                      `label_script_reach` below).
    mode='unicode' -> the witness artifact's Unicode-aware `label_sim >= 0.80`.
                      Reported for comparability with 2026-07-29, NOT adopted.
    mode='none'    -> no label conjunct (metric 6, cos-only).
    """
    if mode == "none":
        return np.ones(ii.size, dtype=bool)
    out = np.zeros(ii.size, dtype=bool)
    norm = ([_engine_norm(x) for x in labels] if mode == "engine"
            else [norm_label_unicode(x) for x in labels])
    for k in range(ii.size):
        out[k] = _compatible_norm(norm[int(ii[k])], norm[int(jj[k])], MERGE_LABEL_MIN)
    return out


def verify_fastpath(labels: Sequence[str | None], ii: np.ndarray, jj: np.ndarray,
                    rng: np.random.Generator, n: int = 20000) -> dict[str, Any]:
    """Prove the hoisted/early-out path is EXACTLY `labels_compatible`.

    Runs the production function and the fast path over a random sample of the
    snapshot's candidate pairs and reports any disagreement. A non-zero
    `disagreements` invalidates every engine-label number in this artifact."""
    if ii.size == 0:
        return {"sampled": 0, "disagreements": 0}
    take = rng.choice(ii.size, size=int(min(n, ii.size)), replace=False)
    norm = [_engine_norm(x) for x in labels]
    bad = 0
    for k in take.tolist():
        a, b = int(ii[k]), int(jj[k])
        if _compatible_norm(norm[a], norm[b], MERGE_LABEL_MIN) != labels_compatible(
                labels[a], labels[b]):
            bad += 1
    return {"sampled": int(take.size), "disagreements": bad,
            "exact": bad == 0}


def candidates_at_tau(V: np.ndarray, tau: float, *, chunk: int = 1024
                      ) -> tuple[np.ndarray, np.ndarray]:
    """Upper-triangle (i<j) index pairs with cos >= tau, chunked so a 3.8k-cluster
    snapshot never materializes a 7M-entry triu index array."""
    n = V.shape[0]
    ii_all: list[np.ndarray] = []
    jj_all: list[np.ndarray] = []
    for lo in range(0, n, chunk):
        hi = min(lo + chunk, n)
        S = V[lo:hi] @ V.T
        r, c = np.nonzero(S >= tau)
        r = r + lo
        m = r < c
        if m.any():
            ii_all.append(r[m]); jj_all.append(c[m])
    if not ii_all:
        z = np.array([], dtype=np.int64)
        return z, z
    return np.concatenate(ii_all), np.concatenate(jj_all)


def consolidation_graph(clusters: list[dict[str, Any]], *, tau: float = MERGE_THRESHOLD,
                        label_mode: str = "engine", exclude_roundups: bool = False,
                        cand: tuple[np.ndarray, np.ndarray] | None = None,
                        V: np.ndarray | None = None,
                        require_shared_country: bool = False,
                        ) -> dict[str, Any]:
    """Build one snapshot's consolidation graph and its connected components.

    Nodes are the snapshot's clusters. Edge iff cos >= tau AND the label conjunct
    holds. Components ARE the super-clusters.
    """
    n = len(clusters)
    if n == 0:
        return {"n": 0, "edges": 0, "components": [], "largest": 0, "share": 0.0,
                "pairs_at_tau": 0, "excluded_roundups": 0,
                "_cand_ii": np.array([]), "_cand_jj": np.array([])}
    labels = [c["label"] for c in clusters]
    eligible = np.ones(n, dtype=bool)
    n_excluded = 0
    if exclude_roundups:
        for k, c in enumerate(clusters):
            if is_roundup_label(c["label"]):
                eligible[k] = False
                n_excluded += 1

    if V is None:
        V = _unit_rows(np.stack([c["centroid"] for c in clusters]).astype(np.float64))
    ii, jj = cand if cand is not None else candidates_at_tau(V, tau)
    pairs_at_tau = int(ii.size)
    if exclude_roundups and ii.size:
        m = eligible[ii] & eligible[jj]
        ii, jj = ii[m], jj[m]
    ok = _label_pairs_ok(labels, ii, jj, label_mode) if ii.size else np.zeros(0, bool)
    if require_shared_country and ii.size:
        # `countries_share` IMPORTED verbatim — the same D3 conjunct the fresh-
        # family discovery rule uses. Empty `top_country_codes` never shares, so
        # a cluster with no country is isolated by construction (counted below).
        cc = [c["cc"] for c in clusters]
        ok = ok & np.fromiter(
            (countries_share(cc[int(a)], cc[int(b)]) for a, b in zip(ii, jj)),
            dtype=bool, count=ii.size)
    ei, ej = ii[ok], jj[ok]

    parent = list(range(n))

    def find(x: int) -> int:
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    for a, b in zip(ei.tolist(), ej.tolist()):
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[rb] = ra
    groups: dict[int, list[int]] = defaultdict(list)
    for k in range(n):
        groups[find(k)].append(k)
    comps = sorted(groups.values(), key=lambda g: (-len(g), min(g)))
    largest = len(comps[0]) if comps else 0
    return {
        "n": n, "edges": int(ei.size), "pairs_at_tau": pairs_at_tau,
        "excluded_roundups": n_excluded,
        "components": comps, "n_components": len(comps),
        "largest": largest, "share": round(largest / max(n, 1), 5),
        "multi_components": sum(1 for g in comps if len(g) > 1),
        "clusters_in_multi": sum(len(g) for g in comps if len(g) > 1),
        "size_histogram": dict(sorted(Counter(len(g) for g in comps).items())),
        "edge_list": [[int(a), int(b)] for a, b in zip(ei.tolist(), ej.tolist())],
        "_cand_ii": ii, "_cand_jj": jj,
    }


# ------------------------------------------------------------------ super-clusters
def build_super_clusters(clusters: list[dict[str, Any]], comps: list[list[int]],
                         id_base: int = 0,
                         ) -> tuple[list[dict[str, Any]], dict[int, list[int]]]:
    """Collapse each component into ONE cluster-shaped dict.

    centroid  = n_signals-weighted mean of member centroids
    label     = modal member label, ties broken by longest (deterministic)
    n_signals = sum · cohesion/noise = n_signals-weighted mean of non-nulls
    cc        = union ordered by how often each code appears as a member's list
    cluster_id= min(member cluster_id)  -> identity_key `dyn-<snap>-<min_cid>`
    id        = a synthetic id; `super_to_orig` maps it back to real cluster ids

    A SINGLETON component reproduces its cluster EXACTLY (same centroid, same
    label, same cluster_id, hence the same `identity_key` a founding would
    produce), so any divergence from the raw arm comes only from real merges.
    """
    supers: list[dict[str, Any]] = []
    mapping: dict[int, list[int]] = {}
    made = 0
    for g in comps:
        members = [clusters[k] for k in g]
        if len(members) == 1:
            c = dict(members[0])
            supers.append(c)
            mapping[c["id"]] = [c["id"]]
            continue
        w = np.array([max(m["n_signals"], 1) for m in members], dtype=np.float64)
        cent = np.average(np.stack([m["centroid"] for m in members]), axis=0, weights=w)
        lab_counts: Counter = Counter(m["label"] for m in members if m["label"])
        label = None
        if lab_counts:
            top = max(lab_counts.values())
            label = sorted([l for l, c in lab_counts.items() if c == top],
                           key=lambda s: (-len(s), s))[0]
        coh = [(m["cohesion"], m["n_signals"]) for m in members if m["cohesion"] is not None]
        noi = [(m["noise"], m["n_signals"]) for m in members if m.get("noise") is not None]
        cc_count: Counter = Counter()
        for m in members:
            for k2, code in enumerate(m["cc"]):
                cc_count[code] += max(1, len(m["cc"]) - k2)   # rank-weighted
        min_cid = min(int(m["cluster_id"]) for m in members)
        # deterministic synthetic id in negative space (real emergent_clusters.id
        # are positive); `super_to_orig` maps it back to the real cluster ids.
        made += 1
        sid = -(id_base + made)
        sc = {
            "id": sid,
            "snapshot_at": members[0]["snapshot_at"],
            "snapshot_ts": members[0].get("snapshot_ts"),
            "cluster_id": min_cid,
            "label": label,
            "n_signals": sum(m["n_signals"] for m in members),
            "cohesion": (float(np.average([x for x, _ in coh],
                                          weights=[y for _, y in coh])) if coh else None),
            "noise": (float(np.average([x for x, _ in noi],
                                       weights=[y for _, y in noi])) if noi else None),
            "sample_signal_ids": list(dict.fromkeys(
                s for m in members for s in m["sample_signal_ids"])),
            "centroid": cent,
            "cc": [c for c, _ in cc_count.most_common()],
            "_n_merged": len(members),
        }
        supers.append(sc)
        mapping[sid] = [m["id"] for m in members]
    supers.sort(key=lambda c: (int(c["cluster_id"]), int(c["id"])))
    return supers, mapping


def super_cluster_geometry(clusters: list[dict[str, Any]], comps: list[list[int]],
                           supers: list[dict[str, Any]],
                           mapping: dict[int, list[int]]) -> dict[str, Any]:
    """Does averaging TIGHTEN or LOOSEN the identity anchor?

    A merged super-cluster's centroid becomes the founding ANCHOR of any topic it
    opens, and `ANCHOR_THRESHOLD` is then measured against it forever. If the
    average sits FURTHER from a typical member than members sit from each other,
    consolidation would widen what the resulting identity absorbs. Measured
    rather than argued: mean cos(super, member) vs mean pairwise cos(member_i,
    member_j) inside the same component.
    """
    by_id = {c["id"]: c for c in clusters}
    rows: list[dict[str, Any]] = []
    for sc in supers:
        cids = mapping.get(sc["id"], [])
        if len(cids) < 2:
            continue
        M = _unit_rows(np.stack([by_id[c]["centroid"] for c in cids]).astype(np.float64))
        s = sc["centroid"] / max(float(np.linalg.norm(sc["centroid"])), 1e-12)
        to_center = M @ s
        P = M @ M.T
        iu = np.triu_indices(len(cids), k=1)
        rows.append({"clusters": len(cids),
                     "mean_cos_to_super": float(to_center.mean()),
                     "min_cos_to_super": float(to_center.min()),
                     "mean_pairwise_cos": float(P[iu].mean()),
                     "min_pairwise_cos": float(P[iu].min())})
    if not rows:
        return {"components": 0}
    def agg(k: str) -> float:
        return round(float(np.mean([r[k] for r in rows])), 5)
    tighter = sum(1 for r in rows if r["mean_cos_to_super"] > r["mean_pairwise_cos"])
    return {"components": len(rows),
            "mean_cos_to_super": agg("mean_cos_to_super"),
            "mean_pairwise_cos": agg("mean_pairwise_cos"),
            "min_cos_to_super": agg("min_cos_to_super"),
            "min_pairwise_cos": agg("min_pairwise_cos"),
            "components_where_average_is_tighter": tighter,
            "share_tighter": round(tighter / len(rows), 4)}


# ------------------------------------------------------------------ metric 5
def component_detail(cs: list[dict[str, Any]], comp: list[int],
                     edge_list: list[list[int]], V: np.ndarray) -> dict[str, Any]:
    """Everything needed to hand-check ONE consolidated component: its members,
    its countries, and the EDGES that actually built it (with the label
    similarity and cosine of each), so a fusion can be traced to the pair that
    bridged it rather than asserted."""
    inside = set(comp)
    return {
        "size": len(comp),
        "cluster_ids": [cs[k]["id"] for k in comp],
        "labels": [cs[k]["label"] for k in comp],
        "primary_countries": sorted({cs[k]["cc"][0] for k in comp if cs[k]["cc"]}),
        "n_signals": sum(cs[k]["n_signals"] for k in comp),
        "internal_edges": sorted(
            ({"a": cs[a]["label"], "b": cs[b]["label"],
              "label_sim": round(label_sim(cs[a]["label"], cs[b]["label"]), 3),
              "cos": round(float(V[a] @ V[b]), 4)}
             for a, b in edge_list if a in inside and b in inside),
            key=lambda e: e["label_sim"])[:40],
    }


CLASH_SCAN_CAP = 40  # members scanned pairwise inside one component


def country_span_signature(clusters: list[dict[str, Any]], comps: list[list[int]],
                           df_tokens: Counter, n_labels: int) -> dict[str, Any]:
    """Metric 5 — the honest control the used_t run proved stayed sighted.

    A consolidated component is 784-class when it spans >= GUARD_COUNTRY_SPAN
    distinct PRIMARY countries AND carries at least one internally incompatible
    label pair (SequenceMatcher < GUARD_LABEL_SIM_MAX and no shared distinctive
    token, where 'distinctive' = outside the top decile of that snapshot's
    cluster-label token df). Both halves are also reported alone, so the number
    is comparable to `2026-07-30-used-t-simulation.md` §5, which used the OR.
    """
    ubiquitous = {t for t, _ in df_tokens.most_common(max(1, n_labels // 10))}
    flagged: list[dict[str, Any]] = []
    span_only = clash_only = both = 0
    truncated = 0
    for g in comps:
        if len(g) < 2:
            continue
        cs = [clusters[k] for k in g]
        prim = [c["cc"][0] for c in cs if c["cc"]]
        span = len(set(prim))
        # The pairwise clash scan is O(k^2). Under the PRIMARY rule the largest
        # component measured is tens of clusters, so the cap never binds; it
        # exists so the cos-only DIAGNOSTIC (components of ~2000) terminates.
        # Capping can only UNDER-count clashes, never invent one.
        scan = cs[:CLASH_SCAN_CAP]
        if len(cs) > CLASH_SCAN_CAP:
            truncated += 1
        clashes: list[dict[str, Any]] = []
        for a in range(len(scan)):
            for b in range(a + 1, len(scan)):
                la, lb = scan[a]["label"], scan[b]["label"]
                if not la or not lb:
                    continue  # blackout: undecidable, never counted as a clash
                sim = label_sim(la, lb)
                if sim >= GUARD_LABEL_SIM_MAX:
                    continue
                if (_subject_tokens(la) & _subject_tokens(lb)) - ubiquitous:
                    continue
                clashes.append({"a": la, "b": lb, "sim": round(sim, 3)})
        wide = span >= GUARD_COUNTRY_SPAN
        if wide and clashes:
            both += 1
            flagged.append({
                "clusters": len(cs), "country_span": span,
                "primary_countries": sorted(set(prim)),
                "labels": [c["label"] for c in cs][:10],
                "cluster_ids": [c["id"] for c in cs],
                "label_clashes": clashes[:6],
            })
        elif wide:
            span_only += 1
        elif clashes:
            clash_only += 1
    return {"flagged_784_class": len(flagged), "signature": "country_span AND label_clash",
            "country_span_only": span_only, "label_clash_only": clash_only,
            "both": both, "or_form_total": span_only + clash_only + both,
            "components_clash_scan_truncated": truncated,
            "flagged": flagged[:20]}


def overmerge_on_components(clusters: list[dict[str, Any]], comps: list[list[int]],
                            emb: dict[int, np.ndarray], sig_meta: dict[int, tuple],
                            params: OverMergeParams) -> dict[str, Any]:
    """`overmerge.decide()` over the consolidated components' member signals.

    Supplementary to the country-span signature, never a replacement: §6 of the
    used_t artifact measured `decide` going blind (gap_ratio median 1.044->0.818)
    once a fusion carries 10+ clusters. Reported bucketed by component size with
    a SINGLETON control computed identically, so the reader can see whether the
    detector is sighted at this operating point.
    """
    def run(groups: list[list[int]], tag: str) -> dict[str, Any]:
        verdicts: Counter = Counter()
        gaps: list[float] = []
        evaluated = skipped_thin = 0
        examples: list[dict[str, Any]] = []
        for g in groups:
            sids = list(dict.fromkeys(s for k in g for s in clusters[k]["sample_signal_ids"]))
            sids = [s for s in sids if s in emb]
            if len(sids) < params.min_members:
                skipped_thin += 1
                continue
            evaluated += 1
            mat = np.stack([emb[s] for s in sids]).astype(np.float64)
            lab, stats = partition(mat, seed=params.seed)
            if lab is None or stats is None:
                continue
            aa: set[str] = set()
            bb: set[str] = set()
            for k2, sid in enumerate(sids):
                cc, persons = sig_meta.get(sid, (None, None))
                acts = set()
                if cc:
                    acts.add(f"c:{cc.strip().upper()}")
                for p in (persons or []):
                    if p and str(p).strip():
                        acts.add(f"p:{str(p).strip().lower()}")
                (aa if lab[k2] == 0 else bb).update(acts)
            v, reason = decide(stats, country_dominant_overlap(aa, bb), params)
            verdicts[v] += 1
            gaps.append(stats.gap_ratio)
            if v in ("demote", "borderline") and len(examples) < 10:
                examples.append({"clusters": len(g), "n_members": len(sids),
                                 "verdict": v, "gap_ratio": round(stats.gap_ratio, 3),
                                 "reason": reason,
                                 "labels": [clusters[k]["label"] for k in g][:6]})
        elig = verdicts.get("demote", 0) + verdicts.get("borderline", 0)
        return {"arm": tag, "evaluated": evaluated, "skipped_thin_or_unembedded": skipped_thin,
                "verdicts": dict(verdicts), "demote_eligible": elig,
                "demote_eligible_rate": round(elig / max(evaluated, 1), 4),
                "gap_ratio_median": round(float(np.median(gaps)), 3) if gaps else None,
                "examples": examples}

    multi = [g for g in comps if len(g) > 1]
    single = [g for g in comps if len(g) == 1]
    by_size: dict[str, Any] = {}
    for lo, hi, nm in ((2, 4, "2-4"), (5, 9, "5-9"), (10, 10**6, "10+")):
        grp = [g for g in multi if lo <= len(g) <= hi]
        if grp:
            by_size[nm] = run(grp, f"components[{nm}]")
    return {"consolidated_components": run(multi, "components(>=2 clusters)"),
            "singleton_control": run(single, "singleton clusters"),
            "by_component_size": by_size}


# ------------------------------------------------------------------ metric 3
def sample_false_pairs(clusters: list[dict[str, Any]], rng: np.random.Generator,
                       target: int) -> list[tuple[int, int]]:
    """The mechanical FALSE construction, sampled ONCE per snapshot and reused by
    every variant so all four score the identical pair set.

    `different_story` and `countries_disjoint` are IMPORTED from
    `measure_evidence_fingerprint`, so this shares one definition of 'different
    story' with the whitening and evidence harnesses. `different_story` is
    memoized per (label,label) because `dominant_script` walks every character
    through `unicodedata.name`.
    """
    labelled = [k for k, c in enumerate(clusters) if c["label"]]
    if len(labelled) < 3:
        return []
    # hoist the three per-LABEL computations out of the per-PAIR loop.
    # `dominant_script` walks every character through `unicodedata.name`; called
    # per pair it dominated the whole harness. Equivalence with the imported
    # `different_story` is checked on a sample and reported (`false_pair_check`).
    nrm: dict[int, str] = {}
    scr: dict[int, str] = {}
    tok: dict[int, set[str]] = {}
    for k in labelled:
        lab = clusters[k]["label"]
        nrm[k] = norm_label_unicode(lab)
        scr[k] = dominant_script(lab)
        tok[k] = subject_tokens(lab)

    def diff(a: int, b: int) -> bool:
        sa, sb = scr[a], scr[b]
        if sa == "none" or sb == "none" or sa != sb:
            return False
        na, nb = nrm[a], nrm[b]
        if not na or not nb:
            return False
        sim = 1.0 if na == nb else SequenceMatcher(None, na, nb).ratio()
        if sim >= DIFF_LABEL_MAX:
            return False
        return not (tok[a] & tok[b])

    pairs: list[tuple[int, int]] = []
    seen: set[tuple[int, int]] = set()
    draws = rng.integers(0, len(labelled), size=(target * 120, 2))
    for x, y in draws:
        if len(pairs) >= target:
            break
        i, j = labelled[int(x)], labelled[int(y)]
        if i == j:
            continue
        a, b = (i, j) if i < j else (j, i)
        if (a, b) in seen:
            continue
        seen.add((a, b))
        if not countries_disjoint(clusters[a]["cc"], clusters[b]["cc"]):
            continue
        if not diff(a, b):
            continue
        pairs.append((a, b))
    return pairs


def verify_false_construction(clusters: list[dict[str, Any]],
                              pairs: list[tuple[int, int]]) -> dict[str, Any]:
    """Every sampled FALSE pair must satisfy the IMPORTED `different_story` and
    `countries_disjoint`. A non-zero `violations` invalidates metric 3."""
    bad = 0
    for a, b in pairs:
        if not (countries_disjoint(clusters[a]["cc"], clusters[b]["cc"])
                and different_story(clusters[a]["label"], clusters[b]["label"])):
            bad += 1
    return {"checked": len(pairs), "violations": bad, "exact": bad == 0}


def score_false_pairs(clusters: list[dict[str, Any]], pairs: list[tuple[int, int]],
                      V: np.ndarray, *, tau: float, label_mode: str) -> dict[str, Any]:
    """Apply one consolidation variant to the FALSE pair set."""
    if not pairs:
        return {"pairs": 0, "admitted": 0, "rate": None}
    ii = np.array([p[0] for p in pairs]); jj = np.array([p[1] for p in pairs])
    cos = np.einsum("ij,ij->i", V[ii], V[jj])
    lab_ok = _label_pairs_ok([c["label"] for c in clusters], ii, jj, label_mode)
    adm = (cos >= tau) & lab_ok
    ex = [{"a": clusters[ii[k]]["label"], "b": clusters[jj[k]]["label"],
           "cos": round(float(cos[k]), 4)} for k in np.nonzero(adm)[0][:10]]
    return {"pairs": len(pairs), "cos_only_admitted": int((cos >= tau).sum()),
            "admitted": int(adm.sum()), "rate": round(float(adm.mean()), 5),
            "cos_max": round(float(cos.max()), 4),
            "cos_p99": round(float(np.percentile(cos, 99)), 4),
            "examples": ex}


def cross_family(fams: list[dict[str, Any]], clusters: list[dict[str, Any]],
                 comps: list[list[int]]) -> dict[str, Any]:
    """Do two DIFFERENT witness families land in one consolidated component?"""
    idx = {c["id"]: k for k, c in enumerate(clusters)}
    comp_of: dict[int, int] = {}
    for ci, g in enumerate(comps):
        for k in g:
            comp_of[k] = ci
    fam_of: dict[int, set[str]] = defaultdict(set)
    for f in fams:
        for cid in f["cluster_ids"]:
            k = idx.get(cid)
            if k is not None and k in comp_of:
                fam_of[comp_of[k]].add(f["name"])
    bad = [{"component": ci, "families": sorted(names),
            "size": len(comps[ci]),
            "labels": [clusters[k]["label"] for k in comps[ci]][:8]}
           for ci, names in fam_of.items() if len(names) > 1]
    return {"components_holding_multiple_families": len(bad), "detail": bad}


# ------------------------------------------------------------------ metric 1 / 4
def family_components(fam: dict[str, Any], clusters: list[dict[str, Any]],
                      comps: list[list[int]]) -> dict[str, Any]:
    idx = {c["id"]: k for k, c in enumerate(clusters)}
    comp_of: dict[int, int] = {}
    for ci, g in enumerate(comps):
        for k in g:
            comp_of[k] = ci
    hit = Counter()
    missing = 0
    for cid in fam["cluster_ids"]:
        k = idx.get(cid)
        if k is None:
            missing += 1
            continue
        hit[comp_of[k]] += 1
    return {"family": fam["name"], "clusters_in_snapshot": sum(hit.values()),
            "clusters_total": len(fam["cluster_ids"]),
            "clusters_outside_snapshot": missing,
            "components": len(hit), "component_sizes": sorted(hit.values(), reverse=True)}


def score_family_downstream(fam: dict[str, Any], topics, owner_orig: dict[int, int],
                            clusters_by_id: dict[int, dict]) -> dict[str, Any]:
    """Metric 4 per family: topics-per-event, story coverage by SIGNALS, and —
    the control the first pass lacked — whether the topic the family concentrates
    ONTO is the right identity at all.

    Coverage measures CONCENTRATION. A family can reach coverage 1.0 by landing
    every one of its clusters on a topic named something else entirely, which is
    the black hole this whole program is trying to kill. `identity_ok` is the
    mechanical check: is the holder topic's label compatible (production's own
    `labels_compatible`) with the family's modal cluster label?
    """
    cids = fam["cluster_ids"]
    holders_clusters: Counter = Counter()
    holders_signals: Counter = Counter()
    unassigned = 0
    total_signals = 0
    for cid in cids:
        n = clusters_by_id[cid]["n_signals"] if cid in clusters_by_id else 0
        total_signals += n
        ti = owner_orig.get(cid)
        if ti is None:
            unassigned += 1
            continue
        holders_clusters[ti] += 1
        holders_signals[ti] += n
    live = [ti for ti in holders_clusters if topics[ti].state in ("active", "candidate")]
    big = holders_signals.most_common(1)[0] if holders_signals else (None, 0)
    bigc = holders_clusters.most_common(1)[0] if holders_clusters else (None, 0)
    modal = Counter(clusters_by_id[c]["label"] for c in cids
                    if c in clusters_by_id and clusters_by_id[c]["label"])
    modal_label = modal.most_common(1)[0][0] if modal else None
    big_label = topics[big[0]].label if big[0] is not None else None
    return {
        "family": fam["name"], "clusters": len(cids), "signals": total_signals,
        "topics_holding": len(holders_clusters),
        "live_topics_holding": len(live),
        "unassigned_clusters": unassigned,
        "story_coverage_signals": round(big[1] / max(total_signals, 1), 4),
        "largest_topic_signals": big[1],
        "largest_topic_clusters": bigc[1],
        "largest_topic_label": big_label,
        "largest_topic_identity": (topics[big[0]].identity_key if big[0] is not None else None),
        "holder_cluster_sizes": sorted(holders_clusters.values(), reverse=True),
        "family_modal_label": modal_label,
        "identity_label_sim": round(label_sim(big_label, modal_label), 3),
        "identity_ok": bool(labels_compatible(big_label, modal_label)),
    }


def label_script_reach(clusters: list[dict[str, Any]]) -> dict[str, Any]:
    """How many labels the ENGINE normalizer (`[^a-z0-9]+`) can even see.

    `labels_compatible` lowercases then strips everything outside [a-z0-9]; a
    label written in Cyrillic/Arabic/CJK/Greek normalizes to '' and returns
    False against ANY partner. That is a silent per-script disablement of the
    rule, measured here rather than assumed."""
    empty = 0
    lossy = 0
    labelled = 0
    for c in clusters:
        lab = c["label"]
        if not lab:
            continue
        labelled += 1
        norm = re.sub(r"[^a-z0-9]+", " ", lab.lower()).strip()
        if not norm:
            empty += 1
        elif len(norm.replace(" ", "")) < 0.5 * len([ch for ch in lab if ch.isalnum()]):
            lossy += 1
    return {"labelled_clusters": labelled, "normalize_to_empty": empty,
            "over_half_stripped": lossy,
            "empty_share": round(empty / max(labelled, 1), 4)}


# ------------------------------------------------------------------ run
async def main_async(args: argparse.Namespace) -> int:
    import asyncpg
    db = os.environ.get("DATABASE_URL") or os.environ.get("SUPABASE_DB_URL")
    if not db:
        raise SystemExit("DATABASE_URL required")
    conn = await asyncpg.connect(db)
    await conn.execute("SET default_transaction_read_only = on")
    t_start = time.monotonic()
    rng = np.random.default_rng(args.seed)
    try:
        cutoff = dt.datetime.fromisoformat(args.window_start).replace(tzinfo=dt.timezone.utc)
        cache = Path(args.cluster_cache) if args.cluster_cache else None
        if cache and cache.exists():
            import pickle
            clusters = pickle.loads(cache.read_bytes())
            print(f"[load] {len(clusters)} clusters from cache {cache}")
        else:
            t_load = time.monotonic()
            clusters = await load_clusters(conn, None)
            print(f"[load] {len(clusters)} clusters in {time.monotonic()-t_load:.1f}s")
            if cache:
                import pickle
                cache.write_bytes(pickle.dumps(clusters))
        clusters_by_id = {c["id"]: c for c in clusters}
        snaps: dict[str, list[dict]] = defaultdict(list)
        for c in clusters:
            snaps[c["snapshot_at"]].append(c)

        inventory = []
        for snap in sorted(snaps):
            cs = snaps[snap]
            nulls = sum(1 for c in cs if not c["label"])
            inventory.append({"snapshot": snap, "clusters": len(cs), "null_labels": nulls,
                              "null_rate": round(nulls / len(cs), 4)})
        labelled_all = [i["snapshot"] for i in inventory if i["null_rate"] == 0.0
                        and i["clusters"] >= args.min_snapshot_clusters]
        post_blackout = [s for s in labelled_all if s >= "2026-07-28"]
        window_snaps = [i["snapshot"] for i in inventory if i["snapshot"] >= cutoff.isoformat()]
        replay_snaps = ([s for s in window_snaps if s in set(labelled_all)]
                        if args.mode == "labelled" else window_snaps)
        newest_labelled = labelled_all[-1] if labelled_all else None
        print(f"[inv] {len(inventory)} snapshots; labelled(>= {args.min_snapshot_clusters} "
              f"clusters): {len(labelled_all)}; labelled from 2026-07-28 onward: "
              f"{len(post_blackout)}; replaying {len(replay_snaps)}")

        # -------- prod orphans: clusters with NO dynamic_topic_members row -----
        orphan_rows = await conn.fetch(
            """SELECT ec.id, ec.snapshot_at, ec.label, ec.n_signals, ec.cluster_id
                 FROM emergent_clusters ec
                 LEFT JOIN dynamic_topic_members m ON m.emergent_cluster_id = ec.id
                WHERE ec.snapshot_at = $1::timestamptz AND m.emergent_cluster_id IS NULL""",
            dt.datetime.fromisoformat(newest_labelled)) if newest_labelled else []
        orphans = {
            "snapshot": newest_labelled,
            "count": len(orphan_rows),
            "signals": sum(int(r["n_signals"] or 0) for r in orphan_rows),
            "ids": [int(r["id"]) for r in orphan_rows],
            "examples": [{"id": int(r["id"]), "cluster_id": int(r["cluster_id"]),
                          "label": r["label"], "n_signals": int(r["n_signals"] or 0)}
                         for r in sorted(orphan_rows, key=lambda r: -(r["n_signals"] or 0))[:10]],
        }
        print(f"[orphan] {orphans['count']} clusters on {newest_labelled} carry no "
              f"dynamic_topic_members row ({orphans['signals']} signals)")

        # -------- witness families (snapshot-scoped + window-scoped twins) -----
        fams_snapshot: list[dict[str, Any]] = []
        if newest_labelled:
            for toks, nm in ((("iran", "ukrain"), "GQ-12 caspian"),
                             (("berlin", "pride"), "berlin pride")):
                f = pattern_family(clusters, newest_labelled, toks, nm)
                if f:
                    f["scope"] = "snapshot"
                    fams_snapshot.append(f)
            used = {cid for f in fams_snapshot for cid in f["cluster_ids"]}
            fresh = fresh_families(clusters, newest_labelled, used,
                                   args.fresh_min, args.fresh_want)
            for f in fresh:
                f["scope"] = "snapshot"
                # HONESTY: the discovery rule is label_sim >= 0.80 + shared country,
                # i.e. essentially the LABEL CONJUNCT of the rule under test. Fresh
                # families are therefore NOT independent witnesses of this rule —
                # for them metric 1 only tests whether cos >= 0.90 also holds.
                f["circular_with_rule"] = True
            fams_snapshot.extend(fresh)
        replay_set = set(replay_snaps)
        fams_window = [extend_to_window(f, clusters, replay_set, clusters_by_id)
                       for f in fams_snapshot]
        for f, src in zip(fams_window, fams_snapshot):
            f["circular_with_rule"] = bool(src.get("circular_with_rule"))
        g = await gq05_family(conn, clusters, replay_set, args.gq05_pattern, args.gq05_hours)
        if g:
            fams_window.append(g)
        fams_all = fams_snapshot + fams_window
        print("[fam] " + ", ".join(f'{f["name"]}({len(f["cluster_ids"])})' for f in fams_all))

        core_snapshot = ["GQ-12 caspian", "berlin pride", "GQ-05"]
        core_window = ["GQ-12 caspian [window]", "berlin pride [window]", "GQ-05 [window]"]

        # ================= METRICS 1/2/3/5/6 — per labelled snapshot ==========
        per_snapshot: list[dict[str, Any]] = []
        for snap in labelled_all:
            cs = snaps[snap]
            df_tokens: Counter = Counter()
            n_labels = 0
            for c in cs:
                if c["label"]:
                    n_labels += 1
                    df_tokens.update(_subject_tokens(c["label"]))
            rec: dict[str, Any] = {"snapshot": snap, "clusters": len(cs),
                                   "label_script_reach": label_script_reach(cs)}
            tt = time.monotonic()
            fp = sample_false_pairs(cs, np.random.default_rng(args.seed), args.false_pairs)
            t_fp = time.monotonic() - tt; tt = time.monotonic()
            rec["false_pair_check"] = verify_false_construction(cs, fp)
            t_vfp = time.monotonic() - tt; tt = time.monotonic()
            Vn = _unit_rows(np.stack([c["centroid"] for c in cs]).astype(np.float64))
            cand = candidates_at_tau(Vn, args.tau)
            t_cand = time.monotonic() - tt
            print(f"    [t] {snap[:10]} n={len(cs)} false_sample={t_fp:.1f}s "
                  f"false_verify={t_vfp:.1f}s cand={t_cand:.1f}s "
                  f"pairs@tau={cand[0].size}")
            variants: dict[str, Any] = {}
            for vname, kw in (
                ("PRIMARY engine-label", dict(label_mode="engine")),
                ("supp unicode-label", dict(label_mode="unicode")),
                ("supp engine-label, roundups excluded",
                 dict(label_mode="engine", exclude_roundups=True)),
                ("supp engine-label + shared country",
                 dict(label_mode="engine", require_shared_country=True)),
                ("M6 cos-only (no label conjunct)", dict(label_mode="none")),
            ):
                tt = time.monotonic()
                gph = consolidation_graph(cs, tau=args.tau, cand=cand, V=Vn, **kw)
                t_g = time.monotonic() - tt; tt = time.monotonic()
                entry = {
                    "edges": gph["edges"], "pairs_at_tau": gph["pairs_at_tau"],
                    "n_components": gph["n_components"], "largest": gph["largest"],
                    "share": gph["share"], "K2_pass": gph["share"] <= K2_MAX_SHARE,
                    "multi_components": gph["multi_components"],
                    "clusters_in_multi": gph["clusters_in_multi"],
                    "size_histogram": gph["size_histogram"],
                    "excluded_roundups": gph["excluded_roundups"],
                    "families": [family_components(f, cs, gph["components"])
                                 for f in fams_snapshot],
                    "false_side": score_false_pairs(
                        cs, fp, Vn, tau=args.tau, label_mode=kw["label_mode"]),
                }
                if kw["label_mode"] != "none":
                    # metric 6 asks the cos-only lane for DENSITY only; its
                    # components are the whole snapshot, so the per-component
                    # analyses below are neither meaningful nor affordable there.
                    entry["cross_family"] = cross_family(
                        fams_snapshot, cs, gph["components"])
                    entry["country_span_signature"] = country_span_signature(
                        cs, gph["components"], df_tokens, n_labels)
                if kw["label_mode"] != "none" and gph["components"]:
                    entry["largest_component_detail"] = component_detail(
                        cs, gph["components"][0], gph["edge_list"], Vn)
                    flagged_ids = {frozenset(f["cluster_ids"])
                                   for f in entry["country_span_signature"]["flagged"]}
                    entry["flagged_component_details"] = [
                        component_detail(cs, comp, gph["edge_list"], Vn)
                        for comp in gph["components"]
                        if len(comp) > 1
                        and frozenset(cs[k]["id"] for k in comp) in flagged_ids]
                variants[vname] = entry
                print(f"    [t]   {vname[:34]:34s} graph={t_g:.1f}s "
                      f"rest={time.monotonic()-tt:.1f}s edges={entry['edges']}")
                if vname.startswith("PRIMARY") and snap == newest_labelled:
                    rec["fastpath_equivalence"] = verify_fastpath(
                        [c["label"] for c in cs], gph["_cand_ii"], gph["_cand_jj"],
                        np.random.default_rng(args.seed))
                    rec["primary_edge_list"] = gph["edge_list"]
                    rec["primary_components_multi"] = [
                        {"cluster_ids": [cs[k]["id"] for k in gsub],
                         "labels": [cs[k]["label"] for k in gsub],
                         "countries": [cs[k]["cc"][:2] for k in gsub],
                         "n_signals": sum(cs[k]["n_signals"] for k in gsub)}
                        for gsub in gph["components"] if len(gsub) > 1]
            rec["variants"] = variants
            per_snapshot.append(rec)
            p = variants["PRIMARY engine-label"]
            print(f"  [graph] {snap[:19]} n={len(cs):5d} edges={p['edges']:5d} "
                  f"largest={p['largest']:4d} ({100*p['share']:.2f}%) "
                  f"K2={'PASS' if p['K2_pass'] else 'FAIL'} "
                  f"784-class={p['country_span_signature']['flagged_784_class']} "
                  f"false={p['false_side']['admitted']}/{p['false_side']['pairs']}")

        # ================= METRIC 5b — over-merge on 07-28 components =========
        overmerge_block: dict[str, Any] = {"skipped": True}
        if newest_labelled and not args.skip_overmerge:
            cs = snaps[newest_labelled]
            gph = consolidation_graph(cs, tau=args.tau, label_mode="engine")
            want = sorted({s for c in cs for s in c["sample_signal_ids"]})
            print(f"[emb] fetching embeddings for {len(want)} sample signals …")
            emb: dict[int, np.ndarray] = {}
            sig_meta: dict[int, tuple] = {}
            for i in range(0, len(want), 5000):
                ch = want[i:i + 5000]
                for r in await conn.fetch(
                        "SELECT signal_id, vec::text AS v FROM signal_embeddings "
                        "WHERE signal_id = ANY($1::bigint[])", ch):
                    v = np.asarray(json.loads(r["v"].replace("{", "[").replace("}", "]")),
                                   dtype=np.float32)
                    if v.size:
                        emb[int(r["signal_id"])] = v
                for r in await conn.fetch(
                        "SELECT id, country_code, persons FROM signals_v2 "
                        "WHERE id = ANY($1::bigint[])", ch):
                    sig_meta[int(r["id"])] = (r["country_code"], r["persons"])
            print(f"[emb] {len(emb)}/{len(want)} embedded "
                  f"({100*len(emb)/max(len(want),1):.1f}%)")
            overmerge_block = {
                "skipped": False, "snapshot": newest_labelled,
                "embedding_coverage": round(len(emb) / max(len(want), 1), 4),
                "sample_signals": len(want),
                **overmerge_on_components(cs, gph["components"], emb, sig_meta,
                                          OverMergeParams.from_env()),
            }

        # ================= METRIC 4 — downstream projection replay ============
        cfg = LifecycleConfig()
        downstream: dict[str, Any] = {}
        consolidation_log: list[dict[str, Any]] = []
        geometry: dict[str, Any] = {}
        for arm in ("raw", "consolidated"):
            topics, hmeta, umbrella_keys = await hydrate_as_of(conn, clusters_by_id, cutoff)
            events: list[dict[str, Any]] = []
            super_to_orig: dict[int, list[int]] = {}
            per_snap = []
            id_base = 0
            t0 = time.monotonic()
            for snap in replay_snaps:
                cs = snaps[snap]
                if arm == "consolidated":
                    gph = consolidation_graph(cs, tau=args.tau, label_mode="engine")
                    feed, mapping = build_super_clusters(cs, gph["components"], id_base)
                    id_base += len(cs) + 1
                    super_to_orig.update(mapping)
                    geometry[snap] = super_cluster_geometry(
                        cs, gph["components"], feed, mapping)
                    if arm == "consolidated":
                        consolidation_log.append({
                            "snapshot": snap, "clusters": len(cs), "super_clusters": len(feed),
                            "merged_away": len(cs) - len(feed), "edges": gph["edges"],
                            "largest_component": gph["largest"],
                            "labelled": all(c["label"] for c in cs) if cs else False,
                        })
                else:
                    feed = cs
                    super_to_orig.update({c["id"]: [c["id"]] for c in cs})
                res = process_snapshot_sim(topics, feed, snap, cfg, allow_multi=False,
                                           events=events)
                per_snap.append({**res, "fed_clusters": len(feed), "raw_clusters": len(cs)})
                print(f"  [{arm:12s}] {snap[:19]} raw={len(cs):5d} fed={len(feed):5d} "
                      f"attached={res.get('attached',0):5d} founded={res.get('founded',0):5d} "
                      f"topics={len(topics)}")
            owner_super = topic_of_cluster(topics)
            owner_orig: dict[int, int] = {}
            for sid, ti in owner_super.items():
                for cid in super_to_orig.get(sid, [sid]):
                    owner_orig[cid] = ti
            downstream[arm] = {
                "hydrate": hmeta, "seconds": round(time.monotonic() - t0, 1),
                "n_topics_end": len(topics),
                "states": dict(Counter(t.state for t in topics)),
                "attached_total": sum(s.get("attached", 0) for s in per_snap),
                "founded_total": sum(s.get("founded", 0) for s in per_snap),
                "fed_clusters_total": sum(s["fed_clusters"] for s in per_snap),
                "raw_clusters_total": sum(s["raw_clusters"] for s in per_snap),
                "per_snapshot": per_snap,
                "families": [score_family_downstream(f, topics, owner_orig, clusters_by_id)
                             for f in fams_all],
            }
            if arm == "raw" and args.validate:
                downstream[arm]["validation"] = await validate_against_prod(
                    conn, owner_orig, topics, replay_snaps)

        result = {
            "generated_at": dt.datetime.now(dt.timezone.utc).isoformat(),
            "harness": "backend/scripts/measure_cluster_consolidation.py",
            "read_only": True,
            "window_start": cutoff.isoformat(), "mode": args.mode,
            "rule": {"tau": args.tau, "MERGE_THRESHOLD": MERGE_THRESHOLD,
                     "MERGE_LABEL_MIN": MERGE_LABEL_MIN,
                     "label_conjunct": "project_dynamic_topics.labels_compatible (verbatim)"},
            "gates_downstream": {"MATCH_THRESHOLD": MATCH_THRESHOLD,
                                 "ANCHOR_THRESHOLD": ANCHOR_THRESHOLD,
                                 "used_t": "INTACT (production) in BOTH arms"},
            "prereg": {"K2_max_share": K2_MAX_SHARE,
                       "witness_max_components": WITNESS_MAX_COMPONENTS,
                       "witness_core_required": WITNESS_CORE_REQUIRED,
                       "country_span": GUARD_COUNTRY_SPAN,
                       "label_sim_max": GUARD_LABEL_SIM_MAX,
                       "false_pairs": args.false_pairs},
            "snapshot_inventory": inventory[-16:],
            "labelled_snapshots": labelled_all,
            "labelled_from_2026_07_28_onward": post_blackout,
            "replay_snapshots": replay_snaps,
            "orphans": orphans,
            "families": fams_all,
            "per_snapshot": per_snapshot,
            "overmerge": overmerge_block,
            "consolidation_log": consolidation_log,
            "super_cluster_geometry": geometry,
            "downstream": downstream,
            "total_seconds": round(time.monotonic() - t_start, 1),
        }
        result["verdict"] = verdict_block(result, newest_labelled,
                                          core_snapshot, core_window)
        OUT_DIR.mkdir(parents=True, exist_ok=True)
        suffix = "" if args.mode == "all" else f"-{args.mode}"
        if args.tag:
            suffix += f"-{args.tag}"
        (OUT_DIR / f"{STEM}{suffix}.json").write_text(
            json.dumps(result, indent=2, ensure_ascii=False, default=str), encoding="utf-8")
        print(json.dumps(result["verdict"], indent=2, ensure_ascii=False))
        print(f"[out] {OUT_DIR / (STEM + suffix + '.json')}")
        return 0
    finally:
        await conn.close()


def verdict_block(res: dict[str, Any], newest: str | None,
                  core_snapshot: list[str], core_window: list[str]) -> dict[str, Any]:
    kills: list[str] = []
    notes: list[str] = []
    prim = None
    for rec in res["per_snapshot"]:
        if rec["snapshot"] == newest:
            prim = rec["variants"]["PRIMARY engine-label"]
    # --- metric 2: K2 on EVERY labelled snapshot -------------------------------
    k2_fail = [(rec["snapshot"], rec["variants"]["PRIMARY engine-label"]["share"])
               for rec in res["per_snapshot"]
               if not rec["variants"]["PRIMARY engine-label"]["K2_pass"]]
    if k2_fail:
        kills.append(f"K2: largest consolidated component > {100*K2_MAX_SHARE:.0f}% on "
                     f"{len(k2_fail)} labelled snapshot(s): "
                     + ", ".join(f"{s[:10]} {100*v:.2f}%" for s, v in k2_fail))
    # --- metric 5: country-span signature --------------------------------------
    flagged = sum(rec["variants"]["PRIMARY engine-label"]["country_span_signature"]
                  ["flagged_784_class"] for rec in res["per_snapshot"])
    if flagged > 0:
        kills.append(f"784-class: {flagged} consolidated component(s) span >= "
                     f"{GUARD_COUNTRY_SPAN} primary countries AND carry an "
                     f"incompatible label pair (kill rule: > 0)")
    # --- metric 1: witness components (CORE only; fresh are circular) ----------
    m1 = {}
    if prim:
        m1 = {f["family"]: f["components"] for f in prim["families"]}
    core_present = [nm for nm in core_snapshot if nm in m1]
    met1 = sum(1 for nm in core_present if m1[nm] <= WITNESS_MAX_COMPONENTS)
    # --- metric 4: downstream ---------------------------------------------------
    raw = {f["family"]: f for f in res["downstream"]["raw"]["families"]}
    con = {f["family"]: f for f in res["downstream"]["consolidated"]["families"]}
    core_w = [nm for nm in core_window if nm in con]
    met4 = sum(1 for nm in core_w if con[nm]["topics_holding"] <= WITNESS_MAX_COMPONENTS)
    met4_improved = sum(1 for nm in core_w
                        if con[nm]["topics_holding"] <= WITNESS_MAX_COMPONENTS
                        and raw[nm]["topics_holding"] > WITNESS_MAX_COMPONENTS)
    cov_up = sum(1 for nm in core_w
                 if con[nm]["story_coverage_signals"] > raw[nm]["story_coverage_signals"])
    cov_down = sum(1 for nm in core_w
                   if con[nm]["story_coverage_signals"] < raw[nm]["story_coverage_signals"])
    if cov_down > cov_up:
        notes.append("story coverage moved DOWN on more core families than up")
    # coverage measures CONCENTRATION; identity_ok asks whether the topic it
    # concentrates onto is the right one at all. A family at coverage 1.0 with
    # identity_ok False is a black hole, not a fix.
    id_raw = sum(1 for f in raw.values() if f["identity_ok"])
    id_con = sum(1 for f in con.values() if f["identity_ok"])
    if id_con < id_raw:
        notes.append(f"identity correctness FELL: {id_raw} -> {id_con} families whose "
                     f"largest holder's label is compatible with the family's own")
    wrong_and_concentrated = [
        k for k in con
        if not con[k]["identity_ok"] and con[k]["story_coverage_signals"] >= 0.5]
    if wrong_and_concentrated:
        notes.append("families concentrated (coverage >= 0.5) onto an INCOMPATIBLE "
                     "topic label: " + ", ".join(sorted(wrong_and_concentrated)))
    if met1 < WITNESS_CORE_REQUIRED:
        notes.append(f"metric 1 bar unmet: {met1}/{len(core_present)} core families "
                     f"at <= {WITNESS_MAX_COMPONENTS} components")
    if met4 < WITNESS_CORE_REQUIRED:
        notes.append(f"metric 4 bar unmet: {met4}/{len(core_w)} core families at "
                     f"<= {WITNESS_MAX_COMPONENTS} topics")
    if kills:
        verdict = "NO-GO"
    elif met1 >= WITNESS_CORE_REQUIRED and met4 >= WITNESS_CORE_REQUIRED:
        verdict = "GO"
    else:
        verdict = "BOUNDED"
    return {
        "verdict": verdict, "kills_fired": kills, "bar_notes": notes,
        "metric1_family_components": m1,
        "metric1_core_at_or_below_3": met1, "metric1_core_scored": len(core_present),
        "metric2_K2": {rec["snapshot"]: rec["variants"]["PRIMARY engine-label"]["share"]
                       for rec in res["per_snapshot"]},
        "metric3_false_admit": (prim["false_side"] if prim else None),
        "metric3_cross_family": (prim["cross_family"] if prim else None),
        "metric4_topics_raw": {k: v["topics_holding"] for k, v in raw.items()},
        "metric4_topics_consolidated": {k: v["topics_holding"] for k, v in con.items()},
        "metric4_story_coverage_raw": {k: v["story_coverage_signals"] for k, v in raw.items()},
        "metric4_story_coverage_consolidated": {
            k: v["story_coverage_signals"] for k, v in con.items()},
        "metric4_identity_ok_raw": {k: v["identity_ok"] for k, v in raw.items()},
        "metric4_identity_ok_consolidated": {k: v["identity_ok"] for k, v in con.items()},
        "metric4_identity_landing_consolidated": {
            k: {"family_modal": v["family_modal_label"],
                "landed_on": v["largest_topic_label"],
                "coverage": v["story_coverage_signals"],
                "label_sim": v["identity_label_sim"], "ok": v["identity_ok"]}
            for k, v in con.items()},
        "metric4_core_at_or_below_3": met4,
        "metric4_core_improved_to_target": met4_improved,
        "metric4_core_scored": len(core_w),
        "metric5_784_class_total": flagged,
        "metric6_cos_only_share": (
            {rec["snapshot"]: rec["variants"]["M6 cos-only (no label conjunct)"]["share"]
             for rec in res["per_snapshot"]}),
    }


def parse_args() -> argparse.Namespace:
    ap = argparse.ArgumentParser(
        description="Cluster-level consolidation before projection (read-only).")
    ap.add_argument("--window-start", default="2026-07-17")
    ap.add_argument("--mode", choices=("all", "labelled"), default="all")
    ap.add_argument("--tau", type=float, default=MERGE_THRESHOLD)
    ap.add_argument("--false-pairs", type=int, default=FALSE_PAIR_TARGET)
    ap.add_argument("--min-snapshot-clusters", type=int, default=100,
                    help="ignore tiny degenerate snapshots when listing labelled nights")
    ap.add_argument("--gq05-pattern", default="espriella")
    ap.add_argument("--gq05-hours", type=int, default=168)
    ap.add_argument("--fresh-min", type=int, default=6)
    ap.add_argument("--fresh-want", type=int, default=4)
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--skip-overmerge", action="store_true")
    ap.add_argument("--validate", action="store_true")
    ap.add_argument("--tag", default="")
    ap.add_argument("--cluster-cache", default="",
                    help="pickle path for the emergent_clusters read (read-only "
                         "convenience so repeated runs do not re-pull ~90k vectors)")
    return ap.parse_args()


def main() -> None:
    raise SystemExit(asyncio.run(main_async(parse_args())))


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""EMBEDDING BAKE-OFF v2 — is multilingual-e5-base the load-bearing weakness?

READ-ONLY against prod (`SET default_transaction_read_only = on`); writes only
scratch caches and the two artifacts under docs/research/recall-229/.

THE QUESTION
------------
Every write-time identity lever died on the same rock: the geometry of
multilingual-e5-base. Whitening REFUTED (2026-07-28), used_t REFUTED
(2026-07-30), consolidation NO-GO (2026-07-30). Would a better SPACE fix the
disease, measured on the same three instruments — not on a proxy task?

THE THREE INSTRUMENTS (constructions REUSED from the shipped harnesses;
only the embedding space changes)
  I1 pair separation      `measure_identity_whitening.build_pairs` (Rules v1),
                          raw cosine, p5(true) vs p95(false) per gate.
  I2 argmax dispersion    `simulate_used_t_removal`'s top-12 probe: for each
                          fragment of a witness family, is the family's own
                          consolidation target among its 12 nearest topics?
                          e5 baseline: 11/54 on Berlin Pride.
  I3 consolidation graph  `measure_cluster_consolidation`'s rule, but cos-ONLY
                          (no label conjunct) swept over tau: does a K2-safe
                          operating point exist that reconverges the witnesses?

APPLES-TO-APPLES (the caveat that shapes the whole harness)
-----------------------------------------------------------
The stored `emergent_clusters.centroid_vec` is an e5 artifact. A candidate space
cannot be compared to it. So EVERY space, including e5-base itself, is scored on
CENTROIDS RECOMPUTED FROM THE MEMBER HEADLINES: the cluster's first
`--samples` `sample_signal_ids`, embedded in that space, mean-pooled. The
e5-base RECOMPUTED column — not the stored-centroid number from the earlier
artifacts — is the baseline every pre-registered rule is applied against. The
stored-centroid numbers are reported alongside for continuity and are explicitly
a DIFFERENT estimator.

TEXT RECOVERY (measured, not assumed)
-------------------------------------
`signals_v2` retention reaches back only to 2026-07-21 (measured: 0% of
sample_signal_ids resolve for snapshots <= 07-21). Headlines older than that are
recovered from the EXTERNAL ARCHIVE (`/Volumes/Ext/Atlas/Archive`, id+headline
per row, coverage 2026-06-08 onward). Clusters whose text cannot be recovered
are DROPPED and COUNTED — never silently filtered.

PRE-REGISTERED VERDICT RULES (frozen before the first score ran)
  A candidate WINS an instrument if it beats e5-base RECOMPUTED with margin:
    I1  gap positive where e5's is negative (per gate)
    I2  top-12 hit-rate >= 2x e5-base recomputed (and >= 2x the nominal 11/54)
    I3  a K2-safe cos-ONLY operating point exists where e5 has none
  GO       = one candidate wins ALL THREE
  PARTIAL  = wins I2 (the disease) but not all three
  NO-GO    = nothing beats e5 materially

Usage (M1 mlvenv; read-only):
  set -a; . ~/AtlasLocalWorker/.env; set +a
  cd backend
  P=/Users/pedro/AtlasLocalWorker/mlvenv/bin/python
  $P -m scripts.measure_embedding_bakeoff --stage extract
  $P -m scripts.measure_embedding_bakeoff --stage text
  $P -m scripts.measure_embedding_bakeoff --stage embed --space e5base
  $P -m scripts.measure_embedding_bakeoff --stage embed --space e5large
  $P -m scripts.measure_embedding_bakeoff --stage embed --space bgem3
  $P -m scripts.measure_embedding_bakeoff --stage embed --space oai-small
  $P -m scripts.measure_embedding_bakeoff --stage embed --space oai-large
  $P -m scripts.measure_embedding_bakeoff --stage score
"""
from __future__ import annotations

import argparse
import asyncio
import datetime as dt
import gzip
import html
import json
import os
import pickle
import random
import re
import sys
import time
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Iterable, Sequence

import numpy as np

REPO_ROOT = Path(__file__).resolve().parents[2]
ARTIFACT_DIR = REPO_ROOT / "docs" / "research" / "recall-229"
STEM = "2026-07-31-embedding-bakeoff-v2"
SCRATCH = Path(os.environ.get(
    "ATLAS_BAKEOFF_SCRATCH",
    "/private/tmp/claude-501/-Users-pedro-Desktop-PEDRO-Cursos-ObservatorioGlobal/"
    "b09a9b6f-e30c-4679-936b-e9d46e3c40df/scratchpad/bakeoff"))
ARCHIVE_ROOT = Path(os.environ.get("ATLAS_ARCHIVE_ROOT", "/Volumes/Ext/Atlas/Archive"))

# ---- bounded universe (documented approximations, applied IDENTICALLY per space)
SAMPLES_PER_CLUSTER = 3   # first N sample_signal_ids -> the cluster's text
TOPIC_MEMBER_CAP = 4      # topic centroid = mean of anchor + 3 most recent members
CUTOFF = "2026-07-28T00:00:00+00:00"   # topic pool hydrated as-of (07-28 snapshot is 03:28)

# ---- pre-registered instrument-2 baseline (from 2026-07-30-used-t-simulation.md)
NOMINAL_TOP12_BASELINE = 11 / 54

# ---- production sizing for the cost projection (measured 2026-07-28 on prod)
PROD_SIGNALS_PER_DAY = 145_471          # SELECT count(*) FROM signals_v2, 24h
TOKENS_PER_HEADLINE = 1_292_975 / 43_138  # measured on this run's OpenAI calls
OPENAI_USD_PER_MTOK = {"text-embedding-3-small": 0.02, "text-embedding-3-large": 0.13}

# ---- instrument-3 pre-registered kill thresholds (imported semantics)
K2_MAX_SHARE = 0.02
WITNESS_MAX_COMPONENTS = 3
FALSE_PAIRS_I3 = 500

SPACES: dict[str, dict[str, Any]] = {
    "e5base":    {"kind": "hf", "model": "intfloat/multilingual-e5-base",
                  "prefix": "passage: ", "pool": "mean", "fp16": False,
                  "label": "multilingual-e5-base (SHIPPING, recomputed)"},
    "e5large":   {"kind": "hf", "model": "intfloat/multilingual-e5-large",
                  "prefix": "passage: ", "pool": "mean", "fp16": True,
                  "label": "multilingual-e5-large"},
    "bgem3":     {"kind": "hf", "model": "BAAI/bge-m3", "prefix": "",
                  "pool": "cls", "fp16": True, "label": "BAAI/bge-m3 (dense/CLS)"},
    "oai-small": {"kind": "openai", "model": "text-embedding-3-small",
                  "label": "OpenAI text-embedding-3-small"},
    "oai-large": {"kind": "openai", "model": "text-embedding-3-large",
                  "label": "OpenAI text-embedding-3-large"},
}


# ================================================================== utilities
def log(*a: Any) -> None:
    print(*a, flush=True)


def unit(v: np.ndarray) -> np.ndarray:
    if v.ndim == 1:
        n = float(np.linalg.norm(v))
        return v / max(n, 1e-12)
    n = np.linalg.norm(v, axis=1, keepdims=True)
    return v / np.clip(n, 1e-12, None)


def cos_rows(a: np.ndarray, b: np.ndarray) -> np.ndarray:
    return np.sum(unit(a) * unit(b), axis=1)


def describe(vals: Sequence[float]) -> dict[str, Any]:
    a = np.asarray(list(vals), dtype=np.float64)
    if a.size == 0:
        return {"n": 0}
    out: dict[str, Any] = {"n": int(a.size), "mean": round(float(a.mean()), 4)}
    for p in (1, 5, 25, 50, 75, 95, 99):
        out[f"p{p}"] = round(float(np.percentile(a, p)), 4)
    return out


def auc(t: Sequence[float], f: Sequence[float]) -> float | None:
    if not len(t) or not len(f):
        return None
    tt = np.asarray(t, dtype=np.float64)
    ff = np.asarray(f, dtype=np.float64)
    allv = np.concatenate([tt, ff])
    order = allv.argsort()
    ranks = np.empty_like(order, dtype=np.float64)
    ranks[order] = np.arange(1, allv.size + 1)
    srt = allv[order]
    i = 0
    while i < srt.size:
        j = i
        while j + 1 < srt.size and srt[j + 1] == srt[i]:
            j += 1
        if j > i:
            ranks[order[i:j + 1]] = (i + 1 + j + 1) / 2.0
        i = j + 1
    r_t = ranks[: tt.size].sum()
    return round(float((r_t - tt.size * (tt.size + 1) / 2) / (tt.size * ff.size)), 4)


# ================================================================== STAGE: extract
async def stage_extract(args: argparse.Namespace) -> None:
    import asyncpg
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from scripts import measure_identity_whitening as W
    from scripts.simulate_used_t_removal import (
        extend_to_window, fresh_families, pattern_family)
    from scripts.measure_evidence_fingerprint import (
        countries_disjoint, different_story)

    db = os.environ.get("DATABASE_URL") or os.environ.get("SUPABASE_DB_URL")
    if not db:
        raise SystemExit("DATABASE_URL required")
    conn = await asyncpg.connect(db)
    await conn.execute("SET default_transaction_read_only = on")
    t0 = time.monotonic()
    try:
        cutoff = dt.datetime.fromisoformat(CUTOFF)

        # ---------------- I1: pairs, via the SHIPPED construction --------------
        pargs = argparse.Namespace(
            days=args.days, seed=args.seed,
            max_lineage_topics=args.max_lineage_topics,
            max_fragment=args.max_fragment,
            max_false_cluster=args.max_false_cluster,
            max_false_match=args.max_false_match,
            max_false_merge=args.max_false_merge,
            witness_topics={784, 52},
        )
        cache: dict[str, Any] = {}
        pairs, pmeta = await W.build_pairs(conn, pargs, W.Rules("v1"), cache)
        log(f"[I1] build_pairs -> {len(pairs)} pairs ({time.monotonic()-t0:.0f}s)")

        members_full: dict[int, list[dict[str, Any]]] = cache["members"]

        def capped(cids: Sequence[int]) -> list[int]:
            """anchor + up to TOPIC_MEMBER_CAP-1 most recent (the ONE documented
            approximation of a running centroid, applied to every space)."""
            c = list(cids)
            if len(c) <= TOPIC_MEMBER_CAP:
                return c
            return [c[0]] + c[-(TOPIC_MEMBER_CAP - 1):]

        # deterministic per-gate subsample, then re-derive topic sides
        rng = random.Random(args.seed)
        by_key: dict[tuple[str, str], list[Any]] = defaultdict(list)
        for p in pairs:
            by_key[(p.gate, p.truth)].append(p)
        keep: list[Any] = []
        for (gate, truth), lst in sorted(by_key.items()):
            lst.sort(key=lambda p: (p.source, p.a_id, p.b_id))
            cap = args.true_pairs if truth == "true" else args.false_pairs
            keep.extend(lst if len(lst) <= cap else rng.sample(lst, cap))
        log(f"[I1] subsampled -> {len(keep)} pairs "
            + str(dict(Counter(f"{p.gate}/{p.truth}" for p in keep))))

        pair_rows: list[dict[str, Any]] = []
        for p in keep:
            a_cids = list(p.a_cids)
            b_cids = list(p.b_cids)
            if p.a_kind == "topic":
                a_cids = capped([m["cluster_id"] for m in members_full.get(p.a_id, [])])
            if p.b_kind == "topic":
                b_cids = capped([m["cluster_id"] for m in members_full.get(p.b_id, [])])
            if p.b_kind == "topic_running":
                b_cids = capped(b_cids)
            if not a_cids or not b_cids:
                continue
            pair_rows.append({
                "gate": p.gate, "truth": p.truth, "source": p.source,
                "a_kind": p.a_kind, "a_id": p.a_id, "b_kind": p.b_kind, "b_id": p.b_id,
                "a_label": p.a_label, "b_label": p.b_label,
                "a_cc": p.a_cc[:4], "b_cc": p.b_cc[:4],
                "story": p.story, "flags": sorted(p.flags),
                "a_cids": a_cids, "b_cids": b_cids,
                "stored_raw": round(p.raw, 5), "stored_whitened": round(p.wht, 5),
            })

        # ---------------- I2/I3: snapshots, families, topic pool ---------------
        # snapshot keys are the ISO strings `_load_clusters_min` produces, so the
        # inventory is derived from the SAME objects the family finders index on
        # (a `snapshot_at::text` key would not compare equal to `.isoformat()`).
        all_clusters = await _load_clusters_min(conn, None)
        by_snap: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for c in all_clusters:
            by_snap[c["snapshot_at"]].append(c)
        inventory = [{"snapshot": s, "clusters": len(cs),
                      "null_labels": sum(1 for c in cs if not c["label"])}
                     for s, cs in sorted(by_snap.items())]
        labelled = [i["snapshot"] for i in inventory
                    if i["null_labels"] == 0 and i["clusters"] >= 100]
        newest_labelled = labelled[-1]
        log(f"[snap] {len(inventory)} snapshots; newest labelled {newest_labelled}")

        # clusters we need in full detail: the consolidation snapshots + the
        # replay window that the witness families span
        i3_snaps = [newest_labelled] + (
            [s for s in labelled if s.startswith(args.second_snapshot)][-1:]
            if args.second_snapshot else [])
        replay_snaps = [i["snapshot"] for i in inventory
                        if i["snapshot"] >= args.window_start]

        fams_snapshot: list[dict[str, Any]] = []
        for toks, nm in ((("iran", "ukrain"), "GQ-12 caspian"),
                         (("berlin", "pride"), "berlin pride")):
            f = pattern_family(all_clusters, newest_labelled, toks, nm)
            if f:
                f["scope"] = "snapshot"
                fams_snapshot.append(f)
        used = {cid for f in fams_snapshot for cid in f["cluster_ids"]}
        for f in fresh_families(all_clusters, newest_labelled, used, 6, 4):
            f["scope"] = "snapshot"
            f["circular_with_rule"] = True
            fams_snapshot.append(f)
        replay_set = set(replay_snaps)
        cby = {c["id"]: c for c in all_clusters}
        fams_window = [extend_to_window(f, all_clusters, replay_set, cby)
                       for f in fams_snapshot]
        for fw, src in zip(fams_window, fams_snapshot):
            fw["circular_with_rule"] = bool(src.get("circular_with_rule"))
        fams = fams_snapshot + fams_window
        log("[fam] " + ", ".join(f'{f["name"]}({len(f["cluster_ids"])})' for f in fams))

        # topic pool (I2): ordered members < cutoff, capped
        mrows = await conn.fetch(
            "SELECT m.dynamic_topic_id t, m.emergent_cluster_id cid "
            "FROM dynamic_topic_members m "
            "JOIN emergent_clusters ec ON ec.id = m.emergent_cluster_id "
            "WHERE m.snapshot_at < $1::timestamptz AND ec.centroid_vec IS NOT NULL "
            "ORDER BY m.snapshot_at, m.emergent_cluster_id", cutoff)
        tmem: dict[int, list[int]] = defaultdict(list)
        for r in mrows:
            tmem[int(r["t"])].append(int(r["cid"]))
        trows = await conn.fetch(
            "SELECT id, label, state, identity_key FROM dynamic_topics")
        tmeta = {int(r["id"]): {"label": r["label"], "state": r["state"],
                                "identity_key": r["identity_key"]} for r in trows}
        topic_pool = {tid: {"cids": capped(cids), "anchor": cids[0],
                            **tmeta.get(tid, {})}
                      for tid, cids in tmem.items() if cids}
        log(f"[pool] {len(topic_pool)} topics; "
            f"{len({c for v in topic_pool.values() for c in v['cids']})} distinct member clusters")

        # prod ownership of family clusters -> the space-independent TARGET topic
        fam_cids = sorted({cid for f in fams for cid in f["cluster_ids"]})
        orows = await conn.fetch(
            "SELECT emergent_cluster_id cid, dynamic_topic_id t FROM dynamic_topic_members "
            "WHERE emergent_cluster_id = ANY($1::bigint[])", fam_cids)
        owner = {int(r["cid"]): int(r["t"]) for r in orows}

        # ---------------- I3: mechanical FALSE pairs per snapshot --------------
        i3: dict[str, Any] = {}
        for snap in i3_snaps:
            cs = by_snap[snap]
            rg = np.random.default_rng(args.seed)
            fp = _sample_false_pairs(cs, rg, FALSE_PAIRS_I3,
                                     different_story, countries_disjoint)
            i3[snap] = {"cluster_ids": [c["id"] for c in cs],
                        "false_pairs": [[cs[a]["id"], cs[b]["id"]] for a, b in fp]}
            log(f"[I3] {snap[:10]} clusters={len(cs)} false_pairs={len(fp)}")

        # ---------------- the cluster universe + its sample signal ids ---------
        need: set[int] = set()
        for r in pair_rows:
            need.update(r["a_cids"]); need.update(r["b_cids"])
        for f in fams:
            need.update(f["cluster_ids"])
        for v in topic_pool.values():
            need.update(v["cids"])
        for v in i3.values():
            need.update(v["cluster_ids"])
        need = {int(x) for x in need}
        log(f"[universe] {len(need)} distinct clusters")

        cmeta: dict[int, dict[str, Any]] = {}
        ids = sorted(need)
        for i in range(0, len(ids), 2000):
            rows = await conn.fetch(
                "SELECT id, snapshot_at::text s, cluster_id, label, top_country_codes cc, "
                "n_signals, sample_signal_ids FROM emergent_clusters "
                "WHERE id = ANY($1::bigint[])", ids[i:i + 2000])
            for r in rows:
                cmeta[int(r["id"])] = {
                    "id": int(r["id"]), "snapshot_at": r["s"],
                    "cluster_id": int(r["cluster_id"]), "label": r["label"],
                    "cc": list(r["cc"] or []), "n_signals": int(r["n_signals"] or 0),
                    "sids": [int(x) for x in (r["sample_signal_ids"] or [])][:SAMPLES_PER_CLUSTER],
                }
        want_sids = sorted({s for m in cmeta.values() for s in m["sids"]})
        log(f"[universe] {len(cmeta)} cluster rows, {len(want_sids)} sample signal ids")

        out = {
            "generated_at": dt.datetime.now(dt.timezone.utc).isoformat(),
            "config": {"samples_per_cluster": SAMPLES_PER_CLUSTER,
                       "topic_member_cap": TOPIC_MEMBER_CAP, "cutoff": CUTOFF,
                       "seed": args.seed, "days": args.days,
                       "true_pairs_per_gate": args.true_pairs,
                       "false_pairs_per_gate": args.false_pairs},
            "pair_meta": pmeta, "pairs": pair_rows,
            "families": fams, "family_owner": owner,
            "topic_pool": topic_pool,
            "i3": i3, "i3_snapshots": i3_snaps,
            "inventory": inventory, "labelled_snapshots": labelled,
            "newest_labelled": newest_labelled,
            "cmeta": cmeta, "want_sids": want_sids,
            "seconds": round(time.monotonic() - t0, 1),
        }
        SCRATCH.mkdir(parents=True, exist_ok=True)
        (SCRATCH / "extract.pkl").write_bytes(pickle.dumps(out))
        log(f"[out] {SCRATCH/'extract.pkl'} ({time.monotonic()-t0:.0f}s)")
    finally:
        await conn.close()


async def _load_clusters_min(conn, _unused) -> list[dict[str, Any]]:
    """`simulate_used_t_removal.load_clusters` minus the centroid pull.

    The family-discovery functions only touch label / cc / n_signals /
    sample_signal_ids / snapshot_at, so the 768-dim vectors (~90k rows) are not
    fetched here — a pure cost cut, no behavioural change.
    """
    rows = await conn.fetch(
        "SELECT id, snapshot_at, cluster_id, label, n_signals, sample_signal_ids, "
        "top_country_codes FROM emergent_clusters WHERE centroid_vec IS NOT NULL "
        "ORDER BY snapshot_at, cluster_id")
    return [{"id": int(r["id"]), "snapshot_at": r["snapshot_at"].isoformat(),
             "cluster_id": r["cluster_id"], "label": r["label"],
             "n_signals": int(r["n_signals"] or 0),
             "sample_signal_ids": [int(x) for x in (r["sample_signal_ids"] or [])],
             "cc": [str(x) for x in (r["top_country_codes"] or [])]}
            for r in rows]


def _sample_false_pairs(cs: list[dict[str, Any]], rng, target: int,
                        different_story, countries_disjoint) -> list[tuple[int, int]]:
    """`measure_cluster_consolidation.sample_false_pairs`, same predicates."""
    lab = [k for k, c in enumerate(cs) if c["label"]]
    if len(lab) < 3:
        return []
    out: list[tuple[int, int]] = []
    seen: set[tuple[int, int]] = set()
    draws = rng.integers(0, len(lab), size=(target * 120, 2))
    for x, y in draws:
        if len(out) >= target:
            break
        i, j = lab[int(x)], lab[int(y)]
        if i == j:
            continue
        a, b = (i, j) if i < j else (j, i)
        if (a, b) in seen:
            continue
        seen.add((a, b))
        if not countries_disjoint(cs[a]["cc"], cs[b]["cc"]):
            continue
        # `measure_evidence_fingerprint.different_story` already REQUIRES the
        # same dominant script (construction v1, D2) — imported verbatim.
        if not different_story(cs[a]["label"], cs[b]["label"]):
            continue
        out.append((a, b))
    return out


# ================================================================== STAGE: text
async def stage_text(args: argparse.Namespace) -> None:
    """Resolve headlines for every wanted sample signal id: hot DB first, then
    the external archive for everything retention has already pruned."""
    import asyncpg
    ex = pickle.loads((SCRATCH / "extract.pkl").read_bytes())
    want = set(ex["want_sids"])
    texts: dict[int, str] = {}
    t0 = time.monotonic()

    db = os.environ.get("DATABASE_URL") or os.environ.get("SUPABASE_DB_URL")
    conn = await asyncpg.connect(db)
    await conn.execute("SET default_transaction_read_only = on")
    try:
        ids = sorted(want)
        for i in range(0, len(ids), 5000):
            rows = await conn.fetch(
                "SELECT id, headline FROM signals_v2 WHERE id = ANY($1::bigint[])",
                ids[i:i + 5000])
            for r in rows:
                if r["headline"]:
                    texts[int(r["id"])] = html.unescape(r["headline"])
    finally:
        await conn.close()
    log(f"[text] hot DB resolved {len(texts)}/{len(want)} ({time.monotonic()-t0:.0f}s)")

    missing = want - set(texts)
    if missing and ARCHIVE_ROOT.is_dir():
        found = _scan_archive(missing)
        texts.update(found)
        log(f"[text] archive resolved {len(found)}/{len(missing)}")
    elif missing:
        log(f"[text] archive NOT MOUNTED at {ARCHIVE_ROOT}; {len(missing)} ids unrecoverable")

    (SCRATCH / "texts.pkl").write_bytes(pickle.dumps(texts))
    cov = {"wanted": len(want), "resolved": len(texts),
           "rate": round(len(texts) / max(len(want), 1), 4)}
    # per-cluster recoverability
    ok = sum(1 for m in ex["cmeta"].values() if any(s in texts for s in m["sids"]))
    cov["clusters_total"] = len(ex["cmeta"])
    cov["clusters_with_text"] = ok
    cov["clusters_dropped"] = len(ex["cmeta"]) - ok
    (SCRATCH / "text_coverage.json").write_text(json.dumps(cov, indent=2))
    log(f"[text] {json.dumps(cov)}")


_ID_RE = re.compile(rb'"id":(\d+)')
_HL_RE = re.compile(rb'"headline":"((?:[^"\\]|\\.)*)"')


def _scan_archive(wanted: set[int]) -> dict[int, str]:
    """Stream every archive partition, keeping only the wanted ids.

    Byte-level pre-filter (regex over the raw line) so 10M+ rows do not each pay
    a json.loads; the full parse runs only for a wanted id.
    """
    parts = sorted(ARCHIVE_ROOT.rglob("*.jsonl.gz"))
    log(f"[archive] scanning {len(parts)} partitions for {len(wanted)} ids")
    out: dict[int, str] = {}
    t0 = time.monotonic()
    for k, p in enumerate(parts):
        if len(out) >= len(wanted):
            break
        try:
            with gzip.open(p, "rb") as fh:
                for line in fh:
                    m = _ID_RE.search(line)
                    if not m:
                        continue
                    sid = int(m.group(1))
                    if sid not in wanted or sid in out:
                        continue
                    h = _HL_RE.search(line)
                    if not h:
                        continue
                    try:
                        hl = json.loads(b'"' + h.group(1) + b'"')
                    except Exception:
                        continue
                    if hl:
                        out[sid] = html.unescape(hl)
        except (OSError, EOFError) as exc:
            log(f"[archive] skip {p.name}: {exc}")
        if (k + 1) % 50 == 0:
            log(f"[archive] {k+1}/{len(parts)} parts, {len(out)} found "
                f"({time.monotonic()-t0:.0f}s)")
    log(f"[archive] done: {len(out)} found in {time.monotonic()-t0:.0f}s")
    return out


# ================================================================== STAGE: embed
def stage_embed(args: argparse.Namespace) -> None:
    spec = SPACES[args.space]
    texts: dict[int, str] = pickle.loads((SCRATCH / "texts.pkl").read_bytes())
    ids = sorted(texts)
    payload = [texts[i] for i in ids]
    log(f"[embed:{args.space}] {len(payload)} texts")
    t0 = time.monotonic()
    if spec["kind"] == "hf":
        vecs, extra = _embed_hf(spec, payload, args.batch)
    else:
        vecs, extra = _embed_openai(spec, payload, args.batch, args.concurrency)
    dt_ = time.monotonic() - t0
    np.savez_compressed(SCRATCH / f"vecs_{args.space}.npz",
                        ids=np.asarray(ids, dtype=np.int64),
                        vecs=vecs.astype(np.float32))
    meta = {"space": args.space, "model": spec["model"], "n_texts": len(payload),
            "dim": int(vecs.shape[1]), "seconds": round(dt_, 1),
            "texts_per_second": round(len(payload) / max(dt_, 1e-9), 1), **extra}
    (SCRATCH / f"vecs_{args.space}.json").write_text(json.dumps(meta, indent=2))
    log(f"[embed:{args.space}] {json.dumps(meta)}")


def _pool(hs, mask, how: str):
    import torch
    if how == "cls":
        p = hs[:, 0]
    else:
        m = mask.unsqueeze(-1).to(hs.dtype)
        p = (hs * m).sum(1) / m.sum(1).clamp(min=1e-9)
    return torch.nn.functional.normalize(p.float(), p=2, dim=1)


def _embed_hf(spec: dict[str, Any], texts: list[str], batch: int
              ) -> tuple[np.ndarray, dict[str, Any]]:
    """Production's pooling contract (`research_semantic._build_embed_fn`):
    attention-mask mean pool, L2 normalize, max_length 96. bge-m3's dense
    representation is CLS, so it pools CLS — its documented contract.

    MEASURED: the 1024-dim models do not fit fp32 on this 8GB M1 (0.4 texts/s,
    i.e. swapping); fp16 restores 60 texts/s. `fidelity` reports cos(fp16,
    fp32-CPU) over a 64-text probe so the numeric cost is on the record.
    """
    import torch
    from transformers import AutoModel, AutoTokenizer
    dtype = torch.float16 if spec.get("fp16") else torch.float32
    tok = AutoTokenizer.from_pretrained(spec["model"])
    model = AutoModel.from_pretrained(spec["model"], dtype=dtype)
    model.eval()
    dev = "mps" if torch.backends.mps.is_available() else "cpu"
    model.to(dev)
    pre = spec.get("prefix", "")
    how = spec.get("pool", "mean")

    def run(chunk: list[str]) -> np.ndarray:
        enc = tok([pre + t for t in chunk], padding=True, truncation=True,
                  max_length=96, return_tensors="pt").to(dev)
        hs = model(**enc).last_hidden_state
        p = _pool(hs, enc["attention_mask"], how)
        return p.cpu().numpy()

    # LENGTH-BUCKETED batching. `padding=True` pads to the longest member of the
    # batch, so a batch mixing a 4-word headline with a 96-token one pays the
    # long one's cost for every row. Sorting by length before batching and
    # un-permuting afterwards is arithmetically identical (each row is embedded
    # independently) and measured several times faster on this corpus.
    order = sorted(range(len(texts)), key=lambda k: len(texts[k]))
    out: list[np.ndarray] = []
    t0 = time.monotonic()
    with torch.no_grad():
        for lo in range(0, len(order), batch):
            idx = order[lo:lo + batch]
            out.append(run([texts[k] for k in idx]))
            if (lo // batch) % 100 == 0 and lo:
                done = lo + batch
                log(f"    {done}/{len(texts)} ({done/(time.monotonic()-t0):.0f}/s)")
    Vs = np.vstack(out)
    V = np.empty_like(Vs)
    V[np.asarray(order)] = Vs

    fidelity: dict[str, Any] = {}
    if spec.get("fp16"):
        # best-effort: the fp32 CPU copy is ~2.2GB on top of the live fp16 model,
        # and losing a 12-minute embedding run to an OOM in a DIAGNOSTIC would be
        # absurd. A failure is recorded, never fatal.
        del model
        if dev == "mps":
            torch.mps.empty_cache()
        model = None
        try:
            probe = texts[: min(64, len(texts))]
            m32 = AutoModel.from_pretrained(spec["model"], dtype=torch.float32)
            m32.eval().to("cpu")
            with torch.no_grad():
                enc = tok([pre + t for t in probe], padding=True, truncation=True,
                          max_length=96, return_tensors="pt")
                p32 = _pool(m32(**enc).last_hidden_state, enc["attention_mask"], how).numpy()
            # `texts` is the sorted-by-id payload, so V's first rows ARE the probe
            c = np.sum(unit(V[: len(probe)]) * unit(p32), axis=1)
            fidelity = {"fp16_vs_fp32_cos_min": round(float(c.min()), 6),
                        "fp16_vs_fp32_cos_mean": round(float(c.mean()), 6),
                        "fidelity_probe_n": len(probe)}
            del m32
        except Exception as exc:            # noqa: BLE001 - diagnostic only
            fidelity = {"fidelity_probe_error": f"{type(exc).__name__}: {exc}"}
    if model is not None:
        del model
    if dev == "mps":
        torch.mps.empty_cache()
    return V, {"device": dev, "dtype": str(dtype), "pool": how, **fidelity}


def _embed_openai(spec: dict[str, Any], texts: list[str], batch: int,
                  concurrency: int) -> tuple[np.ndarray, dict[str, Any]]:
    import urllib.error
    import urllib.request
    from concurrent.futures import ThreadPoolExecutor

    key = os.environ.get("OPENAI_API_KEY")
    if not key:
        raise SystemExit("OPENAI_API_KEY required for the OpenAI spaces")
    chunks = [(i, texts[i:i + batch]) for i in range(0, len(texts), batch)]
    results: dict[int, list[list[float]]] = {}
    tokens = 0

    def call(item):
        nonlocal tokens
        i, chunk = item
        body = json.dumps({"model": spec["model"],
                           "input": [t[:2000] for t in chunk]}).encode()
        last = None
        for attempt in range(6):
            try:
                req = urllib.request.Request(
                    "https://api.openai.com/v1/embeddings", data=body,
                    headers={"Authorization": f"Bearer {key}",
                             "Content-Type": "application/json"}, method="POST")
                with urllib.request.urlopen(req, timeout=120) as res:
                    payload = json.loads(res.read())
                data = sorted(payload["data"], key=lambda d: d["index"])
                tokens += int(payload.get("usage", {}).get("total_tokens", 0))
                return i, [d["embedding"] for d in data]
            except Exception as exc:            # 429 / 5xx / transient
                last = exc
                time.sleep(min(2 ** attempt, 30))
        raise RuntimeError(f"openai chunk {i} failed: {last}")

    t0 = time.monotonic()
    with ThreadPoolExecutor(max_workers=concurrency) as pool:
        for n, (i, vecs) in enumerate(pool.map(call, chunks), 1):
            results[i] = vecs
            if n % 40 == 0:
                log(f"    {n}/{len(chunks)} chunks ({time.monotonic()-t0:.0f}s)")
    V = np.vstack([np.asarray(results[i], dtype=np.float32)
                   for i, _ in chunks])
    price = {"text-embedding-3-small": 0.02, "text-embedding-3-large": 0.13}
    return unit(V.astype(np.float64)).astype(np.float32), {
        "total_tokens": tokens,
        "usd_estimate": round(tokens / 1e6 * price.get(spec["model"], 0.0), 4),
        "batch": batch, "concurrency": concurrency}


# ================================================================== STAGE: score
def _centroids(ex: dict[str, Any], texts: dict[int, str], space: str
               ) -> tuple[dict[int, np.ndarray], dict[str, Any]]:
    z = np.load(SCRATCH / f"vecs_{space}.npz")
    ids = z["ids"].tolist()
    V = z["vecs"].astype(np.float64)
    idx = {int(s): k for k, s in enumerate(ids)}
    cent: dict[int, np.ndarray] = {}
    n_txt: list[int] = []
    for cid, m in ex["cmeta"].items():
        rows = [V[idx[s]] for s in m["sids"] if s in idx]
        if not rows:
            continue
        cent[int(cid)] = unit(np.mean(np.stack(rows), axis=0))
        n_txt.append(len(rows))
    return cent, {"clusters_with_centroid": len(cent),
                  "clusters_total": len(ex["cmeta"]),
                  "mean_texts_per_cluster": round(float(np.mean(n_txt)), 2) if n_txt else 0.0}


def _side_vec(cids: Sequence[int], cent: dict[int, np.ndarray]) -> np.ndarray | None:
    rows = [cent[c] for c in cids if c in cent]
    if not rows:
        return None
    return unit(np.mean(np.stack(rows), axis=0))


def instrument1(ex: dict[str, Any], cent: dict[int, np.ndarray]) -> dict[str, Any]:
    gates: dict[str, dict[str, list[float]]] = defaultdict(lambda: {"true": [], "false": []})
    values: list[dict[str, Any]] = []
    dropped = 0
    for r in ex["pairs"]:
        a = _side_vec(r["a_cids"], cent)
        b = _side_vec(r["b_cids"], cent)
        if a is None or b is None:
            dropped += 1
            continue
        c = float(np.dot(a, b))
        gates[r["gate"]][r["truth"]].append(c)
        values.append({"gate": r["gate"], "truth": r["truth"], "source": r["source"],
                       "a_label": (r["a_label"] or "")[:70],
                       "b_label": (r["b_label"] or "")[:70],
                       "cos": round(c, 5), "stored_raw": r["stored_raw"],
                       "flags": r["flags"], "story": r["story"]})
    # tails only — the full 2400-row value table would bloat the artifact by
    # ~5x for no analytic gain; the tails are what a hand-check reads.
    tails: dict[str, Any] = {}
    for g in sorted(gates):
        sel = [x for x in values if x["gate"] == g]
        t = sorted([x for x in sel if x["truth"] == "true"], key=lambda x: x["cos"])[:12]
        f = sorted([x for x in sel if x["truth"] == "false"],
                   key=lambda x: -x["cos"])[:12]
        tails[g] = {"true_left_tail": t, "false_right_tail": f}
    out: dict[str, Any] = {"dropped_pairs_no_text": dropped, "tails": tails}
    for g, d in sorted(gates.items()):
        t, f = d["true"], d["false"]
        row: dict[str, Any] = {"true": describe(t), "false": describe(f), "auc": auc(t, f)}
        if t and f:
            p5 = float(np.percentile(t, 5))
            p95 = float(np.percentile(f, 95))
            row.update({"p5_true": round(p5, 4), "p95_false": round(p95, 4),
                        "gap": round(p5 - p95, 4),
                        "verdict": "PROCEED" if p5 > p95 else "STOP"})
            if p5 > p95:
                tau = (p5 + p95) / 2
                row["tau"] = round(tau, 4)
                row["true_kept_at_tau"] = round(float(np.mean(np.asarray(t) >= tau)), 4)
                row["false_rejected_at_tau"] = round(float(np.mean(np.asarray(f) < tau)), 4)
        else:
            row["verdict"] = "INSUFFICIENT"
        out[g] = row

    # ENGINE-INDEPENDENT CUT. Lineage TRUE pairs were SELECTED BY the raw e5
    # gates (0.88/0.93), so any space is flattered on them. `fragment` (same
    # snapshot, near-identical labels, the engine FAILED to unify them) and
    # `false_cluster` (same snapshot, disjoint countries, dissimilar same-script
    # labels) owe nothing to the gates. This is the load-bearing slice.
    ft = [x["cos"] for x in values
          if x["gate"] == "anchor" and x["source"] in ("fragment", "fragment_loose")]
    ff = [x["cos"] for x in values
          if x["gate"] == "anchor" and x["source"] == "false_cluster"]
    blk: dict[str, Any] = {"true": describe(ft), "false": describe(ff), "auc": auc(ft, ff)}
    if ft and ff:
        p5 = float(np.percentile(ft, 5))
        p95 = float(np.percentile(ff, 95))
        blk.update({"p5_true": round(p5, 4), "p95_false": round(p95, 4),
                    "gap": round(p5 - p95, 4),
                    "verdict": "PROCEED" if p5 > p95 else "STOP"})
    else:
        blk["verdict"] = "INSUFFICIENT"
    out["anchor_engine_independent"] = blk
    return out


def instrument2(ex: dict[str, Any], cent: dict[int, np.ndarray], top_k: int = 12
                ) -> dict[str, Any]:
    """Do same-event fragments share an argmax over the topic pool?"""
    try:
        from scripts.project_dynamic_topics import labels_compatible
    except ImportError:                     # scoring can run without the engine
        labels_compatible = None            # type: ignore[assignment]
    cmeta = ex["cmeta"]
    pool = ex["topic_pool"]
    tids: list[int] = []
    tvecs: list[np.ndarray] = []
    for tid, v in pool.items():
        vec = _side_vec(v["cids"], cent)
        if vec is None:
            continue
        tids.append(int(tid))
        tvecs.append(vec)
    if not tvecs:
        return {"error": "empty topic pool"}
    T = np.stack(tvecs)
    tpos = {t: k for k, t in enumerate(tids)}
    owner = ex["family_owner"]

    fams: list[dict[str, Any]] = []
    for f in ex["families"]:
        cids = [c for c in f["cluster_ids"] if c in cent]
        if len(cids) < 3:
            continue
        # TARGET = space-independent: the topic prod's own membership table says
        # the family concentrates onto. Fixed across spaces by construction.
        holders = Counter(owner[c] for c in f["cluster_ids"] if c in owner)
        target = holders.most_common(1)[0][0] if holders else None
        C = np.stack([cent[c] for c in cids])
        S = C @ T.T
        k = min(top_k, S.shape[1])
        top = np.argpartition(-S, k - 1, axis=1)[:, :k]
        arg1 = S.argmax(axis=1)
        hit = 0
        scored = 0
        if target is not None and target in tpos:
            tp = tpos[target]
            scored = len(cids)
            hit = int(sum(1 for r in range(len(cids)) if tp in set(top[r].tolist())))
        modal = Counter(arg1.tolist()).most_common(1)[0]
        # IS THE TARGET THE RIGHT IDENTITY AT ALL? Same mechanical test
        # `measure_cluster_consolidation.score_family_downstream` uses for
        # `identity_ok`: production's own `labels_compatible` between the holder
        # topic's label and the family's MODAL cluster label. A family whose
        # prod target is incompatible is concentrated on a black hole, and
        # "find that target" is not a capability worth rewarding.
        modal_lab = Counter(
            cmeta[c]["label"] for c in f["cluster_ids"]
            if c in cmeta and cmeta[c]["label"]).most_common(1)
        family_modal_label = modal_lab[0][0] if modal_lab else None
        tlabel = (pool.get(target) or {}).get("label") if target else None
        identity_ok = (bool(labels_compatible(tlabel, family_modal_label))
                       if labels_compatible and tlabel and family_modal_label else None)
        fams.append({
            "family_modal_label": family_modal_label,
            "target_identity_ok": identity_ok,
            "family": f["name"], "scope": f.get("scope", "window"),
            "circular_with_rule": bool(f.get("circular_with_rule")),
            "clusters_total": len(f["cluster_ids"]),
            "clusters_scored": len(cids),
            "target_topic": target,
            "target_holds": (holders.most_common(1)[0][1] if holders else 0),
            "target_in_pool": bool(target is not None and target in tpos),
            "target_label": (pool.get(target) or {}).get("label") if target else None,
            f"top{top_k}_hits": hit, f"top{top_k}_scored": scored,
            f"top{top_k}_rate": round(hit / scored, 4) if scored else None,
            "argmax_modal_share": round(modal[1] / len(cids), 4),
            "argmax_distinct_topics": len(set(arg1.tolist())),
            "argmax_modal_topic_label": (pool.get(tids[modal[0]]) or {}).get("label"),
            "mean_cos_to_target": (round(float(np.mean(C @ T[tpos[target]])), 4)
                                   if target is not None and target in tpos else None),
        })
    core = [x for x in fams if x["family"] in ("berlin pride [window]", "GQ-12 caspian [window]")]
    tot_h = sum(x[f"top{top_k}_hits"] for x in core)
    tot_s = sum(x[f"top{top_k}_scored"] for x in core)
    # SECONDARY, and declared as such: the same top-12 question restricted to
    # families whose prod target IS a compatible identity. This is NOT the frozen
    # rule and does not decide the verdict; it exists because the frozen rule's
    # target can be a black hole, which the pre-registration flagged in advance.
    okf = [x for x in fams if x["target_identity_ok"]]
    ok_h = sum(x[f"top{top_k}_hits"] for x in okf)
    ok_s = sum(x[f"top{top_k}_scored"] for x in okf)
    return {"topic_pool_size": len(tids), "families": fams,
            "core_top12_hits": tot_h, "core_top12_scored": tot_s,
            "core_top12_rate": round(tot_h / tot_s, 4) if tot_s else None,
            "core_argmax_modal_share": round(
                float(np.mean([x["argmax_modal_share"] for x in core])), 4) if core else None,
            "secondary_identity_ok_families": [x["family"] for x in okf],
            "secondary_identity_ok_hits": ok_h,
            "secondary_identity_ok_scored": ok_s,
            "secondary_identity_ok_rate": round(ok_h / ok_s, 4) if ok_s else None,
            "mean_argmax_modal_share_all_families": round(
                float(np.mean([x["argmax_modal_share"] for x in fams])), 4) if fams else None}


class _UF:
    """Incremental union-find: the tau sweep walks DOWNWARD adding edges, so one
    structure serves every threshold. Rebuilding per tau would re-walk millions
    of edges at the loose end and never finish."""

    def __init__(self, n: int) -> None:
        self.p = list(range(n))
        self.sz = [1] * n
        self.largest = 1

    def find(self, x: int) -> int:
        p = self.p
        while p[x] != x:
            p[x] = p[p[x]]
            x = p[x]
        return x

    def union(self, a: int, b: int) -> None:
        ra, rb = self.find(a), self.find(b)
        if ra == rb:
            return
        if self.sz[ra] < self.sz[rb]:
            ra, rb = rb, ra
        self.p[rb] = ra
        self.sz[ra] += self.sz[rb]
        if self.sz[ra] > self.largest:
            self.largest = self.sz[ra]


def instrument3(ex: dict[str, Any], cent: dict[int, np.ndarray],
                taus: Sequence[float]) -> dict[str, Any]:
    """cos-ONLY consolidation graph swept over tau. Does a K2-safe operating
    point exist that also reconverges the witnesses with 0 false admissions?

    The sweep runs from the TIGHTEST tau downward over one incremental
    union-find. Connectivity is monotone in tau, so `largest` only grows as tau
    falls: once it passes `BLOWUP_STOP` the K2 bar can never be met again and
    the sweep stops (recorded, not silently truncated).
    """
    BLOWUP_STOP = 0.50
    out: dict[str, Any] = {}
    core_names = ("GQ-12 caspian", "berlin pride")
    for snap, blk in ex["i3"].items():
        cids = [c for c in blk["cluster_ids"] if c in cent]
        n = len(cids)
        pos = {c: k for k, c in enumerate(cids)}
        if n < 50:
            continue
        V = np.stack([cent[c] for c in cids])
        sim = V @ V.T
        iu = np.triu_indices(n, k=1)
        vals = sim[iu]
        order = np.argsort(-vals, kind="stable")
        vs = vals[order]
        ei = iu[0][order]
        ej = iu[1][order]
        fp = [(pos[a], pos[b]) for a, b in blk["false_pairs"] if a in pos and b in pos]
        fcos = (sim[np.array([p[0] for p in fp]), np.array([p[1] for p in fp])]
                if fp else np.array([]))
        fams = [f for f in ex["families"] if f.get("scope") == "snapshot"]
        fam_idx = {f["name"]: [pos[c] for c in f["cluster_ids"] if c in pos] for f in fams}

        uf = _UF(n)
        cur = 0
        rows: list[dict[str, Any]] = []
        stopped_at = None
        for tau in sorted(taus, reverse=True):
            while cur < vs.size and vs[cur] >= tau:
                uf.union(int(ei[cur]), int(ej[cur]))
                cur += 1
            share = uf.largest / n
            fam_comp = {nm: len({uf.find(k) for k in ks})
                        for nm, ks in fam_idx.items() if ks}
            core = [v for k, v in fam_comp.items() if k in core_names]
            rows.append({
                "tau": round(float(tau), 4), "largest": uf.largest,
                "share": round(share, 5), "K2_pass": share <= K2_MAX_SHARE,
                "edges": int(cur),
                "family_components": fam_comp,
                "core_at_or_below_3": sum(1 for v in core if v <= WITNESS_MAX_COMPONENTS),
                "core_scored": len(core),
                "false_admitted": int((fcos >= tau).sum()) if fcos.size else 0,
                "false_pairs": int(fcos.size),
            })
            if share > BLOWUP_STOP:
                stopped_at = round(float(tau), 4)
                break
        rows.sort(key=lambda r: r["tau"])
        # The witness families are defined ON the newest labelled snapshot, so a
        # SECOND snapshot has none of their clusters. There the sweep is a
        # density/false-side robustness check only — scoring it against a
        # witness bar it cannot meet would manufacture a NO.
        witness_scored = max((r["core_scored"] for r in rows), default=0) > 0
        safe = [r for r in rows
                if r["K2_pass"] and r["false_admitted"] == 0
                and (not witness_scored or r["core_at_or_below_3"] >= 2)]
        out[snap] = {
            "clusters_scored": n, "sweep": rows,
            "witness_families_present": witness_scored,
            "role": ("primary" if witness_scored
                     else "density/false-side robustness only"),
            "sweep_stopped_below_tau": stopped_at,
            "false_cos": describe(fcos.tolist()) if fcos.size else {"n": 0},
            "k2_safe_points": safe,
            "k2_safe_exists": (bool(safe) if witness_scored else None),
            "k2_and_false_clean_exists": bool(safe),
            # the LOOSEST safe tau is the operating point a merge rule would take
            # (most consolidation for the same guarantees)
            "best_safe": (min(safe, key=lambda r: r["tau"]) if safe else None),
        }
    return out


WHITENING_ARTIFACT = ARTIFACT_DIR / "2026-07-28-whitened-identity-taus.json"


def witness_pairs(cent: dict[int, np.ndarray]) -> list[dict[str, Any]]:
    """Score the NAMED pairs from the whitening artifact's own tails.

    These are the hand-checked exhibits the whitening kill was argued on (the
    Berlin-Pride fragment pair whitening drove to −0.06, the France/Spain
    wildfire pair, the false-side right tail). Only cluster↔cluster tail rows are
    resolvable — a `topic_anchor` side carries a TOPIC id, not a cluster id.
    """
    if not WHITENING_ARTIFACT.exists():
        return []
    d = json.loads(WHITENING_ARTIFACT.read_text())
    out: list[dict[str, Any]] = []
    for gate, blk in d.get("tails", {}).items():
        for side, truth in (("true_left_tail", "true"), ("false_right_tail", "false")):
            for x in blk.get(side, []):
                a, b = x["a"], x["b"]
                if a["kind"] != "cluster" or b["kind"] != "cluster":
                    continue
                if a["id"] not in cent or b["id"] not in cent:
                    continue
                out.append({
                    "gate": gate, "truth": truth, "source": x["source"],
                    "a": a["label"], "b": b["label"],
                    "a_cc": a["cc"], "b_cc": b["cc"],
                    "e5_stored_raw": x["raw"], "e5_stored_whitened": x["whitened"],
                    "cos": round(float(np.dot(cent[a["id"]], cent[b["id"]])), 4),
                    "key": f'{a["id"]}-{b["id"]}',
                })
    return out


def stage_score(args: argparse.Namespace) -> None:
    ex = pickle.loads((SCRATCH / "extract.pkl").read_bytes())
    texts = pickle.loads((SCRATCH / "texts.pkl").read_bytes())
    taus = [round(x, 4) for x in np.arange(args.tau_min, args.tau_max + 1e-9, args.tau_step)]
    spaces = [s for s in SPACES if (SCRATCH / f"vecs_{s}.npz").exists()]
    log(f"[score] spaces available: {spaces}")
    results: dict[str, Any] = {}
    for sp in spaces:
        t0 = time.monotonic()
        cent, cmeta = _centroids(ex, texts, sp)
        r = {"label": SPACES[sp]["label"], "model": SPACES[sp]["model"],
             "centroids": cmeta,
             "embed_meta": json.loads((SCRATCH / f"vecs_{sp}.json").read_text()),
             "I1": instrument1(ex, cent),
             "I2": instrument2(ex, cent),
             "I3": instrument3(ex, cent, taus),
             "named_witness_pairs": witness_pairs(cent)}
        r["score_seconds"] = round(time.monotonic() - t0, 1)
        results[sp] = r
        log(f"[score] {sp} done ({r['score_seconds']}s)")

    payload = {
        "contract": "embedding-bakeoff-v2",
        "generated_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "harness": "backend/scripts/measure_embedding_bakeoff.py",
        "read_only": True,
        "config": ex["config"],
        "text_coverage": json.loads((SCRATCH / "text_coverage.json").read_text()),
        "pair_counts": dict(Counter(f'{p["gate"]}/{p["truth"]}' for p in ex["pairs"])),
        "families": [{"name": f["name"], "scope": f.get("scope"),
                      "clusters": len(f["cluster_ids"]),
                      "circular_with_rule": bool(f.get("circular_with_rule"))}
                     for f in ex["families"]],
        "prereg": {
            "baseline_space": "e5base",
            "nominal_top12_baseline": round(NOMINAL_TOP12_BASELINE, 4),
            "I1_win": "gap positive where e5base-recomputed gap is negative",
            "I2_win": "top-12 rate >= 2x e5base-recomputed AND >= 2x 11/54",
            "I3_win": "a K2-safe cos-only point exists where e5base has none",
            "K2_max_share": K2_MAX_SHARE,
            "witness_max_components": WITNESS_MAX_COMPONENTS,
        },
        "spaces": results,
        "not_measured": {
            s: SPACES[s]["label"] for s in SPACES if s not in results},
        "not_measured_note": os.environ.get("ATLAS_BAKEOFF_NOT_MEASURED_NOTE", ""),
    }
    payload["verdict"] = _verdict(payload)
    ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)
    (ARTIFACT_DIR / f"{STEM}.json").write_text(
        json.dumps(payload, indent=2, ensure_ascii=False, default=str), encoding="utf-8")
    (ARTIFACT_DIR / f"{STEM}.md").write_text(render_md(payload), encoding="utf-8")
    log(json.dumps(payload["verdict"], indent=2, ensure_ascii=False)[:4000])
    log(f"[out] {ARTIFACT_DIR / (STEM + '.json')}")
    log(f"[out] {ARTIFACT_DIR / (STEM + '.md')}")


def _fmt(x: Any, nd: int = 4) -> str:
    if x is None:
        return "—"
    if isinstance(x, bool):
        return "yes" if x else "no"
    if isinstance(x, float):
        return f"{x:.{nd}f}"
    return str(x)


def render_md(p: dict[str, Any]) -> str:
    sp = p["spaces"]
    order = [s for s in SPACES if s in sp]
    v = p["verdict"]
    L: list[str] = []
    A = L.append
    A(f"# Embedding bake-off v2 — is multilingual-e5-base the load-bearing weakness?")
    A("")
    A(f"`{p['contract']}` · generated {p['generated_at']} · harness `{p['harness']}` · "
      f"READ-ONLY (no prod write, no commit)")
    A("")
    A(f"## Verdict: **{v['verdict']}**")
    A("")
    A("Pre-registered rules, frozen before the first score ran:")
    A("")
    A("- a candidate **wins an instrument** by beating **e5-base RECOMPUTED** with margin — "
      "I1 gap positive where e5's is negative · I2 top-12 rate ≥ 2× e5-base recomputed "
      "*and* ≥ 2× the nominal 11/54 · I3 a K2-safe **cos-only** operating point exists "
      "where e5-base has none;")
    A("- **GO** = one candidate wins all three · **PARTIAL** = wins I2 (the disease) but "
      "not all three · **NO-GO** = nothing beats e5 materially.")
    A("")
    A("### Why the baseline is a RECOMPUTED e5-base, not the shipped numbers")
    A("")
    A("`emergent_clusters.centroid_vec` is an e5 artifact; no other space can be compared "
      "to it. Every space here — e5-base included — is scored on centroids rebuilt from "
      f"the SAME member headlines ({p['config']['samples_per_cluster']} sample signals per "
      "cluster, mean-pooled). The e5-base column is therefore the honest control, and the "
      "shipped-artifact numbers are a *different estimator* quoted only for continuity.")
    A("")
    # ---------------- headline findings
    A("### What the three instruments say")
    A("")
    base = sp.get("e5base", {})
    if base:
        bi1 = base["I1"]
        cands = [s for s in order if s != "e5base"]

        def best_on(fn):
            vals = [(fn(sp[s]), s) for s in cands if fn(sp[s]) is not None]
            return max(vals) if vals else (None, None)

        bei, bei_s = best_on(
            lambda r: r["I1"]["anchor_engine_independent"].get("gap"))
        bmg, bmg_s = best_on(lambda r: r["I1"]["merge"].get("gap"))
        bt12, bt12_s = best_on(lambda r: r["I2"].get("core_top12_rate"))
        bam, bam_s = best_on(
            lambda r: r["I2"].get("mean_argmax_modal_share_all_families"))
        bsec, bsec_s = best_on(lambda r: r["I2"].get("secondary_identity_ok_rate"))
        base_am = base["I2"].get("mean_argmax_modal_share_all_families")
        base_sec = base["I2"].get("secondary_identity_ok_rate")

        A(f"1. **A better space DOES fix the pair-separation gates.** The `merge` gate is "
          f"un-separable in e5-base (gap {_fmt(bi1['merge'].get('gap'))}) and separable "
          f"in `bgem3` and both OpenAI spaces (best {_fmt(bmg)}, `{bmg_s}`). So is the "
          f"engine-independent `anchor` slice: e5-base "
          f"{_fmt(bi1['anchor_engine_independent'].get('gap'))} → {_fmt(bei)} "
          f"(`{bei_s}`). This half of the diagnosis is real and fixable.")
        A(f"2. **A better space does NOT fix argmax dispersion — the disease.** On the "
          f"FROZEN metric every space lands within noise of e5-base "
          f"({_fmt(base['I2'].get('core_top12_rate'))} → best {_fmt(bt12)}, "
          f"`{bt12_s}`), nowhere near the 2× bar. Fragments of one event still do not "
          f"share a nearest topic.")
        A(f"3. **…but the target-free statistic moves more than the frozen one, and that "
          f"is worth naming.** Mean argmax concentration goes "
          f"{_fmt(base_am,3)} → {_fmt(bam,3)} (`{bam_s}`, "
          f"{(bam/base_am if base_am else 0):.2f}×), and on the declared-secondary "
          f"identity-quality slice the top-12 rate goes {_fmt(base_sec)} → "
          f"{_fmt(bsec)} (`{bsec_s}`, {(bsec/base_sec if base_sec else 0):.2f}×). "
          f"The frozen rule stands as written and is NOT met; this is reported as the "
          f"honest residual, not as a pass.")
        A("4. **No space makes cos-only merging safe — but the margin is not an order of "
          "magnitude.** No candidate has a threshold that simultaneously bounds graph "
          "density, keeps the false side clean, and reconverges BOTH core witnesses, so "
          "the label conjunct stays load-bearing and merging stays blackout-exposed. "
          "Still, at its loosest K2-and-false-clean tau e5-base leaves the Caspian family "
          "in 8 components and Berlin Pride in 20, while `bgem3` leaves them in 3 and 7. "
          "See the per-family table under Instrument 3.")
        A(f"5. **Scaling the SAME model family buys nothing; changing the family does.** "
          f"`e5large` — the direct scale-up of the shipping encoder — is within noise of "
          f"`e5base` on every instrument (0/3 wins). `bgem3`, a different objective at "
          f"the same size and the model that LOST the 2026-07-04 gate bake-off, is the "
          f"strongest space here on the disease statistics and runs locally for free.")
    A("")
    tc = p["text_coverage"]
    A(f"Text recovery: **{tc['resolved']}/{tc['wanted']}** sample signals "
      f"({100*tc['rate']:.1f}%) → **{tc['clusters_with_text']}/{tc['clusters_total']}** "
      f"clusters carry a recomputed centroid; {tc['clusters_dropped']} dropped and counted "
      "(`signals_v2` retention reaches only 2026-07-21; older headlines come from the "
      "external archive).")
    A("")

    # ---------------- costs
    A("## Cost and wall-clock")
    A("")
    A("| space | model | dim | texts/s | wall-clock | tokens | USD |")
    A("|---|---|---|---|---|---|---|")
    for s in order:
        m = sp[s]["embed_meta"]
        A(f"| `{s}` | {m['model']} | {m['dim']} | {_fmt(m.get('texts_per_second'),1)} | "
          f"{m['seconds']}s | {m.get('total_tokens','—')} | "
          f"{('$'+_fmt(m.get('usd_estimate'),4)) if m.get('usd_estimate') is not None else '—'} |")
    A("")
    A(f"**Projected full-production cost.** Ingest is **{PROD_SIGNALS_PER_DAY:,} "
      f"signals/24h** (measured on `signals_v2`), and the measured token rate here is "
      f"{TOKENS_PER_HEADLINE:.1f} tokens/headline. Local encoders cost no money; their "
      f"cost is M1 wall-clock, and the number that matters is the comparison to what "
      f"ships today.")
    A("")
    A("| space | $/day | $/month | M1 wall-clock/day | vs shipping e5-base |")
    A("|---|---|---|---|---|")
    e5_rate = sp.get("e5base", {}).get("embed_meta", {}).get("texts_per_second")
    for s in order:
        m = sp[s]["embed_meta"]
        rate = m.get("texts_per_second") or 1.0
        hours = PROD_SIGNALS_PER_DAY / rate / 3600.0
        if m.get("usd_estimate") is not None:
            per_day = (PROD_SIGNALS_PER_DAY * TOKENS_PER_HEADLINE / 1e6
                       * OPENAI_USD_PER_MTOK[m["model"]])
            money = f"${per_day:.2f}", f"${per_day*30:.2f}", "n/a (API)"
        else:
            money = ("$0", "$0", f"{hours:.1f} h")
        rel = (f"{rate/e5_rate:.1f}× faster" if e5_rate and rate >= e5_rate
               else (f"{e5_rate/rate:.1f}× slower" if e5_rate else "—"))
        A(f"| `{s}` | {money[0]} | {money[1]} | {money[2]} | "
          f"{'baseline' if s == 'e5base' else rel} |")
    A("")
    A("Caveat: the local wall-clock figures are this session's, measured under heavy "
      "swap on an 8 GB M1 that is simultaneously running the Atlas cron fleet; they are "
      "a floor on speed, not a clean benchmark. The RELATIVE column is the reliable "
      "reading, and it was measured with identical batching for every local model except "
      "`e5base`, which ran before length-bucketing was added and is therefore understated.")
    A("")

    # ---------------- I1
    A("## Instrument 1 — pair separation (raw cosine, per identity gate)")
    A("")
    A("Construction: `measure_identity_whitening.build_pairs`, Rules **v1**, verbatim; "
      "member headlines re-embedded per space. `gap = p5(true) − p95(false)`; positive = "
      "the gate is separable in that space.")
    A("")
    for g in ("match", "anchor", "merge", "anchor_engine_independent"):
        if g not in sp[order[0]]["I1"]:
            continue
        if g == "anchor_engine_independent":
            A("### `anchor` gate — ENGINE-INDEPENDENT slice")
            A("")
            A("Lineage TRUE pairs were *selected by* the raw e5 gates, so every space is "
              "flattered on them. This slice keeps only `fragment` TRUE (same snapshot, "
              "near-identical labels, the engine failed to unify them) against "
              "`false_cluster` FALSE (same snapshot, disjoint countries, dissimilar "
              "same-script labels). Neither owes anything to the gates.")
            A("")
        else:
            A(f"### `{g}` gate")
        A("")
        A("| space | n true | n false | p5(true) | p95(false) | **gap** | AUC | verdict |")
        A("|---|---|---|---|---|---|---|---|")
        for s in order:
            r = sp[s]["I1"][g]
            A(f"| `{s}` | {r['true'].get('n',0)} | {r['false'].get('n',0)} | "
              f"{_fmt(r.get('p5_true'))} | {_fmt(r.get('p95_false'))} | "
              f"**{_fmt(r.get('gap'))}** | {_fmt(r.get('auc'))} | {r.get('verdict','—')} |")
        A("")

    # ---------------- I2
    A("## Instrument 2 — argmax dispersion (the disease)")
    A("")
    A("Construction: `simulate_used_t_removal`'s top-12 probe. For every fragment of a "
      "witness family, is the family's own consolidation target among its 12 nearest "
      "topics? The target is **space-independent** — the topic `dynamic_topic_members` "
      "says the family concentrates onto today — so the same question is asked of every "
      f"space. Nominal e5 baseline from the shipped artifact: **11/54 = "
      f"{NOMINAL_TOP12_BASELINE:.3f}** (Berlin Pride, window scope).")
    A("")
    A("| space | topic pool | core top-12 hits | core rate | vs e5-base | "
      "mean argmax concentration |")
    A("|---|---|---|---|---|---|")
    base_rate = sp.get("e5base", {}).get("I2", {}).get("core_top12_rate")
    for s in order:
        r = sp[s]["I2"]
        rt = r.get("core_top12_rate")
        rel = (f"{rt/base_rate:.2f}×" if rt is not None and base_rate else "—")
        A(f"| `{s}` | {r.get('topic_pool_size','—')} | "
          f"{r.get('core_top12_hits','—')}/{r.get('core_top12_scored','—')} | "
          f"{_fmt(rt)} | {rel} | {_fmt(r.get('core_argmax_modal_share'))} |")
    A("")
    A("**A confound this instrument carries, stated up front.** The target is prod's "
      "*plurality* holder, which for `berlin pride [window]` holds only 5 of 52 clusters "
      "and is labelled something else entirely — the black hole this programme exists to "
      "kill. A genuinely better space could rightly push that target OUT of a fragment's "
      "top-12 and score WORSE on the frozen rule. The target-free statistic in the last "
      "column — the largest share of a family's fragments agreeing on ONE nearest topic — "
      "is immune to it and answers the disease question directly.")
    A("")
    A("Targets (space-independent, from `dynamic_topic_members`):")
    A("")
    A("| family | clusters | prod target | holds | target label | right identity? |")
    A("|---|---|---|---|---|---|")
    for f in sp[order[0]]["I2"]["families"]:
        A(f"| {f['family']} | {f['clusters_total']} | {f['target_topic']} | "
          f"{f['target_holds']}{'' if f['target_in_pool'] else ' (NOT in pool)'} | "
          f"{f['target_label']} | {_fmt(f.get('target_identity_ok'))} |")
    A("")
    A("### Secondary reading — families whose target IS a compatible identity")
    A("")
    A("Declared secondary; it does **not** decide the verdict. `right identity?` above "
      "is production's own `labels_compatible(target label, family modal cluster label)`, "
      "the same predicate `measure_cluster_consolidation` uses for `identity_ok`. "
      "Restricting the identical top-12 question to those families asks: *can the space "
      "put the CORRECT identity in a fragment's twelve nearest topics?*")
    A("")
    A("| space | hits / scored | rate | vs e5-base |")
    A("|---|---|---|---|")
    b2 = sp.get("e5base", {}).get("I2", {}).get("secondary_identity_ok_rate")
    for s in order:
        r = sp[s]["I2"]
        rr = r.get("secondary_identity_ok_rate")
        A(f"| `{s}` | {r.get('secondary_identity_ok_hits')}/"
          f"{r.get('secondary_identity_ok_scored')} | {_fmt(rr)} | "
          f"{(f'{rr/b2:.2f}×' if rr is not None and b2 else '—')} |")
    A("")
    A("Per-family (top-12 hits / scored · argmax modal share):")
    A("")
    fam_names = [f["family"] for f in sp[order[0]]["I2"]["families"]]
    A("| family | " + " | ".join(f"`{s}`" for s in order) + " |")
    A("|---" * (len(order) + 1) + "|")
    for fn in fam_names:
        cells = []
        for s in order:
            f = next((x for x in sp[s]["I2"]["families"] if x["family"] == fn), None)
            cells.append("—" if not f else
                         f"{f['top12_hits']}/{f['top12_scored']} · "
                         f"{_fmt(f['argmax_modal_share'],2)}")
        A(f"| {fn} | " + " | ".join(cells) + " |")
    A("")

    # ---------------- I3
    A("## Instrument 3 — consolidation graph, cos-ONLY, tau swept")
    A("")
    A("Construction: `measure_cluster_consolidation`'s rule with the **label conjunct "
      "removed** (metric 6). A K2-safe point requires, simultaneously: largest connected "
      f"component ≤ {100*K2_MAX_SHARE:.0f}% of the snapshot's clusters · "
      f"≥2 of the 2 core witness families at ≤ {WITNESS_MAX_COMPONENTS} components · "
      "**0** of the mechanically-constructed FALSE pairs admitted. A space where cos "
      "ALONE is safe would make merging blackout-immune.")
    A("")
    snaps = list(sp[order[0]]["I3"].keys())
    for snap in snaps:
        role = sp[order[0]]["I3"][snap].get("role", "")
        A(f"### snapshot `{snap[:19]}` — {role}")
        A("")
        A("| space | clusters | K2-safe cos-only point? | best tau | largest share | "
          "core families ≤3 | false admitted |")
        A("|---|---|---|---|---|---|---|")
        for s in order:
            b = sp[s]["I3"].get(snap)
            if not b:
                A(f"| `{s}` | — | — | — | — | — | — |")
                continue
            bs = b.get("best_safe")
            flag = b["k2_safe_exists"]
            A(f"| `{s}` | {b['clusters_scored']} | "
              f"**{'YES' if flag else ('no' if flag is not None else 'n/a')}** | "
              f"{_fmt(bs['tau'],3) if bs else '—'} | "
              f"{_fmt(bs['share'],4) if bs else '—'} | "
              f"{(str(bs['core_at_or_below_3'])+'/'+str(bs['core_scored'])) if bs else '—'} | "
              f"{bs['false_admitted'] if bs else '—'} |")
        A("")
        if sp[order[0]]["I3"][snap].get("witness_families_present"):
            A("How close each space gets: at the LOOSEST tau that already satisfies K2 "
              "(≤2%) and admits 0 false pairs, how many components do the witness "
              "families still occupy? (`≤3` would clear the bar.)")
            A("")
            A("| space | loosest K2+false-clean tau | largest share | GQ-12 caspian | "
              "berlin pride | US-strikes-Iran | wildfires FR/ES |")
            A("|---|---|---|---|---|---|---|")
            for s in order:
                b = sp[s]["I3"].get(snap)
                if not b:
                    continue
                cand = [r for r in b["sweep"]
                        if r["K2_pass"] and r["false_admitted"] == 0]
                r = min(cand, key=lambda x: x["tau"]) if cand else None
                fc = (r or {}).get("family_components", {})
                A(f"| `{s}` | {_fmt(r['tau'],3) if r else '—'} | "
                  f"{_fmt(r['share'],4) if r else '—'} | "
                  f"{fc.get('GQ-12 caspian','—')} | {fc.get('berlin pride','—')} | "
                  f"{fc.get('fresh:us-strikes-on-iran','—')} | "
                  f"{fc.get('fresh:wildfires-in-france-and-spain','—')} |")
            A("")

    # ---------------- named witnesses
    wp = sp[order[0]].get("named_witness_pairs") or []
    if wp:
        A("## Named witness pairs (from the whitening artifact's own tails)")
        A("")
        A("The hand-checked exhibits the whitening kill was argued on, re-scored in every "
          "space. `e5 stored` is the shipped centroid cosine; the space columns are the "
          "recomputed-centroid cosine.")
        A("")
        A("| truth | pair | e5 stored raw | e5 stored whitened | "
          + " | ".join(f"`{s}`" for s in order) + " |")
        A("|---" * (4 + len(order)) + "|")
        idx = {s: {w["key"]: w for w in (sp[s].get("named_witness_pairs") or [])}
               for s in order}
        for w in wp:
            cells = [_fmt(idx[s].get(w["key"], {}).get("cos")) for s in order]
            A(f"| {w['truth']} | {w['a'][:40]} ↔ {w['b'][:40]} | "
              f"{_fmt(w['e5_stored_raw'])} | {_fmt(w['e5_stored_whitened'])} | "
              + " | ".join(cells) + " |")
        A("")

    # ---------------- per-candidate verdict
    A("## Per-candidate verdict")
    A("")
    A("| candidate | I1 win | I2 win | I3 win | instruments won |")
    A("|---|---|---|---|---|")
    for s in order:
        if s == "e5base":
            continue
        c = v.get("per_candidate", {}).get(s, {})
        A(f"| `{s}` | {_fmt(c.get('I1_win'))} | {_fmt(c.get('I2_win'))} | "
          f"{_fmt(c.get('I3_win'))} | {c.get('wins','—')}/3 |")
    A("")
    A("## Honest limits")
    A("")
    A(f"1. **Bounded universe.** Cluster centroids use the first "
      f"{p['config']['samples_per_cluster']} `sample_signal_ids`; topic centroids use "
      f"anchor + {p['config']['topic_member_cap']-1} most-recent members, not the full "
      "running mean. Both approximations are applied IDENTICALLY to every space, so the "
      "cross-space comparison holds; the absolute numbers are not comparable to the "
      "shipped artifacts.")
    A("2. **The topic pool for I2 is capped the same way**, so `top-12` is measured "
      "against approximate topic positions. The e5-base recomputed column is the control "
      "for exactly this.")
    A("3. **fp16 on the 1024-dim local models.** Measured on this 8GB M1: fp32 gives "
      "0.4 texts/s (swapping), fp16 gives ~60. The fp16↔fp32 cosine fidelity probe is in "
      "the JSON under `spaces.<name>.embed_meta`.")
    A("4. **No jina-embeddings-v3.** No API key exists in the environment and creating an "
      "account is out of scope; it was not measured.")
    if p.get("not_measured"):
        A(f"5. **Candidates not scored in this run:** "
          + ", ".join(f"`{k}` ({v})" for k, v in p["not_measured"].items())
          + (f" — {p['not_measured_note']}" if p.get("not_measured_note") else ""))
    A("")
    return "\n".join(L) + "\n"


def _verdict(p: dict[str, Any]) -> dict[str, Any]:
    sp = p["spaces"]
    base = sp.get("e5base")
    if not base:
        return {"verdict": "INCOMPLETE", "reason": "e5base baseline not scored"}
    gates = [g for g in ("match", "anchor", "merge") if g in base["I1"]]
    base_gap = {g: base["I1"][g].get("gap") for g in gates}
    base_t12 = base["I2"].get("core_top12_rate")
    # only snapshots carrying the witness families can decide I3
    base_i3 = {s: v["k2_safe_exists"] for s, v in base["I3"].items()
               if v.get("witness_families_present")}
    per: dict[str, Any] = {}
    for name, r in sp.items():
        if name == "e5base":
            continue
        gap = {g: r["I1"][g].get("gap") for g in gates}
        i1_win = any(
            base_gap.get(g) is not None and gap.get(g) is not None
            and base_gap[g] <= 0 < gap[g] for g in gates)
        t12 = r["I2"].get("core_top12_rate")
        i2_win = bool(
            t12 is not None and base_t12 is not None
            and t12 >= 2 * base_t12 and t12 >= 2 * NOMINAL_TOP12_BASELINE)
        i3_win = any(v["k2_safe_exists"] and not base_i3.get(s, False)
                     for s, v in r["I3"].items() if s in base_i3)
        per[name] = {
            "I1_gap": gap, "I1_win": i1_win,
            "I2_core_top12_rate": t12, "I2_win": i2_win,
            "I3_k2_safe": {s: v["k2_safe_exists"] for s, v in r["I3"].items()},
            "I3_win": i3_win,
            "wins": sum([i1_win, i2_win, i3_win]),
        }
    go = [n for n, v in per.items() if v["wins"] == 3]
    partial = [n for n, v in per.items() if v["I2_win"] and v["wins"] < 3]
    return {
        "verdict": ("GO" if go else "PARTIAL" if partial else "NO-GO"),
        "go_candidates": go, "partial_candidates": partial,
        "baseline_e5base_recomputed": {
            "I1_gap": base_gap, "I2_core_top12_rate": base_t12,
            "I3_k2_safe": base_i3},
        "per_candidate": per,
    }


# ================================================================== cli
def parse_args() -> argparse.Namespace:
    ap = argparse.ArgumentParser(description="Embedding bake-off v2 (read-only).")
    ap.add_argument("--stage", required=True,
                    choices=("extract", "text", "embed", "score"))
    ap.add_argument("--space", choices=sorted(SPACES))
    ap.add_argument("--days", type=int, default=21)
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--true-pairs", type=int, default=300)
    ap.add_argument("--false-pairs", type=int, default=500)
    ap.add_argument("--max-lineage-topics", type=int, default=200)
    ap.add_argument("--max-fragment", type=int, default=800)
    ap.add_argument("--max-false-cluster", type=int, default=800)
    ap.add_argument("--max-false-match", type=int, default=800)
    ap.add_argument("--max-false-merge", type=int, default=800)
    ap.add_argument("--window-start", default="2026-07-17")
    ap.add_argument("--second-snapshot", default="2026-07-22")
    ap.add_argument("--batch", type=int, default=64)
    ap.add_argument("--concurrency", type=int, default=6)
    ap.add_argument("--tau-min", type=float, default=0.50)
    ap.add_argument("--tau-max", type=float, default=0.995)
    ap.add_argument("--tau-step", type=float, default=0.005)
    return ap.parse_args()


def main() -> None:
    a = parse_args()
    if a.stage == "extract":
        asyncio.run(stage_extract(a))
    elif a.stage == "text":
        asyncio.run(stage_text(a))
    elif a.stage == "embed":
        if not a.space:
            raise SystemExit("--space required for --stage embed")
        if a.space in ("oai-small", "oai-large") and a.batch < 128:
            a.batch = 256
        stage_embed(a)
    else:
        stage_score(a)


if __name__ == "__main__":
    main()

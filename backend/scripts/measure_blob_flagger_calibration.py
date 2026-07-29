#!/usr/bin/env python3
"""Blob-flagger calibration — read-only sweep of blob_entropy_tau × blob_indeg_min.

Trigger: docs/research/recall-229/2026-07-29-sibling-finder-v2-measurement.md §G3 —
`blob_connector_flags` (constellation_walk.py) flags 626/1022 = 61.25% of the
active field at the shipped defaults (tau=1.5, indeg_min=3), yet the G2 hand
judgments showed a real 80/60 separation (flagged share among false neighbors vs
true siblings). Real signal, wrong threshold. This harness re-fits the threshold
against a hand-labeled sample; it changes NOTHING (report + artifact only — a
change rides ATLAS_WALK_BLOB_ENTROPY_TAU / ATLAS_WALK_BLOB_INDEG_MIN env or a
reviewed commit AFTER the artifact).

DESIGN (frozen before any judging — mirrors the G2 protocol)
------------------------------------------------------------
- Field = the exact population story.py's lens caches: dynamic_topics active,
  not umbrella, centroid_vec present. Whitening + build_knn_graph(k=6) verbatim
  from app.services (same objects the endpoint calls).
- The sweep is CHEAP by construction: per-node 2-hop category entropy and
  in-degree do not depend on the thresholds, so each grid point is a pure
  2-D threshold over precomputed (entropy, indeg).
- Sample: 40 topics = 8 entropy octiles × 5, seeded RNG (BLOB_SEED). Octiles
  are equal field mass, so the stratified sample is self-weighting — sample
  precision/recall estimate field precision/recall directly.
- Judging is BLIND: the judging worksheet carries ONLY id + label + up to 12
  member evidence headlines. Entropy/indeg/current-flag stay in a separate meta
  file the judge does not read. Verdicts: blob | clean | unsure.
    blob  = members span 2+ distinct stories (fusion / grab-bag)
    clean = members cohere to one event or one tight running story
  Unsure counts AGAINST the flagger (a flagged unsure = false positive), the
  same conservative rule G2 used.
- Selection rule (frozen HERE, before judging): among grid points with
  field_flag_rate <= 0.25 AND sample precision >= 0.70 (conservative),
  maximize blob RECALL; ties -> higher precision, then lower flag rate.
  If the feasible set is empty, report the honest frontier and no pick.

READ-ONLY DISCIPLINE
--------------------
Every connection runs `SET default_transaction_read_only = on` before any
query. Zero writes. `backend/app/` is never modified.

USAGE
-----
  set -a; . ~/AtlasLocalWorker/.env; set +a
  cd backend
  python -m scripts.measure_blob_flagger_calibration --pull    # cache field
  python -m scripts.measure_blob_flagger_calibration --prep    # sweep + sample + worksheet
  # hand-judge worksheet -> blob_calib_judgments.json (blind: labels+headlines only)
  python -m scripts.measure_blob_flagger_calibration --report  # artifact JSON+MD
"""
from __future__ import annotations

import argparse
import asyncio
import json
import os
import pickle
import random
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

try:
    from app.services.constellation_walk import (
        WalkParams,
        build_knn_graph,
        category_entropy,
    )
    from app.services.whitening import apply_whitening, load_whitening
except ImportError:  # pragma: no cover
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from app.services.constellation_walk import (
        WalkParams, build_knn_graph, category_entropy,
    )
    from app.services.whitening import apply_whitening, load_whitening

REPO_ROOT = Path(__file__).resolve().parents[2]
ARTIFACT_DIR = REPO_ROOT / "docs" / "research" / "recall-229"
ARTIFACT_STEM = "2026-07-29-blob-flagger-calibration"
SCRATCH = Path(os.environ.get("ATLAS_BLOB_CALIB_SCRATCH", "/tmp"))

FIELD_CACHE = SCRATCH / "blob_calib_field.pkl"
META_JSON = SCRATCH / "blob_calib_meta.json"          # judge must NOT read
WORKSHEET_JSON = SCRATCH / "blob_calib_worksheet.json"  # judge reads ONLY this
JUDGMENTS_JSON = SCRATCH / "blob_calib_judgments.json"

BLOB_SEED = 20260729
N_STRATA = 8
PER_STRATUM = 5
HEADLINES_PER_TOPIC = 12

# Frozen sweep grid.
TAU_GRID = [round(1.0 + 0.1 * i, 1) for i in range(25)]   # 1.0 .. 3.4
INDEG_GRID = [3, 4, 5, 6, 7, 8, 10, 12]

# Frozen operating-point constraints (the task's pre-stated targets).
MAX_FLAG_RATE = 0.25
MIN_PRECISION = 0.70

_TOPICS_SQL = """
    SELECT id, label, category, label_status, centroid_vec, agg_n_signals
    FROM dynamic_topics
    WHERE state = 'active' AND NOT is_umbrella AND centroid_vec IS NOT NULL
"""

# Member scoping VERBATIM story.py/_MEMBERS scoping (finder-v2 harness reuse).
_MEMBERS_SQL = """
    SELECT tm.topic_id, s.headline, s.created_at
    FROM topic_members tm
    JOIN signals_v2 s ON s.id = tm.signal_id
    WHERE tm.topic_id = ANY($1::text[])
      AND tm.role = 'evidence'
      AND tm.engine_version = 'v1-compat'
      AND tm.quarantined IS NOT TRUE
      AND tm.assigned_at > NOW() - INTERVAL '7 days'
    ORDER BY s.created_at DESC
"""


async def _pull_topics() -> list[dict]:
    import asyncpg

    dsn = os.environ.get("DATABASE_URL")
    if not dsn:
        raise SystemExit("DATABASE_URL not set (set -a; . ~/AtlasLocalWorker/.env; set +a)")
    conn = await asyncpg.connect(dsn, statement_cache_size=0)
    try:
        await conn.execute("SET default_transaction_read_only = on")
        await conn.execute("SET statement_timeout = 240000")
        rows = await conn.fetch(_TOPICS_SQL)
    finally:
        await conn.close()
    topics = []
    for r in rows:
        v = r["centroid_vec"]
        if v is None or len(v) != 768:
            continue
        tid = int(r["id"])
        topics.append({
            "key": f"dynamic-topic-{tid}",
            "id": tid,
            "label": r["label"] or f"dynamic-topic-{tid}",
            "category": r["category"],
            "label_status": r["label_status"],
            "agg_n_signals": int(r["agg_n_signals"] or 0),
            "vec": [float(x) for x in v],
        })
    return topics


async def _pull_headlines(keys: list[str]) -> dict[str, list[str]]:
    import asyncpg

    dsn = os.environ.get("DATABASE_URL")
    conn = await asyncpg.connect(dsn, statement_cache_size=0)
    try:
        await conn.execute("SET default_transaction_read_only = on")
        await conn.execute("SET statement_timeout = 120000")
        rows = await conn.fetch(_MEMBERS_SQL, keys)
    finally:
        await conn.close()
    out: dict[str, list[str]] = {k: [] for k in keys}
    for r in rows:
        k = r["topic_id"]
        h = (r["headline"] or "").strip()
        if not h:
            continue
        lst = out.setdefault(k, [])
        if h not in lst and len(lst) < HEADLINES_PER_TOPIC:
            lst.append(h)
    return out


def cmd_pull() -> None:
    topics = asyncio.run(_pull_topics())
    FIELD_CACHE.parent.mkdir(parents=True, exist_ok=True)
    with open(FIELD_CACHE, "wb") as f:
        pickle.dump({"pulled_at": datetime.now(timezone.utc).isoformat(),
                     "topics": topics}, f)
    print(f"pulled {len(topics)} active topics -> {FIELD_CACHE}")


def _load_field() -> dict:
    with open(FIELD_CACHE, "rb") as f:
        return pickle.load(f)


def _compute_features(topics: list[dict]) -> tuple[np.ndarray, np.ndarray, list]:
    """Per-node (entropy, indeg) on the endpoint-identical graph."""
    vecs = np.asarray([t["vec"] for t in topics], dtype=np.float32)
    cats = [t["category"] for t in topics]
    whitening = load_whitening()
    whitened = apply_whitening(vecs, whitening)
    params = WalkParams()  # shipped defaults; k=6 locked, not swept
    graph = build_knn_graph(whitened, k=params.k)
    ent = np.array([category_entropy(graph.nbrs, cats, i) for i in range(graph.n)],
                   dtype=np.float32)
    indeg = np.asarray(graph.indeg, dtype=np.int32)
    return ent, indeg, cats


def cmd_prep() -> None:
    field = _load_field()
    topics = field["topics"]
    n = len(topics)
    ent, indeg, _cats = _compute_features(topics)

    # Grid flag rates on the full field.
    grid = []
    for tau in TAU_GRID:
        for dmin in INDEG_GRID:
            flagged = (indeg >= dmin) & (ent >= tau)
            grid.append({"tau": tau, "indeg_min": dmin,
                         "field_flagged": int(flagged.sum()),
                         "field_flag_rate": round(float(flagged.mean()), 4)})

    cur = (indeg >= 3) & (ent >= 1.5)
    print(f"field n={n}  current defaults flag {int(cur.sum())} = {cur.mean():.2%}")

    # Stratified sample: entropy octiles × PER_STRATUM, seeded.
    rng = random.Random(BLOB_SEED)
    order = np.argsort(ent, kind="stable")
    strata = np.array_split(order, N_STRATA)
    sample_idx: list[int] = []
    for s in strata:
        sample_idx.extend(rng.sample(list(map(int, s)), PER_STRATUM))

    keys = [topics[i]["key"] for i in sample_idx]
    heads = asyncio.run(_pull_headlines(keys))

    # BLIND worksheet: id + label + headlines ONLY.
    worksheet = [{
        "key": topics[i]["key"],
        "label": topics[i]["label"],
        "headlines": heads.get(topics[i]["key"], []),
        "verdict": None,
        "note": "",
    } for i in sample_idx]
    with open(WORKSHEET_JSON, "w") as f:
        json.dump(worksheet, f, indent=1, ensure_ascii=False)

    # Meta (features per sampled node + grid) — the judge does not read this.
    meta = {
        "computed_at": datetime.now(timezone.utc).isoformat(),
        "pulled_at": field["pulled_at"],
        "n_field": n,
        "seed": BLOB_SEED,
        "current_defaults": {"tau": 1.5, "indeg_min": 3,
                             "field_flagged": int(cur.sum()),
                             "field_flag_rate": round(float(cur.mean()), 4)},
        "grid": grid,
        "sample": [{
            "key": topics[i]["key"],
            "entropy": round(float(ent[i]), 4),
            "indeg": int(indeg[i]),
            "n_signals": topics[i]["agg_n_signals"],
            "category": topics[i]["category"],
        } for i in sample_idx],
        "field_features": {
            "entropy": [round(float(x), 4) for x in ent],
            "indeg": [int(x) for x in indeg],
        },
    }
    with open(META_JSON, "w") as f:
        json.dump(meta, f, indent=1)
    print(f"worksheet ({len(worksheet)} topics) -> {WORKSHEET_JSON}")
    print(f"meta -> {META_JSON}")


def cmd_report() -> None:
    with open(META_JSON) as f:
        meta = json.load(f)
    with open(JUDGMENTS_JSON) as f:
        judged = json.load(f)

    verdicts = {r["key"]: r["verdict"] for r in judged}
    notes = {r["key"]: r.get("note", "") for r in judged}
    missing = [r["key"] for r in judged if r["verdict"] not in ("blob", "clean", "unsure")]
    if missing:
        raise SystemExit(f"unjudged rows: {missing}")

    sample = meta["sample"]
    for s in sample:
        s["verdict"] = verdicts[s["key"]]
        s["note"] = notes[s["key"]]

    n_blob = sum(1 for s in sample if s["verdict"] == "blob")
    n_clean = sum(1 for s in sample if s["verdict"] == "clean")
    n_unsure = sum(1 for s in sample if s["verdict"] == "unsure")

    def point_stats(tau: float, dmin: int) -> dict:
        tp = fp = fn = 0
        for s in sample:
            flagged = s["indeg"] >= dmin and s["entropy"] >= tau
            is_blob = s["verdict"] == "blob"           # unsure counts against
            if flagged and is_blob:
                tp += 1
            elif flagged and not is_blob:
                fp += 1
            elif (not flagged) and is_blob:
                fn += 1
        prec = tp / (tp + fp) if (tp + fp) else None
        rec = tp / (tp + fn) if (tp + fn) else None
        return {"tp": tp, "fp": fp, "fn": fn,
                "precision": round(prec, 4) if prec is not None else None,
                "recall": round(rec, 4) if rec is not None else None}

    rows = []
    for g in meta["grid"]:
        st = point_stats(g["tau"], g["indeg_min"])
        rows.append({**g, **st})

    # Frozen selection rule.
    feasible = [r for r in rows
                if r["field_flag_rate"] <= MAX_FLAG_RATE
                and r["precision"] is not None and r["precision"] >= MIN_PRECISION
                and r["recall"] is not None]
    feasible.sort(key=lambda r: (-r["recall"], -r["precision"], r["field_flag_rate"]))
    pick = feasible[0] if feasible else None

    cur = point_stats(1.5, 3)
    artifact = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "field_pulled_at": meta["pulled_at"],
        "n_field": meta["n_field"],
        "seed": meta["seed"],
        "design": {
            "strata": N_STRATA, "per_stratum": PER_STRATUM,
            "grid_tau": TAU_GRID, "grid_indeg": INDEG_GRID,
            "constraints": {"max_flag_rate": MAX_FLAG_RATE,
                            "min_precision": MIN_PRECISION},
            "selection": "max recall s.t. constraints; ties: precision, then flag rate",
            "conservative": "unsure counts against the flagger",
            "blind": "judging worksheet carried only label+headlines",
        },
        "sample_verdicts": {"blob": n_blob, "clean": n_clean, "unsure": n_unsure},
        "current_defaults": {**meta["current_defaults"], **cur},
        "pick": pick,
        "feasible_top10": feasible[:10],
        "grid": rows,
        "sample": sample,
    }
    ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)
    out = ARTIFACT_DIR / f"{ARTIFACT_STEM}.json"
    with open(out, "w") as f:
        json.dump(artifact, f, indent=1, ensure_ascii=False)
    print(f"artifact -> {out}")
    if pick:
        print(f"PICK tau={pick['tau']} indeg_min={pick['indeg_min']} "
              f"flag_rate={pick['field_flag_rate']:.2%} "
              f"precision={pick['precision']} recall={pick['recall']}")
    else:
        print("NO feasible operating point — see frontier in artifact")
    print(f"current: flag_rate={meta['current_defaults']['field_flag_rate']:.2%} "
          f"precision={cur['precision']} recall={cur['recall']}")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--pull", action="store_true")
    ap.add_argument("--prep", action="store_true")
    ap.add_argument("--report", action="store_true")
    args = ap.parse_args()
    if args.pull:
        cmd_pull()
    elif args.prep:
        cmd_prep()
    elif args.report:
        cmd_report()
    else:
        ap.print_help()


if __name__ == "__main__":
    main()

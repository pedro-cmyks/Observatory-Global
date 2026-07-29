#!/usr/bin/env python3
"""Gate GC — does the membership-multimodality confirmer actually separate
genuine event fragments from real blobs, on the two witness sets the identity-
three-levers plan pre-registered?

Plan: docs/superpowers/plans/2026-07-29-identity-three-levers.md, Lever C2,
gate GC (frozen BEFORE this run):

  "on the finder-v2 G1 true-positive set (11 rows), confirmed-blob rate <= 3/11
  (was 6/11 flagged) while dt-466 and the calibration sample's hand-labeled
  blobs stay flagged >= 7/9. Kill: if the confirmer can't separate on those
  witnesses, the chip keeps entropy flags AND gains a 'candidate' qualifier
  in the tooltip — never silently better-looking."

Two witness sets, both frozen by construction (ids lifted verbatim from the
cited artifacts, not re-derived here):

  WITNESS A — the 11 G1 true-positive siblings (finder-v2 measurement.json
  §G1, `v1_true` lists for the 3 eligible gate families: berlin-pride from
  anchor dt-7712, fresh:trump-threatens-iran from dt-2854, fresh:trump-
  imposes-50-tariffs-on-canada from dt-5494). These are GENUINE same-event
  fragments — the confirmer should CLEAR most of the entropy flags on them
  (entropy over-fired on real single-story siblings; C2 fixes that).

  WITNESS B — the 9-row sample flagged at the (2.6, 4) calibration pick
  (blob-flagger-calibration.json `sample`, filtered to entropy>=2.6 AND
  indeg>=4), 7 hand-labeled 'blob' + 2 hand-labeled 'clean' (precision 7/9).
  These are the FLAGGER'S OWN validated population — the confirmer should
  PRESERVE the flag on the real blobs.

READ-ONLY DISCIPLINE: every connection runs
`SET default_transaction_read_only = on`. Zero writes.

USAGE
-----
  set -a; . ~/AtlasLocalWorker/.env; set +a
  cd backend
  python -m scripts.measure_c2_confirmer_check
"""
from __future__ import annotations

import asyncio
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

try:
    from app.services.constellation_walk import (
        WalkParams,
        blob_basis_for_ui,
        blob_connector_flags,
        build_knn_graph,
        confirm_blob_candidates,
    )
    from app.services.whitening import apply_whitening, load_whitening
except ImportError:  # pragma: no cover
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from app.services.constellation_walk import (  # type: ignore[no-redef]
        WalkParams, blob_basis_for_ui, blob_connector_flags,
        build_knn_graph, confirm_blob_candidates,
    )
    from app.services.whitening import apply_whitening, load_whitening  # type: ignore[no-redef]

import asyncpg

REPO_ROOT = Path(__file__).resolve().parents[2]
ARTIFACT_DIR = REPO_ROOT / "docs" / "research" / "recall-229"

# WITNESS A: the 11 G1 true-positive siblings (finder-v2 measurement.json §G1,
# `v1_true` per eligible gate family — verbatim, not re-derived).
WITNESS_A_IDS = [
    # berlin-pride, v1 anchor dt-7712, v1_true (6)
    "dynamic-topic-7647", "dynamic-topic-7717", "dynamic-topic-7715",
    "dynamic-topic-7356", "dynamic-topic-7714", "dynamic-topic-7716",
    # fresh:trump-threatens-iran, v1 anchor dt-2854, v1_true (2)
    "dynamic-topic-6993", "dynamic-topic-2805",
    # fresh:trump-imposes-50-tariffs-on-canada, v1 anchor dt-5494, v1_true (3)
    "dynamic-topic-5340", "dynamic-topic-5488", "dynamic-topic-5492",
]

# WITNESS B: the 9 rows flagged at (tau=2.6, indeg_min=4) in the blob-flagger
# calibration sample (blob-flagger-calibration.json `sample`, filtered
# entropy>=2.6 AND indeg>=4) — 7 hand-labeled 'blob', 2 'clean'.
WITNESS_B = [
    ("dynamic-topic-2526", "blob"),
    ("dynamic-topic-3660", "blob"),
    ("dynamic-topic-2733", "blob"),
    ("dynamic-topic-79", "blob"),
    ("dynamic-topic-901", "blob"),
    ("dynamic-topic-2774", "clean"),
    ("dynamic-topic-6975", "clean"),
    ("dynamic-topic-3567", "blob"),
    ("dynamic-topic-3902", "blob"),
]

_TOPICS_SQL = """
    SELECT id, label, category, label_status, centroid_vec
    FROM dynamic_topics
    WHERE state = 'active' AND NOT is_umbrella AND centroid_vec IS NOT NULL
"""

# Mirrors app/routers/story.py's _BLOB_MEMBERS_SQL (== dossier.py's
# _WALK_BLOB_MEMBERS_SQL pattern) verbatim.
_BLOB_MEMBERS_SQL = """
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
MEMBERS_CAP = 200


async def _pull_field() -> tuple[list[str], list[str | None], np.ndarray]:
    dsn = os.environ["DATABASE_URL"]
    conn = await asyncpg.connect(dsn, statement_cache_size=0)
    try:
        await conn.execute("SET default_transaction_read_only = on")
        rows = await conn.fetch(_TOPICS_SQL)
    finally:
        await conn.close()
    keys: list[str] = []
    cats: list[str | None] = []
    vecs: list[list[float]] = []
    for r in rows:
        v = r["centroid_vec"]
        if v is None or len(v) != 768:
            continue
        keys.append(f"dynamic-topic-{int(r['id'])}")
        cats.append(r["category"])
        vecs.append([float(x) for x in v])
    return keys, cats, np.asarray(vecs, dtype=np.float32)


async def _fetch_member_vecs(topic_ids: list[str],
                             idx_by_tid: dict[int, int]) -> dict[int, np.ndarray]:
    if not topic_ids:
        return {}
    dsn = os.environ["DATABASE_URL"]
    conn = await asyncpg.connect(dsn, statement_cache_size=0)
    try:
        await conn.execute("SET default_transaction_read_only = on")
        rows = await conn.fetch(_BLOB_MEMBERS_SQL, topic_ids, MEMBERS_CAP)
    finally:
        await conn.close()
    by_idx: dict[int, list] = {}
    for r in rows:
        node_i = idx_by_tid.get(int(r["tid"]))
        if node_i is None:
            continue
        try:
            vec = np.asarray(json.loads(r["vec"]), dtype=np.float32)
        except Exception:
            continue
        by_idx.setdefault(node_i, []).append(vec)
    return {i: np.vstack(v) for i, v in by_idx.items() if v}


async def main() -> None:
    keys, cats, vecs = await _pull_field()
    key_to_idx = {k: i for i, k in enumerate(keys)}
    print(f"field: {len(keys)} active story topics")

    whitening = load_whitening()
    whitened = apply_whitening(vecs, whitening)
    # WalkParams() literal defaults — NOT from_env() — mirrors the frozen
    # methodology of both cited measurements (finder-v2 C4: "WalkParams()
    # LOCKED defaults, not from_env() — env drift must not move a gate"), so
    # the "was 6/11" / precision-7/9 baselines are reproduced on the SAME
    # entropy_tau/indeg_min the artifacts used, independent of whatever C1
    # env vars may or may not be live wherever this runs.
    params = WalkParams()
    graph = build_knn_graph(whitened, k=params.k)
    blobs = blob_connector_flags(graph, cats, params)
    print(f"entropy candidates (tau={params.blob_entropy_tau}, "
          f"indeg_min={params.blob_indeg_min}): {len(blobs)}/{len(keys)} "
          f"= {len(blobs)/len(keys):.4f}")

    async def confirm(ids: list[str]) -> dict[str, tuple[bool, str | None, int | None]]:
        """id -> (is_blob, blob_basis, idx). idx None when the id has aged
        out of the current active field (honest, not a failure)."""
        present = {i: key_to_idx[i] for i in ids if i in key_to_idx}
        missing = [i for i in ids if i not in key_to_idx]
        if missing:
            print(f"  (aged out of the active field, not scored: {missing})")
        candidate_idx = {i: idx for i, idx in present.items() if idx in blobs}
        idx_by_tid = {int(i.rsplit("-", 1)[1]): idx for i, idx in candidate_idx.items()}
        member_vecs = await _fetch_member_vecs(list(candidate_idx.keys()), idx_by_tid)
        confirmations = confirm_blob_candidates(set(candidate_idx.values()), member_vecs)
        out: dict[str, tuple[bool, str | None, int | None]] = {}
        for i, idx in present.items():
            if idx not in blobs:
                out[i] = (False, None, idx)
                continue
            is_blob, basis = blob_basis_for_ui(confirmations.get(idx))
            out[i] = (is_blob, basis, idx)
        return out

    print("\n=== WITNESS A — 11 G1 true-positive siblings (genuine fragments) ===")
    a = await confirm(WITNESS_A_IDS)
    raw_flagged_a = sum(1 for _is_blob, basis, idx in a.values() if idx in blobs)
    confirmed_a = sum(1 for is_blob, basis, _idx in a.values() if is_blob and basis == "confirmed")
    any_flag_a = sum(1 for is_blob, _b, _i in a.values() if is_blob)
    for i, (is_blob, basis, idx) in a.items():
        raw = "candidate" if idx in blobs else "not-candidate"
        print(f"  {i}: raw={raw} is_blob={is_blob} basis={basis}")
    print(f"raw entropy-candidate count: {raw_flagged_a}/{len(a)}")
    print(f"CONFIRMED-only count: {confirmed_a}/{len(a)}  (any-flag incl. "
          f"candidate_unconfirmed: {any_flag_a}/{len(a)})")
    print(f"GC target: confirmed-blob rate <= 3/11 -> "
          f"{'PASS' if confirmed_a <= 3 else 'FAIL'}")

    print("\n=== WITNESS B — 9-row (2.6,4) calibration sample (7 blob / 2 clean) ===")
    b_ids = [i for i, _v in WITNESS_B]
    b = await confirm(b_ids)
    verdict_by_id = dict(WITNESS_B)
    confirmed_b = sum(1 for is_blob, basis, _idx in b.values() if is_blob and basis == "confirmed")
    any_flag_b = sum(1 for is_blob, _b, _i in b.values() if is_blob)
    confirmed_true_blobs = sum(
        1 for i, (is_blob, basis, _idx) in b.items()
        if verdict_by_id.get(i) == "blob" and is_blob and basis == "confirmed"
    )
    for i, (is_blob, basis, idx) in b.items():
        raw = "candidate" if idx in blobs else "not-candidate"
        print(f"  {i}: hand-label={verdict_by_id.get(i)} raw={raw} "
              f"is_blob={is_blob} basis={basis}")
    print(f"CONFIRMED-only count (all 9): {confirmed_b}/{len(b)}  "
          f"(any-flag incl. candidate_unconfirmed: {any_flag_b}/{len(b)})")
    print(f"CONFIRMED-only count among the 7 hand-labeled TRUE blobs: "
          f"{confirmed_true_blobs}/7")
    print(f"GC target: confirmed >= 7/9 stay flagged -> "
          f"{'PASS' if confirmed_b >= 7 else 'FAIL'}")

    gc_pass = confirmed_a <= 3 and confirmed_b >= 7
    print(f"\n=== GC VERDICT: {'PASS' if gc_pass else 'FAIL — KILL, keep candidate qualifier'} ===")

    ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)
    out_json = {
        "contract": "c2-confirmer-check-v1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "field_n": len(keys),
        "params": {"blob_entropy_tau": params.blob_entropy_tau,
                   "blob_indeg_min": params.blob_indeg_min},
        "witness_a": {i: {"is_blob": v[0], "blob_basis": v[1]} for i, v in a.items()},
        "witness_a_raw_flagged": raw_flagged_a,
        "witness_a_confirmed": confirmed_a,
        "witness_a_any_flag": any_flag_a,
        "witness_b": {i: {"hand_label": verdict_by_id.get(i), "is_blob": v[0],
                         "blob_basis": v[1]} for i, v in b.items()},
        "witness_b_confirmed": confirmed_b,
        "witness_b_any_flag": any_flag_b,
        "witness_b_confirmed_true_blobs_of_7": confirmed_true_blobs,
        "gc_pass": gc_pass,
    }
    out_path = ARTIFACT_DIR / "2026-07-29-c2-confirmer-check.json"
    out_path.write_text(json.dumps(out_json, indent=2))
    print(f"\nwrote {out_path}")


if __name__ == "__main__":
    asyncio.run(main())

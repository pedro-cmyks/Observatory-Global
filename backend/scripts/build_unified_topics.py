"""Unified Engine F3.1 — unified-v2 construction (spec 2026-06-29-atlas-unified-engine §6).

The ONE-engine pass that kills the split-brain: instead of atlas-lexical ‖
dynamic-embedding ‖ discussion-attach (three pipelines, three outputs), a SINGLE
assignment over the universal substrate (the e5 embedding) assigns EVERY embedded
signal — press, forum, (event in F3.3) — to its nearest topic centroid, and the
role separation (evidence/discussion/mood/movement) happens by source_family at
write time. Output: topic_members(engine_version='unified-v2'), the row the A/B
(`engine_ab_report.py`) compares to the v1-compat projection over the same window.

Anchors = the active `dynamic_topics` centroids (the embedding-native topics).
This is the spec §6 "join the nearest existing topic centroid above threshold";
new-topic formation from unassigned dense regions is the documented residual
(§6 step 2, deferred — it is what gives v2 its RECALL edge and is the next slice).

Role map (the separation, at construction, by source_family):
  press/institutional (gdelt/independent/wire/state/ngo/gov) -> evidence
  social                                                     -> discussion (+ mood if nlp_sentiment present)
  event (vessels/aircraft/ACLED/anomalies)                   -> movement  (F3.3)

Honesty invariants (spec §15) carried verbatim: evidence never mixes
discussion/mood; social is verified=false; gate_kept is evidence-only (here a
v2-native CENTROID gate: on-topic confidence = similarity >= gate-threshold,
distinct from v1's lexical scope gate — the A/B measures whether it holds up).

Run (M1 mlvenv — numpy over precomputed embeddings, no torch):
  python -m backend.scripts.build_unified_topics --hours 48 [--dry-run]
"""
from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
from typing import Any

import asyncpg
import numpy as np

ENGINE_VERSION = "unified-v2"

# e5 vectors are L2-normalized, so euclidean on them is monotone in cosine —
# HDBSCAN's default euclidean is fine. 'leaf' keeps fine sub-clusters (prevents
# the #224 mega-blob) at the cost of recall (the companion-spec cliff).
def _cluster_leaf(embs: np.ndarray, min_cluster_size: int, min_samples: int) -> np.ndarray:
    import hdbscan
    return hdbscan.HDBSCAN(
        min_cluster_size=min_cluster_size,
        min_samples=min_samples,
        metric="euclidean",
        cluster_selection_method="leaf",
        core_dist_n_jobs=-1,
    ).fit_predict(embs)

# press/institutional families → evidence; social → discussion. (event → movement
# in F3.3; those live in separate tables, not signals_v2.source_family.)
_EVIDENCE_FAMILIES = frozenset({"gdelt", "independent", "wire", "state", "ngo", "gov", "press"})

# Defaults; calibratable. Signal↔centroid cosine (e5). assign = join the topic;
# gate = "clearly on-topic" (the v2-native evidence gate).
DEFAULT_ASSIGN_THRESHOLD = 0.82
DEFAULT_GATE_THRESHOLD = 0.86


def _parse_vec(text: str) -> np.ndarray:
    # halfvec / real[] render as '[0.1,0.2,...]' or '{0.1,0.2,...}'
    return np.asarray(json.loads(text.replace("{", "[").replace("}", "]")), dtype=np.float32)


def _normalize(m: np.ndarray) -> np.ndarray:
    n = np.linalg.norm(m, axis=1, keepdims=True)
    n[n == 0] = 1.0
    return m / n


async def _load_centroids(conn: asyncpg.Connection) -> tuple[list[int], np.ndarray]:
    rows = await conn.fetch(
        """SELECT id, centroid_vec::text AS vec FROM dynamic_topics
           WHERE state='active' AND centroid_vec IS NOT NULL"""
    )
    ids = [int(r["id"]) for r in rows]
    mat = _normalize(np.vstack([_parse_vec(r["vec"]) for r in rows])) if rows else np.zeros((0, 768))
    return ids, mat


async def _load_signals(conn: asyncpg.Connection, hours: int, max_n: int) -> list[dict[str, Any]]:
    return await conn.fetch(
        f"""
        SELECT s.id, s.source_family, s.nlp_sentiment, e.vec::text AS vec
        FROM signal_embeddings e
        JOIN signals_v2 s ON s.id = e.signal_id
        WHERE s.timestamp > NOW() - ($1::int * INTERVAL '1 hour')
          AND s.headline IS NOT NULL AND length(s.headline) >= 20
        ORDER BY s.timestamp DESC
        LIMIT {int(max_n)}
        """,
        hours,
    )


def _role_for(family: str | None) -> str:
    return "discussion" if (family or "") == "social" else "evidence"


async def run(hours: int, assign_t: float, gate_t: float, max_n: int, dry_run: bool,
              new_mcs: int, new_ms: int, no_new_topics: bool) -> int:
    dsn = os.environ.get("DATABASE_URL")
    if not dsn:
        print("DATABASE_URL not set", file=sys.stderr)
        return 2
    conn = await asyncpg.connect(dsn)
    try:
        topic_ids, centroids = await _load_centroids(conn)
        if not topic_ids:
            print("no active dynamic_topics with centroids — nothing to anchor", file=sys.stderr)
            return 1
        sig_rows = await _load_signals(conn, hours, max_n)
        if not sig_rows:
            print("no embedded signals in window")
            return 0

        sig_vecs = _normalize(np.vstack([_parse_vec(r["vec"]) for r in sig_rows]))
        # cosine = normalized dot; (n_sig x dim) @ (dim x n_topic) → (n_sig x n_topic)
        sims = sig_vecs @ centroids.T
        best = sims.argmax(axis=1)
        best_sim = sims[np.arange(len(sig_rows)), best]

        members: list[tuple] = []
        mood_rows = 0
        sim_assigned: list[float] = []

        def _emit(idx: int, topic_id: str, conf: float, gate_ok: bool) -> None:
            nonlocal mood_rows
            row = sig_rows[idx]
            family = row["source_family"]
            role = _role_for(family)
            gate_kept = (role == "evidence") and gate_ok
            members.append((int(row["id"]), topic_id, role, family, "semantic", conf, gate_kept))
            if role == "discussion" and row["nlp_sentiment"] is not None:
                members.append((int(row["id"]), topic_id, "mood", family, "semantic", conf, None))
                mood_rows += 1

        # Pass 1 — join the nearest EXISTING topic centroid above threshold.
        skipped_idx: list[int] = []
        for i in range(len(sig_rows)):
            s = float(best_sim[i])
            if s < assign_t:
                skipped_idx.append(i)
                continue
            _emit(i, f"dynamic-topic-{topic_ids[int(best[i])]}", s, s >= gate_t)
            sim_assigned.append(s)
        assigned = len(sim_assigned)
        skipped = len(skipped_idx)

        # Pass 2 — NEW-TOPIC FORMATION (spec §6 step 2): cluster the unassigned
        # residual so v2 recovers the recall that assign-to-existing sheds. 'leaf'
        # selection (anti-mega-blob); the companion spec warns this is a cliff, so
        # the A/B MEASURES whether recall actually recovers or shatters into noise.
        new_topics = new_members = 0
        if not no_new_topics and len(skipped_idx) >= new_mcs:
            sk = sig_vecs[skipped_idx]
            labels = _cluster_leaf(sk, new_mcs, new_ms)
            for lab in sorted(set(int(x) for x in labels) - {-1}):
                local = [skipped_idx[j] for j, l in enumerate(labels) if int(l) == lab]
                cvecs = _normalize(sig_vecs[local])
                centroid = cvecs.mean(axis=0)
                cn = np.linalg.norm(centroid)
                if cn == 0:
                    continue
                centroid = centroid / cn
                cohes = sig_vecs[local] @ centroid
                tid = f"unified-new-{lab}"
                for k, idx in enumerate(local):
                    _emit(idx, tid, float(cohes[k]), float(cohes[k]) >= gate_t)
                new_topics += 1
                new_members += len(local)
            print(f"  new-topic formation: {new_topics} topics, {new_members} members "
                  f"recovered from {len(skipped_idx)} skipped "
                  f"({new_members/max(len(skipped_idx),1):.1%} of residual)")

        by_role: dict[str, int] = {}
        for m in members:
            by_role[m[2]] = by_role.get(m[2], 0) + 1
        med = float(np.median(sim_assigned)) if sim_assigned else 0.0
        total_assigned = assigned + new_members
        print(f"centroids={len(topic_ids)} signals={len(sig_rows)} "
              f"pass1_assigned={assigned} skipped={skipped} "
              f"+new={new_members} → total={total_assigned} "
              f"(coverage {total_assigned/len(sig_rows):.1%})")
        print(f"  median pass1 sim={med:.3f} | members by role={by_role} mood+={mood_rows}")

        if dry_run:
            print("(dry-run — no rows written)")
            return 0

        # replace this engine_version's rows for a clean rebuild over the window
        await conn.execute("DELETE FROM topic_members WHERE engine_version=$1", ENGINE_VERSION)
        await conn.executemany(
            """INSERT INTO topic_members
               (signal_id, topic_id, role, source_family, basis, confidence, gate_kept, engine_version)
               VALUES ($1,$2,$3,$4,$5,$6,$7, 'unified-v2')
               ON CONFLICT DO NOTHING""",
            members,
        )
        written = await conn.fetchval(
            "SELECT count(*) FROM topic_members WHERE engine_version=$1", ENGINE_VERSION)
        print(f"wrote {written} topic_members(unified-v2)")
        return 0
    finally:
        await conn.close()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--hours", type=int, default=48)
    ap.add_argument("--assign-threshold", type=float, default=DEFAULT_ASSIGN_THRESHOLD)
    ap.add_argument("--gate-threshold", type=float, default=DEFAULT_GATE_THRESHOLD)
    ap.add_argument("--max-signals", type=int, default=15000)
    ap.add_argument("--new-min-cluster-size", type=int, default=8,
                    help="HDBSCAN min_cluster_size for new-topic formation on the residual")
    ap.add_argument("--new-min-samples", type=int, default=5)
    ap.add_argument("--no-new-topics", action="store_true",
                    help="assign-to-existing only (skip §6 step-2 new-topic formation)")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    return asyncio.run(run(args.hours, args.assign_threshold, args.gate_threshold,
                           args.max_signals, args.dry_run,
                           args.new_min_cluster_size, args.new_min_samples,
                           args.no_new_topics))


if __name__ == "__main__":
    raise SystemExit(main())

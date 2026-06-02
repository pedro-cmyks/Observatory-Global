#!/usr/bin/env python3
"""Project emergent_clusters into the dynamic_topics lifecycle (Phase 6, Sub-A).

Incremental, idempotent writer. Processes emergent_clusters snapshots in
time order; for each not-yet-ingested snapshot it matches each cluster to
the best existing dynamic_topic by centroid cosine (>= MATCH_THRESHOLD,
greedy 1-to-1). Matched clusters attach (running-mean centroid, member
row, last_seen, aggregates); unmatched clusters open a new `candidate`
topic. After each snapshot tick, state transitions run on every topic
using quality signals — not persistence alone — so roundup/incoherent
identities never get promoted.

Runs in SHADOW: writes only dynamic_topics / dynamic_topic_members,
which no product surface reads yet. Use --dry-run to compute without
writing.

Run on the off-iCloud ML/numpy venv with DATABASE_URL:
  /Users/pedro/AtlasLocalWorker/atlasvenv/bin/python -m scripts.project_dynamic_topics
"""

from __future__ import annotations

import argparse
import asyncio
import os
import re
from dataclasses import dataclass
from typing import Any

import numpy as np

from scripts.emergent_topic_identity_resolver import cosine

MATCH_THRESHOLD = 0.85
# Deliberately narrow: only unambiguous grab-bag markers. Broad terms like
# "headlines" or "digest" catch legitimate topics ("Crime Headlines") and
# were validated out. Label-regex is a weak first filter; the robust quality
# gate is the evidence-role student noise rate (next increment).
ROUNDUP_PATTERNS = re.compile(
    r"\b(round\s?up|mixed news|miscellaneous|assorted|news brief|"
    r"various (news|stories|topics|updates)|grab\s?bag)\b",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class LifecycleConfig:
    persist_min: int = 2        # snapshots to be promotable
    cohesion_min: float = 0.50  # mean member cohesion to promote
    volume_min: int = 30        # aggregate kept signals to promote
    noise_max: float = 0.50     # max student noise-rate to promote (quality gate)
    stale_k: int = 2            # active -> deprecated after K unseen ticks
    retire_m: int = 4           # deprecated -> retired after M unseen ticks


def is_roundup_label(label: str | None) -> bool:
    if not label:
        return False
    return bool(ROUNDUP_PATTERNS.search(label))


def next_state(
    state: str,
    *,
    seen_now: bool,
    n_snapshots: int,
    mean_cohesion: float,
    agg_n_signals: int,
    is_roundup: bool,
    since_seen: int,
    cfg: LifecycleConfig,
    noise_rate: float | None = None,
) -> str:
    """Pure state transition for one snapshot tick."""
    quality_ok = noise_rate is None or noise_rate < cfg.noise_max
    qualifies = (
        n_snapshots >= cfg.persist_min
        and mean_cohesion >= cfg.cohesion_min
        and agg_n_signals >= cfg.volume_min
        and not is_roundup
        and quality_ok
    )
    if seen_now:
        if is_roundup or not quality_ok:
            return "candidate"  # roundup or high-noise: never promoted; demote if active
        if qualifies:
            return "active"
        if state in ("deprecated", "retired"):
            return "candidate"  # re-opened / resurrected as provisional
        return state
    # not seen this tick
    if state == "active" and since_seen >= cfg.stale_k:
        return "deprecated"
    if state == "deprecated" and since_seen >= cfg.retire_m:
        return "retired"
    return state


def running_mean(old: np.ndarray, k: int, new: np.ndarray) -> np.ndarray:
    """Incremental mean of k existing vectors plus one new vector."""
    return (old * k + new) / (k + 1)


# ---------- in-memory topic model (mirrors the table) ----------

class Topic:
    __slots__ = (
        "id", "identity_key", "state", "label_counts", "centroid", "first_seen",
        "last_seen", "snapshots", "agg_n_signals", "cohesions", "roundup_votes",
        "n_labels", "since_seen", "members", "dirty", "new", "noises",
    )

    def __init__(self, identity_key, label, centroid, snap, n_signals, cohesion, noise=None):
        from collections import Counter
        self.id: int | None = None
        self.identity_key = identity_key
        self.state = "candidate"
        self.label_counts: Any = Counter({label: 1}) if label else Counter()
        self.centroid = np.array(centroid, dtype=np.float64)
        self.first_seen = snap
        self.last_seen = snap
        self.snapshots = {snap}
        self.agg_n_signals = int(n_signals)
        self.cohesions = [float(cohesion)] if cohesion is not None else []
        self.noises = [float(noise)] if noise is not None else []
        self.roundup_votes = 1 if is_roundup_label(label) else 0
        self.n_labels = 1
        self.since_seen = 0
        self.members: list[dict[str, Any]] = []
        self.dirty = True
        self.new = True

    @property
    def n_member_clusters(self) -> int:
        return len(self.members)

    @property
    def mean_cohesion(self) -> float:
        return float(np.mean(self.cohesions)) if self.cohesions else 0.0

    @property
    def is_roundup(self) -> bool:
        # the topic's representative (mode) label is the identity signal; a
        # grab-bag label ("X News Roundup") marks the topic regardless of the
        # noisier per-member vote. Vote kept as a secondary OR.
        return is_roundup_label(self.label) or (
            self.n_labels > 0 and self.roundup_votes * 2 >= self.n_labels
        )

    @property
    def label(self) -> str:
        return self.label_counts.most_common(1)[0][0] if self.label_counts else ""

    @property
    def noise_rate(self) -> float | None:
        return round(float(np.mean(self.noises)), 4) if self.noises else None

    def attach(self, cluster: dict[str, Any], snap, score: float) -> None:
        self.centroid = running_mean(self.centroid, self.n_member_clusters, np.array(cluster["centroid"]))
        self.last_seen = max(self.last_seen, snap)
        self.snapshots.add(snap)
        self.agg_n_signals += int(cluster["n_signals"])
        if cluster.get("cohesion") is not None:
            self.cohesions.append(float(cluster["cohesion"]))
        self.n_labels += 1
        clabel = cluster.get("label")
        if clabel:
            self.label_counts[clabel] += 1
        if is_roundup_label(clabel):
            self.roundup_votes += 1
        if cluster.get("noise") is not None:
            self.noises.append(float(cluster["noise"]))
        self.members.append({"cluster_id": cluster["id"], "snapshot_at": snap, "match_score": score})
        self.dirty = True


def process_snapshot(topics: list[Topic], snap_clusters: list[dict[str, Any]], snap, cfg: LifecycleConfig) -> list[Topic]:
    """Match a snapshot's clusters, then advance every topic's state one tick."""
    # greedy 1-to-1 match by centroid cosine
    pairs = []
    for ci, c in enumerate(snap_clusters):
        for ti, t in enumerate(topics):
            s = cosine(np.array(c["centroid"]), t.centroid)
            if s >= MATCH_THRESHOLD:
                pairs.append((s, ci, ti))
    pairs.sort(reverse=True)
    used_c: set[int] = set()
    used_t: set[int] = set()
    seen_topics: set[int] = set()
    for s, ci, ti in pairs:
        if ci in used_c or ti in used_t:
            continue
        used_c.add(ci)
        used_t.add(ti)
        topics[ti].attach(snap_clusters[ci], snap, s)
        seen_topics.add(ti)
    for ci, c in enumerate(snap_clusters):
        if ci not in used_c:
            t = Topic(
                identity_key=f"dyn-{c['snapshot_at']}-{c['cluster_id']}",
                label=c["label"], centroid=c["centroid"], snap=snap,
                n_signals=c["n_signals"], cohesion=c.get("cohesion"), noise=c.get("noise"),
            )
            # constructor seeds aggregates from this cluster; record its member row
            t.members.append({"cluster_id": c["id"], "snapshot_at": snap, "match_score": 1.0})
            topics.append(t)
            seen_topics.add(len(topics) - 1)

    # advance state for every topic
    for ti, t in enumerate(topics):
        seen = ti in seen_topics
        t.since_seen = 0 if seen else t.since_seen + 1
        new_state = next_state(
            t.state, seen_now=seen, n_snapshots=len(t.snapshots),
            mean_cohesion=t.mean_cohesion, agg_n_signals=t.agg_n_signals,
            is_roundup=t.is_roundup, since_seen=t.since_seen, cfg=cfg,
            noise_rate=t.noise_rate,
        )
        if new_state != t.state:
            t.state = new_state
            t.dirty = True
    return topics


# ---------- DB ----------

async def load_clusters(conn) -> list[dict[str, Any]]:
    rows = await conn.fetch(
        "SELECT id, snapshot_at, cluster_id, label, n_signals, cohesion, "
        "sample_signal_ids, centroid_vec "
        "FROM emergent_clusters WHERE centroid_vec IS NOT NULL ORDER BY snapshot_at, cluster_id"
    )
    return [
        {
            "id": int(r["id"]), "snapshot_at": r["snapshot_at"].isoformat(),
            "cluster_id": r["cluster_id"], "label": r["label"],
            "n_signals": int(r["n_signals"] or 0),
            "cohesion": float(r["cohesion"]) if r["cohesion"] is not None else None,
            "sample_signal_ids": [int(x) for x in (r["sample_signal_ids"] or [])],
            "centroid": np.array(r["centroid_vec"], dtype=np.float64),
            "noise": None,  # filled by score_clusters_noise when a student is given
        }
        for r in rows
    ]


async def score_clusters_noise(conn, clusters: list[dict[str, Any]], model_path: str) -> None:
    """Attach per-cluster evidence-role noise fraction (in place).

    Embeds each cluster's sample headlines with e5, runs the local student,
    and sets cluster['noise'] = fraction predicted 'noise'. Needs torch.
    """
    import json
    from scripts.score_assignments_gate import _build_embedder
    from scripts.bridge_gate_student_scope import _student_predict

    model = json.loads(open(model_path, encoding="utf-8").read())
    all_ids = sorted({sid for c in clusters for sid in c["sample_signal_ids"]})
    if not all_ids:
        return
    rows = await conn.fetch(
        "SELECT id, headline FROM signals_v2 WHERE id = ANY($1::bigint[])", all_ids
    )
    headline = {int(r["id"]): (r["headline"] or "").strip() for r in rows}

    embed, _ = _build_embedder(model["embedding_model"])
    for c in clusters:
        texts = [headline.get(sid, "") for sid in c["sample_signal_ids"] if headline.get(sid)]
        if not texts:
            c["noise"] = None
            continue
        head_emb = embed([f"query: {t}" for t in texts])
        label_emb = embed([f"query: {(c['label'] or '').strip()}"] * len(texts))
        roles, _ = _student_predict(model, head_emb, label_emb)
        c["noise"] = round(sum(1 for r in roles if r == "noise") / len(roles), 4)


async def ingested_cluster_ids(conn) -> set[int]:
    rows = await conn.fetch("SELECT emergent_cluster_id FROM dynamic_topic_members")
    return {int(r["emergent_cluster_id"]) for r in rows}


def group_by_snapshot(clusters: list[dict[str, Any]]) -> list[tuple[str, list[dict[str, Any]]]]:
    snaps: dict[str, list[dict[str, Any]]] = {}
    for c in clusters:
        snaps.setdefault(c["snapshot_at"], []).append(c)
    return sorted(snaps.items())


async def persist(conn, topics: list[Topic]) -> dict[str, int]:
    from datetime import datetime

    def _ts(v):
        return datetime.fromisoformat(v) if isinstance(v, str) else v

    written = {"inserted": 0, "updated": 0, "members": 0}
    for t in topics:
        if not t.dirty:
            continue
        cohesion = t.mean_cohesion if t.cohesions else None
        first_seen, last_seen = _ts(t.first_seen), _ts(t.last_seen)
        if t.new and t.id is None:
            row = await conn.fetchrow(
                "INSERT INTO dynamic_topics (identity_key, state, label, centroid_vec, "
                "first_seen, last_seen, n_snapshots, agg_n_signals, mean_cohesion, "
                "is_roundup, snapshots_since_seen, noise_rate, last_state_change) "
                "VALUES ($1,$2,$3,$4,$5::timestamptz,$6::timestamptz,$7,$8,$9,$10,$11,$12,NOW()) "
                "ON CONFLICT (identity_key) DO NOTHING RETURNING id",
                t.identity_key, t.state, t.label, [float(x) for x in t.centroid],
                first_seen, last_seen, len(t.snapshots), t.agg_n_signals,
                cohesion, t.is_roundup, t.since_seen, t.noise_rate,
            )
            if row:
                t.id = int(row["id"])
                t.new = False
                written["inserted"] += 1
        else:
            await conn.execute(
                "UPDATE dynamic_topics SET state=$2, label=$3, centroid_vec=$4, "
                "last_seen=$5::timestamptz, n_snapshots=$6, agg_n_signals=$7, mean_cohesion=$8, "
                "is_roundup=$9, snapshots_since_seen=$10, noise_rate=$11, updated_at=NOW(), "
                "last_state_change=CASE WHEN state IS DISTINCT FROM $2 THEN NOW() ELSE last_state_change END "
                "WHERE id=$1",
                t.id, t.state, t.label, [float(x) for x in t.centroid], last_seen,
                len(t.snapshots), t.agg_n_signals, cohesion, t.is_roundup, t.since_seen,
                t.noise_rate,
            )
            written["updated"] += 1
        if t.id is not None:
            for m in t.members:
                res = await conn.execute(
                    "INSERT INTO dynamic_topic_members (dynamic_topic_id, emergent_cluster_id, "
                    "snapshot_at, match_score) VALUES ($1,$2,$3::timestamptz,$4) "
                    "ON CONFLICT (dynamic_topic_id, emergent_cluster_id) DO NOTHING",
                    t.id, m["cluster_id"], _ts(m["snapshot_at"]), m["match_score"],
                )
                if res.endswith("1"):
                    written["members"] += 1
            t.members = []
        t.dirty = False
    return written


async def run(args: argparse.Namespace) -> dict[str, Any]:
    import asyncpg

    db = os.environ.get("DATABASE_URL") or os.environ.get("SUPABASE_DB_URL")
    if not db:
        raise SystemExit("DATABASE_URL required")
    if not args.rebuild:
        raise SystemExit(
            "incremental hydration from existing dynamic_topics is the cron-wiring "
            "increment; for the Sub-A shadow build use --rebuild"
        )
    cfg = LifecycleConfig()
    conn = await asyncpg.connect(db)
    try:
        clusters = await load_clusters(conn)
        if args.student_model:
            await score_clusters_noise(conn, clusters, args.student_model)
        topics: list[Topic] = []  # shadow rebuild starts fresh in-memory
        snapshot_groups = group_by_snapshot(clusters)
        processed_snaps = 0
        for snap, snap_clusters in snapshot_groups:
            process_snapshot(topics, snap_clusters, snap, cfg)
            processed_snaps += 1
        summary: dict[str, Any] = {
            "n_clusters": len(clusters),
            "n_snapshots_processed": processed_snaps,
            "n_topics": len(topics),
            "by_state": _state_counts(topics),
            "roundups": sum(1 for t in topics if t.is_roundup),
            "high_noise": sum(1 for t in topics if (t.noise_rate or 0) >= cfg.noise_max),
            "scored_noise": args.student_model is not None,
            "dry_run": args.dry_run,
        }
        if not args.dry_run:
            if args.rebuild:
                await conn.execute("TRUNCATE dynamic_topic_members, dynamic_topics RESTART IDENTITY CASCADE")
            summary["written"] = await persist(conn, topics)
        return summary
    finally:
        await conn.close()


def _state_counts(topics: list[Topic]) -> dict[str, int]:
    out: dict[str, int] = {}
    for t in topics:
        out[t.state] = out.get(t.state, 0) + 1
    return out


def parse_args() -> argparse.Namespace:
    ap = argparse.ArgumentParser(description="Project emergent_clusters into dynamic_topics (shadow).")
    ap.add_argument("--dry-run", action="store_true", help="compute without writing")
    ap.add_argument("--rebuild", action="store_true", help="rebuild from all snapshots (TRUNCATE first)")
    ap.add_argument("--student-model", help="path to evidence-role student json for the noise quality gate")
    return ap.parse_args()


def main() -> None:
    import json
    args = parse_args()
    summary = asyncio.run(run(args))
    print(json.dumps(summary, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()

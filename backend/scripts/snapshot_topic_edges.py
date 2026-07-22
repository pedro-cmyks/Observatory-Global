#!/usr/bin/env python
"""Edge-snapshot store writer (Track C1, spec docs/superpowers/specs/
2026-07-21-time-axis-versioned-relationships.md §6).

Persists, once per pass, the DERIVED kinship-edge set + the entity backbone
so a later replay/diff feature (C2/C3, NOT built here) can read them cheaply
instead of recomputing the walk graph or the entity co-occurrence backbone
from scratch. The math is pure and lives in
`app.services.topic_edge_snapshot` (`compute_edge_rows`,
`compute_backbone_rows`) — this module is the I/O: it fetches the active
topic centroids + identity keys and the window's topic_members-derived
entity lists, applies the ONE global whitening (`app/services/whitening.py`,
the same commitment the walk endpoint makes — chains spec §2.2), and upserts
the results.

Read-only on everything except the two NEW tables (`topic_edge_snapshots`,
`entity_backbone_edges` — migration 089); additive and reversible, touches no
existing serving path. Mindful/bounded by construction: one scan of active
topic centroids (same scope as `/api/v2/dossier/walk`'s `_WALK_TOPICS_SQL`,
typically ~1.6k rows) + one bounded scan of topic_members/signals_v2 for the
window — no fan-out, no per-topic round trips. This is designed to be
cron-able (like `snapshot_emergent_topics.py`) at whatever cadence C1's open
question #3 settles on (nightly is the likely answer — not built here).

Idempotent: re-running with the same `--snapshot-at` (or the same day, since
a bare invocation stamps "now") upserts in place — `ON CONFLICT` on
(snapshot_at, identity_key_a, identity_key_b) / (window_end, entity_a,
entity_b), never duplicates.

Run:
  python -m backend.scripts.snapshot_topic_edges --window-hours 720 [--dry-run]
"""
from __future__ import annotations

import argparse
import asyncio
import os
import sys
from datetime import datetime, timedelta, timezone

import asyncpg
import numpy as np

from app.services.subjects import classify_subject
from app.services.topic_edge_snapshot import (
    BackboneRow,
    EdgeRow,
    compute_backbone_rows,
    compute_edge_rows,
)
from app.services.whitening import apply_whitening, load_whitening

# Active-topic universe — SAME scope as the walk endpoint's active-topic scan
# (`app/routers/dossier.py` `_WALK_TOPICS_SQL`): story-level (not umbrella)
# topics with a centroid. `identity_key` is the churn-resistant anchor (spec
# §4) this whole store is keyed on.
TOPICS_SQL = """
    SELECT id, identity_key, centroid_vec
    FROM dynamic_topics
    WHERE state = 'active' AND NOT is_umbrella AND centroid_vec IS NOT NULL
"""

# Entity backbone input: persons on EVIDENCE rows across ANY topic (atlas
# slug or dynamic-topic-N) in the rolling window — deliberately a BROADER
# population than the walk graph above (spec: "actors/places outlast
# threads"; the long-arc spine is not scoped to just the currently-active
# story graph). engine_version='v1-compat' is the serving default;
# quarantined (M2 black-hole) rows are excluded, matching the dossier's
# evidence hygiene.
TOPIC_ENTITIES_SQL = """
    SELECT tm.topic_id, s.persons
    FROM topic_members tm
    JOIN signals_v2 s ON s.id = tm.signal_id
    WHERE tm.role = 'evidence'
      AND tm.engine_version = 'v1-compat'
      AND tm.quarantined IS NOT TRUE
      AND tm.assigned_at > NOW() - ($1::int * INTERVAL '1 hour')
      AND s.persons IS NOT NULL
"""

EDGE_UPSERT = """
    INSERT INTO topic_edge_snapshots
        (snapshot_at, identity_key_a, identity_key_b, topic_id_a, topic_id_b,
         degree, weight, basis)
    VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
    ON CONFLICT (snapshot_at, identity_key_a, identity_key_b)
    DO UPDATE SET topic_id_a = EXCLUDED.topic_id_a,
                  topic_id_b = EXCLUDED.topic_id_b,
                  degree = EXCLUDED.degree,
                  weight = EXCLUDED.weight,
                  basis = EXCLUDED.basis
"""

BACKBONE_UPSERT = """
    INSERT INTO entity_backbone_edges
        (window_start, window_end, entity_a, entity_b, cooccur_count, rarity_weight)
    VALUES ($1, $2, $3, $4, $5, $6)
    ON CONFLICT (window_end, entity_a, entity_b)
    DO UPDATE SET window_start = EXCLUDED.window_start,
                  cooccur_count = EXCLUDED.cooccur_count,
                  rarity_weight = EXCLUDED.rarity_weight
"""

BATCH_SIZE = 500


def _clean_persons(raw) -> list[str]:
    """`signals_v2.persons` JSONB -> lowercased names that pass the person
    subject-type gate (`app.services.subjects.classify_subject`). This is a
    LIGHTER gate than the dossier's full actor-hygiene pipeline (no
    multilingual geo-feature-token guard, no GDELT-truncation-variant fold)
    — an acceptable v1 scope for the coarse backbone; the dossier's
    receipt-grade hygiene stays the stricter bar for anything shown as a
    per-pin receipt."""
    out: list[str] = []
    for p in (raw or []):
        name = (p or "").strip().lower()
        if name and classify_subject(name) == "person":
            out.append(name)
    return out


async def fetch_topics(conn) -> tuple[list[str], list[str | None], list[list[float]]]:
    """Active story-level topics -> (topic_ids, identity_keys, centroid_vecs),
    parallel lists in the same order (the index IS the node id for the kNN
    graph)."""
    rows = await conn.fetch(TOPICS_SQL)
    topic_ids: list[str] = []
    identity_keys: list[str | None] = []
    vecs: list[list[float]] = []
    for r in rows:
        v = r["centroid_vec"]
        if v is None:
            continue
        topic_ids.append(f"dynamic-topic-{int(r['id'])}")
        identity_keys.append(r["identity_key"])
        vecs.append([float(x) for x in v])
    return topic_ids, identity_keys, vecs


async def fetch_topic_entities(conn, window_hours: int) -> dict[str, list[str]]:
    """topic_id -> its person names, most-frequent-first (the input shape
    `compute_backbone_rows` expects)."""
    rows = await conn.fetch(TOPIC_ENTITIES_SQL, window_hours)
    counts: dict[str, dict[str, int]] = {}
    for r in rows:
        tid = r["topic_id"]
        bucket = counts.setdefault(tid, {})
        for name in _clean_persons(r["persons"]):
            bucket[name] = bucket.get(name, 0) + 1
    return {
        tid: [n for n, _ in sorted(c.items(), key=lambda kv: -kv[1])]
        for tid, c in counts.items()
    }


async def write_edges(conn, snapshot_at: datetime, rows: list[EdgeRow]) -> int:
    params = [
        (snapshot_at, r.identity_key_a, r.identity_key_b, r.topic_id_a,
         r.topic_id_b, r.degree, r.weight, r.basis)
        for r in rows
    ]
    for i in range(0, len(params), BATCH_SIZE):
        await conn.executemany(EDGE_UPSERT, params[i:i + BATCH_SIZE])
    return len(params)


async def write_backbone(conn, window_start: datetime, window_end: datetime,
                         rows: list[BackboneRow]) -> int:
    params = [
        (window_start, window_end, r.entity_a, r.entity_b, r.cooccur_count,
         r.rarity_weight)
        for r in rows
    ]
    for i in range(0, len(params), BATCH_SIZE):
        await conn.executemany(BACKBONE_UPSERT, params[i:i + BATCH_SIZE])
    return len(params)


async def run(conn, *, snapshot_at: datetime | None = None,
              window_hours: int = 720, dry_run: bool = False) -> dict:
    """One pass: fetch -> compute -> (upsert unless dry_run). Returns a
    summary dict (also the shape printed by the CLI) — honest counts
    including the null-identity skip, never silent."""
    snapshot_at = snapshot_at or datetime.now(timezone.utc)
    window_start = snapshot_at - timedelta(hours=window_hours)

    summary: dict = {
        "snapshot_at": snapshot_at.isoformat(),
        "window_start": window_start.isoformat(),
        "window_hours": window_hours,
        "topics_seen": 0,
        "edges_written": 0,
        "edges_skipped_null_identity": 0,
        "backbone_written": 0,
        "backbone_meta": {},
        "dry_run": dry_run,
    }

    topic_ids, identity_keys, vecs = await fetch_topics(conn)
    summary["topics_seen"] = len(topic_ids)
    if vecs:
        whitened = apply_whitening(np.asarray(vecs, dtype=np.float32), load_whitening())
        edge_rows, skipped = compute_edge_rows(topic_ids, identity_keys, whitened)
        summary["edges_skipped_null_identity"] = skipped
        if dry_run:
            summary["edges_written"] = len(edge_rows)
        elif edge_rows:
            summary["edges_written"] = await write_edges(conn, snapshot_at, edge_rows)

    # Backbone is BEST-EFFORT: the topic_members ⋈ signals_v2 window scan is heavy
    # and can exceed statement_timeout on a warm/large corpus. A failure here must
    # NOT lose the kinship edges already written above — degrade honestly.
    try:
        topic_entities = await fetch_topic_entities(conn, window_hours)
        backbone_rows, meta = compute_backbone_rows(topic_entities)
        summary["backbone_meta"] = meta
        if dry_run:
            summary["backbone_written"] = len(backbone_rows)
        elif backbone_rows:
            summary["backbone_written"] = await write_backbone(
                conn, window_start, snapshot_at, backbone_rows)
    except Exception as exc:  # noqa: BLE001 — best-effort, never blocks the edge write
        summary["backbone_meta"] = {"skipped": type(exc).__name__,
                                    "detail": str(exc)[:200]}
        print(f"backbone skipped ({type(exc).__name__}): {exc}", file=sys.stderr)

    return summary


async def _main_async(args: argparse.Namespace) -> int:
    dsn = os.environ.get("DATABASE_URL")
    if not dsn:
        print("DATABASE_URL not set", file=sys.stderr)
        return 2
    snapshot_at = (
        datetime.fromisoformat(args.snapshot_at).astimezone(timezone.utc)
        if args.snapshot_at else None
    )
    conn = await asyncpg.connect(dsn)
    try:
        await conn.execute("SET statement_timeout = 120000")
        summary = await run(conn, snapshot_at=snapshot_at,
                            window_hours=args.window_hours, dry_run=args.dry_run)
        print(summary)
    finally:
        await conn.close()
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--window-hours", type=int, default=720,
                    help="rolling window for the entity backbone + the "
                         "topic_members scan (default 720h = 30 days)")
    ap.add_argument("--snapshot-at", type=str, default=None,
                    help="ISO timestamp to stamp this pass with (default: now). "
                         "Re-running with the same value converges (upsert), "
                         "never duplicates.")
    ap.add_argument("--dry-run", action="store_true",
                    help="compute + print counts, write nothing")
    args = ap.parse_args()
    return asyncio.run(_main_async(args))


if __name__ == "__main__":
    raise SystemExit(main())

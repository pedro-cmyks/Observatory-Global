#!/usr/bin/env python3
"""Prune emergent_clusters.sample_receipts past their useful life (2026-08-04).

WHY: 55fb4639 (mig 097) froze per-cluster receipt JSON at snapshot-write time
so aged stories keep serving real evidence after the 7-day signals_v2 hot
retention kills the referenced rows. But emergent_clusters NEVER prunes rows
(identity history: dynamic_topic_members references them), so sample_receipts
is unbounded growth on the shared Supabase (~2,700 clusters/night, measured
2026-08-04; the 7.16GB bloat incident is the cautionary tale).

POLICY (reference-state based — NEVER age-of-cluster alone):
    The census (2026-08-04) measured ACTIVE topics referencing member
    clusters back to 2026-05-31 — identity persistence keeps very old
    clusters attached to living stories, and serving those receipts is the
    entire point of mig 097. So a receipt's life ends only when every path
    to serving is gone:

    NULL sample_receipts on a cluster iff ALL of:
      * the cluster is older than --horizon-days (default 90); AND
      * NO referencing dynamic topic keeps it alive, where a topic keeps
        its clusters' receipts while:
          - it is non-retired (active serves the detail path directly;
            candidate is one promotion away), OR
          - it retired less than horizon days ago (TF-3b revival re-enters
            candidate->entailed->active, and an active revival serves ALL
            its member clusters' receipts), OR
          - its retirement time is unknown (last_state_change IS NULL ->
            conservative keep).
      Clusters referenced by NO topic have no serving path at all (binding
      happens only at snapshot-processing time; old clusters never gain
      dynamic_topic_members rows later) and prune on cluster age alone.

TRADEOFF (documented, accepted): a topic that retires and only revives
AFTER >90 retired days loses its pre-retirement archived receipts — its
detail then serves live rows + post-revival frozen receipts only. This is
aligned with 6fe6c28b ("a revival never certifies on its former life":
court certification already stands on POST-revival receipts), and a story
dormant >90 days that returns overwhelmingly re-founds a new identity in
practice. 90d is deliberately generous vs the observed revival cadence
(days-to-weeks); the floor guard (HORIZON_FLOOR_DAYS=30) keeps a
fat-fingered flag from gutting the revival window.

The only sample_receipts reader is the themes.py durable-receipt lane
(active-topic detail via dynamic_topic_members). Universe trajectories read
per-snapshot centroid_vec, deep-history reads archive tables — neither
touches receipts; NULLing this column affects no other consumer.

SAFETY:
  * dry-run by default; --execute writes.
  * JSONL ledger (append) before every write — restore is
      UPDATE emergent_clusters SET sample_receipts = $2::jsonb
      WHERE id = $1 AND sample_receipts IS NULL
    from the ledger's {cluster_id, receipts} pairs.
  * UPDATE re-checks sample_receipts IS NOT NULL (never double-processes).
  * The backfill's work predicate is windowed to RECENT snapshots, so a
    NULLed old row never re-enters its queue.

USAGE:
    python -m backend.scripts.prune_sample_receipts                # dry-run
    python -m backend.scripts.prune_sample_receipts --execute
    python -m backend.scripts.prune_sample_receipts --horizon-days 120
"""
from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Iterator, Mapping, Optional, Sequence

# The revival window this floor protects: retirements younger than this can
# realistically revive and re-serve their receipts. Below it, the prune
# would eat receipts a live lifecycle still wants.
HORIZON_FLOOR_DAYS = 30

_DEFAULT_HORIZON_DAYS = 90

_UPDATE_CHUNK = 1000

_DEFAULT_LEDGER = Path(
    os.environ.get(
        "ATLAS_PRUNE_RECEIPTS_LEDGER",
        str(Path.home() / "AtlasLocalWorker" / "logs"
            / "prune-sample-receipts-ledger.jsonl"),
    )
)

_UPDATE_SQL = """
    UPDATE emergent_clusters
    SET sample_receipts = NULL
    WHERE id = ANY($1::bigint[])
      AND sample_receipts IS NOT NULL
"""


def validate_horizon(days: int) -> int:
    """Horizon floor guard — pure, test-frozen.

    A horizon below HORIZON_FLOOR_DAYS would prune receipts inside the
    realistic revival window; refuse loudly instead of complying.
    """
    if days < HORIZON_FLOOR_DAYS:
        raise ValueError(
            f"--horizon-days {days} is below the floor "
            f"({HORIZON_FLOOR_DAYS}d): pruning inside the revival window "
            "would eat receipts a revived topic still serves"
        )
    return days


def build_select_sql(*, include_receipts: bool) -> str:
    """The policy predicate. The keep-guards in the NOT EXISTS are the
    design (see module docstring); tests freeze each one.

    Dry-run never pulls the receipt payloads over the wire — only the
    execute path needs them (for the ledger).
    """
    receipts_col = (
        ",\n           ec.sample_receipts::text AS receipts_text"
        if include_receipts else ""
    )
    return f"""
    SELECT ec.id,
           ec.snapshot_at,
           pg_column_size(ec.sample_receipts) AS bytes,
           EXISTS (
             SELECT 1 FROM dynamic_topic_members dtm
             WHERE dtm.emergent_cluster_id = ec.id
           ) AS referenced{receipts_col}
    FROM emergent_clusters ec
    WHERE ec.sample_receipts IS NOT NULL
      AND ec.snapshot_at < now() - ($1 || ' days')::interval
      AND NOT EXISTS (
        SELECT 1
        FROM dynamic_topic_members dtm
        JOIN dynamic_topics dt ON dt.id = dtm.dynamic_topic_id
        WHERE dtm.emergent_cluster_id = ec.id
          AND (
            dt.state <> 'retired'
            OR dt.last_state_change IS NULL
            OR dt.last_state_change >= now() - ($1 || ' days')::interval
          )
      )
    ORDER BY ec.id
    """


def summarize(rows: Iterable[Mapping[str, Any]]) -> dict:
    """Prune report over matched rows — pure.

    referenced=True means the cluster has dynamic_topic_members rows but
    every referencing topic is long-retired ('retired_only'); False means
    no topic ever bound it ('unreferenced' — no serving path exists).
    """
    report = {
        "clusters": 0,
        "bytes": 0,
        "by_reason": {
            "retired_only": {"clusters": 0, "bytes": 0},
            "unreferenced": {"clusters": 0, "bytes": 0},
        },
    }
    for row in rows:
        size = int(row["bytes"] or 0)
        reason = "retired_only" if row["referenced"] else "unreferenced"
        report["clusters"] += 1
        report["bytes"] += size
        report["by_reason"][reason]["clusters"] += 1
        report["by_reason"][reason]["bytes"] += size
    return report


def ledger_entry(
    *,
    cluster_id: int,
    snapshot_at: Optional[datetime],
    receipts_text: Optional[str],
    at: datetime,
) -> dict:
    """One restorable JSONL line per pruned cluster — pure.

    Restore: UPDATE emergent_clusters SET sample_receipts = $2::jsonb
    WHERE id = $1 AND sample_receipts IS NULL, feeding (cluster_id,
    json.dumps(receipts)).
    """
    try:
        receipts = json.loads(receipts_text) if receipts_text else []
    except (ValueError, TypeError):
        receipts = []
    return {
        "cluster_id": int(cluster_id),
        "snapshot_at": snapshot_at.isoformat() if snapshot_at else None,
        "receipts": receipts,
        "at": at.isoformat(),
    }


def chunked(items: Sequence[Any], size: int) -> Iterator[list]:
    for i in range(0, len(items), size):
        yield list(items[i:i + size])


async def run(horizon_days: int, execute: bool, ledger_path: Path) -> dict:
    import asyncpg

    dsn = os.getenv("DATABASE_URL")
    if not dsn:
        print("DATABASE_URL not set", file=sys.stderr)
        sys.exit(2)
    validate_horizon(horizon_days)
    conn = await asyncpg.connect(dsn)
    try:
        await conn.execute("SET statement_timeout = 120000")
        rows = await conn.fetch(
            build_select_sql(include_receipts=execute), str(horizon_days)
        )
        report = summarize(rows)
        report["horizon_days"] = horizon_days
        report["nulled"] = 0
        if execute and rows:
            ledger_path.parent.mkdir(parents=True, exist_ok=True)
            now = datetime.now(timezone.utc)
            with open(ledger_path, "a", encoding="utf-8") as ledger:
                for r in rows:
                    ledger.write(json.dumps(ledger_entry(
                        cluster_id=r["id"],
                        snapshot_at=r["snapshot_at"],
                        receipts_text=r["receipts_text"],
                        at=now,
                    ), ensure_ascii=False) + "\n")
                ledger.flush()
                os.fsync(ledger.fileno())
            ids = [int(r["id"]) for r in rows]
            for chunk in chunked(ids, _UPDATE_CHUNK):
                res = await conn.execute(_UPDATE_SQL, chunk)
                # "UPDATE <n>"
                report["nulled"] += int(res.split()[-1])
        return report
    finally:
        await conn.close()


def main() -> None:
    ap = argparse.ArgumentParser(
        description="NULL emergent_clusters.sample_receipts past their "
                    "useful life (reference-state policy; see module doc).")
    ap.add_argument("--horizon-days", type=int, default=_DEFAULT_HORIZON_DAYS,
                    help=f"Retirement/cluster age horizon (default "
                         f"{_DEFAULT_HORIZON_DAYS}, floor "
                         f"{HORIZON_FLOOR_DAYS}).")
    ap.add_argument("--execute", action="store_true",
                    help="Write (default is dry-run report only).")
    ap.add_argument("--ledger", type=Path, default=_DEFAULT_LEDGER,
                    help="Append-mode JSONL ledger of pruned receipts "
                         "(restorable).")
    args = ap.parse_args()
    try:
        validate_horizon(args.horizon_days)
    except ValueError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        sys.exit(2)
    report = asyncio.run(run(args.horizon_days, args.execute, args.ledger))
    mode = "EXECUTED" if args.execute else "DRY-RUN"
    mb = report["bytes"] / (1024 * 1024)
    print(f"[{mode}] {json.dumps(report, indent=2)}")
    print(f"[{mode}] receipts bytes reclaimed (estimate, pre-vacuum): "
          f"{mb:.2f} MB")
    if not args.execute:
        print("(no writes performed — re-run with --execute)")


if __name__ == "__main__":
    main()

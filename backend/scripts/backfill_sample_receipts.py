#!/usr/bin/env python3
"""One-time backfill of emergent_clusters.sample_receipts (mig 097).

WHY (gold day-5 GQ-08/GQ-12, serving fix e55cb08e, durability mig 097): the
7-day signals_v2 hot retention deletes rows that sample_signal_ids keeps
referencing, so an aged story's receipt lane starves (dt-8057: 11 persisted
ids -> 1 alive). The snapshot writer now freezes receipt snapshots at
write time; this script closes the LIVING GAP — clusters written before the
writer shipped whose sample ids still have live signals_v2 rows get their
receipts frozen NOW. Ids retention already deleted are lost — honest: only
live rows are snapshotted, nothing is fabricated.

SCOPE: clusters with sample_receipts IS NULL and snapshot_at inside
--days (default 8 — anything older references signals the 7-day retention
has fully deleted; scanning it would freeze nothing).

SAFETY
  * dry-run by default; --execute required to write.
  * resumable + idempotent: the work predicate is ``sample_receipts IS
    NULL``; processed clusters (including all-dead ones, marked ``[]``)
    never re-enter the queue. A killed run resumes exactly where it died.
  * every write is ledgered (JSONL, one line per cluster) BEFORE it is
    applied.
  * all-dead clusters are marked ``[]`` (processed, nothing recoverable) —
    distinguishable from NULL (never processed) so the resume predicate
    stays exact.

Usage:
    python -m backend.scripts.backfill_sample_receipts               # dry-run
    python -m backend.scripts.backfill_sample_receipts --execute
"""
from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import asyncpg

_REPO_ROOT = Path(__file__).resolve().parents[2]
_DEFAULT_LEDGER = (
    _REPO_ROOT / "docs" / "research" / "recall-229"
    / "2026-08-04-sample-receipts-backfill.jsonl"
)

_SELECT_BATCH = """
    SELECT id, sample_signal_ids
    FROM emergent_clusters
    WHERE sample_receipts IS NULL
      AND snapshot_at > now() - ($1 || ' days')::interval
    ORDER BY id
    LIMIT $2
"""

_SELECT_LIVE = """
    SELECT id, headline, source_url, source_name, country_code, timestamp
    FROM signals_v2
    WHERE id = ANY($1::bigint[])
"""

# Guard: only fill NULL — a concurrent snapshot writer (which writes receipts
# at insert) or a parallel backfill can never be overwritten.
_UPDATE = """
    UPDATE emergent_clusters
    SET sample_receipts = $2::jsonb
    WHERE id = $1 AND sample_receipts IS NULL
"""


def build_receipts_for_cluster(
    sample_ids: list[int], live_by_id: dict[int, Any],
) -> list[dict]:
    """Frozen receipts for the LIVE subset of a cluster's sample ids.

    Preserves the persisted sample order; dead ids are skipped (honest loss —
    their content is unrecoverable from the hot DB). Shape matches the
    snapshot writer's build_sample_receipts: {id, h, u, src, cc, ts}.
    """
    receipts: list[dict] = []
    seen: set[int] = set()
    for sid in sample_ids:
        sid = int(sid)
        if sid in seen:
            continue
        seen.add(sid)
        row = live_by_id.get(sid)
        if row is None or not row["headline"]:
            continue
        ts = row["timestamp"]
        receipts.append({
            "id": sid,
            "h": row["headline"],
            "u": row["source_url"],
            "src": row["source_name"],
            "cc": row["country_code"],
            "ts": ts.isoformat() if ts is not None else None,
        })
    return receipts


async def run(days: int, batch: int, execute: bool, ledger_path: Path) -> dict:
    dsn = os.getenv("DATABASE_URL")
    if not dsn:
        print("DATABASE_URL not set", file=sys.stderr)
        sys.exit(2)
    conn = await asyncpg.connect(dsn)
    stats = {
        "clusters_processed": 0,
        "clusters_with_receipts": 0,
        "clusters_all_dead": 0,
        "receipts_frozen": 0,
        "ids_seen": 0,
        "ids_dead": 0,
        "bytes_written": 0,
    }
    ledger_path.parent.mkdir(parents=True, exist_ok=True)
    ledger = open(ledger_path, "a", encoding="utf-8") if execute else None
    last_id = 0  # dry-run pagination cursor (execute-mode rows leave the queue)
    try:
        while True:
            if execute:
                rows = await conn.fetch(_SELECT_BATCH, str(days), batch)
            else:
                rows = await conn.fetch(
                    _SELECT_BATCH.replace(
                        "WHERE sample_receipts IS NULL",
                        "WHERE sample_receipts IS NULL AND id > $3",
                    ),
                    str(days), batch, last_id,
                )
            if not rows:
                break
            last_id = int(rows[-1]["id"])
            union_ids = sorted({
                int(s) for r in rows for s in (r["sample_signal_ids"] or [])
            })
            live = await conn.fetch(_SELECT_LIVE, union_ids) if union_ids else []
            live_by_id = {int(r["id"]): r for r in live}
            updates: list[tuple[int, str]] = []
            for r in rows:
                sample_ids = [int(s) for s in (r["sample_signal_ids"] or [])]
                receipts = build_receipts_for_cluster(sample_ids, live_by_id)
                payload = json.dumps(receipts, ensure_ascii=False)
                stats["clusters_processed"] += 1
                stats["ids_seen"] += len(set(sample_ids))
                stats["ids_dead"] += len(set(sample_ids)) - len(receipts)
                if receipts:
                    stats["clusters_with_receipts"] += 1
                    stats["receipts_frozen"] += len(receipts)
                else:
                    stats["clusters_all_dead"] += 1
                stats["bytes_written"] += len(payload.encode("utf-8"))
                if ledger is not None:
                    ledger.write(json.dumps({
                        "cluster_id": int(r["id"]),
                        "n_sample": len(set(sample_ids)),
                        "n_frozen": len(receipts),
                        "at": datetime.now(timezone.utc).isoformat(),
                    }) + "\n")
                updates.append((int(r["id"]), payload))
            if execute and updates:
                ledger.flush()
                await conn.executemany(_UPDATE, updates)
            print(
                f"  batch: {len(rows)} clusters "
                f"(total {stats['clusters_processed']}, "
                f"frozen {stats['receipts_frozen']} receipts, "
                f"all-dead {stats['clusters_all_dead']})",
                file=sys.stderr, flush=True,
            )
    finally:
        if ledger is not None:
            ledger.close()
        await conn.close()
    return stats


def main() -> None:
    ap = argparse.ArgumentParser(
        description="Backfill emergent_clusters.sample_receipts (mig 097).")
    ap.add_argument("--days", type=int, default=8,
                    help="Only clusters snapshotted in the last N days "
                         "(older samples are fully retention-dead).")
    ap.add_argument("--batch", type=int, default=500)
    ap.add_argument("--execute", action="store_true",
                    help="Write (default is dry-run report only).")
    ap.add_argument("--ledger", type=Path, default=_DEFAULT_LEDGER)
    args = ap.parse_args()
    stats = asyncio.run(run(args.days, args.batch, args.execute, args.ledger))
    mode = "EXECUTED" if args.execute else "DRY-RUN"
    print(f"[{mode}] {json.dumps(stats, indent=2)}")
    if not args.execute:
        print("(no writes performed — re-run with --execute)")


if __name__ == "__main__":
    main()

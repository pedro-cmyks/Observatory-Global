"""Incremental signal-embedding writer (#223 deliverable 2).

Embeds the deduped hot-window corpus into `signal_embeddings` (halfvec/768,
migration 054) using the snapshot-identical e5 pooling, then sweeps rows
older than the retention window. Designed for the local M1 worker (MPS;
~157K deduped/day ≈ 20-25 min) — Fly shared CPU is too slow to own this.

Idempotent and incremental: only signals without an embedding row are
embedded; one row per deduped headline (latest signal id wins). Safe to run
on any cadence.

Usage (from backend/, with DATABASE_URL set; needs torch+transformers):
    python -m scripts.embed_hot_corpus [--hours 168] [--retention-days 7]
        [--batch 256] [--max-signals 200000] [--dry-run]
"""
from __future__ import annotations

import argparse
import asyncio
import html
import os
import sys
import time

import asyncpg


async def _pending_rows(conn: asyncpg.Connection, hours: int, max_n: int):
    # One representative per headline (latest id), only where no embedding
    # exists yet. Mirrors the snapshot dedup (length >= 20).
    return await conn.fetch(
        f"""
        SELECT DISTINCT ON (s.headline) s.id, s.headline
        FROM signals_v2 s
        LEFT JOIN signal_embeddings e ON e.signal_id = s.id
        WHERE s.timestamp > NOW() - INTERVAL '{int(hours)} hours'
          AND s.headline IS NOT NULL
          AND length(s.headline) >= 20
          AND e.signal_id IS NULL
        ORDER BY s.headline, s.id DESC
        LIMIT {int(max_n)}
        """
    )


async def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--hours", type=int, default=168)
    parser.add_argument("--retention-days", type=int, default=7)
    parser.add_argument("--batch", type=int, default=256)
    parser.add_argument("--max-signals", type=int, default=200_000)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    from app.services.research_semantic import embed_texts, embedder_available
    if not embedder_available():
        print("torch/transformers not available — run from a model venv", file=sys.stderr)
        return 2

    conn = await asyncpg.connect(os.environ["DATABASE_URL"])
    try:
        rows = await _pending_rows(conn, args.hours, args.max_signals)
        from app.services.research_semantic import is_junk_headline
        before = len(rows)
        rows = [r for r in rows if not is_junk_headline(html.unescape(r["headline"]))]
        print(f"pending: {len(rows)} deduped headlines without embeddings "
              f"({before - len(rows)} junk skipped)", file=sys.stderr)
        if args.dry_run:
            return 0

        started = time.monotonic()
        written = 0
        for i in range(0, len(rows), args.batch):
            chunk = rows[i:i + args.batch]
            # headlines arrive HTML-entity-encoded in signals_v2 (&#xNNNN;) —
            # the known serialize bug. Embedding encoded text destroys
            # non-ASCII (Persian/Vietnamese/Turkish) semantics; unescape first.
            vectors = embed_texts(
                [f"passage: {html.unescape(r['headline'])}" for r in chunk]
            )
            if vectors is None:
                print("embedder failed mid-run; aborting cleanly", file=sys.stderr)
                return 1
            # one round trip per batch — executemany is row-by-row over the
            # WAN to Supabase and bottlenecks the whole run (~7/s measured)
            await conn.execute(
                """
                INSERT INTO signal_embeddings (signal_id, vec)
                SELECT t.id, t.v::halfvec
                FROM unnest($1::bigint[], $2::text[]) AS t(id, v)
                ON CONFLICT (signal_id) DO NOTHING
                """,
                [r["id"] for r in chunk],
                ["[" + ",".join(f"{x:.5f}" for x in v) + "]" for v in vectors],
            )
            written += len(chunk)
            if (i // args.batch) % 20 == 0:
                rate = written / max(time.monotonic() - started, 1e-9)
                print(f"  {written}/{len(rows)} ({rate:.0f}/s)", file=sys.stderr)

        swept = await conn.execute(
            f"DELETE FROM signal_embeddings WHERE embedded_at < NOW() - INTERVAL '{int(args.retention_days)} days'"
        )
        elapsed = time.monotonic() - started
        print(f"done: {written} embedded in {elapsed:.0f}s; retention sweep: {swept}",
              file=sys.stderr)
        return 0
    finally:
        await conn.close()


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))

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
    # One representative per headline (latest id), only where no embedding exists
    # yet. #241 Lever 2 (selective): dedup handles syndication; the outer ORDER BY
    # timestamp DESC PRIORITISES RECENT distinct headlines — the embed capacity goes
    # to the served window first, not to alphabetical order (the old query took the
    # first max_n headlines A→Z, so recent stories could starve behind the backlog).
    # No skipping = no recall risk; just spend the scarce embed budget where it serves.
    return await conn.fetch(
        f"""
        SELECT d.id, d.headline FROM (
            SELECT DISTINCT ON (s.headline) s.id, s.headline, s.timestamp
            FROM signals_v2 s
            LEFT JOIN signal_embeddings e ON e.signal_id = s.id
            WHERE s.timestamp > NOW() - INTERVAL '{int(hours)} hours'
              AND s.headline IS NOT NULL
              AND length(s.headline) >= 20
              AND e.signal_id IS NULL
            ORDER BY s.headline, s.id DESC
        ) d
        ORDER BY d.timestamp DESC
        LIMIT {int(max_n)}
        """
    )


async def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--hours", type=int, default=168)
    parser.add_argument("--retention-days", type=int, default=7)
    parser.add_argument("--batch", type=int, default=256)
    parser.add_argument("--write-concurrency", type=int, default=4,
                        help="parallel INSERT streams. The HNSW write (not the "
                             "embed) caps the run; 4-way concurrent writes are "
                             "~5x faster (measured 2026-06-26) with no index drop.")
    parser.add_argument("--max-signals", type=int, default=200_000)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--bulk-reindex", action="store_true",
                        help="#241 fix: DROP the HNSW index, bulk-insert at ~22K/s (vs "
                             "~16/s with the live index), then REBUILD single-threaded "
                             "(~4min/276K; parallel build fails on Supabase shmem). "
                             "Off-peak only — the semantic lane degrades to lexical "
                             "during the rebuild. The rebuild runs in a finally so the "
                             "index is never left dropped. OFF by default.")
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

        if args.bulk_reindex:
            await conn.execute("DROP INDEX IF EXISTS idx_signal_embeddings_vec")
            print("bulk-reindex: HNSW index DROPPED — inserts run un-indexed (~22K/s); "
                  "semantic lane on lexical fallback until rebuild", file=sys.stderr)

        started = time.monotonic()
        written = 0
        _INSERT = """
            INSERT INTO signal_embeddings (signal_id, vec)
            SELECT t.id, t.v::halfvec
            FROM unnest($1::bigint[], $2::text[]) AS t(id, v)
            ON CONFLICT (signal_id) DO NOTHING
        """
        # Parallel writes: embedding is fast (~100-228/s on MPS) but a single
        # SERIAL INSERT stream into the HNSW-indexed table over the WAN caps the
        # whole run (~3/s). Writing batches concurrently over a small pool is ~5x
        # faster (measured 2026-06-26: 27/s serial -> 142/s at 4-way) and needs
        # NO index drop — HNSW handles concurrent inserts.
        cc = max(1, args.write_concurrency)
        write_pool = await asyncpg.create_pool(
            os.environ["DATABASE_URL"], min_size=cc, max_size=cc,
        )

        async def _write(ids: list, vlits: list) -> None:
            async with write_pool.acquire() as wc:
                await wc.execute(_INSERT, ids, vlits)

        pending: set = set()
        try:
            for i in range(0, len(rows), args.batch):
                chunk = rows[i:i + args.batch]
                # headlines arrive HTML-entity-encoded (&#xNNNN;) — embedding the
                # encoded form destroys non-ASCII semantics; unescape first.
                # Run the (blocking, GPU) embed in a thread so the event loop can
                # service the in-flight write tasks meanwhile — embed and write
                # then OVERLAP instead of alternating.
                vectors = await asyncio.to_thread(
                    embed_texts,
                    [f"passage: {html.unescape(r['headline'])}" for r in chunk],
                )
                if vectors is None:
                    print("embedder failed mid-run; aborting cleanly", file=sys.stderr)
                    break
                ids = [r["id"] for r in chunk]
                vlits = ["[" + ",".join(f"{x:.5f}" for x in v) + "]" for v in vectors]
                # bound in-flight writes to the pool size
                if len(pending) >= cc:
                    done, pending = await asyncio.wait(
                        pending, return_when=asyncio.FIRST_COMPLETED
                    )
                    for d in done:
                        d.result()  # surface insert errors
                pending.add(asyncio.create_task(_write(ids, vlits)))
                written += len(chunk)
                if (i // args.batch) % 20 == 0:
                    rate = written / max(time.monotonic() - started, 1e-9)
                    print(f"  {written}/{len(rows)} ({rate:.0f}/s)", file=sys.stderr)
            if pending:
                done, _ = await asyncio.wait(pending)
                for d in done:
                    d.result()
        finally:
            await write_pool.close()
            if args.bulk_reindex:
                # ALWAYS rebuild (finally) so a failed insert never leaves the index
                # dropped. Single-threaded — the parallel build hits Supabase's shmem cap.
                print("bulk-reindex: rebuilding HNSW index (single-threaded ~4min/276K)…",
                      file=sys.stderr)
                await conn.execute("SET max_parallel_maintenance_workers = 0")
                await conn.execute("SET maintenance_work_mem = '256MB'")
                await conn.execute("SET statement_timeout = '1200s'")
                await conn.execute(
                    "CREATE INDEX IF NOT EXISTS idx_signal_embeddings_vec "
                    "ON signal_embeddings USING hnsw (vec halfvec_cosine_ops) "
                    "WITH (m='16', ef_construction='64')")
                print("bulk-reindex: HNSW index REBUILT", file=sys.stderr)

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

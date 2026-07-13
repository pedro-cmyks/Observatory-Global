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


def _ivfflat_list_count(row_count: int) -> int:
    """Choose IVFFlat lists using pgvector's sub-million corpus rule.

    ``rows / 1000`` produced 327 lists for the measured 326,762-row corpus.
    That index built in about 105 seconds on the shared 1 GB database, whereas
    HNSW m=16 and m=8 spilled after 178K/201K tuples and m=4 after 214K.
    The override is bounded because it is interpolated into DDL.
    """
    try:
        override = int(os.getenv("ATLAS_IVFFLAT_LISTS", "0"))
    except ValueError:
        override = 0
    suggested = override or round(max(0, row_count) / 1000)
    return max(16, min(4096, suggested))


async def _pending_rows(
    conn: asyncpg.Connection, hours: int, max_n: int, chunk_hours: int = 12
):
    # One representative per headline (latest id), only where no embedding exists
    # yet, NEWEST FIRST. #241 Lever 2: dedup handles syndication; recency-priority
    # spends the scarce embed budget on the served window first.
    #
    # 2026-07-08 throughput fix: the old query did ONE `DISTINCT ON (headline)`
    # megasort over the whole `hours` window (~700K rows/168h, no btree on
    # headline). Through the Supabase pooler's hard 2-min statement_timeout that
    # sort was killed under cron-time load → the embed step produced ~0 and the
    # substrate starved (0.6% of 24h signals embedded). Now:
    #   • statement_timeout is lifted for THIS session (session-mode pooler, see
    #     main()) so no query is guillotined mid-run, AND
    #   • the window is walked in `chunk_hours` slices most-recent-first, so each
    #     DISTINCT ON sort is bounded (one 12h slice ≈ 50K rows, ~8s) and we STOP
    #     once max_n newest distinct headlines are collected — the backlog tail
    #     never has to sort at all.
    # Cross-slice syndication (same headline straddling a slice boundary) is
    # deduped in Python via `seen`; the newer (earlier-slice) instance wins.
    seen: set = set()
    out: list = []
    start = 0
    while start < hours and len(out) < max_n:
        end = min(start + chunk_hours, hours)
        rows = await conn.fetch(
            f"""
            SELECT d.id, d.headline FROM (
                SELECT DISTINCT ON (s.headline) s.id, s.headline, s.timestamp
                FROM signals_v2 s
                LEFT JOIN signal_embeddings e ON e.signal_id = s.id
                WHERE s.timestamp >  NOW() - INTERVAL '{int(end)} hours'
                  AND s.timestamp <= NOW() - INTERVAL '{int(start)} hours'
                  AND s.headline IS NOT NULL
                  AND length(s.headline) >= 20
                  AND e.signal_id IS NULL
                ORDER BY s.headline, s.id DESC
            ) d
            ORDER BY d.timestamp DESC
            """
        )
        for r in rows:
            h = r["headline"]
            if h in seen:
                continue
            seen.add(h)
            out.append(r)
            if len(out) >= max_n:
                break
        start = end
    return out[:max_n]


async def _rebuild_ann_index(conn: asyncpg.Connection) -> None:
    """Restore the serving ANN index after a bulk write, on every exit path."""
    row_count = int(await conn.fetchval("SELECT count(*) FROM signal_embeddings") or 0)
    lists = _ivfflat_list_count(row_count)
    print(
        f"bulk-reindex: rebuilding IVFFlat index "
        f"(single-threaded; rows={row_count}, lists={lists})…",
        file=sys.stderr,
    )
    # HNSW cannot build inside this 1 GB instance without a long spill: even
    # m=4 exceeded 384 MB after 214K/326K tuples. IVFFlat trains compact lists,
    # built the measured corpus without spill, and reached recall@10=1.00 on
    # 20 dispersed queries at probes=20.
    await conn.execute(
        "SET max_parallel_maintenance_workers = 0; "
        "SET maintenance_work_mem = '384MB'; "
        "SET statement_timeout = 0; "
        "CREATE INDEX IF NOT EXISTS idx_signal_embeddings_vec "
        "ON signal_embeddings USING ivfflat (vec halfvec_cosine_ops) "
        f"WITH (lists='{lists}')"
    )
    await conn.execute("ANALYZE signal_embeddings")
    print("bulk-reindex: IVFFlat index REBUILT", file=sys.stderr)


async def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--hours", type=int, default=168)
    parser.add_argument("--retention-days", type=int, default=7)
    parser.add_argument("--batch", type=int, default=256)
    parser.add_argument("--write-concurrency", type=int, default=4,
                        help="parallel INSERT streams. The ANN-index write (not the "
                             "embed) caps the run; 4-way concurrent writes are "
                             "~5x faster (measured 2026-06-26) with no index drop.")
    parser.add_argument("--max-signals", type=int, default=200_000)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--bulk-reindex", action="store_true",
                        help="#241 recovery: DROP the ANN index, bulk-insert fast (no live-"
                             "index cost), then REBUILD single-threaded at "
                             "maintenance_work_mem='384MB' using measured IVFFlat lists. "
                             "ONE-TIME CATCH-UP ONLY, off-peak — NOT for the cron (the "
                             "rebuild cost makes 3x/day non-viable) and the semantic lane "
                             "degrades to lexical during the rebuild. The rebuild runs in "
                             "a finally so the index is never left dropped. OFF by default.")
    args = parser.parse_args()

    from app.services.research_semantic import embed_texts, embedder_available
    if not embedder_available():
        print("torch/transformers not available — run from a model venv", file=sys.stderr)
        return 2

    conn = await asyncpg.connect(os.environ["DATABASE_URL"])
    index_dropped = False
    try:
        # Lift the pooler's default 2-min statement_timeout for this session
        # (Supabase session-mode pooler, port 5432, honours SET per-connection —
        # verified). Both the dedup select and the HNSW inserts legitimately run
        # longer than 2 min on the M1↔Supabase WAN; without this they are killed
        # mid-run and the embed step yields ~0 (the 2026-07-08 starvation).
        await conn.execute("SET statement_timeout = 0")
        rows = await _pending_rows(conn, args.hours, args.max_signals)
        from app.services.research_semantic import is_junk_headline
        before = len(rows)
        rows = [r for r in rows if not is_junk_headline(html.unescape(r["headline"]))]
        print(f"pending: {len(rows)} deduped headlines without embeddings "
              f"({before - len(rows)} junk skipped)", file=sys.stderr)
        if args.dry_run:
            return 0

        # Reclaim expired hot rows before touching the ANN index. Previously
        # this ran only after all inserts, so a stalled insert retained old
        # vectors and made the next run even harder. The external archive and
        # processed-history lanes remain authoritative for older windows.
        swept = await conn.execute(
            f"DELETE FROM signal_embeddings WHERE embedded_at < NOW() - INTERVAL '{int(args.retention_days)} days'"
        )

        if args.bulk_reindex:
            await conn.execute("DROP INDEX IF EXISTS idx_signal_embeddings_vec")
            index_dropped = True
            print("bulk-reindex: ANN index DROPPED — inserts run un-indexed (~22K/s); "
                  "semantic lane on lexical fallback until rebuild", file=sys.stderr)

        started = time.monotonic()
        written = 0
        # WHERE EXISTS closes most of the retention race: a signal selected as
        # pending can be retention-deleted from signals_v2 before its embedding is
        # written → ForeignKeyViolationError abends the whole 256-row batch. The
        # EXISTS filter drops just-deleted ids in-statement; the rare remaining
        # race (delete commits after the EXISTS read) is caught in _write and the
        # batch retried against the still-present ids.
        _INSERT = """
            INSERT INTO signal_embeddings (signal_id, vec)
            SELECT t.id, t.v::halfvec
            FROM unnest($1::bigint[], $2::text[]) AS t(id, v)
            WHERE EXISTS (SELECT 1 FROM signals_v2 s WHERE s.id = t.id)
            ON CONFLICT (signal_id) DO NOTHING
        """
        # Parallel writes: embedding is fast (~100-228/s on MPS) but a single
        # SERIAL INSERT stream into the ANN-indexed table over the WAN caps the
        # whole run (~3/s). Writing batches concurrently over a small pool is ~5x
        # faster (measured 2026-06-26: 27/s serial -> 142/s at 4-way) and needs
        # NO index drop — IVFFlat handles concurrent inserts.
        cc = max(1, args.write_concurrency)

        write_pool = await asyncpg.create_pool(
            os.environ["DATABASE_URL"], min_size=cc, max_size=cc,
        )

        async def _insert(wc: asyncpg.Connection, ids: list, vlits: list) -> None:
            # SET LOCAL (not a plain SET via pool `init`) is the ONLY reliable way
            # to lift the pooler's 2-min statement_timeout for a pooled write:
            # asyncpg runs `RESET ALL` when a connection is RELEASED, which wipes
            # any session-level SET → a reused pool conn reverts to 2min and the
            # slow live-HNSW insert over the WAN is killed mid-run (the 2026-07-08
            # DIAG: "cancel after 124s on 256 rows; conn timeout=2min"). SET LOCAL
            # is transaction-scoped, so it is re-applied fresh inside every write
            # and survives the reset cycle.
            async with wc.transaction():
                await wc.execute("SET LOCAL statement_timeout = 0")
                await wc.execute(_INSERT, ids, vlits)

        async def _write(ids: list, vlits: list) -> None:
            async with write_pool.acquire() as wc:
                try:
                    await _insert(wc, ids, vlits)
                except asyncpg.exceptions.ForeignKeyViolationError:
                    # Retention deleted a signal between select and insert. Refilter
                    # to ids still present and retry once; drop the rest (they
                    # re-enter next run if re-ingested). Rare tail of the race.
                    present = await wc.fetch(
                        "SELECT s.id FROM signals_v2 s "
                        "WHERE s.id = ANY($1::bigint[])",
                        ids,
                    )
                    keep = {r["id"] for r in present}
                    fids, fvlits = zip(*[
                        (i, v) for i, v in zip(ids, vlits) if i in keep
                    ]) if keep else ((), ())
                    if fids:
                        await _insert(wc, list(fids), list(fvlits))

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
        elapsed = time.monotonic() - started
        print(f"done: {written} embedded in {elapsed:.0f}s; retention sweep: {swept}",
              file=sys.stderr)
        return 0
    finally:
        try:
            # This outer finally starts immediately after the connection opens,
            # so pool-creation errors, embed errors, and failed inserts cannot
            # strand production without its ANN index after a bulk run.
            if index_dropped:
                await _rebuild_ann_index(conn)
        finally:
            await conn.close()


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))

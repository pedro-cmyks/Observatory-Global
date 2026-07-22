#!/usr/bin/env python3
"""Decode HTML-entity-encoded headlines already stored in signals_v2.

WHY (measured 2026-07-22, prod, 168h window): 432,873 / 932,719 press
headlines (46.4%) are stored entity-encoded — ``hurac&#xE1;n`` instead of
``huracán``. One ingest lane produces them: the GDELT GKG ``<PAGE_TITLE>``
writer (``app/services/ingest_v2.parse_gkg_row``), which is why the
concentration is source_lang='xx' (the TRANSLINGUAL feed, 79.4% encoded) and
'en' (GDELT English, 6.6%), while every declared non-English RSS lane is
~0.0%.

The write-side fix landed in ``parse_gkg_row``; this script repairs the rows
written before it. Two live defects it closes for stored data:

* lexical matching silently misses accented words (a folded ``&#xE1;`` token
  becomes ``xe1``, so the word does not exist — measured: keyword 'huracan'
  scored 0 press matches against 16 real ones in the same 48h window);
* reprint dedup double-counts: 4,355 distinct headline texts appear in the
  corpus BOTH encoded and plain, so an encoded and a plain copy of one wire
  story read as two stories, inflating the volume that feeds the
  0.45*log-volume term in rank_threads.

SAFETY
* dry-run by default; --execute is required to write.
* keyset-paginated by id, batched, bounded by --max-rows.
* every changed row is appended to a JSONL ledger BEFORE the batch is
  written, so the pass is reversible with --revert <ledger>.
* html.unescape is idempotent for the entity forms GDELT emits, so a
  re-run over already-decoded rows is a no-op (0 changed).

Usage:
    python scripts/backfill_decode_headlines.py                  # dry-run
    python scripts/backfill_decode_headlines.py --execute
    python scripts/backfill_decode_headlines.py --revert docs/.../ledger.jsonl
"""
from __future__ import annotations

import argparse
import asyncio
import html
import json
import os
import sys
from pathlib import Path

import asyncpg

# Rows whose headline could plausibly carry an entity. Cheap pre-filter in
# SQL; the authoritative test is html.unescape(h) != h, done in Python.
ENTITY_RE = r"&#[0-9]+;|&#[xX][0-9a-fA-F]+;|&[a-zA-Z][a-zA-Z0-9]{1,7};"

UPDATE_SQL = """
UPDATE signals_v2 AS s
SET headline = v.headline
FROM (SELECT * FROM unnest($1::bigint[], $2::text[]) AS t(id, headline)) AS v
WHERE s.id = v.id
"""


def decode(headline: str) -> str:
    """The whole transform. Kept as a named function so the tests can pin it."""
    return html.unescape(headline)


def _load_cursor(state_path: Path) -> int:
    """Resume point from the last run. MEASURED (2026-07-22) why this must be
    persisted rather than re-derived: the pre-filter only returns rows that
    still carry entities, so a fresh pass from id 0 has to scan PAST every
    already-decoded row to find the next match. With ~196K rows decoded that
    SELECT ran >180s and hit statement_timeout, while the same query from the
    real cursor returned 2,000 rows in 3.6s. The scan cost grows with progress
    — a nightly job that restarts at 0 would get slower until it could never
    finish."""
    try:
        return int(json.loads(state_path.read_text(encoding="utf-8"))["last_id"])
    except Exception:
        return 0


def _save_cursor(state_path: Path, last_id: int) -> None:
    state_path.parent.mkdir(parents=True, exist_ok=True)
    tmp = state_path.with_suffix(state_path.suffix + ".tmp")
    tmp.write_text(json.dumps({"last_id": last_id}), encoding="utf-8")
    tmp.replace(state_path)  # atomic: a killed run never leaves a torn cursor


async def _connect() -> asyncpg.Connection:
    dsn = os.getenv("DATABASE_URL")
    if not dsn:
        print("DATABASE_URL not set", file=sys.stderr)
        raise SystemExit(2)
    conn = await asyncpg.connect(dsn)
    # The pooler's default statement_timeout kills a wide unnest UPDATE
    # mid-pass (measured: this script died at row ~180,000 with
    # QueryCanceledError). Same cure as the matview-refresh handler — raise it
    # for THIS session only, never globally.
    await conn.execute("SET statement_timeout = '180s'")
    return conn


async def _update_with_retry(conn, ids: list[int], decoded: list[str]) -> int:
    """Apply one batch, halving on a statement timeout. A batch that cannot
    be split any further is reported and skipped, never silently dropped."""
    pending = [(ids, decoded)]
    applied = 0
    while pending:
        chunk_ids, chunk_new = pending.pop()
        try:
            await conn.execute(UPDATE_SQL, chunk_ids, chunk_new)
            applied += len(chunk_ids)
        except asyncpg.exceptions.QueryCanceledError:
            if len(chunk_ids) <= 100:
                print(f"  ! skipped {len(chunk_ids)} rows at id={chunk_ids[0]} "
                      f"(timeout at minimum chunk)", file=sys.stderr)
                continue
            mid = len(chunk_ids) // 2
            pending.append((chunk_ids[mid:], chunk_new[mid:]))
            pending.append((chunk_ids[:mid], chunk_new[:mid]))
    return applied


async def backfill(batch: int, max_rows: int, execute: bool, ledger_path: Path,
                   start_id: int = 0, state_path: Path | None = None) -> dict:
    conn = await _connect()
    scanned = changed = written = 0
    last_id = start_id
    samples: list[tuple[str, str]] = []
    ledger = None
    try:
        if execute:
            ledger_path.parent.mkdir(parents=True, exist_ok=True)
            ledger = ledger_path.open("a", encoding="utf-8")
        while scanned < max_rows:
            rows = await conn.fetch(
                """
                SELECT id, headline FROM signals_v2
                WHERE id > $1 AND headline IS NOT NULL AND headline ~ $2
                ORDER BY id LIMIT $3
                """,
                last_id,
                ENTITY_RE,
                min(batch, max_rows - scanned),
            )
            if not rows:
                break
            last_id = rows[-1]["id"]
            scanned += len(rows)

            ids: list[int] = []
            befores: list[str] = []
            decoded: list[str] = []
            for r in rows:
                new = decode(r["headline"])
                if new == r["headline"]:
                    continue
                ids.append(r["id"])
                befores.append(r["headline"])
                decoded.append(new)
                if len(samples) < 5:
                    samples.append((r["headline"], new))
            changed += len(ids)

            if ids and execute:
                # Ledger first: a crash mid-UPDATE leaves a superset of the
                # applied changes, which reverts cleanly (revert is itself
                # idempotent — it restores an exact prior value).
                for rid, before, after in zip(ids, befores, decoded):
                    ledger.write(
                        json.dumps({"id": rid, "before": before, "after": after},
                                   ensure_ascii=False) + "\n"
                    )
                ledger.flush()
                written += await _update_with_retry(conn, ids, decoded)

            if execute and state_path is not None:
                _save_cursor(state_path, last_id)

            print(f"  scanned={scanned} changed={changed} written={written} "
                  f"last_id={last_id}", flush=True)
    finally:
        if ledger:
            ledger.close()
        await conn.close()
    return {"scanned": scanned, "changed": changed, "written": written,
            "samples": samples, "last_id": last_id}


async def revert(ledger_path: Path, batch: int) -> int:
    conn = await _connect()
    restored = 0
    try:
        ids: list[int] = []
        befores: list[str] = []
        with ledger_path.open(encoding="utf-8") as fh:
            for line in fh:
                rec = json.loads(line)
                ids.append(int(rec["id"]))
                befores.append(rec["before"])
                if len(ids) >= batch:
                    await conn.execute(UPDATE_SQL, ids, befores)
                    restored += len(ids)
                    ids, befores = [], []
        if ids:
            await conn.execute(UPDATE_SQL, ids, befores)
            restored += len(ids)
    finally:
        await conn.close()
    return restored


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--batch", type=int, default=2000)
    ap.add_argument("--max-rows", type=int, default=2_000_000)
    ap.add_argument("--start-id", type=int, default=None,
                    help="resume after this signals_v2.id; default reads the "
                         "persisted cursor (--state), 0 on a first run")
    ap.add_argument("--state", default=None,
                    help="cursor file (default: <ledger>.cursor.json)")
    ap.add_argument("--execute", action="store_true",
                    help="write (default is dry-run)")
    # Outside the repo by design: ~450K before/after pairs is ~90 MB, an ops
    # artifact, not source. Sits with the other AtlasLocalWorker run logs.
    ap.add_argument("--ledger", default=str(
        Path.home() / "AtlasLocalWorker" / "logs" / "headline-decode-ledger.jsonl"))
    ap.add_argument("--revert", default=None, metavar="LEDGER")
    args = ap.parse_args()

    repo = Path(__file__).resolve().parents[2]

    if args.revert:
        n = asyncio.run(revert(Path(args.revert), args.batch))
        print(f"reverted {n} rows from {args.revert}")
        return

    ledger = Path(args.ledger)
    if not ledger.is_absolute():
        ledger = repo / ledger
    state = Path(args.state) if args.state else ledger.with_suffix(".cursor.json")
    start_id = args.start_id if args.start_id is not None else _load_cursor(state)

    print(f"resuming after id={start_id} (cursor: {state})")
    out = asyncio.run(backfill(args.batch, args.max_rows, args.execute, ledger,
                               start_id, state))
    mode = "EXECUTE" if args.execute else "DRY-RUN"
    print(f"\n[{mode}] scanned={out['scanned']} changed={out['changed']} "
          f"written={out['written']} last_id={out['last_id']}")
    for before, after in out["samples"]:
        print(f"  - {before!r}\n  + {after!r}")
    if args.execute:
        print(f"ledger: {ledger}  (revert: --revert {ledger})")
        if out["scanned"] == 0:
            print("nothing left to decode — corpus is clean at this cursor")


if __name__ == "__main__":
    main()

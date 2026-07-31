#!/usr/bin/env python3
"""Backfill NULL headlines on the GDELT translingual lane from the GDELT archive.

WHY (diagnosed 2026-07-30, fixed at the parser in ff55d6b0): parse_gkg_row's
``len(words) >= 4`` title validation was script-blind, so CJK ``<PAGE_TITLE>``s
(1-3 space-separated tokens) were discarded and ``headline`` stored NULL —
53.3% of CN / 45.5% of TW / 38.5% of JP ``gdelt_gkg_translated`` rows, ~33k
signals/week for the lane's lifetime. The parser fix stops the bleeding going
forward; this script repairs the rows written before it.

The titles are mechanically recoverable: GDELT keeps every 15-minute
``…translation.gkg.csv.zip`` forever, and a signal's ``timestamp`` IS the GKG
DATE field (col 0) = the file bucket, so one UTC day of NULL rows maps to that
day's 96 archive files. Rows are matched by ``source_url`` (GKG col 4,
DocumentIdentifier — UNIQUE in signals_v2), and a recovered title must pass
the SAME fixed validation as the parser before it is written.

TWO TARGETS, one pass per UTC day:
  * prod ``signals_v2`` — the 7-day hot window still holds pre-fix NULL rows;
    backfilling them makes embedding/NER eligible by predicate (both pipelines
    select ``headline IS NOT NULL`` + not-yet-processed, so no re-enqueue is
    needed — they pick the rows up on the next cron).
  * the external archive (``/Volumes/Ext/Atlas/Archive``) — gzip JSONL
    partitions hold the NULL rows as-captured back to May. Matched partitions
    are rewritten (only matched lines re-serialized; every other line kept
    byte-identical) and their manifest records updated: the manifest sha256 is
    the digest of the UNCOMPRESSED lines exactly as archive_export.py computes
    it, so archive_verify.py keeps passing. Originals are copied to a backup
    dir before the first rewrite.

SAFETY
  * dry-run by default; --execute required to write.
  * idempotent: prod UPDATE guards ``AND s.headline IS NULL``; a re-run finds
    no NULL rows. Archive re-run: the index is rebuilt from file mtimes, and a
    backfilled row no longer matches ``headline IS NULL``.
  * resumable: per-day state file; a killed run redoes at most one day.
  * every write is ledgered (JSONL) before it is applied; --revert-prod
    restores NULL where the current value is exactly what we wrote;
    --revert-archive restores the backed-up partition + manifest files.

Usage:
    python scripts/backfill_null_headlines.py --days 2026-07-28          # dry-run, one day
    python scripts/backfill_null_headlines.py                            # dry-run, all days
    python scripts/backfill_null_headlines.py --execute                  # full run
    python scripts/backfill_null_headlines.py --revert-prod <ledger>
    python scripts/backfill_null_headlines.py --revert-archive <backup-dir>
"""
from __future__ import annotations

import argparse
import asyncio
import gzip
import hashlib
import html
import io
import json
import os
import re
import shutil
import sys
import time
import urllib.error
import urllib.request
import zipfile
from collections import Counter, defaultdict
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

ARCHIVE_ROOT = Path("/Volumes/Ext/Atlas/Archive")
GDELT_URL = "http://data.gdeltproject.org/gdeltv2/{stamp}.translation.gkg.csv.zip"
ATTRIBUTION = "gdelt_gkg_translated"

# ---------------------------------------------------------------------------
# Title validation — LOCKSTEP duplicate of parse_gkg_row (ingest_v2.py,
# ff55d6b0). A recovered title is only written if the CURRENT parser would
# have kept it. The four CJK ranges are the script_floor.py ranges. Parity is
# pinned by backend/tests/test_backfill_null_headlines.py against the same
# fixture titles as test_gkg_cjk_title_validation.py.
# ---------------------------------------------------------------------------
_CJK_TITLE_RE = re.compile("[぀-ヿ㐀-䶿一-鿿가-힣]")
_CJK_TITLE_MIN_CHARS = 10


def _cjk_ratio(text: str) -> float:
    if not text:
        return 0.0
    return len(_CJK_TITLE_RE.findall(text)) / len(text)


def accept_title(raw: str) -> str | None:
    """html-unescape + strip + the fixed parser validation. None = reject."""
    candidate = html.unescape(raw).strip()
    if not candidate or re.match(r"^\d{6,}", candidate):
        return None
    if len(candidate.split()) >= 4:
        return candidate
    if len(candidate) >= _CJK_TITLE_MIN_CHARS and _cjk_ratio(candidate) > 0.5:
        return candidate
    return None


# ---------------------------------------------------------------------------
# GDELT day fetch: 96 15-min translation files -> {source_url: accepted_title}
# ---------------------------------------------------------------------------

def day_buckets(day: date) -> list[str]:
    return [
        f"{day:%Y%m%d}{h:02d}{m:02d}00"
        for h in range(24)
        for m in (0, 15, 30, 45)
    ]


def _fetch(url: str, dest: Path, retries: int = 3) -> bool:
    """Download url -> dest. False on 404 (bucket genuinely absent)."""
    for attempt in range(retries):
        try:
            tmp = dest.with_suffix(".tmp")
            with urllib.request.urlopen(url, timeout=180) as resp, tmp.open("wb") as fh:
                shutil.copyfileobj(resp, fh)
            tmp.replace(dest)
            return True
        except urllib.error.HTTPError as e:
            if e.code == 404:
                return False
            if attempt == retries - 1:
                raise
        except (urllib.error.URLError, OSError):
            if attempt == retries - 1:
                raise
        time.sleep(2 * (attempt + 1))
    return False


_PAGE_TITLE_RE = re.compile(r"<PAGE_TITLE>(.+?)</PAGE_TITLE>")


def parse_gkg_titles(data: bytes, out: dict[str, str]) -> int:
    """Extract url -> accepted title from one unzipped GKG csv. Tab-split, no
    csv module: GKG is tab-delimited with no quoting and embedded quote chars
    choke csv.reader. First title wins (reprints across buckets are identical).
    """
    n = 0
    for line in data.decode("utf-8", errors="replace").splitlines():
        cols = line.split("\t")
        if len(cols) < 27:
            continue
        url = cols[4]
        if not url or url in out:
            continue
        m = _PAGE_TITLE_RE.search(cols[26])
        if not m:
            continue
        title = accept_title(m.group(1))
        if title:
            out[url] = title
            n += 1
    return n


def day_url_titles(day: date, cache_dir: Path, keep: bool,
                   workers: int = 6) -> tuple[dict[str, str], int]:
    """Download+parse the day's translation files. Returns (map, missing_buckets).

    Downloads run on a small thread pool (network-bound, ~1.2 GB/day across 96
    files — sequential fetch measured ~11 min/day, pool ~3); parsing stays
    sequential (shared dict, first-title-wins must be deterministic).
    """
    from concurrent.futures import ThreadPoolExecutor

    cache_dir.mkdir(parents=True, exist_ok=True)
    titles: dict[str, str] = {}
    missing = 0

    def ensure(stamp: str) -> bool:
        dest = cache_dir / f"{stamp}.translation.gkg.csv.zip"
        if dest.exists():
            return True
        return _fetch(GDELT_URL.format(stamp=stamp), dest)

    stamps = day_buckets(day)
    with ThreadPoolExecutor(max_workers=workers) as pool:
        fetched = dict(zip(stamps, pool.map(ensure, stamps)))

    for stamp in stamps:
        if not fetched[stamp]:
            missing += 1
            continue
        dest = cache_dir / f"{stamp}.translation.gkg.csv.zip"
        try:
            with zipfile.ZipFile(dest) as zf:
                for name in zf.namelist():
                    parse_gkg_titles(zf.read(name), titles)
        except zipfile.BadZipFile:
            # Torn cache from an earlier kill: refetch once.
            dest.unlink()
            if _fetch(GDELT_URL.format(stamp=stamp), dest):
                with zipfile.ZipFile(dest) as zf:
                    for name in zf.namelist():
                        parse_gkg_titles(zf.read(name), titles)
            else:
                missing += 1
        if not keep:
            dest.unlink(missing_ok=True)
    return titles, missing


# ---------------------------------------------------------------------------
# Archive index: one scan of every partition -> per-day NULL-row locations.
# Cached; invalidated when the partition file set (path+mtime+size) changes.
# ---------------------------------------------------------------------------

def _partition_fingerprint(files: list[Path]) -> str:
    h = hashlib.sha256()
    for fp in files:
        st = fp.stat()
        h.update(f"{fp}|{st.st_mtime_ns}|{st.st_size}".encode())
    return h.hexdigest()


def build_archive_index(archive_root: Path, cache_path: Path,
                        rebuild: bool = False) -> dict:
    files = sorted(archive_root.rglob("part-*.jsonl.gz"))
    fp = _partition_fingerprint(files)
    if cache_path.exists() and not rebuild:
        try:
            idx = json.loads(cache_path.read_text(encoding="utf-8"))
            if idx.get("fingerprint") == fp:
                return idx
        except Exception:
            pass
    print(f"[index] scanning {len(files)} partitions for NULL "
          f"{ATTRIBUTION} rows…", file=sys.stderr)
    paths: list[str] = []
    path_no: dict[str, int] = {}
    days: dict[str, list[list]] = defaultdict(list)
    for i, fpath in enumerate(files):
        rel = str(fpath.relative_to(archive_root))
        try:
            with gzip.open(fpath, "rt", encoding="utf-8", errors="replace") as fh:
                for line in fh:
                    if '"headline":null' not in line:
                        continue
                    try:
                        r = json.loads(line)
                    except json.JSONDecodeError:
                        continue
                    if r.get("headline") or r.get("attribution_method") != ATTRIBUTION:
                        continue
                    url = r.get("source_url")
                    rid = r.get("id")
                    if not url or rid is None:
                        continue
                    if rel not in path_no:
                        path_no[rel] = len(paths)
                        paths.append(rel)
                    days[(r.get("timestamp") or "")[:10]].append(
                        [path_no[rel], int(rid), url])
        except OSError as e:
            print(f"[index] skip {rel}: {e}", file=sys.stderr)
        if (i + 1) % 200 == 0:
            print(f"[index] {i+1}/{len(files)}", file=sys.stderr)
    idx = {"fingerprint": fp, "built_at":
           datetime.now(timezone.utc).isoformat(), "paths": paths,
           "days": dict(days)}
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    tmp = cache_path.with_suffix(".tmp")
    tmp.write_text(json.dumps(idx), encoding="utf-8")
    tmp.replace(cache_path)
    n = sum(len(v) for v in days.values())
    print(f"[index] {n} NULL rows across {len(days)} days, "
          f"{len(paths)} partitions", file=sys.stderr)
    return idx


# ---------------------------------------------------------------------------
# Archive rewrite: re-serialize matched lines, keep the rest byte-identical,
# recompute the manifest's uncompressed-line sha256, update the manifest.
# ---------------------------------------------------------------------------

def _find_manifest(partition: Path, archive_root: Path) -> tuple[Path, Path]:
    """Return (manifest_path, base_dir) whose manifest.jsonl records this
    partition. Walk up from the partition to the first dir with manifest.jsonl
    (an incremental run dir, or the archive root)."""
    d = partition.parent
    while d >= archive_root:
        m = d / "manifest.jsonl"
        if m.exists():
            return m, d
        d = d.parent
    raise FileNotFoundError(f"no manifest.jsonl above {partition}")


def rewrite_partition(partition: Path, fixes: dict[int, str],
                      archive_root: Path, backup_root: Path,
                      execute: bool) -> dict:
    """Apply id->headline fixes to one gzip partition. Returns stats."""
    manifest_path, base_dir = _find_manifest(partition, archive_root)
    rel = str(partition.relative_to(base_dir))

    out_lines: list[bytes] = []
    digest = hashlib.sha256()
    changed = 0
    rows = 0
    with gzip.open(partition, "rt", encoding="utf-8", errors="replace") as fh:
        for line in fh:
            line = line.rstrip("\n")
            if not line:
                continue
            rows += 1
            new_line = line
            if '"headline":null' in line:
                try:
                    r = json.loads(line)
                except json.JSONDecodeError:
                    r = None
                if r is not None and not r.get("headline"):
                    rid = r.get("id")
                    try:
                        rid = int(rid)
                    except (TypeError, ValueError):
                        rid = None
                    if rid in fixes:
                        r["headline"] = fixes[rid]
                        new_line = json.dumps(r, ensure_ascii=False,
                                              sort_keys=True,
                                              separators=(",", ":"))
                        changed += 1
            raw = new_line.encode("utf-8")
            digest.update(raw)
            digest.update(b"\n")
            out_lines.append(raw)

    stats = {"partition": str(partition), "rows": rows, "changed": changed}
    if not changed or not execute:
        return stats

    # Backup first (partition + its manifest), never overwriting an earlier
    # backup — the first copy is the true original.
    b_part = backup_root / partition.relative_to(archive_root)
    b_man = backup_root / manifest_path.relative_to(archive_root)
    b_part.parent.mkdir(parents=True, exist_ok=True)
    b_man.parent.mkdir(parents=True, exist_ok=True)
    if not b_part.exists():
        shutil.copy2(partition, b_part)
    if not b_man.exists():
        shutil.copy2(manifest_path, b_man)

    tmp = partition.with_suffix(".gz.tmp")
    with gzip.open(tmp, "wb") as fh:
        for raw in out_lines:
            fh.write(raw)
            fh.write(b"\n")
    tmp.replace(partition)

    # Manifest record: sha256 + bytes change; row_count is unchanged by
    # construction (we only edit one field of existing lines).
    new_sha = digest.hexdigest()
    new_bytes = partition.stat().st_size
    records = []
    hit = False
    for mline in manifest_path.read_text(encoding="utf-8").splitlines():
        if not mline.strip():
            continue
        rec = json.loads(mline)
        if rec.get("relative_path") == rel:
            rec["sha256"] = new_sha
            rec["bytes"] = new_bytes
            hit = True
        records.append(rec)
    if not hit:
        raise RuntimeError(f"manifest record for {rel} not found in {manifest_path}")
    mtmp = manifest_path.with_suffix(".jsonl.tmp")
    mtmp.write_text(
        "".join(json.dumps(r, ensure_ascii=False, sort_keys=True,
                           separators=(",", ":")) + "\n" for r in records),
        encoding="utf-8")
    mtmp.replace(manifest_path)
    stats["sha256"] = new_sha
    return stats


# ---------------------------------------------------------------------------
# Prod side
# ---------------------------------------------------------------------------

UPDATE_SQL = """
UPDATE signals_v2 AS s
SET headline = v.headline
FROM (SELECT * FROM unnest($1::bigint[], $2::text[]) AS t(id, headline)) AS v
WHERE s.id = v.id AND s.headline IS NULL
"""


async def _connect():
    import asyncpg
    dsn = os.getenv("DATABASE_URL")
    if not dsn:
        print("DATABASE_URL not set (prod target needs it; "
              "use --target archive to skip)", file=sys.stderr)
        raise SystemExit(2)
    conn = await asyncpg.connect(dsn)
    await conn.execute("SET statement_timeout = '180s'")
    return conn


async def prod_null_rows(conn, day: date) -> list:
    return await conn.fetch(
        """
        SELECT id, source_url FROM signals_v2
        WHERE attribution_method = $1 AND headline IS NULL
          AND timestamp >= $2 AND timestamp < $3
        """,
        ATTRIBUTION,
        datetime(day.year, day.month, day.day, tzinfo=timezone.utc),
        datetime(day.year, day.month, day.day, tzinfo=timezone.utc) + timedelta(days=1),
    )


async def prod_days(conn) -> list[str]:
    rows = await conn.fetch(
        """
        SELECT DISTINCT date_trunc('day', timestamp)::date AS d
        FROM signals_v2
        WHERE attribution_method = $1 AND headline IS NULL
        """, ATTRIBUTION)
    return sorted(str(r["d"]) for r in rows)


async def prod_apply(conn, ids: list[int], titles: list[str],
                     batch: int = 2000) -> int:
    written = 0
    for i in range(0, len(ids), batch):
        result = await conn.execute(UPDATE_SQL, ids[i:i + batch],
                                    titles[i:i + batch])
        written += int(result.split()[-1])
    return written


# ---------------------------------------------------------------------------
# Reverts
# ---------------------------------------------------------------------------

async def revert_prod(ledger_path: Path) -> int:
    conn = await _connect()
    restored = 0
    try:
        ids: list[int] = []
        titles: list[str] = []
        with ledger_path.open(encoding="utf-8") as fh:
            for line in fh:
                rec = json.loads(line)
                if rec.get("t") != "prod":
                    continue
                ids.append(int(rec["id"]))
                titles.append(rec["h"])
        for i in range(0, len(ids), 2000):
            result = await conn.execute(
                """
                UPDATE signals_v2 AS s SET headline = NULL
                FROM (SELECT * FROM unnest($1::bigint[], $2::text[])
                      AS t(id, headline)) AS v
                WHERE s.id = v.id AND s.headline = v.headline
                """, ids[i:i + 2000], titles[i:i + 2000])
            restored += int(result.split()[-1])
    finally:
        await conn.close()
    return restored


def revert_archive(backup_root: Path, archive_root: Path) -> int:
    n = 0
    for src in sorted(backup_root.rglob("*")):
        if not src.is_file():
            continue
        dest = archive_root / src.relative_to(backup_root)
        shutil.copy2(src, dest)
        n += 1
        print(f"restored {dest}")
    return n


# ---------------------------------------------------------------------------
# Day pass
# ---------------------------------------------------------------------------

async def process_day(day_s: str, args, idx: dict, conn, ledger,
                      backup_root: Path, state: dict) -> dict:
    """One UTC day: prod and archive halves are tracked separately in state
    ("prod:<day>" / "arch:<day>") so a prod-only pass never masks a later
    archive pass over the same day."""
    day = date.fromisoformat(day_s)
    done = set(state["done_days"])
    do_prod = conn is not None and (not args.execute or f"prod:{day_s}" not in done)
    do_arch = args.target in ("both", "archive") and (
        not args.execute or f"arch:{day_s}" not in done)

    arch_rows = idx["days"].get(day_s, []) if do_arch else []
    prod_rows = await prod_null_rows(conn, day) if do_prod else []
    if not arch_rows and not prod_rows:
        return {"day": day_s, "skip": "no NULL rows pending"}

    titles, missing = day_url_titles(day, Path(args.gdelt_cache) / day_s,
                                     args.keep_downloads)

    stats = Counter()
    stats["gdelt_urls"] = len(titles)
    stats["gdelt_missing_buckets"] = missing
    samples: list[str] = []

    # prod
    p_ids, p_titles = [], []
    for r in prod_rows:
        t = titles.get(r["source_url"])
        if t:
            p_ids.append(r["id"])
            p_titles.append(t)
            if len(samples) < 3:
                samples.append(t)
    stats["prod_null"] = len(prod_rows)
    stats["prod_matched"] = len(p_ids)
    if args.execute:
        if p_ids:
            for rid, t in zip(p_ids, p_titles):
                ledger.write(json.dumps(
                    {"t": "prod", "day": day_s, "id": rid, "h": t},
                    ensure_ascii=False) + "\n")
            ledger.flush()
            stats["prod_written"] = await prod_apply(conn, p_ids, p_titles)
        if do_prod:
            state["done_days"].append(f"prod:{day_s}")

    # archive
    by_partition: dict[str, dict[int, str]] = defaultdict(dict)
    for path_i, rid, url in arch_rows:
        t = titles.get(url)
        if t:
            by_partition[idx["paths"][path_i]][rid] = t
            if len(samples) < 3:
                samples.append(t)
    stats["archive_null"] = len(arch_rows)
    stats["archive_matched"] = sum(len(v) for v in by_partition.values())
    stats["archive_partitions"] = len(by_partition)
    if args.execute:
        if by_partition:
            for rel, fixes in sorted(by_partition.items()):
                for rid, t in fixes.items():
                    ledger.write(json.dumps(
                        {"t": "arch", "day": day_s, "id": rid, "h": t, "p": rel},
                        ensure_ascii=False) + "\n")
                ledger.flush()
                out = rewrite_partition(Path(args.archive_root) / rel, fixes,
                                        Path(args.archive_root), backup_root,
                                        execute=True)
                stats["archive_written"] += out["changed"]
        if do_arch:
            state["done_days"].append(f"arch:{day_s}")

    return {"day": day_s, **stats, "samples": samples}


def _load_state(path: Path) -> dict:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {"done_days": []}


def _save_state(path: Path, state: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(state), encoding="utf-8")
    tmp.replace(path)


async def run(args) -> None:
    state_dir = Path(args.state_dir)
    state_dir.mkdir(parents=True, exist_ok=True)
    backup_root = Path(args.backup_dir)

    idx = {"days": {}, "paths": []}
    if args.target in ("both", "archive"):
        idx = build_archive_index(Path(args.archive_root),
                                  state_dir / "archive-null-index.json",
                                  rebuild=args.rebuild_index)

    conn = None
    if args.target in ("both", "prod"):
        conn = await _connect()

    try:
        if args.days:
            days = sorted(args.days)
        else:
            days = sorted(set(idx["days"]) |
                          set(await prod_days(conn) if conn else []))
            if args.from_day:
                days = [d for d in days if d >= args.from_day]
            if args.to_day:
                days = [d for d in days if d <= args.to_day]

        state_path = state_dir / "backfill-state.json"
        state = _load_state(state_path)
        done = set(state["done_days"])
        if args.execute:
            pending = [d for d in days
                       if (conn is not None and f"prod:{d}" not in done)
                       or (args.target in ("both", "archive")
                           and f"arch:{d}" not in done)]
        else:
            pending = days
        print(f"{len(pending)} day(s) to process "
              f"({len(days) - len(pending)} already done)", flush=True)

        totals = Counter()
        ledger = None
        if args.execute:
            ledger_path = Path(args.ledger)
            ledger_path.parent.mkdir(parents=True, exist_ok=True)
            ledger = ledger_path.open("a", encoding="utf-8")
        try:
            for day_s in pending:
                out = await process_day(day_s, args, idx, conn,
                                        ledger, backup_root, state)
                print(json.dumps(out, ensure_ascii=False), flush=True)
                for k, v in out.items():
                    if isinstance(v, int):
                        totals[k] += v
                if args.execute:
                    _save_state(state_path, state)
        finally:
            if ledger:
                ledger.close()

        mode = "EXECUTE" if args.execute else "DRY-RUN"
        print(f"\n[{mode}] totals: {json.dumps(dict(totals))}")
        if args.execute:
            print(f"ledger: {args.ledger}\nbackups: {backup_root}")
    finally:
        if conn is not None:
            await conn.close()


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--target", choices=["both", "prod", "archive"],
                    default="both")
    ap.add_argument("--days", nargs="*", help="specific UTC days (YYYY-MM-DD); "
                    "default = every day with NULL rows")
    ap.add_argument("--from-day", help="inclusive lower bound")
    ap.add_argument("--to-day", help="inclusive upper bound")
    ap.add_argument("--execute", action="store_true",
                    help="write (default is dry-run)")
    ap.add_argument("--archive-root", default=str(ARCHIVE_ROOT))
    ap.add_argument("--gdelt-cache",
                    default="/Volumes/Ext/Atlas/GdeltCache",
                    help="where the day's GDELT zips land (~1.2 GB/day)")
    ap.add_argument("--keep-downloads", action="store_true",
                    help="keep the GDELT zips after a day is processed")
    ap.add_argument("--rebuild-index", action="store_true")
    ap.add_argument("--state-dir", default=str(
        Path.home() / "AtlasLocalWorker" / "null-headline-backfill"))
    ap.add_argument("--ledger", default=str(
        Path.home() / "AtlasLocalWorker" / "logs" /
        "null-headline-backfill-ledger.jsonl"))
    ap.add_argument("--backup-dir", default="/Volumes/Ext/Atlas/Backups/"
                    "null-headline-backfill")
    ap.add_argument("--revert-prod", metavar="LEDGER")
    ap.add_argument("--revert-archive", metavar="BACKUP_DIR")
    args = ap.parse_args()

    if args.revert_prod:
        n = asyncio.run(revert_prod(Path(args.revert_prod)))
        print(f"reverted {n} prod rows")
        return
    if args.revert_archive:
        n = revert_archive(Path(args.revert_archive), Path(args.archive_root))
        print(f"restored {n} archive files")
        return

    asyncio.run(run(args))


if __name__ == "__main__":
    main()

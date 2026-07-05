#!/usr/bin/env python
"""S3 (time-as-dimension, 2026-07-05) — populate historical_evidence_samples
from the EXTERNAL ARCHIVE so a scrubbed past day can serve real receipts.

The mig-029 table existed with 0 rows; this fills it: for every archived day
and country, up to K distinct-source, non-junk headlines (HTML-unescaped),
with url + source + sentiment — the evidence a click on a scrubbed day shows.

topic_slug uses the sentinel '_all' (country-day samples; per-topic archive
attribution doesn't exist historically — that's the robot/identities
program). sample_id is deterministic → re-runs are idempotent
(ON CONFLICT DO NOTHING). Resumable: --skip-existing-days.

Runs on the M1 (needs /Volumes/Ext/Atlas/Archive) with DATABASE_URL.
Usage: python backend/scripts/populate_historical_evidence_samples.py
         [--per-country 5] [--skip-existing-days]
"""
from __future__ import annotations

import argparse
import asyncio
import glob
import gzip
import hashlib
import html
import json
import os
import re
import sys
from collections import defaultdict
from datetime import date, datetime
from pathlib import Path

ARCHIVE_ROOT = Path(os.environ.get("ATLAS_ARCHIVE_ROOT", "/Volumes/Ext/Atlas/Archive"))

# Mirrors research_semantic.is_junk_headline (kept inline: offline script,
# no app import needed).
_JUNK = re.compile(r"\.s?html?\b|^doc\s|^untitled\b", re.IGNORECASE)


def _is_junk(headline: str) -> bool:
    if not headline or _JUNK.search(headline):
        return True
    words = [w for w in headline.split() if any(c.isalpha() for c in w)]
    return len(words) < 3


def _day_partitions() -> dict[str, list[Path]]:
    """day 'YYYY-MM-DD' → every partition file touching that day (base +
    incremental trees)."""
    out: dict[str, list[Path]] = defaultdict(list)
    pattern = str(ARCHIVE_ROOT / "**" / "year=*" / "month=*" / "day=*" / "**" / "*.jsonl.gz")
    for f in glob.glob(pattern, recursive=True):
        p = Path(f)
        parts = {seg.split("=")[0]: seg.split("=")[1]
                 for seg in p.parts if "=" in seg and seg.count("=") == 1}
        try:
            day = f"{parts['year']}-{parts['month']}-{parts['day']}"
        except KeyError:
            continue
        out[day].append(p)
    return out


def _sample_day(files: list[Path], day: str, per_country: int) -> list[tuple]:
    """Up to per_country distinct-source, non-junk headlines per country."""
    by_cc: dict[str, list[dict]] = defaultdict(list)
    seen_src: dict[str, set] = defaultdict(set)
    seen_hl: dict[str, set] = defaultdict(set)
    for f in files:
        try:
            with gzip.open(f, "rt", encoding="utf-8", errors="replace") as fh:
                for line in fh:
                    try:
                        r = json.loads(line)
                    except Exception:
                        continue
                    cc = (r.get("country_code") or "").strip().upper()
                    if len(cc) != 2:
                        continue
                    if len(by_cc[cc]) >= per_country:
                        continue
                    headline = html.unescape(r.get("headline") or "").strip()
                    if _is_junk(headline):
                        continue
                    src = (r.get("source_name") or "").strip().lower()
                    hl_key = headline.lower()
                    if src and src in seen_src[cc]:
                        continue  # distinct sources first
                    if hl_key in seen_hl[cc]:
                        continue  # syndication dupes across partitions
                    seen_src[cc].add(src)
                    seen_hl[cc].add(hl_key)
                    rel = str(f.relative_to(ARCHIVE_ROOT))
                    sid = f"hes1:{day}:{cc}:" + hashlib.sha1(hl_key.encode()).hexdigest()[:12]
                    by_cc[cc].append({
                        "sample_id": sid,
                        "day": day,
                        "cc": cc,
                        "source_family": r.get("source_family") or "unknown",
                        "signal_class": r.get("signal_class") or "unknown",
                        "path": rel,
                        "source_name": r.get("source_name"),
                        "source_url": r.get("source_url"),
                        "headline": headline,
                        "ts": r.get("timestamp"),
                        "sentiment": r.get("nlp_sentiment") if r.get("nlp_sentiment") is not None else r.get("sentiment"),
                    })
        except Exception as exc:
            print(f"  ! {f.name}: {exc}", file=sys.stderr)
    def _ts(v):
        if not v:
            return None
        try:
            return datetime.fromisoformat(str(v).replace("Z", "+00:00"))
        except Exception:
            return None

    rows = []
    for cc, items in by_cc.items():
        for it in items:
            rows.append((
                it["sample_id"], date.fromisoformat(it["day"]), "_all", it["cc"], it["source_family"],
                it["signal_class"], it["path"], it["source_name"], it["source_url"],
                it["headline"], _ts(it["ts"]), it["sentiment"],
                "distinct-source-sample-v1", "hes-v1",
            ))
    return rows


async def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--per-country", type=int, default=5)
    ap.add_argument("--skip-existing-days", action="store_true")
    ap.add_argument("--limit-days", type=int, default=0, help="0 = all")
    args = ap.parse_args()

    if not ARCHIVE_ROOT.exists():
        print(f"archive root missing: {ARCHIVE_ROOT}", file=sys.stderr)
        return 2

    import asyncpg
    dsn = os.environ.get("DATABASE_URL")
    if not dsn:
        print("DATABASE_URL not set", file=sys.stderr)
        return 2
    conn = await asyncpg.connect(dsn, statement_cache_size=0)

    try:
        existing: set[str] = set()
        if args.skip_existing_days:
            rows = await conn.fetch(
                "SELECT DISTINCT day FROM historical_evidence_samples WHERE model_version='hes-v1'")
            existing = {r["day"].isoformat() for r in rows}

        days = _day_partitions()
        todo = sorted(d for d in days if d not in existing)
        if args.limit_days:
            todo = todo[:args.limit_days]
        print(f"days in archive: {len(days)} · to process: {len(todo)}")

        total = 0
        for day in todo:
            rows = _sample_day(days[day], day, args.per_country)
            if rows:
                await conn.executemany(
                    """
                    INSERT INTO historical_evidence_samples
                        (sample_id, day, topic_slug, country_code, source_family,
                         signal_class, archive_relative_path, source_name,
                         source_url, headline, signal_timestamp, sentiment,
                         selection_reason, model_version)
                    VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12,$13,$14)
                    ON CONFLICT (sample_id) DO NOTHING
                    """,
                    rows,
                )
            total += len(rows)
            print(f"  {day}: {len(rows)} samples ({len(days[day])} partitions)")
        print(f"done: {total} samples inserted/kept")
    finally:
        await conn.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))

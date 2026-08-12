"""#235 (2026-08-11): per-feed RSS freshness watchdog.

A stuck-cache feed is SILENT BY CONSTRUCTION: sana.sy's WordPress page cache
froze /en/feed/ at 2026-07-28 while the site kept publishing — every item fell
outside the ingest overlap window, the feed yielded zero signals for six days,
and nothing anywhere said so (the ingestor logs per-cycle yield, not per-feed
staleness; a feed that fetches 200 + parses clean + returns old items looks
healthy at every layer). The 08-03 fix (cache-bust param) healed SANA; this
watchdog makes the CLASS visible for all ~230 curated feeds.

Nightly (scoped-snapshot runner step, non-fatal): fetch each CURATED_FEEDS
url exactly as the ingestor would (same UA, same cache-bust set — the
watchdog must measure what the ingestor SEES, so a stuck cache on a non-busted
feed stays visible), read the NEWEST item's own timestamp, and append one
`atlas_alert`-format line per defective feed to the reliability ledger
(`ATLAS_RELIABILITY_ALERTS_LOG`; unset = stderr only, never a crash):

    2026-08-11 03:00:00 [FEED_STALE] feed=sana_sy age_days=13.2 url=…

Alert classes: FEED_STALE (newest item older than --max-age-days, default 7)
· FEED_UNREACHABLE (HTTP != 200 / network error) · FEED_UNPARSEABLE (bozo,
no entries) · FEED_EMPTY (parsed, zero entries) · FEED_UNDATED (entries carry
no parseable date — the watchdog must NOT inherit ingest's now() fallback, or
an undated stuck feed would read perpetually fresh). Exit 0 always: the
ledger is the alert channel; a watchdog must never kill the nightly.

Run (repo root, mlvenv — feedparser installed 2026-08-11, trafilatura
precedent):
    python -m backend.scripts.rss_feed_freshness_watchdog            # all feeds
    python -m backend.scripts.rss_feed_freshness_watchdog --feeds sana_sy
    python -m backend.scripts.rss_feed_freshness_watchdog --max-age-days 3
"""
from __future__ import annotations

import argparse
import asyncio
import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import aiohttp
import feedparser

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.services.ingest_rss import (  # noqa: E402
    CURATED_FEEDS,
    _CACHE_BUST_FEEDS,
    _cache_bust,
)

# ok never ledgers; every failure class maps to its own [TAG] so the weekly
# read can grep one class at a time.
ALERT_TAGS: dict[str, str] = {
    "stale": "FEED_STALE",
    "unreachable": "FEED_UNREACHABLE",
    "unparseable": "FEED_UNPARSEABLE",
    "empty": "FEED_EMPTY",
    "undated": "FEED_UNDATED",
}

_UA = {"User-Agent": "Observatory-Global/1.0 RSS-Ingestor"}
_CONCURRENCY = 8
_TIMEOUT = aiohttp.ClientTimeout(total=30)


def watchdog_url(feed_name: str, url: str) -> str:
    """The exact URL the ingestor would hit: cache-bust ONLY the feeds the
    ingestor busts. Busting everything would hide the stuck-cache class this
    watchdog exists to detect."""
    return _cache_bust(url) if feed_name in _CACHE_BUST_FEEDS else url


def newest_entry_time(entries) -> datetime | None:
    """Max entry timestamp, or None when NO entry carries a parseable date.

    Deliberately not ingest's parse_entry_time: its now() fallback would make
    an undated stuck feed read as age 0 forever."""
    newest: datetime | None = None
    for entry in entries:
        for attr in ("published_parsed", "updated_parsed", "created_parsed"):
            t = getattr(entry, attr, None)
            if t:
                try:
                    dt = datetime(*t[:6], tzinfo=timezone.utc)
                except (TypeError, ValueError):
                    continue
                if newest is None or dt > newest:
                    newest = dt
                break
    return newest


def classify_feed(*, fetched_ok: bool, parsed_ok: bool, entry_count: int,
                  newest: datetime | None, now: datetime,
                  max_age: timedelta) -> tuple[str, timedelta | None]:
    """(status, age-of-newest-item). Status ∈ ok|stale|unreachable|
    unparseable|empty|undated."""
    if not fetched_ok:
        return "unreachable", None
    if not parsed_ok:
        return "unparseable", None
    if entry_count == 0:
        return "empty", None
    if newest is None:
        return "undated", None
    age = now - newest
    return ("stale" if age > max_age else "ok"), age


def format_alert(status: str, feed_name: str, url: str, *,
                 age: timedelta | None, now: datetime) -> str:
    """One `atlas_alert`-format ledger line (label_hygiene precedent) so
    python- and shell-emitted alerts interleave in one ledger."""
    tag = ALERT_TAGS[status]
    parts = [f"feed={feed_name}"]
    if age is not None:
        parts.append(f"age_days={age.total_seconds() / 86400:.1f}")
    parts.append(f"url={url}")
    stamp = now.strftime("%Y-%m-%d %H:%M:%S")
    return f"{stamp} [{tag}] {' '.join(parts)}"


def _ledger(line: str) -> None:
    print(line, file=sys.stderr)
    path = os.environ.get("ATLAS_RELIABILITY_ALERTS_LOG")
    if path:
        try:
            os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
            with open(path, "a", encoding="utf-8") as fh:
                fh.write(line + "\n")
        except OSError:
            pass


async def _check_one(session: aiohttp.ClientSession, sem: asyncio.Semaphore,
                     feed_name: str, url: str, now: datetime,
                     max_age: timedelta) -> tuple[str, str, timedelta | None]:
    fetched_ok = False
    parsed_ok = False
    entry_count = 0
    newest: datetime | None = None
    async with sem:
        try:
            async with session.get(watchdog_url(feed_name, url),
                                   timeout=_TIMEOUT, headers=_UA) as resp:
                if resp.status == 200:
                    fetched_ok = True
                    content = await resp.read()
        except (aiohttp.ClientError, asyncio.TimeoutError, OSError):
            pass
    if fetched_ok:
        feed = feedparser.parse(content)
        parsed_ok = not (feed.bozo and not feed.entries)
        if parsed_ok:
            entry_count = len(feed.entries)
            newest = newest_entry_time(feed.entries)
    status, age = classify_feed(fetched_ok=fetched_ok, parsed_ok=parsed_ok,
                                entry_count=entry_count, newest=newest,
                                now=now, max_age=max_age)
    return feed_name, status, age


async def _run(feeds: dict[str, tuple], max_age: timedelta) -> None:
    now = datetime.now(timezone.utc)
    sem = asyncio.Semaphore(_CONCURRENCY)
    async with aiohttp.ClientSession() as session:
        results = await asyncio.gather(*(
            _check_one(session, sem, name, spec[0], now, max_age)
            for name, spec in feeds.items()
        ))
    counts: dict[str, int] = {}
    for feed_name, status, age in results:
        counts[status] = counts.get(status, 0) + 1
        if status != "ok":
            _ledger(format_alert(status, feed_name, feeds[feed_name][0],
                                 age=age, now=now))
    summary = " · ".join(f"{k} {counts.get(k, 0)}"
                         for k in ("ok", "stale", "unreachable", "unparseable",
                                   "empty", "undated"))
    print(f"FEED FRESHNESS WATCHDOG: {len(results)} feeds · {summary} "
          f"· threshold {max_age.days}d")


def main() -> None:
    ap = argparse.ArgumentParser(description="Per-feed RSS freshness watchdog (#235).")
    ap.add_argument("--max-age-days", type=float, default=7.0,
                    help="alert when a feed's newest item is older than this (default 7)")
    ap.add_argument("--feeds", default="",
                    help="comma-separated feed names to check (default: all curated)")
    args = ap.parse_args()
    feeds = dict(CURATED_FEEDS)
    if args.feeds:
        wanted = {f.strip() for f in args.feeds.split(",") if f.strip()}
        unknown = wanted - feeds.keys()
        if unknown:
            print(f"unknown feeds: {sorted(unknown)}", file=sys.stderr)
        feeds = {k: v for k, v in feeds.items() if k in wanted}
    asyncio.run(_run(feeds, timedelta(days=args.max_age_days)))


if __name__ == "__main__":
    main()

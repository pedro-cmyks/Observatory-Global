#!/usr/bin/env python3
"""L4 markets — the NEWS-INTENSITY accumulator (forward, point-in-time by construction).

The reverse-study substrate: a daily per-category and per-country news-intensity panel.
Run once per day near end-of-day; each row is a FORWARD snapshot that sees only that
day's data → point-in-time by construction (computed_pit=1). This is why it must start
now: a value reconstructed later from Atlas's retrospective clustering would LEAK future
structure (design §2/§6). There is deliberately NO backfill.

Separate-consumer rule: reads the Atlas PUBLIC API only (/api/v2/threads), writes the
markets-side sqlite store, never Atlas's DB.

Intensity proxy (v0): summed `signal_count` over the 24h thread population, grouped by
`category` and by `subject_countries` (verified subject geography, not coverage volume).
A thread spanning 2 subject countries contributes its count to each (co-occurrence
intensity). This is a PROXY, versioned `news-intensity-v0-threads-24h`; it is refined by
bumping method_version, never by rewriting history. NOTE: the /threads window is a
rolling 24h ending at run time, stamped to the run's UTC calendar day — run at a
CONSISTENT hour so the daily series is comparable.

Usage:
  python3 markets/accumulate_news_intensity.py [--base URL] [--hours 24] [--db PATH]
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.request
from collections import defaultdict
from datetime import datetime, timezone

from markets import store

METHOD_VERSION = "news-intensity-v0-threads-top50-24h"


def fetch_threads(base: str, hours: int) -> list[dict]:
    # /api/v2/threads caps limit at 50 (le=50). v0 intensity is therefore the TOP-50
    # ranked threads' signal_count — a consistent daily proxy, not the full population;
    # refined by bumping METHOD_VERSION (a fuller per-category source), never by rewrite.
    url = f"{base.rstrip('/')}/api/v2/threads?hours={hours}&limit=50"
    req = urllib.request.Request(url, headers={"User-Agent": "AtlasMarketsL4/1.0"})
    with urllib.request.urlopen(req, timeout=30) as r:
        d = json.loads(r.read())
    return d.get("threads", d if isinstance(d, list) else [])


def aggregate(threads: list[dict]) -> tuple[dict[str, tuple[float, int]],
                                            dict[str, tuple[float, int]]]:
    """-> (by_category, by_country); each maps id -> (intensity, n_threads)."""
    cat_i: dict[str, float] = defaultdict(float)
    cat_n: dict[str, int] = defaultdict(int)
    cc_i: dict[str, float] = defaultdict(float)
    cc_n: dict[str, int] = defaultdict(int)
    for t in threads:
        sc = float(t.get("signal_count") or 0)
        cat = (t.get("category") or t.get("parent_domain") or "").strip()
        if cat:
            cat_i[cat] += sc
            cat_n[cat] += 1
        for cc in (t.get("subject_countries") or []):
            if cc:
                cc_i[cc] += sc
                cc_n[cc] += 1
    by_cat = {k: (cat_i[k], cat_n[k]) for k in cat_i}
    by_cc = {k: (cc_i[k], cc_n[k]) for k in cc_i}
    return by_cat, by_cc


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--base",
                    default=os.environ.get("ATLAS_API_BASE",
                                           "https://atlas-api-pedro.fly.dev"))
    ap.add_argument("--hours", type=int, default=24)
    ap.add_argument("--db", default=None)
    args = ap.parse_args()

    day = datetime.now(timezone.utc).date().isoformat()
    try:
        threads = fetch_threads(args.base, args.hours)
    except Exception as e:  # noqa: BLE001
        print(f"news accumulator: API fetch failed ({e}) — no rows written", file=sys.stderr)
        return 1
    if not threads:
        print("news accumulator: 0 threads returned — no rows written (honest empty)",
              file=sys.stderr)
        return 1

    by_cat, by_cc = aggregate(threads)
    db_path = None if args.db is None else __import__("pathlib").Path(args.db)
    conn = store.connect(db_path)
    for cat, (inten, n) in by_cat.items():
        store.upsert_news_intensity(conn, day, "category", cat, inten, n, METHOD_VERSION)
    for cc, (inten, n) in by_cc.items():
        store.upsert_news_intensity(conn, day, "country", cc, inten, n, METHOD_VERSION)

    cov = store.coverage(conn)
    conn.close()
    print(f"news accumulator: {day} — {len(by_cat)} categories + {len(by_cc)} countries "
          f"from {len(threads)} threads; store now holds {cov['news_rows']} news rows "
          f"across {cov['news_days']} day(s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

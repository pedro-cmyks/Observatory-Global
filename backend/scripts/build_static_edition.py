#!/usr/bin/env python3
"""Write the published edition: the JSON files the public Brief reads.

Atlas has no server behind its public page any more. This script asks the
LOCAL API (started by `atlas up`) for exactly the responses the Brief needs
and writes them as files under <out>/edition/, following the same path rule
the frontend uses to look them up (frontend-v2/src/lib/staticEdition.ts —
change both or the page asks for files that were never written):

    /api/v2/country-edition?hours=24&cc=CO
        -> edition/api/v2/country-edition__cc=CO&hours=24.json

Params sorted by key then value; values keep [A-Za-z0-9_.-], anything else
becomes '-'; no query -> no '__' suffix.

Usage (from backend/):
    python -m scripts.build_static_edition --out ~/AtlasLocalWorker/static-edition/site
    python -m scripts.build_static_edition --out DIR --api http://127.0.0.1:8000 --max-countries 250
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

EDITION_VERSION = "static-edition-v1"
HOURS = 24  # the Brief is the day's edition — always 24h (Pedro, 2026-07-05)

# What the Brief and the landing page fetch, with the exact parameters they
# use (frontend-v2/src/pages/BriefNewspaper.tsx, Landing.tsx, lib/delight.ts).
GLOBAL_URLS = [
    "/health",  # the landing page's signal counter
    f"/api/v2/briefing?hours={HOURS}",
    f"/api/v2/briefing/insight?hours={HOURS}",
    "/api/v2/investigation/daily-publication",
    f"/api/v2/attention/eclipse?hours={HOURS}",
    "/api/v2/delight",
    f"/api/v2/threads?hours={HOURS}&limit=4",
    "/api/v2/voice-mix?hours=168",
    f"/api/v2/heat/countries?hours={HOURS}&limit=250",
    "/api/v2/markets",  # the Brief's markets band (honest "not part of the edition" surface)
]


def country_urls(cc: str) -> list[str]:
    return [
        f"/api/v2/country-edition?cc={cc}&hours={HOURS}",
        f"/api/v2/nodes?focus_type=country&focus_value={cc}&hours={HOURS}&limit=5",
        f"/api/v2/threads?hours={HOURS}&limit=6&country_code={cc}",
        f"/api/v2/markets?country={cc}",
    ]


_SAFE = re.compile(r"[^A-Za-z0-9_.-]")


def edition_path(url: str) -> str:
    """Mirror of editionPathFor() in the frontend."""
    parsed = urllib.parse.urlsplit(url)
    path = parsed.path.rstrip("/")
    params = sorted(
        (_SAFE.sub("-", k), _SAFE.sub("-", v))
        for k, v in urllib.parse.parse_qsl(parsed.query, keep_blank_values=True)
    )
    query = "&".join(f"{k}={v}" for k, v in params)
    return f"edition{path}{'__' + query if query else ''}.json"


def fetch_json(api: str, url: str, timeout: float = 120) -> tuple[int, bytes]:
    req = urllib.request.Request(api + url, headers={"accept": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, r.read()
    except urllib.error.HTTPError as e:
        return e.code, e.read()


def write(out: Path, rel: str, body: bytes) -> None:
    target = out / rel
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(body)


def pick_countries(heat: dict | list, briefing: dict, cap: int) -> list[str]:
    """Every country the page can open a door to, most-covered first."""
    seen: list[str] = []

    def add(cc):
        if isinstance(cc, str) and len(cc) == 2 and cc.isalpha() and cc.upper() not in seen:
            seen.append(cc.upper())

    # /heat/countries serves {"items": [{"country_code": ..}]}; the briefing's
    # heat_countries carries {"code": ..}. Accept both spellings.
    rows = (heat.get("items") or heat.get("countries")) if isinstance(heat, dict) else heat
    for row in rows or []:
        if isinstance(row, dict):
            add(row.get("country_code") or row.get("code") or row.get("cc"))
    for row in briefing.get("heat_countries") or []:
        if isinstance(row, dict):
            add(row.get("country_code") or row.get("code"))
    for t in briefing.get("top_threads") or []:
        for cc in (t.get("countries") or t.get("top_countries") or []) if isinstance(t, dict) else []:
            add(cc if isinstance(cc, str) else (cc.get("code") if isinstance(cc, dict) else None))
    return seen[:cap]


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--out", required=True, help="site directory; files go under <out>/edition/")
    ap.add_argument("--api", default="http://127.0.0.1:8000", help="the local API")
    ap.add_argument("--max-countries", type=int, default=250)
    ap.add_argument("--data-through", default=None,
                    help="ISO moment of the newest signal (atlas passes it from the database)")
    args = ap.parse_args()

    out = Path(args.out).expanduser()
    t0 = time.monotonic()
    ok = failed = 0
    cached: dict[str, bytes] = {}

    def grab(url: str) -> bool:
        nonlocal ok, failed
        status, body = fetch_json(args.api, url)
        if status != 200:
            failed += 1
            print(f"  FAILED {status} {url}", flush=True)
            return False
        write(out, edition_path(url), body)
        cached[url] = body
        ok += 1
        return True

    for url in GLOBAL_URLS:
        grab(url)
    if f"/api/v2/briefing?hours={HOURS}" not in cached:
        print("build_static_edition: the briefing itself failed — no edition written", flush=True)
        return 1

    heat = json.loads(cached.get(f"/api/v2/heat/countries?hours={HOURS}&limit=250", b"[]"))
    briefing = json.loads(cached[f"/api/v2/briefing?hours={HOURS}"])
    countries = pick_countries(heat, briefing, args.max_countries)
    print(f"  global     {ok} files · {len(countries)} countries to snapshot", flush=True)

    done = []
    for i, cc in enumerate(countries, 1):
        if all(grab(u) for u in country_urls(cc)):
            done.append(cc)
        if i % 25 == 0:
            print(f"      {i}/{len(countries)} countries", flush=True)

    meta = {
        "version": EDITION_VERSION,
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "data_through": args.data_through,
        "countries": done,
        "files": ok,
    }
    write(out, "edition/meta.json", json.dumps(meta, indent=1).encode())
    size = sum(p.stat().st_size for p in (out / "edition").rglob("*.json"))
    print(f"  edition    {ok} files, {failed} failed, {len(done)} country editions, "
          f"{size / 1e6:.1f} MB · {time.monotonic() - t0:.0f}s", flush=True)
    return 0 if failed == 0 else 2


if __name__ == "__main__":
    sys.exit(main())

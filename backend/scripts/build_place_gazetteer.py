#!/usr/bin/env python3
"""Build backend/app/data/place_to_country.json — place name → ISO2 gazetteer.

Source: GeoNames (https://www.geonames.org, CC-BY 4.0):
  - cities15000.zip      → every city with population >= 15,000 (name + asciiname)
  - admin1CodesASCII.txt → first-order admin divisions (states/provinces/regions)

Rules (precision-first, documented in the emitted _meta):
  - keys are normalized: NFC, casefold, whitespace collapsed
  - names < 4 chars are DROPPED (precision: "Ufa", "Rio", "Of" never resolve)
  - a small stoplist drops city names that are extremely common English words
    ("Along" IN, "Most" CZ, "Best" NL, "Deal" GB); legitimate major cities that
    are also words (Split HR, Nice FR, Mobile US) are KEPT — ambiguity + length
    are the real guards, not aggressive stoplisting
  - a name mapping to >1 country is DROPPED unless one country's largest
    holder has >= 10x the population of the runner-up (keeps London→GB over
    London CA; drops Hamilton CA/NZ/US/BM). Admin-1 rows carry population 0 in
    the dump, so any 15k+ city outranks a same-named admin-1 region abroad.

Coverage limits (honest): only GeoNames `name` + `asciiname` are kept — NO
alternatenames — so native-script forms (Cyrillic, Arabic, CJK, …) do NOT
resolve through this gazetteer; the resolver's country-pattern fallback covers
a hand-built native lexicon at country level only.

Repeatable: downloads are cached in --cache-dir; re-run to rebuild.

Usage:
  .venv/bin/python scripts/build_place_gazetteer.py \
      [--cache-dir /tmp/geonames] [--out app/data/place_to_country.json]
"""
from __future__ import annotations

import argparse
import datetime as dt
import io
import json
import re
import sys
import unicodedata
import urllib.request
import zipfile
from collections import defaultdict
from pathlib import Path
from typing import Iterable

CITIES_URL = "https://download.geonames.org/export/dump/cities15000.zip"
ADMIN1_URL = "https://download.geonames.org/export/dump/admin1CodesASCII.txt"

MIN_NAME_LEN = 4
DOMINANCE_RATIO = 10

# Extremely common English words that are also GeoNames entries (small US
# towns, mostly) where the word sense vastly outweighs the place sense in news
# text. Deliberately small — ambiguity + length rules do the real work
# (Split/Nice/Mobile/Male/Salé stay; Hamilton/San Jose/Florence drop as
# ambiguous). "odessa" is a CROSS-SPELLING collision: GeoNames names the
# Ukrainian city "Odesa", so Odessa TX won the map undetected — dropped.
COMMON_WORD_STOPLIST = {
    "along", "most", "best", "deal",
    "normal", "surprise", "university", "union", "march",
    "independence", "liberty", "enterprise",
    "hurricane", "holiday", "sunrise",
    "odessa",
}

_WS = re.compile(r"\s+")


def normalize_place(value: str) -> str:
    """Must stay in sync with app.services.subject_geography._normalize_place."""
    return _WS.sub(" ", unicodedata.normalize("NFC", str(value or "")).casefold()).strip()


def _fetch(url: str, cache_dir: Path) -> bytes:
    cache_dir.mkdir(parents=True, exist_ok=True)
    cached = cache_dir / url.rsplit("/", 1)[-1]
    if cached.exists() and cached.stat().st_size > 0:
        print(f"cache hit: {cached}", file=sys.stderr)
        return cached.read_bytes()
    print(f"downloading {url} ...", file=sys.stderr)
    req = urllib.request.Request(url, headers={"User-Agent": "atlas-gazetteer-builder/1.0"})
    with urllib.request.urlopen(req, timeout=120) as resp:
        data = resp.read()
    cached.write_bytes(data)
    return data


def parse_cities(text: str) -> Iterable[tuple[str, str, str, int]]:
    """Yield (name, asciiname, country_iso2, population) from cities15000.txt."""
    for line in text.splitlines():
        if not line.strip():
            continue
        cols = line.split("\t")
        if len(cols) < 15:
            continue
        name, asciiname, country = cols[1], cols[2], cols[8].strip().upper()
        try:
            population = int(cols[14] or 0)
        except ValueError:
            population = 0
        if len(country) == 2:
            yield name, asciiname, country, population


def parse_admin1(text: str) -> Iterable[tuple[str, str, str]]:
    """Yield (name, asciiname, country_iso2) from admin1CodesASCII.txt.

    Format: `CC.ADM1<TAB>name<TAB>asciiname<TAB>geonameid`.
    """
    for line in text.splitlines():
        cols = line.split("\t")
        if len(cols) < 3 or "." not in cols[0]:
            continue
        country = cols[0].split(".", 1)[0].strip().upper()
        if len(country) == 2:
            yield cols[1], cols[2], country


def build_places(
    city_rows: Iterable[tuple[str, str, str, int]],
    admin1_rows: Iterable[tuple[str, str, str]],
) -> dict[str, str]:
    """Apply normalization + length/stoplist/ambiguity-dominance rules."""
    # normalized name -> {country: max population seen for that name there}
    by_name: dict[str, dict[str, int]] = defaultdict(dict)

    def _add(raw: str, country: str, population: int) -> None:
        key = normalize_place(raw)
        if len(key) < MIN_NAME_LEN or key in COMMON_WORD_STOPLIST:
            return
        bucket = by_name[key]
        bucket[country] = max(bucket.get(country, 0), population)

    for name, asciiname, country, population in city_rows:
        _add(name, country, population)
        _add(asciiname, country, population)
    for name, asciiname, country in admin1_rows:
        # admin-1 rows carry no population in the dump → 0 (documented in _meta)
        _add(name, country, 0)
        _add(asciiname, country, 0)

    places: dict[str, str] = {}
    for key, countries in by_name.items():
        if len(countries) == 1:
            places[key] = next(iter(countries))
            continue
        ranked = sorted(countries.items(), key=lambda kv: -kv[1])
        top_country, top_pop = ranked[0]
        second_pop = ranked[1][1]
        if top_pop > 0 and top_pop >= DOMINANCE_RATIO * max(second_pop, 1):
            places[key] = top_country  # dominant holder kept
        # else: ambiguous, dropped — the resolver returns None, never a guess
    return places


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cache-dir", type=Path, default=Path("/tmp/geonames-cache"))
    parser.add_argument(
        "--out", type=Path,
        default=Path(__file__).resolve().parents[1] / "app" / "data" / "place_to_country.json",
    )
    args = parser.parse_args()

    zip_bytes = _fetch(CITIES_URL, args.cache_dir)
    with zipfile.ZipFile(io.BytesIO(zip_bytes)) as zf:
        cities_text = zf.read("cities15000.txt").decode("utf-8")
    admin1_text = _fetch(ADMIN1_URL, args.cache_dir).decode("utf-8")

    city_rows = list(parse_cities(cities_text))
    admin1_rows = list(parse_admin1(admin1_text))
    places = build_places(city_rows, admin1_rows)

    doc = {
        "_meta": {
            "attribution": (
                "Place data from GeoNames (https://www.geonames.org), "
                "licensed under CC-BY 4.0 "
                "(https://creativecommons.org/licenses/by/4.0/)."
            ),
            "license": "CC-BY 4.0",
            "sources": [CITIES_URL, ADMIN1_URL],
            "built_at": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "builder": "backend/scripts/build_place_gazetteer.py",
            "rules": {
                "normalize": "NFC + casefold + whitespace collapse",
                "min_name_len": MIN_NAME_LEN,
                "common_word_stoplist": sorted(COMMON_WORD_STOPLIST),
                "ambiguity": (
                    f"names in >1 country dropped unless the top country holds "
                    f">= {DOMINANCE_RATIO}x the runner-up's population; admin-1 "
                    "rows count as population 0, so any 15k+ city outranks a "
                    "same-named admin-1 region abroad"
                ),
                "coverage": (
                    "GeoNames name + asciiname only (no alternatenames): "
                    "native-script forms (Cyrillic/Arabic/CJK/...) do not "
                    "resolve here"
                ),
            },
            "counts": {
                "city_rows": len(city_rows),
                "admin1_rows": len(admin1_rows),
                "places": len(places),
            },
        },
        "places": dict(sorted(places.items())),
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(
        json.dumps(doc, ensure_ascii=False, separators=(",", ":"), sort_keys=False),
        encoding="utf-8",
    )
    size = args.out.stat().st_size
    print(f"wrote {args.out} — {len(places)} places, {size/1_000_000:.2f} MB", file=sys.stderr)
    if size >= 1_500_000:
        print("WARNING: exceeded the 1.5MB budget", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

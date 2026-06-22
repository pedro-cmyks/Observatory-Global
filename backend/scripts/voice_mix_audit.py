#!/usr/bin/env python3
"""Voice Mix audit — measure narrative diversity of the live corpus (#160/#230).

Atlas aggregates global media, but "global" is a claim that must be measured,
not assumed. This read-only report quantifies WHOSE voice is in the corpus:
language mix, English dominance, CJK presence, state-media share, and the
geographic spread of source origins.

It is the proof instrument for the diversification program: run it before a
change to capture a baseline, run it after to show the delta. The single
`diversity_score` (0-100) is a transparent blend of three sub-metrics defined
below — it exists to make "did we get more diverse?" a number, not a vibe.

Sub-metrics (all over the language-KNOWN slice; 'xx'/untagged GDELT excluded):
  - english_balance   = 1 - english_share_of_known   (lower English = higher)
  - language_entropy  = Shannon(H) over known langs, normalized by ln(n_langs)
  - cjk_coverage      = min(cjk_share / CJK_TARGET, 1.0)   (target 5% of known)
  diversity_score = 100 * mean(english_balance, language_entropy, cjk_coverage)

Usage:
    .venv/bin/python -m scripts.voice_mix_audit [--hours 168] [--json-out PATH]
"""
from __future__ import annotations

import argparse
import asyncio
import json
import math
import os
from datetime import datetime, timezone

import asyncpg

DATABASE_URL = os.getenv("DATABASE_URL", "")
CJK_LANGS = ("zh", "ja", "ko")
CJK_TARGET = 0.05  # aspirational CJK share of language-known corpus

LANG_SQL = """
SELECT COALESCE(NULLIF(TRIM(source_lang), ''), '(null)') AS lang, COUNT(*) AS n
FROM signals_v2
WHERE timestamp > now() - ($1::int * interval '1 hour')
GROUP BY 1
"""

ORIGIN_SQL = """
SELECT COALESCE(NULLIF(TRIM(source_origin_country), ''), '(null)') AS origin,
       COUNT(*) AS n
FROM signals_v2
WHERE timestamp > now() - ($1::int * interval '1 hour')
GROUP BY 1
"""

EXTRA_SQL = """
SELECT
    COUNT(*)                                          AS total,
    COUNT(*) FILTER (WHERE is_state_media)            AS state_media,
    COUNT(*) FILTER (WHERE source_family = 'api')     AS api_family,
    COUNT(DISTINCT source_name)                       AS distinct_sources
FROM signals_v2
WHERE timestamp > now() - ($1::int * interval '1 hour')
"""

# Untagged buckets: 'xx' is GDELT's no-language marker, '(null)' is genuinely
# missing. Both are "language unknown" — excluded from the known-language slice
# so English dominance is measured honestly against signals we can attribute.
UNKNOWN_LANGS = {"xx", "(null)", "un", "und"}


def _shannon_norm(counts: list[int]) -> float:
    total = sum(counts)
    if total <= 0 or len(counts) <= 1:
        return 0.0
    h = -sum((c / total) * math.log(c / total) for c in counts if c > 0)
    return h / math.log(len(counts))


async def audit(hours: int) -> dict:
    conn = await asyncpg.connect(DATABASE_URL)
    try:
        lang_rows = await conn.fetch(LANG_SQL, hours)
        origin_rows = await conn.fetch(ORIGIN_SQL, hours)
        extra = await conn.fetchrow(EXTRA_SQL, hours)
    finally:
        await conn.close()

    total = int(extra["total"])
    langs = {r["lang"]: int(r["n"]) for r in lang_rows}
    known = {k: v for k, v in langs.items() if k not in UNKNOWN_LANGS}
    known_total = sum(known.values())
    unknown_total = total - known_total

    en = known.get("en", 0)
    cjk = {l: known.get(l, 0) for l in CJK_LANGS}
    cjk_total = sum(cjk.values())

    english_share_known = (en / known_total) if known_total else 0.0
    cjk_share = (cjk_total / known_total) if known_total else 0.0
    lang_entropy = _shannon_norm(list(known.values()))

    english_balance = 1.0 - english_share_known
    cjk_coverage = min(cjk_share / CJK_TARGET, 1.0) if CJK_TARGET else 0.0
    diversity_score = round(
        100 * (english_balance + lang_entropy + cjk_coverage) / 3, 1
    )

    origins = {r["origin"]: int(r["n"]) for r in origin_rows}
    origin_known = {k: v for k, v in origins.items() if k != "(null)"}
    ok_total = sum(origin_known.values()) or 1
    # HHI concentration of origin countries (0=spread, 1=monopoly)
    hhi = sum((v / ok_total) ** 2 for v in origin_known.values())
    top_origins = sorted(origin_known.items(), key=lambda kv: -kv[1])[:10]

    top_langs = sorted(known.items(), key=lambda kv: -kv[1])[:15]
    state = int(extra["state_media"])

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "window_hours": hours,
        "total_signals": total,
        "language_known": known_total,
        "language_unknown": unknown_total,
        "unknown_pct": round(100 * unknown_total / total, 1) if total else 0,
        "english_share_of_known": round(english_share_known, 4),
        "non_english_share_of_known": round(1 - english_share_known, 4),
        "cjk": {**cjk, "total": cjk_total, "share_of_known": round(cjk_share, 4)},
        "language_entropy_norm": round(lang_entropy, 4),
        "distinct_known_languages": len(known),
        "state_media": state,
        "state_media_pct": round(100 * state / total, 2) if total else 0,
        "distinct_sources": int(extra["distinct_sources"]),
        "origin_hhi": round(hhi, 4),
        "top_origin_countries": [{"cc": c, "n": n} for c, n in top_origins],
        "top_languages": [{"lang": l, "n": n} for l, n in top_langs],
        "diversity_score": diversity_score,
        "_components": {
            "english_balance": round(english_balance, 4),
            "language_entropy_norm": round(lang_entropy, 4),
            "cjk_coverage": round(cjk_coverage, 4),
        },
    }


def _print_summary(r: dict) -> None:
    print(f"\n=== Voice Mix Audit — last {r['window_hours']}h ===")
    print(f"total signals:        {r['total_signals']:,}")
    print(f"language unknown:     {r['language_unknown']:,} ({r['unknown_pct']}%)")
    print(f"language known:       {r['language_known']:,}")
    print(f"English share known:  {r['english_share_of_known']*100:.1f}%")
    print(f"non-English share:    {r['non_english_share_of_known']*100:.1f}%")
    c = r["cjk"]
    print(f"CJK (zh/ja/ko):       {c['zh']}/{c['ja']}/{c['ko']}  "
          f"= {c['total']} ({c['share_of_known']*100:.2f}% of known)")
    print(f"language entropy:     {r['language_entropy_norm']} "
          f"({r['distinct_known_languages']} known langs)")
    print(f"state media:          {r['state_media']:,} ({r['state_media_pct']}%)")
    print(f"origin HHI:           {r['origin_hhi']} (1.0 = single-country)")
    print(f"top origins:          " +
          ", ".join(f"{o['cc']} {o['n']}" for o in r['top_origin_countries'][:6]))
    print(f"\n>>> DIVERSITY SCORE:  {r['diversity_score']} / 100")
    print(f"    components: {r['_components']}\n")


async def main() -> None:
    ap = argparse.ArgumentParser(description="Voice Mix diversity audit")
    ap.add_argument("--hours", type=int, default=168)
    ap.add_argument("--json-out", type=str, default=None)
    args = ap.parse_args()

    if not DATABASE_URL:
        raise SystemExit("DATABASE_URL not set")

    result = await audit(args.hours)
    _print_summary(result)

    if args.json_out:
        with open(args.json_out, "w") as f:
            json.dump(result, f, indent=2)
        print(f"wrote {args.json_out}")


if __name__ == "__main__":
    asyncio.run(main())

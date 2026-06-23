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
import os
from datetime import datetime, timezone

import asyncpg

from app.services import voice_mix

DATABASE_URL = os.getenv("DATABASE_URL", "")

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

async def audit(hours: int) -> dict:
    conn = await asyncpg.connect(DATABASE_URL)
    try:
        lang_rows = await conn.fetch(LANG_SQL, hours)
        origin_rows = await conn.fetch(ORIGIN_SQL, hours)
        extra = await conn.fetchrow(EXTRA_SQL, hours)
    finally:
        await conn.close()

    lang_counts = {r["lang"]: int(r["n"]) for r in lang_rows}
    origin_counts = {r["origin"]: int(r["n"]) for r in origin_rows}
    report = voice_mix.compute(
        lang_counts, origin_counts,
        int(extra["total"]), int(extra["state_media"]),
        int(extra["distinct_sources"]),
    )
    report["generated_at"] = datetime.now(timezone.utc).isoformat()
    report["window_hours"] = hours
    return report


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
    ve = r.get("voice_entropy", 0)
    band = r.get("voice_entropy_target", [0.65, 0.70])
    status = "IN TARGET" if band[0] <= ve <= band[1] else ("ABOVE" if ve > band[1] else "below")
    print(f"\n>>> VOICE DIVERSITY (origin entropy): {ve}  "
          f"[target {band[0]}-{band[1]} → {status}]  "
          f"over {r.get('distinct_origin_countries', 0)} countries")
    print(f">>> DIVERSITY SCORE (language):       {r['diversity_score']} / 100")
    print(f"    components: {r['components']}\n")


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

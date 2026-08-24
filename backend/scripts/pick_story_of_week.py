#!/usr/bin/env python
"""Story-of-the-week picker (READ-ONLY) — the weekly LinkedIn ritual's shortlist.

Ranks the publishable stories of the last N days so Pedro can pick ONE to share
(ThemeDetail's "LinkedIn kit" builds the card + caption once a story is open).

Publishable = dynamic_topics active, recently seen, not junk, and court-entailed
when the court column exists. The score is deliberately simple and printed in
components, never as an opaque total:

    vol  = log10(1 + evidence_members)          scale, log-damped (volume never buys the top alone)
    geo  = 2 * min(countries, 12) / 12          cross-country spread of member signals
    lang = 2 * min(langs, 6) / 6                cross-language spread of member signals
    score = vol + geo + lang

Honesty notes printed with the output:
  * evidence members = topic_members role='evidence' engine_version='v1-compat'
    (non-quarantined when that column exists) — the served membership.
  * country/lang spreads are measured over member signals still in the 7-day
    hot window (signals_v2 retention); older members can't contribute.
  * Any column this script expected but the schema doesn't have is reported,
    and the corresponding filter/measure is skipped — never guessed.

Usage:
    DATABASE_URL=... python backend/scripts/pick_story_of_week.py [--days 7] [--limit 10]

No writes. Safe to run any time.
"""
from __future__ import annotations

import argparse
import asyncio
import math
import os
import sys

COLUMNS_SQL = """
    SELECT table_name, column_name
    FROM information_schema.columns
    WHERE table_schema = 'public'
      AND table_name IN ('dynamic_topics', 'topic_members', 'signals_v2')
"""


async def main() -> int:
    ap = argparse.ArgumentParser(description="Rank publishable stories for the weekly share ritual (read-only)")
    ap.add_argument("--days", type=int, default=7, help="Recency window in days (default 7)")
    ap.add_argument("--limit", type=int, default=10, help="Rows to print (default 10)")
    ap.add_argument("--country", default=None,
                    help="Comma-separated ISO2 codes — only stories with member "
                         "signals in these countries (e.g. CO,MX)")
    ap.add_argument("--region", choices=["latam"], default=None,
                    help="Preset country set; combines with --country")
    args = ap.parse_args()

    import asyncpg

    dsn = os.environ.get("DATABASE_URL")
    if not dsn:
        print("DATABASE_URL not set", file=sys.stderr)
        return 2

    conn = await asyncpg.connect(dsn, statement_cache_size=0)
    try:
        cols: dict[str, set[str]] = {}
        for r in await conn.fetch(COLUMNS_SQL):
            cols.setdefault(r["table_name"], set()).add(r["column_name"])

        dt = cols.get("dynamic_topics", set())
        tm = cols.get("topic_members", set())
        sv = cols.get("signals_v2", set())
        if not dt:
            print("dynamic_topics not found — nothing to rank", file=sys.stderr)
            return 2

        # ---- filters, each applied only when its column really exists ----
        filters = ["last_seen > now() - ($1::int * interval '1 day')"]
        skipped: list[str] = []
        if "state" in dt:
            filters.append("state = 'active'")
        else:
            skipped.append("dynamic_topics.state (active filter skipped)")
        if "is_junk" in dt:
            filters.append("is_junk IS DISTINCT FROM TRUE")
        else:
            skipped.append("dynamic_topics.is_junk (junk filter skipped)")
        court_col = "label_status" if "label_status" in dt else None
        if court_col:
            filters.append(f"{court_col} = 'entailed'")
        else:
            skipped.append("dynamic_topics.label_status (court filter skipped — no court verdict measurable)")

        court_select = f"c.{court_col}" if court_col else "NULL::text"

        # ---- member aggregation, only over what topic_members really has ----
        if not tm or "topic_id" not in tm:
            print("topic_members not found — cannot count evidence members", file=sys.stderr)
            return 2
        mem_where = ["tm.topic_id = 'dynamic-topic-' || c.id::text"]
        if "role" in tm:
            mem_where.append("tm.role = 'evidence'")
        else:
            skipped.append("topic_members.role (role filter skipped)")
        if "engine_version" in tm:
            mem_where.append("tm.engine_version = 'v1-compat'")
        else:
            skipped.append("topic_members.engine_version (engine filter skipped)")
        if "quarantined" in tm:
            mem_where.append("tm.quarantined IS DISTINCT FROM TRUE")

        measure_countries = "country_code" in sv
        measure_langs = "source_lang" in sv
        if not measure_countries:
            skipped.append("signals_v2.country_code (country spread not measurable)")
        if not measure_langs:
            skipped.append("signals_v2.source_lang (language spread not measurable)")

        country_expr = (
            "count(DISTINCT s.country_code) FILTER (WHERE s.country_code IS NOT NULL)"
            if measure_countries else "NULL::bigint"
        )
        lang_expr = (
            "count(DISTINCT s.source_lang) FILTER (WHERE s.source_lang IS NOT NULL AND s.source_lang <> 'xx')"
            if measure_langs else "NULL::bigint"
        )

        # Optional country/region scoping (Pedro 08-24: "quisiera poner algo de
        # Colombia o de Latinoamérica"). A story qualifies when >=1 member
        # signal carries one of the requested subject countries; the matched
        # codes and in-set member count are printed, never inferred.
        LATAM = ["CO", "VE", "EC", "PE", "BO", "BR", "AR", "CL", "PY", "UY",
                 "MX", "GT", "HN", "SV", "NI", "CR", "PA", "CU", "DO", "HT",
                 "GY", "SR", "BZ", "PR"]
        cc_set: list[str] = []
        if args.region == "latam":
            cc_set += LATAM
        if args.country:
            cc_set += [c.strip().upper() for c in args.country.split(",") if c.strip()]
        cc_set = sorted(set(cc_set))
        if cc_set and not measure_countries:
            raise SystemExit("--country/--region need signals_v2.country_code")

        region_select = (
            ",\n                   count(tm.signal_id) FILTER (WHERE s.country_code = ANY($2::text[])) AS region_members"
            ",\n                   array_remove(array_agg(DISTINCT s.country_code) FILTER (WHERE s.country_code = ANY($2::text[])), NULL) AS region_ccs"
            if cc_set else ""
        )
        region_having = (
            "HAVING count(tm.signal_id) FILTER (WHERE s.country_code = ANY($2::text[])) > 0"
            if cc_set else ""
        )
        sql = f"""
            WITH c AS (
                SELECT id, label, {court_select.replace('c.', '')} AS court
                FROM dynamic_topics c
                WHERE {' AND '.join(filters)}
            )
            SELECT c.id, c.label, c.court,
                   count(tm.signal_id) AS members,
                   {country_expr} AS countries,
                   {lang_expr} AS langs{region_select}
            FROM c
            LEFT JOIN topic_members tm ON {' AND '.join(mem_where)}
            LEFT JOIN signals_v2 s ON s.id = tm.signal_id
            GROUP BY c.id, c.label, c.court
            {region_having}
        """
        rows = (await conn.fetch(sql, args.days, cc_set)
                if cc_set else await conn.fetch(sql, args.days))
    finally:
        await conn.close()

    # ---- transparent score, computed here so every component is printable ----
    scored = []
    for r in rows:
        members = r["members"] or 0
        countries = r["countries"]
        langs = r["langs"]
        vol = math.log10(1 + members)
        geo = 2 * min(countries, 12) / 12 if countries is not None else 0.0
        lang = 2 * min(langs, 6) / 6 if langs is not None else 0.0
        scored.append({
            "id": r["id"], "label": r["label"] or "(unlabeled)", "court": r["court"],
            "members": members, "countries": countries, "langs": langs,
            "vol": vol, "geo": geo, "lang": lang, "score": vol + geo + lang,
            "region_members": r["region_members"] if "region_members" in r.keys() else None,
            "region_ccs": list(r["region_ccs"] or []) if "region_ccs" in r.keys() else None,
        })
    scored.sort(key=lambda x: x["score"], reverse=True)

    print(f"Story of the week — publishable stories, last {args.days}d "
          f"({len(scored)} candidates after filters)")
    print("filters: active" + (" · not-junk" if "is_junk" in dt else "")
          + (" · court=entailed" if court_col else "")
          + f" · last_seen within {args.days}d")
    print("spreads measured over member signals still in the hot window (7d retention)")
    if skipped:
        print("NOT measurable in this schema: " + "; ".join(skipped))
    print()
    hdr = (f"{'#':>2}  {'score':>6}  {'vol':>5} {'geo':>5} {'lang':>5}  "
           f"{'members':>7} {'ctry':>4} {'lang':>4}  {'court':<8} {'topic':<18} label")
    print(hdr)
    print("-" * len(hdr))
    for i, s in enumerate(scored[: args.limit], 1):
        ctry = str(s["countries"]) if s["countries"] is not None else "n/m"
        lng = str(s["langs"]) if s["langs"] is not None else "n/m"
        label = s["label"][:56]
        region = ""
        if s.get("region_members") is not None:
            region = (f"  [{s['region_members']} in "
                      f"{','.join(s['region_ccs'][:4])}"
                      f"{'…' if len(s['region_ccs']) > 4 else ''}]")
        print(f"{i:>2}  {s['score']:>6.3f}  {s['vol']:>5.2f} {s['geo']:>5.2f} {s['lang']:>5.2f}  "
              f"{s['members']:>7} {ctry:>4} {lng:>4}  {(s['court'] or 'n/m'):<8} "
              f"dynamic-topic-{s['id']:<5}  {label}{region}")
    print()
    print("deep links:")
    for i, s in enumerate(scored[: args.limit], 1):
        print(f"{i:>2}. /app?theme=dynamic-topic-{s['id']}  —  {s['label'][:64]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))

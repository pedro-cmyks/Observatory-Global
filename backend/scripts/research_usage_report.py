#!/usr/bin/env python
"""L3 usage read (W0, L3 deep review 2026-07-05) — the weekly numbers that make
the wedge anti-goal governable for the investigation layer.

Joins the two L3 signals:
  - telemetry_events: workbench_open, investigation_created, pin,
    dossier_generated, search_story_open, first_value_moment{kind}
  - research_pin_events (#218): impression/open/pin/unpin/dismiss per plan

This finally READS research_pin_events (it was write-only since mig 053).
Fold the output into the weekly telemetry read (playbook PB-8).

Usage: python backend/scripts/research_usage_report.py [--days 7]
"""
from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys

TELEMETRY_SQL = """
    SELECT event,
           COALESCE(props->>'kind', '') AS kind,
           count(*) AS n,
           count(DISTINCT session_id) AS sessions
    FROM telemetry_events
    WHERE created_at > NOW() - ($1::int * INTERVAL '1 day')
      AND (event IN ('workbench_open', 'investigation_created', 'pin',
                     'dossier_generated', 'search_story_open', 'search_query',
                     'app_open')
           OR event = 'first_value_moment')
    GROUP BY event, COALESCE(props->>'kind', '')
    ORDER BY n DESC
"""

PIN_EVENTS_SQL = """
    SELECT event_type,
           count(*) AS n,
           count(DISTINCT plan_id) AS plans,
           count(DISTINCT investigation_id) AS investigations
    FROM research_pin_events
    WHERE created_at > NOW() - ($1::int * INTERVAL '1 day')
    GROUP BY event_type
    ORDER BY n DESC
"""

# Funnel: of sessions that opened the app, how many reached each L3 stage.
FUNNEL_SQL = """
    WITH stage AS (
        SELECT session_id,
               bool_or(event = 'app_open') AS opened,
               bool_or(event = 'search_query') AS searched,
               bool_or(event = 'search_story_open') AS story,
               bool_or(event = 'workbench_open') AS workbench,
               bool_or(event = 'investigation_created') AS created,
               bool_or(event = 'pin') AS pinned,
               bool_or(event = 'dossier_generated') AS reported
        FROM telemetry_events
        WHERE created_at > NOW() - ($1::int * INTERVAL '1 day')
        GROUP BY session_id
    )
    SELECT count(*) FILTER (WHERE opened) AS opened,
           count(*) FILTER (WHERE searched) AS searched,
           count(*) FILTER (WHERE story) AS story,
           count(*) FILTER (WHERE workbench) AS workbench,
           count(*) FILTER (WHERE created) AS created,
           count(*) FILTER (WHERE pinned) AS pinned,
           count(*) FILTER (WHERE reported) AS reported
    FROM stage
"""


async def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--days", type=int, default=7)
    args = ap.parse_args()

    import asyncpg
    dsn = os.environ.get("DATABASE_URL")
    if not dsn:
        print("DATABASE_URL not set", file=sys.stderr)
        return 2
    conn = await asyncpg.connect(dsn, statement_cache_size=0)
    try:
        tele = await conn.fetch(TELEMETRY_SQL, args.days)
        pins = await conn.fetch(PIN_EVENTS_SQL, args.days)
        funnel = await conn.fetchrow(FUNNEL_SQL, args.days)
    finally:
        await conn.close()

    print(f"L3 usage read — last {args.days}d\n")

    print("telemetry (client):")
    if not tele:
        print("  (no events)")
    for r in tele:
        label = f"{r['event']}" + (f"[{r['kind']}]" if r["kind"] else "")
        print(f"  {label:40s} {r['n']:>6d} ev  {r['sessions']:>4d} sessions")

    print("\nresearch_pin_events (#218 server log):")
    if not pins:
        print("  (no events)")
    for r in pins:
        print(f"  {r['event_type']:40s} {r['n']:>6d} ev  "
              f"{r['plans']:>4d} plans  {r['investigations'] or 0:>3d} investigations")

    print("\nsession funnel (app → search → story → workbench → created → pin → report):")
    stages = ["opened", "searched", "story", "workbench", "created", "pinned", "reported"]
    vals = {s: (funnel[s] or 0) for s in stages}
    base = vals["opened"] or 1
    for s in stages:
        pct = 100.0 * vals[s] / base
        print(f"  {s:10s} {vals[s]:>5d}  ({pct:5.1f}% of opened)")

    # B0 (L1 review): AI-lane health — the Editor's Analysis went silently
    # dark for ~6 days once; the weekly read now checks it explicitly.
    api = os.environ.get("ATLAS_API_URL", "https://atlas-api-pedro.fly.dev")
    print("\nAI-lane health (insight endpoints):")
    try:
        import httpx
        async with httpx.AsyncClient(timeout=30) as client:
            r = await client.get(f"{api}/api/v2/briefing/insight?hours=24")
            d = r.json()
            status = d.get("provider") or d.get("error") or ("cached" if d.get("insight") else "unknown")
            alive = bool(d.get("insight"))
            print(f"  briefing/insight: {'ALIVE' if alive else 'DEAD'} ({status})")
            if not alive:
                print("  ⚠ Editor's Analysis is dark — check ANTHROPIC/DEEPSEEK keys (PB-8).")
    except Exception as exc:
        print(f"  check failed: {exc}")

    print("\n" + json.dumps({"days": args.days, "funnel": vals}))
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))

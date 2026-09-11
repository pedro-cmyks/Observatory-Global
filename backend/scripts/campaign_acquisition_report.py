#!/usr/bin/env python3
"""Campaign acquisition read — did the LinkedIn post bring anyone, and what
did they do? (campaign spec 2026-08-24 §2.2 — the weekly read of the ritual)

Reads telemetry_events only (read-only). Every client event carries
`props.acq` (this visit's touch) and `props.acq_first` (the client's first
touch of record) since 2026-09-11 (frontend lib/acquisition.ts). The
campaign link tags: utm_source=linkedin · utm_campaign=sow-YYYY-Www ·
utm_content=<story id>.

Per campaign tag (and per source), by SESSION:
  arrived   — sessions with any tagged event
  opened    — app_open / brief_open
  story     — thread_open / brief_thread_open (the deep link's story rendered)
  value     — first_value_moment
  signed_up — sign_up
  installed — install_prompt_accepted
Plus the untagged baseline (sessions with NO touch at all) so the campaign
cohort is judged against the ambient traffic of the same window, and a
by-day line per campaign so the golden-hour / decay shape is visible.

Honest by construction: a session that never sent an `acq` is reported as
"untagged", never assumed organic-LinkedIn; the lnkd.in wrapper and the iOS
in-app browser strip the referrer, so ONLY the UTM tags count as attribution.

Usage:
  DATABASE_URL=... python scripts/campaign_acquisition_report.py [--days 14]
      [--campaign sow-2026-w37] [--md docs/state/2026-09-18-campaign-read.md]
"""
from __future__ import annotations

import argparse
import asyncio
import os
import sys
from datetime import datetime, timezone

# Event names are the client's (frontend-v2/src/lib/telemetry.ts callers).
_OPEN = ("app_open", "brief_open")
_STORY = ("thread_open", "brief_thread_open", "search_story_open")
_VALUE = ("first_value_moment",)
_SIGNUP = ("sign_up",)
_INSTALL = ("install_prompt_accepted",)

COHORT_SQL = """
WITH ev AS (
    SELECT session_id, event, created_at,
           COALESCE(props->'acq'->>'source', props->'acq_first'->>'source')     AS source,
           COALESCE(props->'acq'->>'campaign', props->'acq_first'->>'campaign') AS campaign,
           COALESCE(props->'acq'->>'content', props->'acq_first'->>'content')   AS content
    FROM telemetry_events
    WHERE created_at > NOW() - ($1::int * INTERVAL '1 day')
      AND session_id IS NOT NULL
),
tagged AS (
    -- a session is attributed to the FIRST tag it ever sent in the window
    SELECT DISTINCT ON (session_id) session_id, source, campaign, content
    FROM ev WHERE source IS NOT NULL
    ORDER BY session_id, created_at
),
sess AS (
    SELECT e.session_id,
           COALESCE(t.source, '(untagged)')   AS source,
           COALESCE(t.campaign, '(untagged)') AS campaign,
           t.content,
           bool_or(e.event = ANY($2::text[])) AS opened,
           bool_or(e.event = ANY($3::text[])) AS story,
           bool_or(e.event = ANY($4::text[])) AS value,
           bool_or(e.event = ANY($5::text[])) AS signed_up,
           bool_or(e.event = ANY($6::text[])) AS installed,
           count(*)                           AS n_events,
           min(e.created_at)                  AS first_seen
    FROM ev e LEFT JOIN tagged t USING (session_id)
    GROUP BY e.session_id, t.source, t.campaign, t.content
)
SELECT source, campaign,
       count(*)                              AS arrived,
       count(*) FILTER (WHERE opened)        AS opened,
       count(*) FILTER (WHERE story)         AS story,
       count(*) FILTER (WHERE value)         AS value,
       count(*) FILTER (WHERE signed_up)     AS signed_up,
       count(*) FILTER (WHERE installed)     AS installed,
       percentile_cont(0.5) WITHIN GROUP (ORDER BY n_events) AS median_events,
       min(first_seen)                       AS first_seen,
       max(first_seen)                       AS last_seen
FROM sess
GROUP BY source, campaign
ORDER BY (source = '(untagged)'), arrived DESC
"""

BY_DAY_SQL = """
WITH ev AS (
    SELECT session_id, created_at,
           COALESCE(props->'acq'->>'campaign', props->'acq_first'->>'campaign') AS campaign
    FROM telemetry_events
    WHERE created_at > NOW() - ($1::int * INTERVAL '1 day')
      AND session_id IS NOT NULL
      AND COALESCE(props->'acq'->>'campaign', props->'acq_first'->>'campaign') IS NOT NULL
),
firsts AS (
    SELECT session_id, campaign, min(created_at) AS first_seen
    FROM ev GROUP BY session_id, campaign
)
SELECT campaign, date_trunc('day', first_seen)::date AS day, count(*) AS new_sessions
FROM firsts
GROUP BY campaign, day
ORDER BY campaign, day
"""


def _pct(n: int, base: int) -> str:
    return f"{(100.0 * n / base):5.1f}%" if base else "   — "


async def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--days", type=int, default=14)
    ap.add_argument("--campaign", default=None, help="only this utm_campaign tag (e.g. sow-2026-w37)")
    ap.add_argument("--md", default=None, help="also write a markdown artifact here")
    args = ap.parse_args()

    import asyncpg

    dsn = os.environ.get("DATABASE_URL")
    if not dsn:
        print("DATABASE_URL not set", file=sys.stderr)
        return 2
    conn = await asyncpg.connect(dsn, statement_cache_size=0)
    try:
        cohorts = await conn.fetch(
            COHORT_SQL, args.days, list(_OPEN), list(_STORY), list(_VALUE), list(_SIGNUP), list(_INSTALL)
        )
        days = await conn.fetch(BY_DAY_SQL, args.days)
    finally:
        await conn.close()

    if args.campaign:
        cohorts = [r for r in cohorts if r["campaign"] in (args.campaign, "(untagged)")]
        days = [r for r in days if r["campaign"] == args.campaign]

    lines: list[str] = []
    out = lines.append
    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    out(f"# Campaign acquisition read — last {args.days}d ({stamp})")
    out("")
    out("Attribution = UTM tags on the first comment's link (utm_source / utm_campaign).")
    out("`(untagged)` = sessions that sent no tag at all — the ambient baseline, NOT LinkedIn.")
    out("")
    out("| source | campaign | arrived | opened | story | value | signed up | installed | median ev | first seen | last seen |")
    out("|---|---|---:|---:|---:|---:|---:|---:|---:|---|---|")
    tagged_total = 0
    for r in cohorts:
        a = r["arrived"]
        if r["source"] != "(untagged)":
            tagged_total += a
        out(
            f"| {r['source']} | {r['campaign']} | {a} "
            f"| {r['opened']} ({_pct(r['opened'], a).strip()}) "
            f"| {r['story']} ({_pct(r['story'], a).strip()}) "
            f"| {r['value']} ({_pct(r['value'], a).strip()}) "
            f"| {r['signed_up']} ({_pct(r['signed_up'], a).strip()}) "
            f"| {r['installed']} "
            f"| {float(r['median_events'] or 0):.0f} "
            f"| {r['first_seen']:%m-%d %H:%M} | {r['last_seen']:%m-%d %H:%M} |"
        )
    if not cohorts:
        out("| — | — | 0 | | | | | | | | |")
    out("")
    if tagged_total == 0:
        out("**No tagged sessions in the window.** Either nothing was published, the post's "
            "first comment carried an untagged link, or the deploy carrying lib/acquisition.ts "
            "is not live yet (check `atlas.acq.v1` in a browser that followed the link).")
        out("")

    if days:
        out("## New tagged sessions by day (golden hour → decay)")
        out("")
        out("| campaign | day | new sessions |")
        out("|---|---|---:|")
        for r in days:
            out(f"| {r['campaign']} | {r['day']} | {r['new_sessions']} |")
        out("")

    out("## How to read it")
    out("")
    out("- `story` = the deep link's story actually rendered (thread_open) — the click paid off.")
    out("- `value` = first_value_moment — the reader reached something Atlas measures.")
    out("- Judge each post against the PREVIOUS posts' rows, not against the untagged baseline "
        "(different intent); the baseline is there to spot a window where everything was down.")
    out("- LinkedIn-side numbers (impressions, reactions, comments ≥10 words, profile views) "
        "live in LinkedIn analytics — pair them by campaign tag in the calendar doc.")

    text = "\n".join(lines)
    print(text)
    if args.md:
        os.makedirs(os.path.dirname(args.md) or ".", exist_ok=True)
        with open(args.md, "w", encoding="utf-8") as fh:
            fh.write(text + "\n")
        print(f"\n(written {args.md})")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))

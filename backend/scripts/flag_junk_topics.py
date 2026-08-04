"""Flag + demote junk topics; report useful coverage (2026-07-09 gate).

Computes the content-based junk flag (scripts/topic_junk.classify_topic_junk) for
every topic that carries unified-v2 members — the served + anchoring population —
from five signals: the R3.1 category, the label, the per-topic distinct-source
count over a member sample, the PR-wire attorney-solicitation receipt fraction
over the same sample (2026-08-03 census class), and the recurring service-content
receipt fraction over the same sample (2026-08-04 fresh-cohort re-census class:
daily exchange-rate posts / rating reiterations / gadget spec listicles /
production-cost report mills / prayer-horoscope-lottery calendars). Persists
dynamic_topics.is_junk / junk_reason, and
(unless --no-demote) demotes junk ACTIVE topics to 'candidate' so they stop serving.

Effects, once persisted:
  - build_unified_topics._load_centroids excludes is_junk anchors -> the junk
    gravity wells stop vacuuming signals next build (coverage reclaim).
  - project_dynamic_topics promotion honors is_junk -> junk never re-promotes.

Also the MEASUREMENT tool: prints junk fraction + useful-coverage (non-junk member
signals / window signals) before/after, so the effect is quantified, not asserted.

Read-mostly + one UPDATE per changed topic (light on a loaded DB). Idempotent,
reversible (UPDATE dynamic_topics SET is_junk=false, junk_reason=NULL). Runs after
build_unified_topics in the embed cron.

  cd backend && python -m scripts.flag_junk_topics [--dry-run] [--no-demote] [--sample 60]
"""
from __future__ import annotations

import argparse
import asyncio
import os
import sys
from collections import Counter, defaultdict

import asyncpg

from scripts.topic_junk import (
    classify_topic_junk,
    is_pr_wire_solicitation,
    is_recurring_service_content,
)

ENGINE_VERSION = "unified-v2"
# The engine version serving/court actually read (thread detail + label court
# default). The service-content witnesses (dt-633/4013/6485/1577, 2026-08-04)
# carry their junk in this lane — their unified-v2 presence is 1-12 incidental
# members — so the service fraction must see the SERVED evidence receipts, not
# only the unified-v2 sample. nsrc + pr-wire stay on the unified-v2 sample
# (unchanged behavior).
SERVED_ENGINE_VERSION = "v1-compat"
# Denominator for the coverage %: embedded signals in the build window. 336h to
# match the runner's PROJECT_HOURS (build_unified_topics --hours). Reported both
# ways (embedded-window and 24h-signals) so the number is unambiguous.
WINDOW_HOURS = 336


async def _topics_with_members(conn: asyncpg.Connection) -> list[asyncpg.Record]:
    # Every topic that carries unified-v2 members = the served + anchoring set
    # (active topics AND u2- candidates that build_unified_topics anchors on).
    return await conn.fetch(
        """
        SELECT dt.id, dt.label, dt.category, dt.state, dt.identity_key,
               count(tm.signal_id) AS mem
        FROM dynamic_topics dt
        JOIN topic_members tm
          ON tm.topic_id = 'dynamic-topic-' || dt.id AND tm.engine_version = $1
        WHERE dt.state = 'active'
           OR (dt.state = 'candidate' AND dt.identity_key LIKE 'u2-%')
        GROUP BY dt.id
        """,
        ENGINE_VERSION,
    )


async def _member_source_stats(
    conn: asyncpg.Connection, ids: list[int], sample: int,
) -> tuple[dict[int, int], dict[int, float | None], dict[int, float | None]]:
    """Per topic, over the `sample` most-recent members PER LANE: distinct
    outlet count + PR-wire spam fraction (both from the unified-v2 sample,
    unchanged) + recurring service-content fraction (over the UNION of the
    unified-v2 sample and the SERVED v1-compat evidence receipts — the lane
    the court measured and the analyst sees; junk in either lane pollutes).
    Fractions are None when the topic yields no joinable rows in their lane."""
    rows = await conn.fetch(
        f"""
        SELECT lane, tid, source_name, source_url, headline FROM (
          SELECT CASE WHEN tm.engine_version = $1 THEN 'u2' ELSE 'served' END
                     AS lane,
                 (split_part(tm.topic_id, '-', 3))::int AS tid, s.source_name,
                 s.source_url, s.headline,
                 row_number() OVER (PARTITION BY tm.topic_id, tm.engine_version
                                    ORDER BY s.timestamp DESC) AS rn
          FROM topic_members tm
          JOIN signals_v2 s ON s.id = tm.signal_id
          WHERE tm.topic_id = ANY($2::text[])
            AND (tm.engine_version = $1
                 OR (tm.engine_version = $3 AND tm.role = 'evidence'
                     AND COALESCE(tm.quarantined, false) = false))
        ) q WHERE rn <= {int(sample)}
        """,
        ENGINE_VERSION,
        [f"dynamic-topic-{i}" for i in ids],
        SERVED_ENGINE_VERSION,
    )
    srcs: dict[int, set[str]] = defaultdict(set)
    pr_counts: dict[int, list[int]] = defaultdict(lambda: [0, 0])  # [spam, total]
    svc_counts: dict[int, list[int]] = defaultdict(lambda: [0, 0])  # [svc, total]
    for r in rows:
        if r["lane"] == "u2":
            if r["source_name"]:
                srcs[r["tid"]].add(r["source_name"])
            pr_counts[r["tid"]][1] += 1
            if is_pr_wire_solicitation(
                    r["source_name"], r["source_url"], r["headline"]):
                pr_counts[r["tid"]][0] += 1
        svc_counts[r["tid"]][1] += 1
        if is_recurring_service_content(r["headline"]):
            svc_counts[r["tid"]][0] += 1
    nsrc = {i: len(srcs.get(i, set())) for i in ids}
    pr_frac = {
        i: (pr_counts[i][0] / pr_counts[i][1] if pr_counts[i][1] else None)
        for i in ids
    }
    svc_frac = {
        i: (svc_counts[i][0] / svc_counts[i][1] if svc_counts[i][1] else None)
        for i in ids
    }
    return nsrc, pr_frac, svc_frac


async def _useful_coverage(conn: asyncpg.Connection, junk_ids: set[int]) -> dict:
    total = await conn.fetchval(
        "SELECT count(DISTINCT signal_id) FROM topic_members WHERE engine_version=$1",
        ENGINE_VERSION,
    )
    junk_sig = 0
    if junk_ids:
        junk_sig = await conn.fetchval(
            """SELECT count(DISTINCT signal_id) FROM topic_members
               WHERE engine_version=$1 AND topic_id = ANY($2::text[])""",
            ENGINE_VERSION,
            [f"dynamic-topic-{i}" for i in junk_ids],
        )
    denom_win = await conn.fetchval(
        """SELECT count(*) FROM signal_embeddings e JOIN signals_v2 s ON s.id=e.signal_id
           WHERE s.timestamp > NOW() - ($1::int * INTERVAL '1 hour')
             AND s.headline IS NOT NULL AND length(s.headline) >= 20""",
        WINDOW_HOURS,
    )
    denom_24 = await conn.fetchval(
        """SELECT count(*) FROM signals_v2 s
           WHERE s.timestamp > NOW() - INTERVAL '24 hours'
             AND s.headline IS NOT NULL AND length(s.headline) >= 20""",
    )
    useful = total - junk_sig
    return {
        "assigned": total, "junk_signals": junk_sig, "useful_signals": useful,
        "denom_window_embedded": denom_win, "denom_24h_signals": denom_24,
        "total_cov_window": total / denom_win if denom_win else 0.0,
        "useful_cov_window": useful / denom_win if denom_win else 0.0,
        "total_cov_24h": total / denom_24 if denom_24 else 0.0,
        "useful_cov_24h": useful / denom_24 if denom_24 else 0.0,
    }


async def run(dry_run: bool, no_demote: bool, sample: int,
              list_reason: str | None = None) -> int:
    dsn = os.environ.get("DATABASE_URL")
    if not dsn:
        print("DATABASE_URL not set", file=sys.stderr)
        return 2
    conn = await asyncpg.connect(dsn)
    # 600s to match build_unified_topics: the count(DISTINCT signal_id) coverage
    # queries + the per-topic source window scan run heavy while the embedder is
    # draining a backlog (measured cancels at 240s on a loaded pooler, 2026-07-09).
    await conn.execute("SET statement_timeout = '600s'")
    try:
        topics = await _topics_with_members(conn)
        if not topics:
            print("no topics carry unified-v2 members — nothing to flag")
            return 0
        ids = [int(r["id"]) for r in topics]
        nsrc, pr_frac, svc_frac = await _member_source_stats(conn, ids, sample)

        junk: dict[int, str] = {}
        reason_hist: Counter = Counter()
        for r in topics:
            reason = classify_topic_junk(
                r["category"], r["label"], int(r["mem"]), nsrc.get(int(r["id"])),
                pr_wire_fraction=pr_frac.get(int(r["id"])),
                service_fraction=svc_frac.get(int(r["id"])))
            if reason:
                junk[int(r["id"])] = reason
                reason_hist[reason.split(";")[0].split(":")[0]] += 1

        cov = await _useful_coverage(conn, set(junk))
        # Count active junk to demote. This run only recomputes is_junk for
        # member-carrying topics; a junk topic already de-anchored by a prior
        # gated build has ~0 members and is skipped above, so it would linger
        # active+empty in serving. Demote EVERY active is_junk topic (persisted
        # flag), not just the member-carrying ones freshly flagged this run.
        already_junk = {int(r["id"]) for r in await conn.fetch(
            "SELECT id FROM dynamic_topics WHERE state='active' AND is_junk")}
        demote_ids = sorted(
            {int(r["id"]) for r in topics
             if int(r["id"]) in junk and r["state"] == "active"} | already_junk)

        print(f"topics with unified-v2 members: {len(topics)}")
        print(f"junk topics: {len(junk)} ({len(junk)/len(topics):.1%})  "
              f"primary reasons={dict(reason_hist)}")
        print(f"assigned signals: {cov['assigned']}  "
              f"junk-held: {cov['junk_signals']} "
              f"({cov['junk_signals']/max(cov['assigned'],1):.1%})  "
              f"useful: {cov['useful_signals']}")
        print(f"coverage vs {WINDOW_HOURS}h-embedded ({cov['denom_window_embedded']}): "
              f"total {cov['total_cov_window']:.1%} -> useful {cov['useful_cov_window']:.1%}")
        print(f"coverage vs 24h-signals ({cov['denom_24h_signals']}): "
              f"total {cov['total_cov_24h']:.1%} -> useful {cov['useful_cov_24h']:.1%}")
        print(f"would demote {len(demote_ids)} active junk topics -> candidate")

        if list_reason:
            # spot-check surface: every flagged topic whose reason carries the
            # given prefix, with state + label (used by the service-content
            # dry-run review; harmless in every mode).
            by_id = {int(r["id"]): r for r in topics}
            print(f"flagged topics matching reason '{list_reason}':")
            for i in sorted(junk):
                if list_reason in junk[i]:
                    r = by_id[i]
                    print(f"  dt-{i} [{r['state']}] ({r['category']}) "
                          f"{r['label']!r} -> {junk[i]}")

        if dry_run:
            print("(dry-run — no writes)")
            return 0

        # Persist flags: set is_junk on the junk set, clear it on the rest of the
        # scored population (reversible + keeps stale flags from lingering).
        await conn.executemany(
            "UPDATE dynamic_topics SET is_junk=true, junk_reason=$2 WHERE id=$1",
            [(i, junk[i]) for i in junk],
        )
        clear_ids = [i for i in ids if i not in junk]
        if clear_ids:
            await conn.execute(
                "UPDATE dynamic_topics SET is_junk=false, junk_reason=NULL "
                "WHERE id = ANY($1::bigint[]) AND is_junk",
                clear_ids,
            )
        if demote_ids and not no_demote:
            await conn.execute(
                "UPDATE dynamic_topics SET state='candidate', "
                "last_state_change=NOW(), updated_at=NOW() "
                "WHERE id = ANY($1::bigint[])",
                demote_ids,
            )
            print(f"demoted {len(demote_ids)} junk topics to candidate")
        print(f"flagged {len(junk)} junk topics")
        return 0
    finally:
        await conn.close()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--no-demote", action="store_true",
                    help="flag is_junk but leave active state (de-anchor only)")
    ap.add_argument("--sample", type=int, default=60,
                    help="members per topic sampled for the distinct-source count")
    ap.add_argument("--list-reason", default=None,
                    help="print flagged topics whose junk_reason contains this "
                         "substring (spot-check surface, e.g. 'service-content')")
    args = ap.parse_args()
    return asyncio.run(
        run(args.dry_run, args.no_demote, args.sample, args.list_reason))


if __name__ == "__main__":
    raise SystemExit(main())

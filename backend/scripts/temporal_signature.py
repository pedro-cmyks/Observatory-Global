#!/usr/bin/env python
"""Temporal signature — the lineage speaks for EVERY thread (Lane C, mig 085).

Classifies each ACTIVE dynamic topic's shape in time from the persisted
narrative_lineage edges (mig 084) + the topic's own hot span:

  new          the census ATTEMPTED the topic (member coverage >= floor,
               recorded in the census' topic-coverage.jsonl) and found NO
               ancestor archive unit — genuinely first coverage since the
               archive begins (May).
  continuous   one unbroken weekly chain. 1-week quiet gaps are absorbed —
               the Stage-B unit hole (archive lags the hot window ~1 week)
               must never fabricate a resurrection. The DEFAULT: surfaces
               render no badge for it.
  resurrected  exactly one >=2-week quiet gap, then returned (all classified
               topics are currently active). The dead-lineage-descendant
               edge case (a live topic stitched to a lineage that ended
               weeks ago) folds here by construction — the gap between the
               lineage's last week and the hot span IS the quiet.
  recurrent    >=3 eras — went quiet (>=2 weeks) and returned, twice or more.

Below the census member floor (coverage row `included: false`) or when the
topic has no stitch AND no coverage bookkeeping exists -> signature NULL:
absence over guess. A topic WITH a stitch classifies even if the coverage
row is missing — a measured lineage is evidence.

Umbrellas inherit the MAJORITY signature of their active children; ties fall
to 'continuous' when it is among the tied values, else NULL (no badge).
Umbrellas with no voting children fall back to their own stitch, if any.

Hot-span approximation (documented limitation): the topic is treated as
present every week from monday(first_seen) to monday(last_seen) —
dynamic_topics carries no weekly activity ledger, and an active identity is
tracked continuously by the snapshot pipeline. A topic that resurrected
KEEPING its identity_key therefore reads continuous over its own hot span;
its archive-side gaps still classify.

Writes dynamic_topics.temporal_signature + signature_meta for every active
topic each run (NULL when unclassifiable) — a stale signature never
outlives its lineage. Read-only otherwise; bounded SELECTs.

Run (M1, after census + load in the nightly runner):
  python -m backend.scripts.temporal_signature --write
"""
from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
from collections import Counter, defaultdict
from datetime import date, timedelta
from pathlib import Path
from typing import Iterable

COVERAGE_DEFAULT = Path(
    "/Volumes/Ext/Atlas/Embeddings/lineage-index/topic-coverage.jsonl")

SIGNATURES = ("new", "continuous", "recurrent", "resurrected")
MIN_QUIET_WEEKS = 2   # a real era break; 1-week holes are absorbed


# ── pure logic ──────────────────────────────────────────────────────────────

def monday(d: date) -> date:
    return d - timedelta(days=d.weekday())


def hot_weeks(first_seen: date | None, last_seen: date | None) -> set[date]:
    """Weekly Mondays the topic's hot identity spans (see module docstring)."""
    if last_seen is None:
        return set()
    if first_seen is None:
        return {monday(last_seen)}
    out, w, end = set(), monday(first_seen), monday(last_seen)
    while w <= end:
        out.add(w)
        w += timedelta(weeks=1)
    return out


def split_eras(weeks: Iterable[date],
               min_quiet_weeks: int = MIN_QUIET_WEEKS) -> list[list[date]]:
    """Sorted unique weeks -> eras, split where >= min_quiet_weeks are quiet.

    Quiet weeks between adjacent present Mondays a < b = (b-a)/7 - 1.
    """
    ws = sorted(set(weeks))
    if not ws:
        return []
    eras: list[list[date]] = [[ws[0]]]
    for prev, cur in zip(ws, ws[1:]):
        quiet = (cur - prev).days // 7 - 1
        if quiet >= min_quiet_weeks:
            eras.append([cur])
        else:
            eras[-1].append(cur)
    return eras


def classify_topic(archive_weeks: list[date], hot_first: date | None,
                   hot_last: date | None, *,
                   coverage_included: bool | None) -> tuple[str | None, dict]:
    """(signature | None, signature_meta) for one non-umbrella topic."""
    if not archive_weeks:
        if coverage_included is not True:
            return None, {}      # below floor / never attempted — no guess
        hw = sorted(hot_weeks(hot_first, hot_last))
        return "new", {
            "eras": 1, "gap_weeks": 0,
            "first_seen_week": hw[0].isoformat() if hw else None,
        }

    weeks = set(archive_weeks) | hot_weeks(hot_first, hot_last)
    eras = split_eras(weeks)
    meta: dict = {
        "eras": len(eras),
        "first_seen_week": min(weeks).isoformat(),
        "weeks_present": len(weeks),
    }
    if len(eras) == 1:
        meta["gap_weeks"] = 0
        return "continuous", meta
    # latest gap = quiet weeks between the last two eras; the current era's
    # start is the "returned" week the chip copy speaks
    prev_end, cur_start = eras[-2][-1], eras[-1][0]
    meta["gap_weeks"] = (cur_start - prev_end).days // 7 - 1
    meta["returned_week"] = cur_start.isoformat()
    return ("resurrected" if len(eras) == 2 else "recurrent"), meta


def umbrella_signature(children: list[str | None]) -> tuple[str | None, dict]:
    """Majority-of-children; unclassified children don't vote; ties fall to
    'continuous' when tied, else None (absence over guess)."""
    votes = Counter(s for s in children if s)
    if not votes:
        return None, {}
    top = max(votes.values())
    tied = sorted(s for s, n in votes.items() if n == top)
    if len(tied) == 1:
        sig = tied[0]
    elif "continuous" in tied:
        sig = "continuous"
    else:
        sig = None
    meta = {"inherited": True, "children": dict(votes)}
    return sig, meta


# ── loader ──────────────────────────────────────────────────────────────────

class _UF:
    def __init__(self) -> None:
        self.p: dict[int, int] = {}

    def find(self, x: int) -> int:
        self.p.setdefault(x, x)
        while self.p[x] != x:
            self.p[x] = self.p[self.p[x]]
            x = self.p[x]
        return x

    def union(self, a: int, b: int) -> None:
        ra, rb = self.find(a), self.find(b)
        if ra != rb:
            self.p[rb] = ra


def load_coverage(path: Path) -> dict[int, bool]:
    """topic_id -> included (census member floor). Missing file -> {}."""
    if not path.exists():
        return {}
    out: dict[int, bool] = {}
    for line in path.read_text().splitlines():
        try:
            r = json.loads(line)
            out[int(r["topic_id"])] = bool(r.get("included"))
        except (ValueError, KeyError, TypeError):
            continue
    return out


async def compute_signatures(conn, coverage: dict[int, bool]) -> dict[int, tuple[str | None, dict]]:
    topics = await conn.fetch(
        """SELECT id, first_seen, last_seen, is_umbrella, parent_id
           FROM dynamic_topics WHERE state = 'active' AND NOT is_junk""")
    tu = await conn.fetch(
        """SELECT topic_id, unit_id, week FROM narrative_lineage
           WHERE kind = 'topic_unit'""")
    uu = await conn.fetch(
        """SELECT src_unit_id, unit_id, src_week, week FROM narrative_lineage
           WHERE kind = 'unit_unit'""")

    # global components over archive units + week per unit (edges carry the
    # weeks, so archive_story_units is never touched)
    uf = _UF()
    unit_week: dict[int, date] = {}
    for r in uu:
        s, d = int(r["src_unit_id"]), int(r["unit_id"])
        uf.union(s, d)
        if r["src_week"]:
            unit_week.setdefault(s, r["src_week"])
        if r["week"]:
            unit_week.setdefault(d, r["week"])
    stitched_units: dict[int, set[int]] = defaultdict(set)
    for r in tu:
        u = int(r["unit_id"])
        stitched_units[int(r["topic_id"])].add(u)
        if r["week"]:
            unit_week.setdefault(u, r["week"])

    comp_weeks: dict[int, set[date]] = defaultdict(set)
    for u, wk in unit_week.items():
        comp_weeks[uf.find(u)].add(monday(wk))

    def archive_weeks_of(tid: int) -> list[date]:
        weeks: set[date] = set()
        for u in stitched_units.get(tid, ()):
            weeks |= comp_weeks.get(uf.find(u), set())
        return sorted(weeks)

    out: dict[int, tuple[str | None, dict]] = {}
    children_of: dict[int, list[int]] = defaultdict(list)
    for t in topics:
        tid = int(t["id"])
        if t["parent_id"] is not None:
            children_of[int(t["parent_id"])].append(tid)
        if t["is_umbrella"]:
            continue
        out[tid] = classify_topic(
            archive_weeks_of(tid),
            t["first_seen"] and t["first_seen"].date(),
            t["last_seen"] and t["last_seen"].date(),
            coverage_included=coverage.get(tid),
        )

    for t in topics:
        if not t["is_umbrella"]:
            continue
        tid = int(t["id"])
        sig, meta = umbrella_signature(
            [out.get(c, (None, {}))[0] for c in children_of.get(tid, [])])
        if sig is None and not meta:
            # no voting children — fall back to the umbrella's own stitch
            sig, meta = classify_topic(
                archive_weeks_of(tid),
                t["first_seen"] and t["first_seen"].date(),
                t["last_seen"] and t["last_seen"].date(),
                coverage_included=coverage.get(tid),
            )
        out[tid] = (sig, meta)
    return out


async def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--coverage", type=Path, default=COVERAGE_DEFAULT,
                    help="census topic-coverage.jsonl (member floor source)")
    ap.add_argument("--write", action="store_true")
    args = ap.parse_args()

    coverage = load_coverage(args.coverage)
    if not coverage:
        print(f"WARN no coverage file at {args.coverage} — unstitched topics "
              "will stay NULL (never guessed 'new')", file=sys.stderr)

    import asyncpg
    conn = await asyncpg.connect(os.environ["DATABASE_URL"],
                                 statement_cache_size=0)
    try:
        sigs = await compute_signatures(conn, coverage)
        dist = Counter(s for s, _ in sigs.values())
        dist_out = {(k or "unclassified"): v for k, v in dist.items()}
        print(json.dumps({"active_topics": len(sigs),
                          "distribution": dist_out}, indent=1))
        if not args.write:
            print("dry-run (no writes)")
            return 0
        rows = [(tid, sig, json.dumps(meta) if meta else None)
                for tid, (sig, meta) in sigs.items()]
        for i in range(0, len(rows), 500):
            await conn.executemany(
                """UPDATE dynamic_topics
                   SET temporal_signature = $2, signature_meta = $3::jsonb
                   WHERE id = $1""", rows[i:i + 500])
        print(f"wrote {len(rows)} topics")
    finally:
        await conn.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))

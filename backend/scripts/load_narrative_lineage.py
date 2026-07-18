#!/usr/bin/env python
"""Load the narrative-lineage census edges into narrative_lineage (mig 084).

Input: lineage-edges.json emitted by narrative_lineage_census.py census phase
({method, topic_unit_edges, unit_unit_edges, lineages}). Idempotent upsert on
the per-kind identity (topic_id,unit_id) / (src_unit_id,unit_id); re-runs
update sim/method/candidate in place. `--prune-stale` additionally deletes
edges the current census no longer emits (the census always writes the FULL
set, so nightly refreshes should pass it).

Honesty: the census only emits edges at/above its MEASURED thresholds, but
near-threshold stitches (within --near of theta) are stored candidate=true,
and if a threshold came from the non-bimodal fallback ("treat with caution")
ALL edges of that kind are candidates — the serving layer shows candidates as
candidates, never asserts them.

Run from the M1 (or anywhere with DATABASE_URL):
  python backend/scripts/load_narrative_lineage.py [--edges PATH] [--write]
"""
from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
from datetime import date
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_EDGES = (REPO_ROOT / "docs" / "research" / "narrative-lineage"
                 / "lineage-edges.json")
NEAR_DEFAULT = 0.02

UPSERT_TOPIC_UNIT = """
    INSERT INTO narrative_lineage
        (kind, topic_id, unit_id, sim, week, method, candidate)
    VALUES ('topic_unit', $1, $2, $3, $4::date, $5, $6)
    ON CONFLICT (topic_id, unit_id) WHERE kind = 'topic_unit'
    DO UPDATE SET sim = EXCLUDED.sim, week = EXCLUDED.week,
                  method = EXCLUDED.method, candidate = EXCLUDED.candidate
"""

UPSERT_UNIT_UNIT = """
    INSERT INTO narrative_lineage
        (kind, src_unit_id, unit_id, sim, src_week, week, edge_kind,
         method, candidate)
    VALUES ('unit_unit', $1, $2, $3, $4::date, $5::date, $6, $7, $8)
    ON CONFLICT (src_unit_id, unit_id) WHERE kind = 'unit_unit'
    DO UPDATE SET sim = EXCLUDED.sim, src_week = EXCLUDED.src_week,
                  week = EXCLUDED.week, edge_kind = EXCLUDED.edge_kind,
                  method = EXCLUDED.method, candidate = EXCLUDED.candidate
"""


def build_method_string(method: dict) -> str:
    """Compact provenance the endpoint can parse: build id + measured taus.

    When the census measured per-country noise floors (leak-5 fix: same-
    language edges must clear max(theta, country p95 control + margin)),
    that is provenance the serving meta must carry too — appended compactly
    so parse_method_thetas' tu=/uu= regexes are untouched.
    """
    base = (f"census-v0 gen={method.get('generated_at', '?')} "
            f"tu={method.get('theta_topic_unit')} "
            f"uu={method.get('theta_unit_unit')}")
    pcf = method.get("per_country_floor")
    if pcf:
        base += (f" floors={pcf.get('n_countries', 0)}cc"
                 f"(p{pcf.get('percentile', 95):g}+{pcf.get('margin')})")
    return base


def is_candidate(sim: float, theta: float | None, bimodal: bool,
                 near: float = NEAR_DEFAULT) -> bool:
    """Low-confidence stitch policy (documented in the module docstring)."""
    if not bimodal:
        return True
    if theta is None:
        return True
    return sim < theta + near


def _d(v) -> date | None:
    """ISO week string -> date (asyncpg binds date-typed params as objects)."""
    return date.fromisoformat(v) if v else None


def parse_edges(doc: dict, near: float = NEAR_DEFAULT) -> dict:
    """lineage-edges.json -> keyed upsert rows (pure; testable).

    Returns {"method": str, "topic_unit": {(topic_id, unit_id): row},
             "unit_unit": {(src_unit_id, unit_id): row}} — dict keys ARE the
    upsert identity, so parsing the same document twice yields the same keyed
    set (idempotence by construction; last-wins matches upsert semantics).
    """
    method = doc.get("method") or {}
    method_str = build_method_string(method)
    meas = method.get("theta_measurement") or {}
    tu_theta = method.get("theta_topic_unit")
    uu_theta = method.get("theta_unit_unit")
    tu_bimodal = bool((meas.get("topic_unit") or {}).get("bimodal"))
    uu_bimodal = bool((meas.get("unit_unit") or {}).get("bimodal"))

    topic_unit: dict[tuple[int, int], tuple] = {}
    for e in doc.get("topic_unit_edges") or []:
        key = (int(e["topic_id"]), int(e["unit_id"]))
        topic_unit[key] = (
            key[0], key[1], float(e["sim"]), _d(e.get("week")), method_str,
            is_candidate(float(e["sim"]), tu_theta, tu_bimodal, near))

    unit_unit: dict[tuple[int, int], tuple] = {}
    for e in doc.get("unit_unit_edges") or []:
        key = (int(e["src_unit_id"]), int(e["dst_unit_id"]))
        unit_unit[key] = (
            key[0], key[1], float(e["sim"]), _d(e.get("src_week")),
            _d(e.get("dst_week")), e.get("kind"), method_str,
            is_candidate(float(e["sim"]), uu_theta, uu_bimodal, near))

    return {"method": method_str, "topic_unit": topic_unit,
            "unit_unit": unit_unit}


async def load(conn, parsed: dict, prune_stale: bool = False) -> dict:
    """Upsert the parsed edge set; optionally prune edges not in it."""
    tu_rows = list(parsed["topic_unit"].values())
    uu_rows = list(parsed["unit_unit"].values())
    for i in range(0, len(tu_rows), 500):
        await conn.executemany(UPSERT_TOPIC_UNIT, tu_rows[i:i + 500])
    for i in range(0, len(uu_rows), 500):
        await conn.executemany(UPSERT_UNIT_UNIT, uu_rows[i:i + 500])
    pruned = 0
    if prune_stale:
        # the census emits the FULL current edge set — anything else is stale
        r1 = await conn.execute(
            """DELETE FROM narrative_lineage nl
               WHERE nl.kind = 'topic_unit'
                 AND NOT EXISTS (
                   SELECT 1 FROM unnest($1::bigint[], $2::bigint[]) AS k(t, u)
                   WHERE k.t = nl.topic_id AND k.u = nl.unit_id)""",
            [a for a, _ in parsed["topic_unit"]],
            [b for _, b in parsed["topic_unit"]])
        r2 = await conn.execute(
            """DELETE FROM narrative_lineage nl
               WHERE nl.kind = 'unit_unit'
                 AND NOT EXISTS (
                   SELECT 1 FROM unnest($1::bigint[], $2::bigint[]) AS k(s, u)
                   WHERE k.s = nl.src_unit_id AND k.u = nl.unit_id)""",
            [a for a, _ in parsed["unit_unit"]],
            [b for _, b in parsed["unit_unit"]])
        pruned = sum(int(str(r).rsplit(" ", 1)[-1] or 0) for r in (r1, r2))
    return {"topic_unit": len(tu_rows), "unit_unit": len(uu_rows),
            "pruned": pruned}


async def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--edges", type=Path, default=DEFAULT_EDGES)
    ap.add_argument("--near", type=float, default=NEAR_DEFAULT,
                    help="candidate band above theta (sim < theta+near)")
    ap.add_argument("--prune-stale", action="store_true",
                    help="delete edges absent from this census emission")
    ap.add_argument("--write", action="store_true")
    args = ap.parse_args()

    if not args.edges.exists():
        print(f"edges file missing: {args.edges} — nothing to load "
              "(census not run yet?)", file=sys.stderr)
        return 2
    parsed = parse_edges(json.loads(args.edges.read_text()), args.near)
    n_cand = sum(1 for r in parsed["topic_unit"].values() if r[5]) + \
        sum(1 for r in parsed["unit_unit"].values() if r[7])
    print(f"parsed {len(parsed['topic_unit'])} topic_unit + "
          f"{len(parsed['unit_unit'])} unit_unit edges "
          f"({n_cand} candidates) [{parsed['method']}]", file=sys.stderr)
    if not args.write:
        print("dry-run (no writes)")
        return 0

    import asyncpg
    conn = await asyncpg.connect(os.environ["DATABASE_URL"],
                                 statement_cache_size=0)
    try:
        stats = await load(conn, parsed, prune_stale=args.prune_stale)
        n = await conn.fetchval("SELECT count(*) FROM narrative_lineage")
        print(f"upserted {stats}; table now holds {n} edges")
    finally:
        await conn.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))

"""Lever A0 — simulate court-verdict enforcement modes over the SERVED field.

Read-only. Reproduces `/threads` faithfully: the same SQL population
(`_fetch_dynamic_threads_with_conn`), the same scorer (`rank_threads`), the
same same-event collapse (`dedupe_same_event_threads`). Nothing is
reimplemented — the only thing this harness varies is the court multiplier
table and (for mode-2) which rows may occupy the fold.

BASELINE IS NOT "NO ENFORCEMENT". `thread_ranking` already ships a court damp
(rank v2, `ac4a4881`): failed x0.50, partial x0.85, entailed/NULL x1.00, behind
`ATLAS_RANK_V2` which defaults ON and is unset in fly.toml and in Fly secrets.
So mode-0 = today = a live 0.5 damp. `mode-0-nocourt` is included as the
counterfactual that isolates what the shipped damp already buys.

Modes
-----
  mode-0-nocourt   reference: court multiplier disabled entirely (1.0/1.0)
  mode-0           baseline == today's serving (failed 0.50, partial 0.85)
  mode-1-f{F}      rank damp, failed x F  (F in 0.7 / 0.5 / 0.3); partial stays
                   at the shipped 0.85; `unchecked` NEVER damped (atlas rows,
                   umbrellas and any unjudged topic keep multiplier 1.0 — the
                   court never punishes the unjudged).
  mode-2-nofetch   exclude `failed` from the fold with NO over-fetch: the page
                   simply loses those rows (what A1-as-specified would do).
  mode-2-backfill  exclude `failed` and backfill from a deeper pool (requires a
                   serving over-fetch; measures the ceiling of exclusion).

Fetch depth
-----------
`/threads?limit=L` fetches exactly L candidates (`ORDER BY recent_n_signals
DESC LIMIT $2`) and ranks within them, so a pure RANK damp cannot change WHICH
rows are served at L — only their order. Two variants are therefore measured:

  variant S (shallow)  pool depth == page size  == today's serving contract.
  variant D (deep)     pool depth == 3x page    == serving would have to
                       over-fetch; shows what enforcement could reach.

Usage
-----
    set -a; source ~/AtlasLocalWorker/.env; set +a
    backend/.venv/bin/python backend/scripts/measure_court_enforcement.py \
        --out docs/research/label-court/2026-07-29-court-enforcement-simulation.json
"""
from __future__ import annotations

import argparse
import asyncio
import copy
import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import asyncpg  # noqa: E402

from app.services import thread_ranking  # noqa: E402
from app.services.thread_intelligence import (  # noqa: E402
    _DYNAMIC_TOPICS_SQL,
    _fetch_dynamic_threads_with_conn,
    dedupe_same_event_threads,
    stamped_counts,
)
from app.services.thread_ranking import rank_threads  # noqa: E402

STATUSES = ("entailed", "partial", "failed", "unchecked")

# (door name, country_code | None, page size). Global page = 40 to match the
# audit's top-40 frame; country doors = 24 = country_edition._MAX_THREADS.
DEFAULT_DOORS: list[tuple[str, str | None, int]] = [
    ("GLOBAL", None, 40),
    ("US", "US", 24),
    ("TR", "TR", 24),
    ("CO", "CO", 24),
    ("VE", "VE", 24),   # thin door (7 candidate topics at probe time)
    ("NG", "NG", 24),   # thin door (4 candidate topics at probe time)
]

POOL_MULT = 3
VISIBLE_FOLD = 10  # what a reader actually sees before scrolling

SHIPPED_PARTIAL = thread_ranking._COURT_DAMP["partial"]

MODES: list[dict[str, Any]] = [
    {"name": "mode-0-nocourt", "kind": "rank", "damp": {}},
    {"name": "mode-0", "kind": "rank",
     "damp": {"failed": 0.5, "partial": SHIPPED_PARTIAL}},
    {"name": "mode-1-f0.7", "kind": "rank",
     "damp": {"failed": 0.7, "partial": SHIPPED_PARTIAL}},
    {"name": "mode-1-f0.5", "kind": "rank",
     "damp": {"failed": 0.5, "partial": SHIPPED_PARTIAL}},
    {"name": "mode-1-f0.3", "kind": "rank",
     "damp": {"failed": 0.3, "partial": SHIPPED_PARTIAL}},
    {"name": "mode-2-nofetch", "kind": "exclude-nofetch",
     "damp": {"failed": 0.5, "partial": SHIPPED_PARTIAL}},
    {"name": "mode-2-backfill", "kind": "exclude-backfill",
     "damp": {"failed": 0.5, "partial": SHIPPED_PARTIAL}},
]

BASELINE = "mode-0"


def status_of(thread: dict) -> str:
    s = str(thread.get("label_status") or "").strip().lower()
    return s if s in STATUSES else "unchecked"


def compose(threads: list[dict]) -> dict[str, Any]:
    counts = stamped_counts(threads)          # the served census, verbatim
    n = len(threads) or 1
    return {
        "rows": len(threads),
        "counts": counts,
        "share": {k: round(v / n, 4) for k, v in counts.items()},
    }


def _rank_with_damp(pool: list[dict], damp: dict[str, float]) -> list[dict]:
    """Score+order with a patched court table, then collapse same-event dups.

    Deep-copies the pool: `rank_threads` writes headline_diversity into
    quality{} and `dedupe_same_event_threads` MERGES surviving rows in place,
    so a shared pool would leak state across modes.
    """
    work = copy.deepcopy(pool)
    original = thread_ranking._COURT_DAMP
    thread_ranking._COURT_DAMP = dict(damp)
    try:
        ranked = rank_threads(work)
    finally:
        thread_ranking._COURT_DAMP = original
    return dedupe_same_event_threads(ranked)


def serve(mode: dict, pool_shallow: list[dict], pool_deep: list[dict],
          page: int, variant: str) -> list[dict]:
    pool = pool_shallow if variant == "S" else pool_deep
    kind = mode["kind"]
    if kind == "rank":
        return _rank_with_damp(pool, mode["damp"])[:page]
    if kind == "exclude-nofetch":
        # the fold is today's page minus its failed rows — no replacement
        served = _rank_with_damp(pool, mode["damp"])[:page]
        return [t for t in served if status_of(t) != "failed"]
    if kind == "exclude-backfill":
        # failed rows never enter: drop BEFORE the same-event collapse so a
        # clean duplicate can still represent the event, then take the page.
        kept = [t for t in pool if status_of(t) != "failed"]
        return _rank_with_damp(kept, mode["damp"])[:page]
    raise ValueError(kind)


def key(thread: dict) -> str:
    return str(thread.get("thread_id") or thread.get("label") or "?")


def diff(base: list[dict], other: list[dict]) -> dict[str, Any]:
    base_pos = {key(t): i for i, t in enumerate(base)}
    other_pos = {key(t): i for i, t in enumerate(other)}
    entered = [
        {"rank": other_pos[key(t)] + 1, "label": t.get("label"),
         "status": status_of(t), "signals": t.get("signal_count"),
         "thread_id": key(t)}
        for t in other if key(t) not in base_pos
    ]
    exited = [
        {"rank": base_pos[key(t)] + 1, "label": t.get("label"),
         "status": status_of(t), "signals": t.get("signal_count"),
         "thread_id": key(t)}
        for t in base if key(t) not in other_pos
    ]
    return {"entered": entered, "exited": exited,
            "n_entered": len(entered), "n_exited": len(exited)}


def head(threads: list[dict], n: int = VISIBLE_FOLD) -> list[dict[str, Any]]:
    return [
        {"rank": i + 1, "label": t.get("label"), "status": status_of(t),
         "signals": t.get("signal_count"), "thread_id": key(t)}
        for i, t in enumerate(threads[:n])
    ]


def size_by_status(threads: list[dict]) -> dict[str, Any]:
    """Current-window signal_count per verdict. The confound check: if
    `entailed` skews small, enforcing the verdict is partly a proxy for
    'prefer small topics' — which the gate's entailed-share cannot see."""
    buckets: dict[str, list[int]] = {}
    for t in threads:
        buckets.setdefault(status_of(t), []).append(int(t.get("signal_count") or 0))
    out = {}
    for st, vals in buckets.items():
        vals.sort()
        out[st] = {
            "n": len(vals),
            "mean": round(sum(vals) / len(vals), 1),
            "median": vals[len(vals) // 2],
            "max": vals[-1],
        }
    return out


async def fetch_pool(conn: Any, cc: str | None, limit: int) -> list[dict]:
    return await _fetch_dynamic_threads_with_conn(
        conn, hours=24, limit=limit, country_code=cc,
    )


# Mirrors the serving _DYNAMIC_TOPICS_COUNTRY_SQL EXISTS (post dark-door fix,
# 2026-07-29): latest-snapshot codes, any position — the honest candidate
# definition. The pre-fix all-snapshot `top_country_codes[1]` variant counted
# topics whose country membership was historical, which is exactly the
# phantom-candidate defect §9 measured.
_DOOR_CANDIDATES_SQL = """
SELECT COUNT(DISTINCT dt.id)::int
FROM dynamic_topics dt
JOIN dynamic_topic_members dtmc ON dtmc.dynamic_topic_id = dt.id
JOIN emergent_clusters ecc ON ecc.id = dtmc.emergent_cluster_id
WHERE dt.state='active' AND dt.is_umbrella = false
  AND dt.last_seen > NOW() - INTERVAL '72 hours'
  AND dtmc.snapshot_at = (
      SELECT MAX(snapshot_at) FROM dynamic_topic_members
      WHERE dynamic_topic_id = dt.id
  )
  AND $1 = ANY(ecc.top_country_codes)
"""


async def scan_doors(conn: Any, ccs: list[str]) -> list[dict[str, Any]]:
    """Candidate topics the country SQL believes exist vs rows actually served.

    Gate GA condition (a) is a percentage of *served* rows, so a door already
    at 0 can never violate it. This scan makes that vacuity visible.
    """
    out = []
    for cc in ccs:
        cand = await conn.fetchval(_DOOR_CANDIDATES_SQL, cc)
        served = await fetch_pool(conn, cc, 24)
        out.append({
            "cc": cc,
            "sql_candidates_72h": int(cand or 0),
            "served_rows": len(served),
            "failed_rows": sum(1 for t in served if status_of(t) == "failed"),
        })
        print(f"  scan {cc}: cand={cand} served={len(served)}", file=sys.stderr)
    return out


SCAN_CCS = [
    "RU", "UA", "IR", "GB", "US", "ES", "IN", "GR", "FR", "DE", "ID", "TR",
    "IT", "BR", "CA", "CN", "PL", "AR", "IL", "BE", "IE", "MX", "AU", "JP",
    "EG", "PK", "CO", "SA", "VE", "SE", "CL", "ZA", "NZ", "NG",
]


async def run(doors: list[tuple[str, str | None, int]],
              do_scan: bool = True) -> dict[str, Any]:
    dsn = os.environ["DATABASE_URL"]
    conn = await asyncpg.connect(dsn)
    # The Supabase pooler drops startup `server_settings`, so set it on the
    # live session and verify — a read-only claim that isn't checked is a
    # claim, not a guarantee.
    await conn.execute("SET default_transaction_read_only = on")
    result: dict[str, Any] = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "rank_v2_enabled": thread_ranking.rank_v2_enabled(),
        "shipped_court_damp": dict(thread_ranking._COURT_DAMP),
        "visible_fold": VISIBLE_FOLD,
        "pool_mult": POOL_MULT,
        "doors": {},
    }
    try:
        assert await conn.fetchval("SHOW default_transaction_read_only") == "on"
        for name, cc, page in doors:
            print(f"[door] {name} page={page} ...", file=sys.stderr)
            pool_shallow = await fetch_pool(conn, cc, page)
            pool_deep = await fetch_pool(conn, cc, page * POOL_MULT)
            door: dict[str, Any] = {
                "country_code": cc,
                "page": page,
                "pool_shallow": len(pool_shallow),
                "pool_deep": len(pool_deep),
                "pool_composition_shallow": compose(pool_shallow),
                "pool_composition_deep": compose(pool_deep),
                "variants": {},
            }
            for variant in ("S", "D"):
                served_by_mode: dict[str, list[dict]] = {}
                for mode in MODES:
                    served_by_mode[mode["name"]] = serve(
                        mode, pool_shallow, pool_deep, page, variant,
                    )
                base = served_by_mode[BASELINE]
                vout: dict[str, Any] = {}
                for mode in MODES:
                    served = served_by_mode[mode["name"]]
                    vout[mode["name"]] = {
                        "page": compose(served),
                        "visible_fold": compose(served[:VISIBLE_FOLD]),
                        "rows_delta_vs_baseline": len(served) - len(base),
                        "rows_pct_of_baseline": (
                            round(len(served) / len(base), 4) if base else None
                        ),
                        "diff_vs_baseline": diff(base, served),
                        "head": head(served),
                    }
                door["variants"][variant] = vout

            # POST-HOC mode-3 (NOT pre-registered in gate GA — reported as a
            # finding, never scored as an adopted mode). Same shipped damp,
            # deeper fetch: the court verdict finally SELECTS instead of only
            # reordering an already volume-selected page.
            base_s = serve(MODES[1], pool_shallow, pool_deep, page, "S")
            over_d = serve(MODES[1], pool_shallow, pool_deep, page, "D")
            door["mode-3-overfetch"] = {
                "note": "post-hoc; baseline = variant S mode-0 (today's serving)",
                "baseline": compose(base_s),
                "page": compose(over_d),
                "rows_delta_vs_baseline": len(over_d) - len(base_s),
                "rows_pct_of_baseline": (
                    round(len(over_d) / len(base_s), 4) if base_s else None
                ),
                "entailed_share_delta_pp": round(
                    (compose(over_d)["share"]["entailed"]
                     - compose(base_s)["share"]["entailed"]) * 100, 1
                ),
                "diff_vs_baseline": diff(base_s, over_d),
                "head_baseline": head(base_s, 20),
                "head_overfetch": head(over_d, 20),
            }
            door["size_by_status_deep_pool"] = size_by_status(pool_deep)
            result["doors"][name] = door
        if do_scan:
            print("[scan] country doors ...", file=sys.stderr)
            result["door_scan"] = await scan_doors(conn, SCAN_CCS)
    finally:
        await conn.close()
    return result


# ==========================================================================
# A0b — the fetch-side enforcement gate (pre-registration
# `docs/superpowers/specs/2026-07-29-a0b-fetch-gate-preregistration.md`).
#
# The intervention: `/threads` fetches M x limit candidates, applies the
# SHIPPED ranking (incl. the live court damp — no new rank code), serves the
# top `limit`. This is exactly `fetch_threads`'s dynamic path with the fetch
# widened and the cut unchanged:
#
#     dedupe_same_event_threads(rank_threads(dynamic))[:limit]
#
# so the harness calls the SAME functions in the SAME order and varies only
# the depth handed to `_fetch_dynamic_threads_with_conn`.
#
# Conditions (frozen before this code was written):
#   C1 global top-40 entailed-share delta >= +15pp
#   C2 no door in the C2 set loses more than 5pp of entailed-share
#   C3 global top-10 median signal_count >= 50% of baseline's
#   C4 no door loses >25% of its served rows; global top-40 >= 30 rows
#   C5 M x LIMIT fetch stays inside the endpoint's existing budget
# ==========================================================================

A0B_MULTS = (2, 3, 4)

# Scored C2 set (operational reading, recorded before scoring): the gate says
# "the 5 most populated doors (incl. US, TR, DE)". By candidate depth the five
# most populated are RU/UA/IR/GB/IN, which would exclude all three mandated
# doors, so the scored set is the three mandated + the two deepest remaining
# (RU 142, UA 110 candidates). Every other alive door is measured too and
# reported as an unscored shadow-C2 — a door outside the scored five that gets
# worse is reported beside the verdict, never hidden by the frame.
A0B_C2_SCORED = ("US", "TR", "DE", "RU", "UA")

# Gate-required doors first (the artifact is dumped after each door, so a
# truncated run still carries everything C1-C4 are scored on).
A0B_DOORS: list[tuple[str, str | None, int]] = [
    ("GLOBAL", None, 40),
    ("US", "US", 24), ("TR", "TR", 24), ("DE", "DE", 24),
    ("RU", "RU", 24), ("UA", "UA", 24),
    # thin-but-alive (1 served row each at baseline — the only alive thin doors)
    ("AR", "AR", 24), ("IL", "IL", 24),
    # shadow-C2 (measured, unscored): the rest of the alive doors
    ("IR", "IR", 24), ("GB", "GB", 24), ("IN", "IN", 24), ("ES", "ES", 24),
    ("GR", "GR", 24), ("FR", "FR", 24), ("ID", "ID", 24), ("IT", "IT", 24),
    ("BR", "BR", 24), ("CA", "CA", 24), ("CN", "CN", 24),
]


def median_signals(threads: list[dict], n: int) -> float:
    vals = sorted(int(t.get("signal_count") or 0) for t in threads[:n])
    if not vals:
        return 0.0
    mid = len(vals) // 2
    return float(vals[mid]) if len(vals) % 2 else (vals[mid - 1] + vals[mid]) / 2


def a0b_serve(pool: list[dict], page: int) -> list[dict]:
    """Serving, verbatim: shipped damp, shipped scorer, shipped collapse, cut
    to the page. The ONLY variable across arms is how deep `pool` was fetched."""
    return _rank_with_damp(pool, dict(thread_ranking._COURT_DAMP))[:page]


async def a0b_cost(conn: Any, page: int, mults: tuple[int, ...],
                   reps: int) -> dict[str, Any]:
    """C5 — timed real fetches at each depth, interleaved so cache warmth is
    shared across arms (a cold baseline vs warm over-fetch would flatter the
    over-fetch). Also EXPLAIN(ANALYZE) the bare topic SQL so the SQL cost and
    the per-row sample-signal round trips can be told apart."""
    depths = [page] + [page * m for m in mults]
    timings: dict[int, list[float]] = {d: [] for d in depths}
    for _ in range(reps):
        for d in depths:
            t0 = time.perf_counter()
            await fetch_pool(conn, None, d)
            timings[d].append(time.perf_counter() - t0)
    def pct(vals: list[float], p: float) -> float:
        s = sorted(vals)
        return round(s[min(len(s) - 1, int(p * len(s)))], 3)
    out: dict[str, Any] = {"reps": reps, "note": (
        "wall-clock of _fetch_dynamic_threads_with_conn (topic SQL + one "
        "sample-signal query per served row), run from this machine against "
        "prod; interleaved arms share cache warmth"
    ), "by_depth": {}}
    for d in depths:
        v = timings[d]
        out["by_depth"][str(d)] = {
            "p50_s": pct(v, 0.5), "p95_s": pct(v, 0.95),
            "min_s": round(min(v), 3), "max_s": round(max(v), 3),
            "samples": [round(x, 3) for x in v],
        }
    # SQL-only cost, separated from the per-row sample fetches
    sql_only: dict[str, Any] = {}
    for d in depths:
        rows = await conn.fetch(
            "EXPLAIN (ANALYZE, BUFFERS, FORMAT JSON) " + _DYNAMIC_TOPICS_SQL,
            24, d, timeout=120,
        )
        plan = json.loads(rows[0][0])[0]
        sql_only[str(d)] = {
            "execution_ms": round(plan.get("Execution Time", 0.0), 1),
            "planning_ms": round(plan.get("Planning Time", 0.0), 1),
            "rows_out": plan["Plan"].get("Actual Rows"),
        }
    out["topic_sql_explain_analyze"] = sql_only
    return out


async def run_a0b(doors: list[tuple[str, str | None, int]],
                  mults: tuple[int, ...], cost_reps: int,
                  out: Path | None = None) -> dict[str, Any]:
    dsn = os.environ["DATABASE_URL"]
    conn = await asyncpg.connect(dsn)
    await conn.execute("SET default_transaction_read_only = on")
    result: dict[str, Any] = {
        "gate": "A0b",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "rank_v2_enabled": thread_ranking.rank_v2_enabled(),
        "shipped_court_damp": dict(thread_ranking._COURT_DAMP),
        "mults": list(mults),
        "c2_scored_doors": list(A0B_C2_SCORED),
        "visible_fold": VISIBLE_FOLD,
        "doors": {},
    }
    try:
        assert await conn.fetchval("SHOW default_transaction_read_only") == "on"
        result["field"] = {
            "topics_by_status": {
                f"{'umbrella' if r['is_umbrella'] else 'child'}:{r['st']}": r["n"]
                for r in await conn.fetch(
                    "SELECT is_umbrella, COALESCE(label_status,'unchecked') st,"
                    " COUNT(*)::int n FROM dynamic_topics WHERE state='active'"
                    " GROUP BY 1,2"
                )
            },
            "members_max_snapshot": str(await conn.fetchval(
                "SELECT MAX(snapshot_at) FROM dynamic_topic_members")),
            "clusters_max_snapshot": str(await conn.fetchval(
                "SELECT MAX(snapshot_at) FROM emergent_clusters")),
        }
        for name, cc, page in doors:
            print(f"[a0b] {name} page={page} ...", file=sys.stderr)
            pools = {1: await fetch_pool(conn, cc, page)}
            for m in mults:
                pools[m] = await fetch_pool(conn, cc, page * m)
            base = a0b_serve(pools[1], page)
            base_comp = compose(base)
            door: dict[str, Any] = {
                "country_code": cc,
                "page": page,
                "baseline": {
                    "pool_fetched": len(pools[1]),
                    **base_comp,
                    "median_signals_top10": median_signals(base, VISIBLE_FOLD),
                    "head": head(base, 20),
                },
                "arms": {},
            }
            for m in mults:
                served = a0b_serve(pools[m], page)
                comp = compose(served)
                door["arms"][f"M{m}"] = {
                    "pool_fetched": len(pools[m]),
                    **comp,
                    "entailed_share_delta_pp": round(
                        (comp["share"]["entailed"]
                         - base_comp["share"]["entailed"]) * 100, 1),
                    "failed_share_delta_pp": round(
                        (comp["share"]["failed"]
                         - base_comp["share"]["failed"]) * 100, 1),
                    "unchecked_share": comp["share"]["unchecked"],
                    "rows_pct_of_baseline": (
                        round(len(served) / len(base), 4) if base else None),
                    "median_signals_top10": median_signals(served, VISIBLE_FOLD),
                    "median_signals_pct_of_baseline": (
                        round(median_signals(served, VISIBLE_FOLD)
                              / median_signals(base, VISIBLE_FOLD), 4)
                        if median_signals(base, VISIBLE_FOLD) else None),
                    "visible_fold": compose(served[:VISIBLE_FOLD]),
                    "diff_vs_baseline": diff(base, served),
                    "head": head(served, 20),
                }
            door["size_by_status_deepest_pool"] = size_by_status(
                pools[max(mults)])
            result["doors"][name] = door
            if out is not None:      # partial dump: a killed run keeps its doors
                out.parent.mkdir(parents=True, exist_ok=True)
                out.write_text(json.dumps(result, indent=2, default=str))
        print("[a0b] cost ...", file=sys.stderr)
        result["cost"] = await a0b_cost(conn, 40, mults, cost_reps)
    finally:
        await conn.close()
    return result


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", required=True, help="JSON artifact path")
    ap.add_argument(
        "--doors", default=None,
        help="comma list NAME:CC:PAGE (CC '-' for global), default built-in set",
    )
    ap.add_argument("--no-scan", action="store_true",
                    help="skip the country-door candidates-vs-served scan")
    ap.add_argument("--a0b", action="store_true",
                    help="run the A0b fetch-gate simulation instead of A0")
    ap.add_argument("--mults", default="2,3,4",
                    help="A0b fetch multipliers (default 2,3,4)")
    ap.add_argument("--cost-reps", type=int, default=5,
                    help="A0b C5 timing repetitions per depth")
    args = ap.parse_args()
    doors = DEFAULT_DOORS
    if args.a0b:
        doors = A0B_DOORS
    if args.doors:
        doors = []
        for spec in args.doors.split(","):
            nm, cc, pg = spec.split(":")
            doors.append((nm, None if cc == "-" else cc.upper(), int(pg)))
    out = Path(args.out)
    if args.a0b:
        mults = tuple(int(x) for x in args.mults.split(","))
        payload = asyncio.run(run_a0b(doors, mults, args.cost_reps, out))
    else:
        payload = asyncio.run(run(doors, do_scan=not args.no_scan))
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, indent=2, default=str))
    print(f"wrote {out}", file=sys.stderr)


if __name__ == "__main__":
    main()

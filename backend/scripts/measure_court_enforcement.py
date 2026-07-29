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
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import asyncpg  # noqa: E402

from app.services import thread_ranking  # noqa: E402
from app.services.thread_intelligence import (  # noqa: E402
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


_DOOR_CANDIDATES_SQL = """
SELECT COUNT(DISTINCT dt.id)::int
FROM dynamic_topics dt
JOIN dynamic_topic_members dtmc ON dtmc.dynamic_topic_id = dt.id
JOIN emergent_clusters ecc ON ecc.id = dtmc.emergent_cluster_id
WHERE dt.state='active' AND dt.is_umbrella = false
  AND dt.last_seen > NOW() - INTERVAL '72 hours'
  AND ecc.top_country_codes[1] = $1
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


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", required=True, help="JSON artifact path")
    ap.add_argument(
        "--doors", default=None,
        help="comma list NAME:CC:PAGE (CC '-' for global), default built-in set",
    )
    ap.add_argument("--no-scan", action="store_true",
                    help="skip the country-door candidates-vs-served scan")
    args = ap.parse_args()
    doors = DEFAULT_DOORS
    if args.doors:
        doors = []
        for spec in args.doors.split(","):
            nm, cc, pg = spec.split(":")
            doors.append((nm, None if cc == "-" else cc.upper(), int(pg)))
    payload = asyncio.run(run(doors, do_scan=not args.no_scan))
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, indent=2, default=str))
    print(f"wrote {out}", file=sys.stderr)


if __name__ == "__main__":
    main()

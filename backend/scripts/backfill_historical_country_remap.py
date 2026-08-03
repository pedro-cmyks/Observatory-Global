"""Backfill archive-derived country codes misfiled by the FIPS/ISO map bug
(b7ab7def) in historical_topic_country_daily + historical_evidence_samples.

Follows backend/scripts/backfill_country_code_remap.py (the signals_v2 heal)
pattern: key-guarded single-hop remap, --dry-run default, --execute to apply,
--revert with a JSONL ledger, batched, idempotent via committed ledgers.

WHAT THIS FIXES
---------------
The archive-fed tables were populated from the immutable external archive,
which stores the PRE-fix codes: Lebanon under LS=Lesotho, Serbia under raw
GEC RB, Paraguay under PA=Panama, Kosovo under KV, ... (May-05→Jul-21). The
correction map is docs/research/country-code-remap/country-code-corrections-
v1.json, consumed through app/services/country_corrections.py (which the
archive WRITERS now also apply at write time, so future re-syncs cannot
re-poison — this script heals the existing stock).

SCOPE INVARIANTS (load-bearing)
-------------------------------
1. GDELT lane only. In these tables the lane marker is source_family:
   'gdelt', plus 'unknown' = the 2026-05-05..05-09 pre-family archive era,
   MEASURED to be GDELT-lane content (LS-unknown = Lebanon, BH-unknown =
   Belize, GA-unknown = Gambia; zero genuine Lesotho/Bahrain/Gabon rows in
   the samples — see the 2026-07-30 session + country_corrections.py).
   Families derived from real outlets (press/independent/state/wire/...)
   are ISO-correct (MN independent = ikon.mn Mongolia, PA independent =
   tvn-2.com Panama) and are NEVER touched.
2. model_version scope: 'atlas-hist-v1' for the daily table, 'hes-v1' for
   evidence samples. The 'archive-topics-v1' rows (archive_cluster_offline)
   are EXCLUDED: that lane derives source_family from the outlet DOMAIN (its
   family does not mark the lane) and is DELETE-and-replace rebuildable by
   design — its heal is a rebuild through the now-corrected writer.
3. Single-hop from the STORED code, applied in TOPOLOGICAL pair order:
   chains exist (BP→SB→PM→PA→PY, MG→MN→MC→MO, GK→GG→GE, ...) so a pair
   (old→new) runs only after the pair evacuating `new` has run — otherwise
   ex-PM Panama rows would merge into still-parked Paraguay rows and then
   double-hop to PY.
4. Ledgered rows are excluded from re-runs (chain targets make healed rows
   indistinguishable from still-wrong rows; the ledger IS the idempotency
   mechanism). Ledgers land in
   docs/research/country-code-remap/ledgers/historical/ — a SUBDIRECTORY so
   the signals_v2 script's *.jsonl glob (id-keyed records) never reads them.

PK-COLLISION MERGE POLICY (daily table)
---------------------------------------
historical_topic_country_daily's PK is (day, topic_slug, country_code,
source_family, signal_class, model_version); remapping LS→LB can collide
with a genuine LB row for the same key (e.g. written by the gdelt-lane
outlet-origin override path). Colliding rows are MERGED — the only DELETE
this script performs — with app/services/country_corrections.merge_daily_rows:

  signal_count, evidence_sample_count       → summed (exact)
  sentiment/topic/entity coverage           → weighted by signal_count (exact)
  avg_sentiment                             → weighted by signal_count
                                              (approximate: the true weight
                                              sentiment_n is not stored;
                                              documented in the module)
  local_voice_ratio                         → weighted when both present,
                                              else the non-null side
  source_diversity                          → NOT mergeable (source-set
                                              overlap unknowable): the
                                              larger-signal_count side's
                                              value wins, the other side's
                                              value is preserved in the
                                              ledger (both full rows are
                                              ledgered on every merge)

Every merge ledgers BOTH sides (source row + target pre-merge values) so
--revert restores the target and re-inserts the source exactly.

KNOWN RESIDUE (documented, not touched): aggregate rows carry no headline,
so the ~375:1 LS Liechtenstein split cannot apply to the daily table (LS →
LB wholesale); evidence rows DO carry headlines and get the LI split. The
override-path contribution (genuine Panama inside gdelt-lane PA aggregates,
~14% of that bucket in the 7d hot measurement) is not separable at aggregate
grain and rides along to PY — same acceptance as the corrections artifact.

Usage (DATABASE_URL required):
  python scripts/backfill_historical_country_remap.py                  # dry-run, both tables
  python scripts/backfill_historical_country_remap.py --table daily    # dry-run, one table
  python scripts/backfill_historical_country_remap.py --execute
  python scripts/backfill_historical_country_remap.py --revert <ledger.jsonl>
"""
from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
from datetime import date, datetime, timezone
from pathlib import Path

import asyncpg

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.services.country_corrections import (  # noqa: E402
    DAILY_MERGE_COLUMNS,
    correct_country_code,
    load_remap,
    merge_daily_rows,
)

DAILY_TABLE = "historical_topic_country_daily"
EVIDENCE_TABLE = "historical_evidence_samples"

DAILY_MODEL_VERSION = "atlas-hist-v1"
EVIDENCE_MODEL_VERSION = "hes-v1"
LANE_FAMILIES = ["gdelt", "unknown"]

# PK columns of the daily table, in ledger/plan order.
DAILY_PK = ("day", "topic_slug", "country_code", "source_family",
            "signal_class", "model_version")

LEDGER_DIR = (
    Path(__file__).resolve().parents[2]
    / "docs" / "research" / "country-code-remap" / "ledgers" / "historical"
)


# ── pure logic (unit-tested) ─────────────────────────────────────────────────

def ordered_pairs(remap: dict[str, str]) -> list[tuple[str, str]]:
    """Remap pairs in a safe application order: a pair (old→new) whose target
    is itself a remap key runs only AFTER the pair evacuating that target.
    Raises on a cycle (would make single-hop application order-impossible).
    """
    remaining = dict(remap)
    order: list[tuple[str, str]] = []
    while remaining:
        ready = sorted((o, n) for o, n in remaining.items() if n not in remaining)
        if not ready:
            raise ValueError(f"cycle in remap: {sorted(remaining.items())}")
        for old, new in ready:
            order.append((old, new))
            del remaining[old]
    return order


def _sig(day, topic_slug, country_code, source_family, signal_class,
         model_version) -> tuple:
    return (str(day), topic_slug, country_code, source_family, signal_class,
            model_version)


def row_sig(row: dict) -> tuple:
    return _sig(*(row[c] for c in DAILY_PK))


def plan_daily(rows: list[dict], excluded_sigs: set[tuple],
               remap: dict[str, str]) -> list[dict]:
    """Simulate the remap over the fetched daily rows and return the ordered
    op list. ``rows`` must contain BOTH the candidates (country_code in remap
    keys) and every potential collision resident (country_code in remap
    values, same family/model scope).

    Ops:
      {'op': 'move',  'pk': {...old pk...}, 'old', 'new'}
      {'op': 'merge', 'pk': {...old pk...}, 'old', 'new',
       'source_row': {mergeable cols}, 'target_before': {...},
       'target_after': {...}}
    """
    state: dict[tuple, dict] = {}
    for r in rows:
        state[row_sig(r)] = dict(r)
    candidates_by_old: dict[str, list[dict]] = {}
    for r in rows:
        cc = r["country_code"]
        if cc in remap and row_sig(r) not in excluded_sigs:
            candidates_by_old.setdefault(cc, []).append(r)

    ops: list[dict] = []
    for old, new in ordered_pairs(remap):
        for r in sorted(candidates_by_old.get(old, ()), key=row_sig):
            sig_old = row_sig(r)
            cur = state.pop(sig_old, None)
            if cur is None:
                continue  # already consumed (defensive; shouldn't happen)
            pk = {c: r[c] for c in DAILY_PK}
            sig_new = _sig(str(r["day"]), r["topic_slug"], new,
                           r["source_family"], r["signal_class"],
                           r["model_version"])
            if sig_new in state:
                target = state[sig_new]
                merged = merge_daily_rows(target, cur)
                ops.append({
                    "op": "merge", "pk": pk, "old": old, "new": new,
                    "source_row": {c: cur[c] for c in DAILY_MERGE_COLUMNS},
                    "target_before": {c: target[c] for c in DAILY_MERGE_COLUMNS},
                    "target_after": {c: merged[c] for c in DAILY_MERGE_COLUMNS},
                })
                state[sig_new] = merged
            else:
                ops.append({"op": "move", "pk": pk, "old": old, "new": new})
                moved = dict(cur)
                moved["country_code"] = new
                state[sig_new] = moved
    return ops


def plan_evidence(rows: list[dict], excluded_ids: set[str]) -> list[dict]:
    """rows: (sample_id, country_code, headline) dicts, already lane/model
    scoped by the fetch. Returns move ops (PK is sample_id — no collisions;
    the LS→LI Liechtenstein split applies via the stored headline)."""
    remap = load_remap()
    ops: list[dict] = []
    for r in rows:
        if r["sample_id"] in excluded_ids:
            continue
        cc = r["country_code"]
        if cc not in remap:
            continue
        new = correct_country_code(cc, headline=r.get("headline"))
        if new != cc:
            ops.append({"op": "move", "sample_id": r["sample_id"],
                        "old": cc, "new": new})
    return ops


def summarize_ops(ops: list[dict]) -> dict[tuple[str, str, str], int]:
    counts: dict[tuple[str, str, str], int] = {}
    for op in ops:
        key = (op["old"], op["new"], op["op"])
        counts[key] = counts.get(key, 0) + 1
    return counts


def load_ledger_exclusions(ledger_dir: Path) -> tuple[set[tuple], set[str]]:
    """Applied post-move identities from committed ledgers: daily rows by
    their CURRENT (post-move) PK signature, evidence rows by sample_id."""
    daily_sigs: set[tuple] = set()
    evidence_ids: set[str] = set()
    if not ledger_dir.is_dir():
        return daily_sigs, evidence_ids
    for path in sorted(ledger_dir.glob("*.jsonl")):
        with path.open(encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                rec = json.loads(line)
                if rec.get("type") == "meta":
                    continue
                if rec.get("table") == DAILY_TABLE:
                    pk = rec["pk"]
                    daily_sigs.add(_sig(pk["day"], pk["topic_slug"],
                                        rec["new"], pk["source_family"],
                                        pk["signal_class"],
                                        pk["model_version"]))
                elif rec.get("table") == EVIDENCE_TABLE:
                    evidence_ids.add(rec["sample_id"])
    return daily_sigs, evidence_ids


# ── DB access ────────────────────────────────────────────────────────────────

DAILY_FETCH_SQL = f"""
    SELECT day, topic_slug, country_code, source_family, signal_class,
           model_version, signal_count, avg_sentiment, sentiment_coverage,
           topic_coverage, entity_coverage, local_voice_ratio,
           source_diversity, evidence_sample_count
    FROM {DAILY_TABLE}
    WHERE model_version = $1
      AND source_family = ANY($2::text[])
      AND country_code = ANY($3::text[])
"""

EVIDENCE_FETCH_SQL = f"""
    SELECT sample_id, country_code, headline
    FROM {EVIDENCE_TABLE}
    WHERE model_version = $1
      AND source_family = ANY($2::text[])
      AND country_code = ANY($3::text[])
"""


async def fetch_daily_rows(conn) -> list[dict]:
    remap = load_remap()
    codes = sorted(set(remap) | set(remap.values()))
    rows = await conn.fetch(DAILY_FETCH_SQL, DAILY_MODEL_VERSION,
                            LANE_FAMILIES, codes)
    return [dict(r) for r in rows]


async def fetch_evidence_rows(conn) -> list[dict]:
    rows = await conn.fetch(EVIDENCE_FETCH_SQL, EVIDENCE_MODEL_VERSION,
                            LANE_FAMILIES, sorted(load_remap()))
    return [dict(r) for r in rows]


DAILY_MOVE_SQL = f"""
    UPDATE {DAILY_TABLE} t
    SET country_code = $1, updated_at = NOW()
    FROM unnest($2::date[], $3::text[], $4::text[], $5::text[], $6::text[])
         AS k(day, topic_slug, source_family, signal_class, model_version)
    WHERE t.day = k.day AND t.topic_slug = k.topic_slug
      AND t.country_code = $7
      AND t.source_family = k.source_family
      AND t.signal_class = k.signal_class
      AND t.model_version = k.model_version
    RETURNING t.day, t.topic_slug, t.source_family, t.signal_class,
              t.model_version
"""

DAILY_MERGE_UPDATE_SQL = f"""
    UPDATE {DAILY_TABLE}
    SET signal_count = $7, avg_sentiment = $8, sentiment_coverage = $9,
        topic_coverage = $10, entity_coverage = $11, local_voice_ratio = $12,
        source_diversity = $13, evidence_sample_count = $14,
        updated_at = NOW()
    WHERE day = $1 AND topic_slug = $2 AND country_code = $3
      AND source_family = $4 AND signal_class = $5 AND model_version = $6
"""

DAILY_DELETE_SQL = f"""
    DELETE FROM {DAILY_TABLE}
    WHERE day = $1 AND topic_slug = $2 AND country_code = $3
      AND source_family = $4 AND signal_class = $5 AND model_version = $6
"""


def _merge_update_args(pk: dict, new: str, after: dict) -> list:
    return [
        pk["day"], pk["topic_slug"], new, pk["source_family"],
        pk["signal_class"], pk["model_version"],
        after["signal_count"], after["avg_sentiment"],
        after["sentiment_coverage"], after["topic_coverage"],
        after["entity_coverage"], after["local_voice_ratio"],
        after["source_diversity"], after["evidence_sample_count"],
    ]


def _ledger_daily(op: dict) -> dict:
    rec = {"table": DAILY_TABLE, "op": op["op"],
           "pk": {**op["pk"], "day": str(op["pk"]["day"])},
           "old": op["old"], "new": op["new"]}
    if op["op"] == "merge":
        rec["source_row"] = op["source_row"]
        rec["target_before"] = op["target_before"]
        rec["target_after"] = op["target_after"]
    return rec


async def apply_daily(conn, ops: list[dict], ledger_fh) -> dict[str, int]:
    """Apply in plan order (topologically safe). Moves batched per (old,new)
    in chunks; merges one transaction each. Ledger appended after commit."""
    applied = {"move": 0, "merge": 0, "skipped": 0}
    chunk: list[dict] = []

    async def flush_moves():
        if not chunk:
            return
        old = chunk[0]["old"]
        new = chunk[0]["new"]
        try:
            async with conn.transaction():
                returned = await conn.fetch(
                    DAILY_MOVE_SQL, new,
                    [c["pk"]["day"] for c in chunk],
                    [c["pk"]["topic_slug"] for c in chunk],
                    [c["pk"]["source_family"] for c in chunk],
                    [c["pk"]["signal_class"] for c in chunk],
                    [c["pk"]["model_version"] for c in chunk],
                    old,
                )
        except asyncpg.UniqueViolationError as exc:
            # A row appeared at a target PK between fetch and apply (live
            # divergence). Nothing from this chunk was applied or ledgered;
            # a re-run re-plans it (as a merge).
            print(f"  WARN chunk {old}->{new} skipped on PK collision "
                  f"(re-run re-plans it as a merge): {exc}", flush=True)
            applied["skipped"] += len(chunk)
            chunk.clear()
            return
        done = {(str(r["day"]), r["topic_slug"], r["source_family"],
                 r["signal_class"], r["model_version"]) for r in returned}
        for c in chunk:
            key = (str(c["pk"]["day"]), c["pk"]["topic_slug"],
                   c["pk"]["source_family"], c["pk"]["signal_class"],
                   c["pk"]["model_version"])
            if key in done:
                ledger_fh.write(json.dumps(_ledger_daily(c)) + "\n")
                applied["move"] += 1
            else:
                applied["skipped"] += 1
                print(f"  WARN move not applied (row changed?): "
                      f"{c['old']}->{c['new']} {key}", flush=True)
        ledger_fh.flush()
        print(f"  {old} -> {new}: +{len(done)} moves", flush=True)
        chunk.clear()

    for op in ops:
        if op["op"] == "move":
            if chunk and (chunk[0]["old"] != op["old"]
                          or chunk[0]["new"] != op["new"]
                          or len(chunk) >= 500):
                await flush_moves()
            chunk.append(op)
            continue
        # merge — flush pending moves first to preserve plan order
        await flush_moves()
        pk = op["pk"]
        try:
            async with conn.transaction():
                upd = await conn.execute(
                    DAILY_MERGE_UPDATE_SQL,
                    *_merge_update_args(pk, op["new"], op["target_after"]))
                dele = await conn.execute(
                    DAILY_DELETE_SQL, pk["day"], pk["topic_slug"], op["old"],
                    pk["source_family"], pk["signal_class"],
                    pk["model_version"])
                if upd != "UPDATE 1" or dele != "DELETE 1":
                    raise RuntimeError(f"merge guard failed ({upd}, {dele})")
        except RuntimeError as exc:
            applied["skipped"] += 1
            print(f"  WARN merge skipped {op['old']}->{op['new']} "
                  f"{pk['topic_slug']}@{pk['day']}: {exc}", flush=True)
            continue
        ledger_fh.write(json.dumps(_ledger_daily(op)) + "\n")
        ledger_fh.flush()
        applied["merge"] += 1
    await flush_moves()
    return applied


EVIDENCE_MOVE_SQL = f"""
    UPDATE {EVIDENCE_TABLE}
    SET country_code = $1
    WHERE sample_id = ANY($2::text[]) AND country_code = $3
    RETURNING sample_id
"""


async def apply_evidence(conn, ops: list[dict], ledger_fh) -> dict[str, int]:
    applied = {"move": 0, "skipped": 0}
    groups: dict[tuple[str, str], list[str]] = {}
    for op in ops:
        groups.setdefault((op["old"], op["new"]), []).append(op["sample_id"])
    for (old, new), ids in sorted(groups.items()):
        done_total = 0
        for i in range(0, len(ids), 1000):
            batch = ids[i:i + 1000]
            async with conn.transaction():
                returned = await conn.fetch(EVIDENCE_MOVE_SQL, new, batch, old)
            done = {r["sample_id"] for r in returned}
            for sid in batch:
                if sid in done:
                    ledger_fh.write(json.dumps(
                        {"table": EVIDENCE_TABLE, "op": "move",
                         "sample_id": sid, "old": old, "new": new}) + "\n")
                else:
                    applied["skipped"] += 1
            ledger_fh.flush()
            done_total += len(done)
        applied["move"] += done_total
        print(f"  {old} -> {new}: {done_total}/{len(ids)}", flush=True)
    return applied


# ── revert ───────────────────────────────────────────────────────────────────

async def revert(conn, ledger_path: Path) -> dict[str, int]:
    """Replay a ledger in REVERSE order: moves go back guarded on the current
    code; merges restore the target's pre-merge values and re-insert the
    source row (ON CONFLICT DO NOTHING + warning — a re-synced row may own
    the PK again)."""
    records = []
    with ledger_path.open(encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            rec = json.loads(line)
            if rec.get("type") != "meta":
                records.append(rec)
    counts = {"move": 0, "merge": 0, "skipped": 0}
    for rec in reversed(records):
        if rec["table"] == EVIDENCE_TABLE:
            res = await conn.execute(
                f"UPDATE {EVIDENCE_TABLE} SET country_code = $1 "
                f"WHERE sample_id = $2 AND country_code = $3",
                rec["old"], rec["sample_id"], rec["new"])
            if res == "UPDATE 1":
                counts["move"] += 1
            else:
                counts["skipped"] += 1
            continue
        pk = rec["pk"]
        pk_day = date.fromisoformat(pk["day"])
        if rec["op"] == "move":
            res = await conn.execute(
                f"UPDATE {DAILY_TABLE} SET country_code = $7, "
                f"updated_at = NOW() "
                f"WHERE day = $1 AND topic_slug = $2 AND country_code = $3 "
                f"  AND source_family = $4 AND signal_class = $5 "
                f"  AND model_version = $6",
                pk_day, pk["topic_slug"], rec["new"], pk["source_family"],
                pk["signal_class"], pk["model_version"], rec["old"])
            if res == "UPDATE 1":
                counts["move"] += 1
            else:
                counts["skipped"] += 1
                print(f"  WARN move revert skipped: {pk} {rec['new']}->"
                      f"{rec['old']}", flush=True)
            continue
        # merge revert
        before = rec["target_before"]
        src = rec["source_row"]
        async with conn.transaction():
            upd = await conn.execute(
                DAILY_MERGE_UPDATE_SQL,
                pk_day, pk["topic_slug"], rec["new"], pk["source_family"],
                pk["signal_class"], pk["model_version"],
                before["signal_count"], before["avg_sentiment"],
                before["sentiment_coverage"], before["topic_coverage"],
                before["entity_coverage"], before["local_voice_ratio"],
                before["source_diversity"], before["evidence_sample_count"])
            ins = await conn.execute(
                f"INSERT INTO {DAILY_TABLE} (day, topic_slug, country_code, "
                f"source_family, signal_class, signal_count, avg_sentiment, "
                f"sentiment_coverage, topic_coverage, entity_coverage, "
                f"local_voice_ratio, source_diversity, evidence_sample_count, "
                f"model_version, updated_at) "
                f"VALUES ($1::date,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12,$13,"
                f"$14,NOW()) ON CONFLICT DO NOTHING",
                pk_day, pk["topic_slug"], rec["old"], pk["source_family"],
                pk["signal_class"], src["signal_count"], src["avg_sentiment"],
                src["sentiment_coverage"], src["topic_coverage"],
                src["entity_coverage"], src["local_voice_ratio"],
                src["source_diversity"], src["evidence_sample_count"],
                pk["model_version"])
        if upd != "UPDATE 1":
            print(f"  WARN merge revert: target not restored {pk}", flush=True)
        if ins != "INSERT 0 1":
            print(f"  WARN merge revert: source row not re-inserted "
                  f"(PK occupied) {pk}", flush=True)
        counts["merge"] += 1
    return counts


# ── reporting ────────────────────────────────────────────────────────────────

def print_summary(title: str, ops: list[dict]) -> None:
    counts = summarize_ops(ops)
    moves = sum(n for (_, _, k), n in counts.items() if k == "move")
    merges = sum(n for (_, _, k), n in counts.items() if k == "merge")
    print(f"\n{title}: {len(ops)} ops ({moves} moves, {merges} merges)")
    by_pair: dict[tuple[str, str], dict[str, int]] = {}
    for (old, new, kind), n in counts.items():
        by_pair.setdefault((old, new), {}).setdefault(kind, 0)
        by_pair[(old, new)][kind] += n
    for (old, new), kinds in sorted(
            by_pair.items(), key=lambda kv: -sum(kv[1].values())):
        merge_note = f" ({kinds['merge']} merges)" if kinds.get("merge") else ""
        print(f"  {old} -> {new}: {sum(kinds.values())}{merge_note}")


async def verify(conn) -> None:
    remap = load_remap()
    rows = await conn.fetch(
        f"SELECT country_code, count(*) AS n, sum(signal_count) AS signals "
        f"FROM {DAILY_TABLE} WHERE model_version=$1 "
        f"AND source_family=ANY($2::text[]) AND country_code=ANY($3::text[]) "
        f"GROUP BY 1 ORDER BY 1",
        DAILY_MODEL_VERSION, LANE_FAMILIES, sorted(remap))
    print("\nREMAINING daily rows in source buckets (gdelt/unknown lane; "
          "chain residents excluded via ledger on re-runs):")
    for r in rows:
        print(f"  {r['country_code']}: {r['n']} rows / {r['signals']} signals")
    rows = await conn.fetch(
        f"SELECT country_code, count(*) AS n FROM {EVIDENCE_TABLE} "
        f"WHERE model_version=$1 AND source_family=ANY($2::text[]) "
        f"AND country_code=ANY($3::text[]) GROUP BY 1 ORDER BY 1",
        EVIDENCE_MODEL_VERSION, LANE_FAMILIES, sorted(remap))
    print("REMAINING evidence rows in source buckets:")
    for r in rows:
        print(f"  {r['country_code']}: {r['n']}")


# ── main ─────────────────────────────────────────────────────────────────────

async def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    mode = ap.add_mutually_exclusive_group()
    mode.add_argument("--dry-run", action="store_true",
                      help="print the plan, write nothing (DEFAULT)")
    mode.add_argument("--execute", action="store_true",
                      help="write the ledger, then apply the plan")
    mode.add_argument("--revert", metavar="LEDGER",
                      help="revert a previously applied ledger file")
    ap.add_argument("--table", choices=["daily", "evidence", "all"],
                    default="all")
    args = ap.parse_args()

    db = os.environ.get("DATABASE_URL")
    if not db:
        print("DATABASE_URL required", file=sys.stderr)
        return 2

    conn = await asyncpg.connect(db)
    try:
        await conn.execute("SET statement_timeout = '900s'")

        if args.revert:
            counts = await revert(conn, Path(args.revert))
            print(f"REVERTED: {counts}")
            return 0

        remap = load_remap()
        daily_sigs, evidence_ids = load_ledger_exclusions(LEDGER_DIR)

        daily_ops: list[dict] = []
        evidence_ops: list[dict] = []
        if args.table in ("daily", "all"):
            rows = await fetch_daily_rows(conn)
            candidates = [r for r in rows if r["country_code"] in remap]
            daily_ops = plan_daily(rows, daily_sigs, remap)
            print(f"{DAILY_TABLE}: fetched={len(rows)} "
                  f"candidates={len(candidates)} "
                  f"ledger-excluded={len(candidates) - len(daily_ops)}")
            print_summary(f"PLAN {DAILY_TABLE}", daily_ops)
        if args.table in ("evidence", "all"):
            rows = await fetch_evidence_rows(conn)
            evidence_ops = plan_evidence(rows, evidence_ids)
            print(f"\n{EVIDENCE_TABLE}: fetched={len(rows)} "
                  f"ledger-excluded={len(rows) - len(evidence_ops)}")
            print_summary(f"PLAN {EVIDENCE_TABLE}", evidence_ops)

        if not args.execute:
            print("\n(dry-run — nothing written; re-run with --execute)")
            return 0

        LEDGER_DIR.mkdir(parents=True, exist_ok=True)
        now = datetime.now(timezone.utc)
        ledger_path = (LEDGER_DIR /
                       f"{now.strftime('%Y%m%dT%H%M%SZ')}-historical-remap.jsonl")
        with ledger_path.open("w", encoding="utf-8") as fh:
            fh.write(json.dumps({
                "type": "meta", "run_at": now.isoformat(),
                "daily_scope": f"{DAILY_TABLE} model_version="
                               f"{DAILY_MODEL_VERSION} "
                               f"source_family IN {LANE_FAMILIES}",
                "evidence_scope": f"{EVIDENCE_TABLE} model_version="
                                  f"{EVIDENCE_MODEL_VERSION} "
                                  f"source_family IN {LANE_FAMILIES}",
                "planned_daily_ops": len(daily_ops),
                "planned_evidence_ops": len(evidence_ops),
            }) + "\n")
            fh.flush()
            if daily_ops:
                print(f"\nAPPLYING {DAILY_TABLE} ...")
                applied = await apply_daily(conn, daily_ops, fh)
                print(f"APPLIED {DAILY_TABLE}: {applied}")
            if evidence_ops:
                print(f"\nAPPLYING {EVIDENCE_TABLE} ...")
                applied = await apply_evidence(conn, evidence_ops, fh)
                print(f"APPLIED {EVIDENCE_TABLE}: {applied}")
        print(f"\nledger written (applied rows only): {ledger_path}")
        await verify(conn)
        return 0
    finally:
        await conn.close()


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))

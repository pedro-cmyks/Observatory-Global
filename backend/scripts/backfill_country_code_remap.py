"""Backfill signals_v2.country_code for rows written before the FIPS/ISO map
fix (b7ab7def, 2026-07-28).

WHAT THIS FIXES
---------------
Before the fix, backend/app/services/country_codes.py mis-translated or
passed through ~48 divergent FIPS 10-4 (GEC) codes, so GDELT-lane rows were
stored under a wrong-but-plausible ISO code (Lebanon under LS=Lesotho, Serbia
under the raw GEC RB, Panama under the raw GEC PM, ...). Every bucket in
REMAP below was verified against live headline samples before being listed —
see docs/research/country-code-remap/2026-07-28-country-code-remap.md.

SCOPE INVARIANTS (all load-bearing, do not relax)
-------------------------------------------------
1. GDELT lane only (source_family='gdelt'). RSS/NewsData/social lanes write
   ISO directly and were never wrong (verified: MN=ikon.mn Mongolia,
   PA=tvn-2.com Panama are CORRECT rows that must not move).
2. geo_confidence != 0.35 — that value is exactly the ingest
   outlet_origin_override path (ingest_v2._GEO_OVERRIDE_CONFIDENCE), which
   writes ISO codes from the outlet's ccTLD/domain, not FIPS. Measured: the
   82 conf-0.35 rows in the PA bucket are genuine Panama.
3. created_at < --max-created-at (REQUIRED). After the map fix deploys, the
   NEW map legitimately emits several of these bucket codes for OTHER
   countries (post-fix Lesotho=LS, Guernsey→GG, Monaco→MC, Costa Rica→CR).
   A blanket re-run without the cutoff would corrupt those correct rows.
   Set the cutoff at (or before) the fix's deploy time, never after.
4. Previously-ledgered ids are excluded. Chain targets (PM→PA while PA→PY,
   MG→MN→MC→MO, GK→GG→GE, ...) make remapped rows indistinguishable from
   still-wrong rows, so the ledger IS the idempotency mechanism.

CONTAMINATED BUCKETS — NEVER ADD: CN (China+Comoros), GB (UK+Gabon),
PL (Poland+Portugal), ZA (SouthAfrica+Zambia), MA (Morocco+Madagascar),
LT (Lithuania+Lesotho), TD (Chad+Trinidad), PS (Palestine+Palau), plus any
bucket in the b7ab7def commit's [WARNING] pairs whose two feeders both have
live volume. Those need re-derivation from raw GDELT fields, not a remap.

DELIBERATELY NOT REMAPPED: OS (GDELT GEC 'Oceans' pseudo-code — no ISO
equivalent), YI (GEC Serbia-and-Montenegro, defunct 2006 — no honest
successor for pan-Yugoslav retrospectives), CR (bucket is 100% conf-0.35
override rows = correct Costa Rica), TK (24 GDELT-geocoded rows whose
content is Turkey — GDELT geocoder pathology; neither TK nor TC is honest).

Usage:
  python scripts/backfill_country_code_remap.py --measure
  python scripts/backfill_country_code_remap.py --execute \
      --max-created-at 2026-07-28T22:00:00+00:00
  python scripts/backfill_country_code_remap.py --revert <ledger.jsonl>

Ledgers land in docs/research/country-code-remap/ledgers/ (repo-committed:
they are the reversal path and the re-run exclusion set).
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

import asyncpg

# ---------------------------------------------------------------------------
# The verified remap table: stored (wrong) code -> correct ISO 3166-1 alpha-2.
# Source of truth for the mapping direction: b7ab7def country_codes.py; every
# entry here was ALSO verified against live prod headline samples 2026-07-28.
# ---------------------------------------------------------------------------
REMAP: dict[str, str] = {
    # The seven mis-mapped / high-volume passthrough classes from the 7d
    # blast-radius measurement:
    'LS': 'LB',  # Lebanon (FIPS LE mis-mapped to LS). Special-cased below:
                 #   FIPS LS = Liechtenstein ALSO passed through into this
                 #   bucket (5 rows measured) — split by headline keyword.
    'PM': 'PA',  # Panama        (GEC PM passthrough)
    'PA': 'PY',  # Paraguay      (FIPS PA mis-mapped to PA)
    'MG': 'MN',  # Mongolia      (GEC MG passthrough; ISO MG = Madagascar)
    'MN': 'MC',  # Monaco        (GEC MN passthrough; ISO MN = Mongolia)
    'MC': 'MO',  # Macau         (GEC MC passthrough; ISO MC = Monaco)
    'GA': 'GM',  # Gambia        (FIPS GA mis-mapped to GA=Gabon)
    # Raw GEC codes with no ISO meaning (pure passthrough residue):
    'RB': 'RS',  # Serbia        (pre-2008 GEC code)
    'KV': 'XK',  # Kosovo        (Atlas convention: user-assigned XK)
    'CS': 'CR',  # Costa Rica
    'OD': 'SS',  # South Sudan
    'PP': 'PG',  # Papua New Guinea
    # Additional pure buckets found by diffing the old map against b7ab7def
    # and verified by sample (2026-07-28). Volumes 1-501 rows/7d each.
    'GG': 'GE',  # Georgia (country)   (GEC GG; ISO GG = Guernsey)
    'AN': 'AD',  # Andorra
    'RQ': 'PR',  # Puerto Rico
    'BH': 'BZ',  # Belize              (ISO BH = Bahrain; GEC Bahrain = BA)
    'TI': 'TJ',  # Tajikistan
    'NS': 'SR',  # Suriname
    'AY': 'AQ',  # Antarctica
    'GJ': 'GD',  # Grenada
    'GK': 'GG',  # Guernsey            (chains into the GG→GE move)
    'BP': 'SB',  # Solomon Islands     (chains: BP→SB while SB→PM)
    'TX': 'TM',  # Turkmenistan
    'VQ': 'VI',  # U.S. Virgin Islands (chains: VQ→VI while VI→VG)
    'CJ': 'KY',  # Cayman Islands
    'GQ': 'GU',  # Guam                (ISO GQ = Eq. Guinea; GEC EK feeds it)
    'TT': 'TL',  # Timor-Leste         (ISO TT = Trinidad; GEC TD contaminated)
    'MF': 'YT',  # Mayotte             (ISO MF = St-Martin; GEC RN feeds MF)
    'ST': 'LC',  # Saint Lucia         (chains: TP→ST while ST→LC)
    'AC': 'AG',  # Antigua and Barbuda
    'TP': 'ST',  # Sao Tome and Principe
    'MB': 'MQ',  # Martinique
    'NH': 'VU',  # Vanuatu
    'CW': 'CK',  # Cook Islands        (ISO CW = Curacao; GEC UC = Curacao)
    'VT': 'VA',  # Vatican
    'MH': 'MS',  # Montserrat          (chains: RM→MH while MH→MS)
    'AA': 'AW',  # Aruba
    'AQ': 'AS',  # American Samoa      (chains: AY→AQ while AQ→AS)
    'RM': 'MH',  # Marshall Islands
    'VI': 'VG',  # British Virgin Islands
    'FP': 'PF',  # French Polynesia
    'WI': 'EH',  # Western Sahara
    'EK': 'GQ',  # Equatorial Guinea
    'AV': 'AI',  # Anguilla
    'CQ': 'MP',  # Northern Mariana Islands
    'WQ': 'UM',  # Wake Island → US Minor Outlying
    'FG': 'GF',  # French Guiana
    'TL': 'TK',  # Tokelau             (2 rows; lands beside the 24-row TK
                 #   Turkey-content pathology, which stays as-is — documented)
    'RN': 'MF',  # Saint Martin (French part)
    'SB': 'PM',  # Saint Pierre and Miquelon
}

# ingest_v2._GEO_OVERRIDE_CONFIDENCE — rows written by outlet_origin_override
# carry ISO codes (ccTLD/domain derived), NOT FIPS. Never remap them.
OVERRIDE_GEO_CONFIDENCE = 0.35

# FIPS LS = Liechtenstein leaked into the Lebanon bucket (see module doc).
# Rows matching this pattern go to LI instead of LB; hand-verified on all 5
# live hits (Vaduz police blotter, Liechtenstein heatwave, LGT-adjacent
# corporate news). Residual risk accepted: a Liechtenstein row that names
# neither token follows the Lebanon majority (volume ratio ~375:1).
LIECHTENSTEIN_RE = re.compile(r'liechtenstein|vaduz', re.IGNORECASE)

LEDGER_DIR = (
    Path(__file__).resolve().parents[2]
    / 'docs' / 'research' / 'country-code-remap' / 'ledgers'
)


def plan_row(country_code: str, geo_confidence: float | None,
             headline: str | None) -> str | None:
    """Return the corrected ISO code for one candidate row, or None to skip.

    Pure single-hop: the returned code is FINAL. Chains in REMAP are resolved
    by each row moving exactly once from its CURRENT stored code.
    """
    cc = (country_code or '').strip()
    if cc not in REMAP:
        return None
    if geo_confidence is not None and abs(geo_confidence - OVERRIDE_GEO_CONFIDENCE) < 1e-9:
        return None  # outlet-origin override row: ISO already, not FIPS
    if cc == 'LS' and headline and LIECHTENSTEIN_RE.search(headline):
        return 'LI'
    return REMAP[cc]


def build_plan(rows, ledgered_ids: set[int]) -> list[tuple[int, str, str]]:
    """rows: iterable of (id, country_code, geo_confidence, headline).
    Returns [(id, old, new)] with ledgered ids excluded."""
    plan: list[tuple[int, str, str]] = []
    for rid, cc, conf, headline in rows:
        if rid in ledgered_ids:
            continue
        new = plan_row(cc, conf, headline)
        if new is not None and new != cc:
            plan.append((rid, cc.strip(), new))
    return plan


def load_ledgered_ids(ledger_dir: Path) -> set[int]:
    ids: set[int] = set()
    if not ledger_dir.is_dir():
        return ids
    for path in sorted(ledger_dir.glob('*.jsonl')):
        with path.open(encoding='utf-8') as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                rec = json.loads(line)
                if rec.get('type') == 'meta':
                    continue
                ids.add(int(rec['id']))
    return ids


CANDIDATE_SQL = """
    SELECT id, country_code, geo_confidence, headline
    FROM signals_v2
    WHERE source_family = 'gdelt'
      AND country_code = ANY($1::text[])
      AND created_at < $2
"""


async def fetch_candidates(conn, cutoff: datetime):
    return await conn.fetch(CANDIDATE_SQL, list(REMAP.keys()), cutoff)


def summarize(plan) -> dict[tuple[str, str], int]:
    counts: dict[tuple[str, str], int] = {}
    for _rid, old, new in plan:
        counts[(old, new)] = counts.get((old, new), 0) + 1
    return counts


async def apply_plan(conn, plan, ledger_fh=None) -> dict[tuple[str, str], int]:
    """Apply per-group transactions, id-keyed, guarded on the old value.

    signals_v2 is HOT (ingest + NLP fleet hold row locks in long batch
    transactions — a plain guarded UPDATE sat >300s on 19 rows in the first
    prod run), so each group takes only the rows it can lock RIGHT NOW
    (FOR UPDATE SKIP LOCKED) and commits. Locked rows are simply not
    applied and not ledgered; the idempotent re-run picks them up.

    The ledger records ONLY applied ids, appended after each group commits.
    (Crash window between a commit and its append is accepted and tiny;
    an unledgered applied row is only a re-run hazard for chain targets.)
    """
    # Measured on prod (EXPLAIN ANALYZE, 2026-07-28): ~0.5s/row, IO-bound —
    # every touched heap/index page is a cold ~40ms read and country_code
    # updates can't be HOT (it's in 3 indexes), so all ~28 indexes get new
    # entries per row. Chunk small enough that one statement stays well
    # under its timeout, commit per chunk, and keep grinding.
    chunk_size = 50  # 200 hit even a 600s statement_timeout under depleted IO
    applied: dict[tuple[str, str], int] = {}
    groups: dict[tuple[str, str], list[int]] = {}
    for rid, old, new in plan:
        groups.setdefault((old, new), []).append(rid)
    for (old, new), ids in sorted(groups.items()):
        done = 0
        for i in range(0, len(ids), chunk_size):
            chunk = ids[i:i + chunk_size]
            try:
                async with conn.transaction():
                    await conn.execute("SET LOCAL statement_timeout = '600s'")
                    await conn.execute("SET LOCAL lock_timeout = '15s'")
                    rows = await conn.fetch(
                        "UPDATE signals_v2 SET country_code = $1 "
                        "WHERE id IN (SELECT id FROM signals_v2 "
                        "             WHERE id = ANY($2::bigint[]) "
                        "               AND country_code = $3 "
                        "             FOR UPDATE SKIP LOCKED) "
                        "RETURNING id",
                        new, chunk, old,
                    )
            except (asyncpg.QueryCanceledError,
                    asyncpg.LockNotAvailableError) as exc:
                print(f"  chunk {old}->{new} [{i}:{i + len(chunk)}] skipped: "
                      f"{exc.__class__.__name__} (re-run picks it up)",
                      flush=True)
                continue
            done += len(rows)
            if ledger_fh is not None:
                for r in rows:
                    ledger_fh.write(json.dumps(
                        {'id': r['id'], 'old': old, 'new': new}) + '\n')
                ledger_fh.flush()
            print(f"  {old} -> {new}: {done}/{len(ids)}", flush=True)
        applied[(old, new)] = done
    return applied


async def revert(conn, ledger_path: Path) -> dict[tuple[str, str], int]:
    groups: dict[tuple[str, str], list[int]] = {}
    with ledger_path.open(encoding='utf-8') as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            rec = json.loads(line)
            if rec.get('type') == 'meta':
                continue
            groups.setdefault((rec['old'], rec['new']), []).append(int(rec['id']))
    reverted: dict[tuple[str, str], int] = {}
    async with conn.transaction():
        for (old, new), ids in sorted(groups.items()):
            result = await conn.execute(
                "UPDATE signals_v2 SET country_code = $1 "
                "WHERE id = ANY($2::bigint[]) AND country_code = $3",
                old, ids, new,
            )
            reverted[(old, new)] = int(result.split()[-1])
    return reverted


def _print_counts(title: str, counts: dict[tuple[str, str], int]) -> None:
    print(f"\n{title}")
    total = 0
    for (old, new), n in sorted(counts.items(), key=lambda kv: -kv[1]):
        print(f"  {old} -> {new}: {n}")
        total += n
    print(f"  TOTAL: {total}")


async def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    mode = ap.add_mutually_exclusive_group(required=True)
    mode.add_argument('--measure', action='store_true',
                      help='print the plan, write nothing')
    mode.add_argument('--execute', action='store_true',
                      help='write the ledger, then apply the plan')
    mode.add_argument('--revert', metavar='LEDGER',
                      help='revert a previously applied ledger file')
    ap.add_argument('--max-created-at',
                    help='ISO timestamp; only rows created STRICTLY before it '
                         'are touched. REQUIRED for --execute; must not be '
                         'after the country_codes.py fix reached prod ingest.')
    args = ap.parse_args()

    db = os.environ.get('DATABASE_URL')
    if not db:
        print('DATABASE_URL required', file=sys.stderr)
        return 2

    conn = await asyncpg.connect(db)
    try:
        # The candidate fetch scans ~10k rows + headlines; under depleted
        # storage IO (measured 2026-07-28: ~40ms/block cold reads) it can
        # crawl past 5 minutes. Updates set their own tighter LOCAL timeouts.
        await conn.execute("SET statement_timeout = '900s'")

        if args.revert:
            reverted = await revert(conn, Path(args.revert))
            _print_counts('REVERTED', reverted)
            return 0

        if args.max_created_at:
            cutoff = datetime.fromisoformat(args.max_created_at)
            if cutoff.tzinfo is None:
                cutoff = cutoff.replace(tzinfo=timezone.utc)
        elif args.measure:
            cutoff = datetime.now(timezone.utc)
        else:
            print('--execute requires an explicit --max-created-at '
                  '(see module docstring, invariant 3)', file=sys.stderr)
            return 2
        if cutoff > datetime.now(timezone.utc):
            print('--max-created-at is in the future; refusing', file=sys.stderr)
            return 2

        ledgered = load_ledgered_ids(LEDGER_DIR)
        rows = await fetch_candidates(conn, cutoff)
        plan = build_plan(
            ((r['id'], r['country_code'], r['geo_confidence'], r['headline'])
             for r in rows),
            ledgered,
        )
        skipped = len(rows) - len(plan)
        print(f"candidates={len(rows)} planned={len(plan)} "
              f"skipped={skipped} (override/ledgered/liech-split) "
              f"cutoff={cutoff.isoformat()}")
        _print_counts('PLAN', summarize(plan))

        if args.measure:
            return 0

        LEDGER_DIR.mkdir(parents=True, exist_ok=True)
        now = datetime.now(timezone.utc)
        ledger_path = LEDGER_DIR / f"{now.strftime('%Y%m%dT%H%M%SZ')}-remap.jsonl"
        with ledger_path.open('w', encoding='utf-8') as fh:
            fh.write(json.dumps({
                'type': 'meta', 'run_at': now.isoformat(),
                'cutoff': cutoff.isoformat(), 'planned_rows': len(plan),
                'scope': "signals_v2 source_family='gdelt' "
                         f"geo_confidence!={OVERRIDE_GEO_CONFIDENCE}",
            }) + '\n')
            applied = await apply_plan(conn, plan, ledger_fh=fh)
        print(f"ledger written (applied rows only): {ledger_path}")

        _print_counts('APPLIED', applied)
        planned_counts = summarize(plan)
        for key, n in applied.items():
            if n != planned_counts[key]:
                print(f"  note: {key[0]}->{key[1]} applied {n} != planned "
                      f"{planned_counts[key]} (rows locked by a concurrent "
                      f"writer or changed; re-run to pick up the remainder)")

        remaining = await conn.fetch(
            "SELECT country_code, count(*) AS n FROM signals_v2 "
            "WHERE source_family='gdelt' AND country_code = ANY($1::text[]) "
            "GROUP BY 1 ORDER BY 1", list(REMAP.keys()))
        print('\nREMAINING in source buckets (post-cutoff rows + excluded '
              'override rows; shrinks to overrides only once the map fix '
              'deploys and a final sweep runs):')
        for r in remaining:
            print(f"  {r['country_code']}: {r['n']}")
        return 0
    finally:
        await conn.close()


if __name__ == '__main__':
    sys.exit(asyncio.run(main()))

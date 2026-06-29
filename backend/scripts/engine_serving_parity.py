"""Unified Engine F0.3 — serving parity gate (spec 2026-06-29-atlas-unified-engine §10/§11).

Compares the CURRENT atlas-evidence list path (`THREADS_SQL` over
`signal_topic_assignments`) against the UNIFIED read path
(`THREADS_SQL_TOPIC_MEMBERS` over `topic_members`, role='evidence',
engine_version='v1-compat') over the SAME window/filters. The read-flag
(`ATLAS_SERVE_THREADS_FROM_TOPIC_MEMBERS`) is only safe to flip in prod once this
prints ALL PASS — it is the F0.3 acceptance gate AND the seed of the F3 A/B
report (`engine_ab_report.py`).

Read-only. Repeatable. Compares the serving-relevant fields per topic and the
ordered thread_id list (the LIST is what /threads serves; dynamic-topic rows are
NOT compared here — they stay sourced from aggregates either way, spec §10).

Run:  python -m backend.scripts.engine_serving_parity --hours 168
"""
from __future__ import annotations

import argparse
import asyncio
import os
import sys
from typing import Any

import asyncpg

from app.services.thread_intelligence import (
    THREADS_SQL,
    THREADS_SQL_TOPIC_MEMBERS,
    V1_COMPAT_ENGINE_VERSION,
    assemble_thread,
)

# CRITICAL fields — must be byte-exact for the flag to be safe to flip. These are
# what the list endpoint serves and ranks on (set, order, volume, gate counts,
# geo, sources, entities).
_CRITICAL_FIELDS = (
    "signal_count",
    "gated_signal_count",
    "gate_scored_count",
    "source_count",
    "country_count",
    "changed_10h",
    "top_countries",
    "top_country_names",
    "top_sources",
    "top_entities",
)

# COSMETIC near-parity — reported, NOT gated. Documented, bounded, and converging:
#   avg_confidence: topic_members.confidence is REAL (float4); averaging hundreds
#     of rows accumulates ~1e-3 rounding vs the source double. Same member set.
#   related_threads: a top-5 co-occurrence annotation. THREADS_SQL counts it over
#     ALL-TIME signal_topic_assignments; the unified path counts it over the
#     windowed topic_members projection — so it is MORE window-consistent, and the
#     top-5 boundary reshuffles by <=2 chips. Not the served list/order/counts.
_CONFIDENCE_TOL = 0.005


def _related_key(thread: dict[str, Any]) -> list[tuple[str, int]]:
    return sorted(
        (str(r.get("topic")), int(r.get("co_signals") or 0))
        for r in (thread.get("related_threads") or [])
    )


def _quality_lex(thread: dict[str, Any]) -> tuple[int, int]:
    q = thread.get("quality") or {}
    return int(q.get("lex_count") or 0), int(q.get("theme_count") or 0)


async def _fetch(conn: Any, sql: str, args: tuple) -> list[dict[str, Any]]:
    rows = await conn.fetch(sql, *args, timeout=15)
    return [assemble_thread(r) for r in rows]


def _diff_case(current: list[dict], unified: list[dict]) -> tuple[list[str], list[str]]:
    """Returns (critical_problems, cosmetic_notes). The flag gates on critical."""
    critical: list[str] = []
    cosmetic: list[str] = []
    cur_by = {t["thread_id"]: t for t in current}
    uni_by = {t["thread_id"]: t for t in unified}

    only_cur = set(cur_by) - set(uni_by)
    only_uni = set(uni_by) - set(cur_by)
    if only_cur:
        critical.append(f"  threads only in CURRENT ({len(only_cur)}): {sorted(only_cur)[:5]}")
    if only_uni:
        critical.append(f"  threads only in UNIFIED ({len(only_uni)}): {sorted(only_uni)[:5]}")

    # ordered list (what the list endpoint serves)
    cur_order = [t["thread_id"] for t in current]
    uni_order = [t["thread_id"] for t in unified]
    if cur_order != uni_order:
        for i, (a, b) in enumerate(zip(cur_order, uni_order)):
            if a != b:
                critical.append(f"  ORDER diverges at #{i}: current={a} unified={b}")
                break
        if len(cur_order) != len(uni_order):
            critical.append(f"  length differs: current={len(cur_order)} unified={len(uni_order)}")

    for tid in sorted(set(cur_by) & set(uni_by)):
        c, u = cur_by[tid], uni_by[tid]
        for f in _CRITICAL_FIELDS:
            if c.get(f) != u.get(f):
                critical.append(f"  {tid}.{f}: current={c.get(f)!r} unified={u.get(f)!r}")
        if _quality_lex(c) != _quality_lex(u):
            critical.append(f"  {tid}.quality(lex,theme): current={_quality_lex(c)} unified={_quality_lex(u)}")
        cc, uc = round(float(c.get("avg_confidence") or 0), 3), round(float(u.get("avg_confidence") or 0), 3)
        if abs(cc - uc) > _CONFIDENCE_TOL:
            critical.append(f"  {tid}.avg_confidence beyond tol: current={cc} unified={uc}")
        elif cc != uc:
            cosmetic.append(f"  {tid}.avg_confidence (REAL precision): current={cc} unified={uc}")
        if _related_key(c) != _related_key(u):
            cosmetic.append(f"  {tid}.related_threads (window-scoped co-occ): current={_related_key(c)} unified={_related_key(u)}")
    return critical, cosmetic


async def run(hours: int, limit: int) -> int:
    db = os.environ.get("DATABASE_URL")
    if not db:
        print("DATABASE_URL not set", file=sys.stderr)
        return 2
    conn = await asyncpg.connect(db)
    # (label, topic_slug, country_codes)
    cases: list[tuple[str, str | None, list[str] | None]] = [
        ("global", None, None),
        ("country=US", None, ["US"]),
        ("country=CO", None, ["CO"]),
    ]
    # add a real topic_slug case if any exist in-window
    try:
        slug = await conn.fetchval(
            """SELECT at.slug FROM signal_topic_assignments a
               JOIN atlas_topics at ON at.id = a.topic_id
               WHERE a.model_version='theme-hint-lex-v2'
                 AND a.assigned_at >= NOW() - ($1::int * INTERVAL '1 hour')
               GROUP BY at.slug ORDER BY COUNT(*) DESC LIMIT 1""",
            hours,
        )
        if slug:
            cases.append((f"topic={slug}", str(slug), None))
    except Exception as exc:  # noqa: BLE001
        print(f"(could not pick a topic_slug case: {exc})")

    all_pass = True
    cosmetic_total = 0
    try:
        for label, slug, countries in cases:
            current = await _fetch(conn, THREADS_SQL, (hours, limit, slug, countries or None))
            unified = await _fetch(
                conn,
                THREADS_SQL_TOPIC_MEMBERS,
                (hours, limit, slug, countries or None, V1_COMPAT_ENGINE_VERSION),
            )
            critical, cosmetic = _diff_case(current, unified)
            status = "PASS" if not critical else "FAIL"
            if critical:
                all_pass = False
            cosmetic_total += len(cosmetic)
            extra = f" (+{len(cosmetic)} cosmetic)" if cosmetic else ""
            print(f"[{status}] {label}: current={len(current)} unified={len(unified)} threads{extra}")
            for p in critical:
                print(p)
            for p in cosmetic:
                print("  NOTE" + p)
    finally:
        await conn.close()

    print(
        "\n"
        + (
            f"CRITICAL PARITY: ALL PASS — read-flag safe to flip "
            f"({cosmetic_total} cosmetic near-parity notes, documented + non-blocking)"
            if all_pass
            else "CRITICAL PARITY FAILED — do NOT flip the flag"
        )
    )
    return 0 if all_pass else 1


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--hours", type=int, default=168)
    ap.add_argument("--limit", type=int, default=50)
    args = ap.parse_args()
    return asyncio.run(run(args.hours, args.limit))


if __name__ == "__main__":
    raise SystemExit(main())

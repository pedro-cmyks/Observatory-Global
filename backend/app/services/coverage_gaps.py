"""Canonical coverage-gap definition (the "Under the Radar" substrate).

A COVERAGE GAP = an Atlas category that received real signal in the window but
had ZERO rows clear the quality gate — "attention without verified coverage",
the wedge's "what is missing". Honest by construction: a raw-count floor avoids
thin-noise rows, and `gate_pending` (nothing scored yet) is labeled separately
from `none_verified` (scored, none admitted) — never conflated with "rejected".

This module is the ONE definition. Previously the SQL was duplicated in
`routers/briefing.py` (global) and `services/country_edition.py` (country);
both now import from here, as does GET /api/v2/attention/coverage-gaps.
"""
from __future__ import annotations

import logging
import os

logger = logging.getLogger(__name__)

# Global floor: raw >= 20 in the window (thin-noise guard).
GLOBAL_GAP_FLOOR = 20

GLOBAL_GAPS_SQL = """
    SELECT t.slug, t.label,
           COUNT(*)::int AS raw_signals,
           COUNT(*) FILTER (WHERE a.gate_kept)::int AS verified,
           COUNT(*) FILTER (WHERE a.gate_score IS NOT NULL)::int AS scored
    FROM signal_topic_assignments a
    JOIN atlas_topics t ON t.id = a.topic_id
    WHERE a.assigned_at > NOW() - ($1::int * INTERVAL '1 hour')
    GROUP BY t.slug, t.label
    HAVING COUNT(*) >= $2
       AND COUNT(*) FILTER (WHERE a.gate_kept) = 0
    ORDER BY raw_signals DESC
    LIMIT 6
"""

# Country scope adds the signals_v2 join for the country predicate and uses a
# lower floor (per-country volume is smaller than global).
COUNTRY_GAPS_SQL = """
    SELECT t.slug, t.label,
           COUNT(*)::int AS raw_signals,
           COUNT(*) FILTER (WHERE a.gate_kept)::int AS verified,
           COUNT(*) FILTER (WHERE a.gate_score IS NOT NULL)::int AS scored
    FROM signal_topic_assignments a
    JOIN atlas_topics t ON t.id = a.topic_id
    JOIN signals_v2 s ON s.id = a.signal_id
    WHERE a.assigned_at > NOW() - ($1::int * INTERVAL '1 hour')
      AND s.country_code = $2
    GROUP BY t.slug, t.label
    HAVING COUNT(*) >= $3
       AND COUNT(*) FILTER (WHERE a.gate_kept) = 0
    ORDER BY raw_signals DESC
    LIMIT 6
"""

# The strongest rows the ~75%-precision extended model recovers from a gap's raw
# pool — read as leads, never as verified evidence.
EXTENDED_RECEIPTS_SQL = """
    SELECT s.headline, s.source_name AS source,
           s.source_url AS url,
           a.gate_score::float AS gate_score
    FROM signal_topic_assignments a
    JOIN atlas_topics t ON t.id = a.topic_id
    JOIN signals_v2 s ON s.id = a.signal_id
    WHERE t.slug = $1
      AND a.assigned_at > NOW() - ($2::int * INTERVAL '1 hour')
      AND a.gate_score >= $3
    ORDER BY a.gate_score DESC
    LIMIT 40
"""


def country_gap_floor() -> int:
    """Per-country raw floor. Tunable via ATLAS_COUNTRY_GAP_MIN (default 8)."""
    return int(os.getenv("ATLAS_COUNTRY_GAP_MIN", "8"))


def gap_status(scored: int) -> str:
    """`gate_pending` = not yet scored (NOT rejected); else `none_verified`."""
    return "gate_pending" if scored == 0 else "none_verified"


async def attach_extended_receipts(conn, gap_rows: list[dict], hours: int) -> dict[str, list]:
    """Best-effort extended receipts per gap slug, keyed by slug.

    Guarded PER GAP (the delight lesson): one failing query must never blank the
    whole section — a failure just means that gap carries no receipts.
    """
    out: dict[str, list] = {}
    if not gap_rows:
        return out
    from app.routers.themes import _extended_gate_thresholds
    from app.services.gap_receipts import GAP_RECEIPTS_K, pick_extended_receipts

    per_topic_ext, _global_ext = _extended_gate_thresholds()
    for gap_row in gap_rows:
        slug = gap_row["slug"]
        ext_thr = per_topic_ext.get(slug)
        if ext_thr is None:
            continue
        try:
            ext_rows = await conn.fetch(EXTENDED_RECEIPTS_SQL, slug, hours, float(ext_thr))
            out[slug] = pick_extended_receipts(
                [dict(r) for r in ext_rows], float(ext_thr), GAP_RECEIPTS_K
            )
        except Exception:
            logger.exception("gap receipts query failed for %s", slug)
    return out


async def fetch_coverage_gaps(
    conn,
    *,
    hours: int,
    country: str | None = None,
    global_floor: int = GLOBAL_GAP_FLOOR,
    country_floor: int | None = None,
    with_receipts: bool = True,
) -> list[dict]:
    """Assembled coverage gaps for one scope: global (country=None) or country."""
    if country:
        floor = country_gap_floor() if country_floor is None else country_floor
        rows = await conn.fetch(COUNTRY_GAPS_SQL, hours, country, floor)
    else:
        rows = await conn.fetch(GLOBAL_GAPS_SQL, hours, global_floor)

    gaps = [{
        "slug": r["slug"],
        "label": r["label"],
        "raw_signals": r["raw_signals"],
        "verified": r["verified"],
        "scored": r["scored"],
        "status": gap_status(r["scored"]),
        "extended_receipts": [],
    } for r in rows]

    if with_receipts and gaps:
        by_slug = await attach_extended_receipts(conn, gaps, hours)
        for gap in gaps:
            gap["extended_receipts"] = by_slug.get(gap["slug"], [])
    return gaps

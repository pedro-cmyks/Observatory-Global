"""Canonical coverage-gap definition (the "Under the Radar" substrate).

A COVERAGE GAP = an Atlas category that received real signal in the window but
had ZERO rows clear the quality gate — "attention without verified coverage",
the wedge's "what is missing". Honest by construction: a raw-count floor avoids
thin-noise rows, and `gate_pending` (nothing scored yet) is labeled separately
from `none_verified` (scored, none admitted) — never conflated with "rejected".

This module is meant to become the ONE definition. `routers/briefing.py`
(global scope) and `services/country_edition.py` (country scope) currently
duplicate this SQL inline; both are being migrated onto this module, as will
the new GET /api/v2/attention/coverage-gaps endpoint.
"""
from __future__ import annotations

import logging
import os
from typing import Any

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
    """Per-country raw floor. Tunable via ATLAS_COUNTRY_GAP_MIN (default 8).

    A garbage env value must not take down every country request — falls back
    to 8 with a logged warning instead of raising.
    """
    raw = os.getenv("ATLAS_COUNTRY_GAP_MIN", "8")
    try:
        return int(raw)
    except (TypeError, ValueError):
        logger.warning(
            "ATLAS_COUNTRY_GAP_MIN=%r is not a valid int; falling back to 8", raw
        )
        return 8


def gap_status(scored: int) -> str:
    """`gate_pending` = not yet scored (NOT rejected); else `none_verified`."""
    return "gate_pending" if scored == 0 else "none_verified"


async def fetch_extended_receipts_by_slug(
    conn,
    slugs: list[str],
    hours: int,
    *,
    timeout: float | None = None,
) -> dict[str, list[dict[str, Any]]]:
    """Best-effort extended receipts, keyed by gap slug.

    Guarded PER SLUG (the delight lesson): one failing query must never blank
    the whole section — a failure just means that one slug carries no receipts
    while every other slug's lookup proceeds normally. Returns a plain dict;
    the caller (`fetch_coverage_gaps`) does the attaching onto its gap rows.
    """
    out: dict[str, list[dict[str, Any]]] = {}
    if not slugs:
        return out

    # FOLLOW-UP: this loader belongs in app/services/, not app/routers/themes.py
    # — a service reaching into a router inverts the layering. Left as a lazy,
    # in-function import (not module-level) so importing this module never has
    # to pull in themes.py's heavier router import chain. Moving the loader
    # into services/ would remove this lazy import, the layering inversion,
    # and the sys.modules stub the tests use to exercise this path.
    from app.routers.themes import _extended_gate_thresholds
    from app.services.gap_receipts import GAP_RECEIPTS_K, pick_extended_receipts

    per_topic_ext, _global_ext = _extended_gate_thresholds()
    for slug in slugs:
        ext_thr = per_topic_ext.get(slug)
        if ext_thr is None:
            continue
        try:
            ext_rows = await conn.fetch(
                EXTENDED_RECEIPTS_SQL, slug, hours, float(ext_thr), timeout=timeout
            )
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
    floor: int | None = None,
    with_receipts: bool = True,
    timeout: float | None = None,
) -> list[dict[str, Any]]:
    """Assembled coverage gaps for one scope: global or country.

    `country` is normalized here (trimmed + uppercased); `None`, `""`, and
    whitespace-only all resolve to the global scope. `floor` overrides the
    scope's default (GLOBAL_GAP_FLOOR globally, `country_gap_floor()` for a
    country) when explicitly given.

    The primary query is NOT wrapped in try/except and never degrades to an
    empty list on failure — callers must be able to tell "no gaps exist" from
    "the gap query failed" (an empty list read as the former would render a
    false-confident "nothing under the radar"). Pass `timeout` and let the
    caller's own guard (`_fetch_section` in briefing.py, a try/except in the
    endpoint) handle a slow/failing query. Only the per-slug receipts lookup
    below is best-effort.
    """
    cc = (country or "").strip().upper() or None
    eff_floor = (
        floor if floor is not None
        else (country_gap_floor() if cc else GLOBAL_GAP_FLOOR)
    )

    if cc:
        rows = await conn.fetch(COUNTRY_GAPS_SQL, hours, cc, eff_floor, timeout=timeout)
    else:
        rows = await conn.fetch(GLOBAL_GAPS_SQL, hours, eff_floor, timeout=timeout)

    gaps: list[dict[str, Any]] = [{
        "slug": r["slug"],
        "label": r["label"],
        "raw_signals": r["raw_signals"],
        "verified": r["verified"],
        "scored": r["scored"],
        "status": gap_status(r["scored"]),
        "extended_receipts": [],
    } for r in rows]

    if with_receipts and gaps:
        slugs = [g["slug"] for g in gaps]
        by_slug = await fetch_extended_receipts_by_slug(conn, slugs, hours, timeout=timeout)
        for gap in gaps:
            gap["extended_receipts"] = by_slug.get(gap["slug"], [])
    return gaps

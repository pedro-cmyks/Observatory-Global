"""Coverage-gaps endpoint ("Under the Radar" substrate).

GET /api/v2/attention/coverage-gaps[?country=CC&hours=]

Categories with domestic raw signal but zero verified (gate-kept) coverage —
the "what is missing" lens. See `get_coverage_gaps` docstring for the full
status-code contract.

Note: this router used to also serve GET /api/v2/attention/silent-risks (the
Wikipedia-attention-vs-media-coverage detector, #172). That endpoint was
formally closed 2026-07-22 after measurement showed its core signal
(`_INFO_DESERT_FLOOR`) was inverted and its "silence" was largely a lexical-
matcher artifact, not a measured phenomenon (see CLAUDE.md 2026-07-22 and
`docs/research/silent-risk/`). It was returning HTTP 502 in production and has
been removed; this file now serves coverage-gaps only.
"""
from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Query

from app import db
from app.services.coverage_gaps import (
    GLOBAL_GAP_FLOOR,
    country_gap_floor,
    fetch_coverage_gaps,
)

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/api/v2/attention/coverage-gaps")
async def get_coverage_gaps(
    country: str | None = Query(None, pattern=r"^[A-Za-z]{2}$"),
    hours: int = Query(24, ge=1, le=168),
) -> dict:
    """Coverage gaps for one scope — the "Under the Radar" substrate.

    Global (no country) mirrors the Brief's "What is missing"; with a country it
    is the domestic band. Same definition either way (services/coverage_gaps).
    A secondary lens must never 500 the dock, so every failure mode degrades to
    an explicit envelope instead — never a bare empty list a reader could
    mistake for "measured, and there is nothing".

    `status` is the machine-readable contract (branch on this, not on `notes`
    prose — `notes` is human copy only and may change wording):
      - "ok"       — the query ran and returned at least one gap.
      - "empty"    — the query ran cleanly; no category reached the raw-signal
                     floor with zero verified coverage. This is NOT the same
                     claim as "everything with signal cleared the gate" — a
                     category under the floor is simply unmeasured here.
      - "degraded" — the query did not run or failed (db unavailable, timeout,
                     or any other exception); `gaps` is [] but that reflects a
                     failure to measure, not a measured zero.

    `floor` is the raw-signal count a category must clear before it is even
    considered a candidate gap (global vs. country floors differ — see
    services/coverage_gaps) — always present so the frontend can name the
    threshold to the reader instead of guessing.
    """
    cc = country.upper() if country else None
    scope = "country" if cc else "global"
    floor = country_gap_floor() if cc else GLOBAL_GAP_FLOOR
    notes: list[str] = []
    gaps: list[dict] = []
    degraded = False

    if db.pool is None:
        notes.append("database unavailable")
        degraded = True
    else:
        try:
            # One wall-clock budget for the whole request (the primary query
            # plus up to 6 sequential per-slug receipt lookups) — the earlier
            # per-statement `statement_timeout` bounds each query but not the
            # request as a whole, and the pool has no command_timeout, so a
            # network stall would otherwise hang indefinitely on a scarce
            # connection. TimeoutError (raised by asyncio.timeout on expiry)
            # is an OSError subclass, so it lands in the except below.
            async with asyncio.timeout(10):
                async with db.pool.acquire() as conn:
                    await conn.execute("SET statement_timeout = 12000")
                    gaps = await fetch_coverage_gaps(
                        conn, hours=hours, country=cc, timeout=8.0
                    )
        except Exception:
            logger.exception("coverage-gaps query failed scope=%s cc=%s", scope, cc)
            notes.append("coverage gaps temporarily unavailable")
            degraded = True
            # Reset explicitly: a real reachable failure mode is the query
            # succeeding (gaps assigned) and THEN the connection release
            # raising inside __aexit__ (asyncpg terminates + re-raises on a
            # failed reset — a genuine Supabase-pooler-drop mode). Without
            # this, `gaps` would keep its already-assigned value while
            # `status` reports "degraded" — contradicting the docstring's
            # promise that a degraded response always carries `gaps: []`.
            gaps = []

    if degraded:
        status = "degraded"
    elif gaps:
        status = "ok"
    else:
        status = "empty"
        notes.append(
            f"no category reached the {floor}-signal floor with zero verified "
            "coverage in this window"
        )

    return {
        "contract": "coverage-gaps-v0",
        "scope": scope,
        "country": cc,
        "hours": hours,
        "floor": floor,
        "status": status,
        "gaps": gaps,
        "notes": notes,
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }

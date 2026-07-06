"""GET /api/v2/emergent — emergent narrative clusters from the latest snapshot.

The emergent topic discovery layer (spec:
`docs/superpowers/specs/2026-05-29-emergent-topic-discovery-design.md`)
runs HDBSCAN + scope-gate-style precision filter + DeepSeek labeling on
the rolling signal window and writes one row per surviving cluster to
`emergent_clusters` at the configured cadence.

This router exposes the MOST RECENT snapshot's clusters within a window,
sorted by velocity (signal-count delta vs the prior matched snapshot)
with `n_signals` as the tiebreaker. The brief uses this as the "What's
Emerging" lead, parallel to the existing curated Watchlist over
`atlas_topics`.

Degrades to an empty list with `warnings: ["emergent_clusters_missing"]`
if the table is absent (e.g. a deploy that has not yet applied mig 046).
"""
from __future__ import annotations

import os

from fastapi import APIRouter, Header, HTTPException, Query
from app import db

router = APIRouter()


def _require_admin_token(token: str | None) -> None:
    expected = os.getenv("ATLAS_ADMIN_TOKEN")
    if not expected:
        raise HTTPException(status_code=403, detail="admin token not configured")
    if token != expected:
        raise HTTPException(status_code=401, detail="invalid admin token")


@router.get("/api/v2/emergent")
async def get_emergent(
    hours: int = Query(
        24, ge=1, le=168,
        description="Only consider snapshots whose snapshot_at is within this lookback window.",
    ),
    limit: int = Query(
        20, ge=1, le=100,
        description="Top-N clusters to return, sorted by velocity DESC NULLS LAST, n_signals DESC.",
    ),
    x_atlas_admin_token: str | None = Header(default=None, alias="X-Atlas-Admin-Token"),
):
    """Return the most recent emergent snapshot's clusters within `hours`.

    Admin-only: this inspector dumps internal cluster fields (gate thresholds,
    cohesion, vendor agreement, sample signal ids) and no product surface
    consumes it, so it is gated behind the admin token.
    """
    _require_admin_token(x_atlas_admin_token)
    async with db.pool.acquire() as conn:
        has_table = await conn.fetchval(
            "SELECT to_regclass('emergent_clusters') IS NOT NULL"
        )
        if not has_table:
            return {
                "snapshot_at": None,
                "window_hours": hours,
                "clusters": [],
                "warnings": ["emergent_clusters_missing"],
            }

        latest = await conn.fetchrow(
            f"""
            SELECT MAX(snapshot_at) AS snap
            FROM emergent_clusters
            WHERE snapshot_at > NOW() - INTERVAL '{int(hours)} hours'
            """
        )
        snap = latest["snap"] if latest else None
        if snap is None:
            return {
                "snapshot_at": None,
                "window_hours": hours,
                "clusters": [],
                "warnings": [],
            }

        rows = await conn.fetch(
            """
            SELECT
                id,
                snapshot_at,
                snapshot_window_h,
                cluster_id,
                label,
                description,
                raw_signal_count,
                n_signals,
                gate_threshold,
                velocity,
                cohesion,
                top_country_codes,
                sample_signal_ids,
                vendor_agreement
            FROM emergent_clusters
            WHERE snapshot_at = $1
            ORDER BY velocity DESC NULLS LAST, n_signals DESC
            LIMIT $2
            """,
            snap,
            limit,
        )

        clusters = [
            {
                "id": int(r["id"]),
                "cluster_id": int(r["cluster_id"]),
                "label": r["label"],
                "description": r["description"],
                "raw_signal_count": int(r["raw_signal_count"]),
                "n_signals": int(r["n_signals"]),
                "gate_threshold": float(r["gate_threshold"]) if r["gate_threshold"] is not None else None,
                "velocity": int(r["velocity"]) if r["velocity"] is not None else None,
                "cohesion": float(r["cohesion"]) if r["cohesion"] is not None else None,
                "top_country_codes": list(r["top_country_codes"] or []),
                "sample_signal_ids": [int(x) for x in (r["sample_signal_ids"] or [])],
                "vendor_agreement": r["vendor_agreement"],
            }
            for r in rows
        ]

        return {
            "snapshot_at": snap.isoformat(),
            "snapshot_window_hours": int(rows[0]["snapshot_window_h"]) if rows else None,
            "window_hours": hours,
            "clusters": clusters,
            "warnings": [],
        }

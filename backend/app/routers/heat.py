"""
Atlas composite heat endpoint (issue #165, ADR-tier methodology in
docs/methodology/atlas-heat.md).

Reads pre-computed components from the `country_heat_v2` materialised view
shipped by migration 017. The view does all the math; this router only
shapes the response and adds UX warnings.
"""
from __future__ import annotations

import json
import logging
import os
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Header, HTTPException, Query, Request

from app import db

logger = logging.getLogger(__name__)
router = APIRouter()


# Component-driven flags surfaced to the UI.
def _compute_warnings(row: dict[str, Any]) -> list[str]:
    flags: list[str] = []
    if (row.get("local_voice_ratio") or 0.5) < 0.2:
        flags.append("external_coverage")
    if (row.get("source_diversity_norm") or 0) < 0.3:
        flags.append("wire_dominance")
    if (row.get("volume_now") or 0) < 50 and (row.get("geo_confidence_mean") or 1) < 0.7:
        flags.append("thin_coverage")
    if (row.get("polyphony_norm") or 1) < 0.3 and (row.get("volume_now") or 0) > 100:
        flags.append("echo_chamber")
    return flags


def _require_admin_token(token: str | None) -> None:
    expected = os.getenv("ATLAS_ADMIN_TOKEN")
    if not expected:
        raise HTTPException(status_code=403, detail="admin token not configured")
    if token != expected:
        raise HTTPException(status_code=401, detail="invalid admin token")


@router.get("/api/v2/heat/countries")
async def get_country_heat(
    request: Request,
    hours: int = Query(24, ge=1, le=720, description="Time window in hours (v1 supports 24)"),
    limit: int = Query(50, ge=1, le=200),
):
    """Return countries ranked by Atlas composite heat (see methodology doc)."""
    cache_key = f"heat:countries:{hours}:{limit}"
    redis = getattr(request.app.state, "redis", None)
    if redis:
        try:
            cached = await redis.get(cache_key)
            if cached:
                return json.loads(cached)
        except Exception:
            pass

    if hours != 24:
        raise HTTPException(
            status_code=400,
            detail="hours_window=24 only in v1. See issue #165 for additional windows.",
        )

    async with db.pool.acquire() as conn:
        try:
            rows = await conn.fetch(
                """
                SELECT
                    country_code,
                    hours_window,
                    atlas_heat,
                    z_velocity_norm,
                    surprise_kl_norm,
                    source_diversity_norm,
                    local_voice_ratio,
                    polyphony_norm,
                    geo_confidence_mean,
                    duplication_index_norm,
                    volume_now,
                    volume_baseline_daily,
                    refreshed_at
                FROM country_heat_v2
                WHERE hours_window = $1
                ORDER BY atlas_heat DESC NULLS LAST
                LIMIT $2
                """,
                hours,
                limit,
            )
        except Exception as exc:
            logger.exception("country_heat_v2 query failed")
            raise HTTPException(
                status_code=503,
                detail="country_heat_v2 materialised view not available — apply migration 017 and refresh.",
            ) from exc

    items = []
    for row in rows:
        record = dict(row)
        items.append({
            "country_code": record["country_code"],
            "atlas_heat": round(float(record["atlas_heat"]), 3) if record["atlas_heat"] is not None else None,
            "components": {
                "z_velocity": round(float(record["z_velocity_norm"]), 3) if record["z_velocity_norm"] is not None else None,
                "surprise_kl": round(float(record["surprise_kl_norm"]), 3) if record["surprise_kl_norm"] is not None else None,
                "source_diversity": round(float(record["source_diversity_norm"]), 3) if record["source_diversity_norm"] is not None else None,
                "local_voice_ratio": round(float(record["local_voice_ratio"]), 3) if record["local_voice_ratio"] is not None else None,
                "polyphony": round(float(record["polyphony_norm"]), 3) if record["polyphony_norm"] is not None else None,
                "geo_confidence_mean": round(float(record["geo_confidence_mean"]), 3) if record["geo_confidence_mean"] is not None else None,
                "duplication_index": round(float(record["duplication_index_norm"]), 3) if record["duplication_index_norm"] is not None else None,
            },
            "volume_now": int(record["volume_now"] or 0),
            "volume_baseline_daily": (
                round(float(record["volume_baseline_daily"]), 1)
                if record["volume_baseline_daily"] is not None else None
            ),
            "warnings": _compute_warnings(record),
        })

    refreshed_at = max((r["refreshed_at"] for r in rows if r["refreshed_at"]), default=None)
    response = {
        "hours": hours,
        "items": items,
        "refreshed_at": refreshed_at.isoformat() if refreshed_at else datetime.now(timezone.utc).isoformat(),
    }

    if redis:
        try:
            await redis.setex(cache_key, 60, json.dumps(response))
        except Exception:
            pass

    return response


@router.post("/api/v2/heat/countries/refresh")
async def refresh_country_heat(
    x_atlas_admin_token: str | None = Header(default=None, alias="X-Atlas-Admin-Token"),
):
    """Refresh the country_heat_v2 materialised view. Cron + manual analyst trigger."""
    _require_admin_token(x_atlas_admin_token)
    async with db.pool.acquire() as conn:
        try:
            # CONCURRENTLY needs unique index + prior data. Fall back on first run.
            try:
                await conn.execute("REFRESH MATERIALIZED VIEW CONCURRENTLY country_heat_v2")
            except Exception:
                await conn.execute("REFRESH MATERIALIZED VIEW country_heat_v2")
            count = await conn.fetchval("SELECT COUNT(*) FROM country_heat_v2")
        except Exception as exc:
            logger.exception("country_heat_v2 refresh failed")
            raise HTTPException(status_code=500, detail="refresh failed") from exc
    return {"ok": True, "rows": int(count or 0), "refreshed_at": datetime.now(timezone.utc).isoformat()}

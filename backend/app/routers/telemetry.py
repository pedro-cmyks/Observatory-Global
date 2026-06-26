"""Anonymous time-to-value telemetry (master-consolidation T5.1).

One write endpoint. No PII — `session_id` is a random client id. Best-effort by
design: a telemetry failure must NEVER break the product, so DB issues return
accepted=0, not a 500. This is the founder-review's "instrument before you guess"
lever: measure whether users reach a value moment (evidence view / dossier).
"""
from __future__ import annotations

import json
import logging

from fastapi import APIRouter
from pydantic import BaseModel, Field

from app import db

logger = logging.getLogger(__name__)
router = APIRouter()


class TelemetryEvent(BaseModel):
    event: str = Field(..., min_length=1, max_length=64)
    session_id: str | None = Field(None, max_length=64)
    props: dict | None = None


class TelemetryBatch(BaseModel):
    events: list[TelemetryEvent] = Field(..., min_length=1, max_length=50)


@router.post("/api/v2/telemetry", status_code=202)
async def record_telemetry(batch: TelemetryBatch) -> dict:
    if db.pool is None:
        return {"accepted": 0, "degraded": True}
    rows = [
        (e.event, e.session_id, json.dumps(e.props) if e.props else None)
        for e in batch.events
    ]
    try:
        async with db.pool.acquire() as conn:
            await conn.executemany(
                "INSERT INTO telemetry_events (event, session_id, props) "
                "VALUES ($1, $2, $3::jsonb)",
                rows,
            )
    except Exception as exc:  # never break the UI
        logger.warning("telemetry write failed: %s", exc)
        return {"accepted": 0, "degraded": True}
    return {"accepted": len(rows)}
